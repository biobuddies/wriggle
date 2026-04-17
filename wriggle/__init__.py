# pyright: reportAny=false, reportArgumentType=false, reportAttributeAccessIssue=false, reportImplicitStringConcatenation=false, reportPrivateImportUsage=false, reportReturnType=false, reportUnknownMemberType=false, reportUnknownVariableType=false

from decimal import Decimal
from math import isfinite

from sqlglot import exp, parse_one
from wasmtime import wat2wasm

type SelectExpression = int | float | str | exp.Expression


def literal_int(self: exp.Literal) -> int:
    if self.args['is_string']:
        raise TypeError(self)
    return int(self.this)


def neg_int(self: exp.Neg) -> int:
    return -int(self.this)


def literal_float(self: exp.Literal) -> float:
    if self.args['is_string']:
        raise TypeError(self)
    return float(self.this)


def neg_float(self: exp.Neg) -> float:
    return -float(self.this)


exp.Literal.__int__ = literal_int
exp.Neg.__int__ = neg_int
exp.Literal.__float__ = literal_float
exp.Neg.__float__ = neg_float


def datez(when: str = 'now') -> exp.Expression:
    return exp.Anonymous(this='STRFTIME', expressions=[exp.convert('%Y-%m-%dZ'), exp.convert(when)])


def timez(when: str = 'now') -> exp.Expression:
    return exp.Anonymous(this='STRFTIME', expressions=[exp.convert('%H:%M:%SZ'), exp.convert(when)])


def datetimez(when: str = 'now') -> exp.Expression:
    return exp.Anonymous(
        this='STRFTIME', expressions=[exp.convert('%Y-%m-%d %H:%M:%SZ'), exp.convert(when)]
    )


def select_expression(expression: SelectExpression) -> exp.Expression:
    if isinstance(expression, exp.Expression):
        return expression
    converted = exp.convert(expression)
    if type(expression) is int:
        signed_i64(converted)  # pyrefly: ignore[bad-argument-type]
    elif type(expression) is float:
        finite_f64(converted)  # pyrefly: ignore[bad-argument-type]
    return converted  # pyrefly: ignore[bad-return]


def select(*expressions: SelectExpression) -> str:
    if not expressions:
        raise TypeError('select() missing 1 required positional argument: expression')
    return exp.select(*(select_expression(expression) for expression in expressions)).sql(
        dialect='sqlite'
    )


def result_bytes(expression: exp.Expression) -> bytes:
    return expression.sql(dialect='sqlite').encode()


def signed_i64(expression: exp.Expression) -> int:
    integer = int(expression)  # pyrefly: ignore[bad-argument-type]
    minimum = -9223372036854775808  # signed 64-bit
    maximum = 9223372036854775807  # signed 64-bit
    if minimum <= integer <= maximum:
        return integer
    if integer < minimum:
        raise OverflowError(f'{integer} below signed 64-bit minimum {minimum}')
    raise OverflowError(f'{integer} above signed 64-bit maximum {maximum}')


def finite_f64(expression: exp.Expression) -> float:
    text = expression.sql(dialect='sqlite')
    real = float(expression)  # pyrefly: ignore[bad-argument-type]
    if isfinite(real):
        if Decimal(text) == Decimal(str(real)):
            return real
        raise OverflowError(f'{text} more precise than representable 64-bit float {real}')
    raise OverflowError(f'{text} outside finite 64-bit float range')


def validate_expression(expression: exp.Expression, query: str) -> None:
    if isinstance(expression, exp.Literal):
        if not expression.args['is_string']:
            signed_i64(expression) if expression.is_int else finite_f64(expression)
        return
    if (
        isinstance(expression, exp.Neg)
        and isinstance(expression.this, exp.Literal)
        and not expression.this.args['is_string']
    ):
        signed_i64(expression) if expression.this.is_int else finite_f64(expression)
        return
    if (
        isinstance(expression, exp.TimeToStr)
        and isinstance(expression.args.get('format'), exp.Literal)
        and expression.args['format'].args['is_string']
        and isinstance(expression.this, exp.TsOrDsToTimestamp)
        and isinstance(expression.this.this, exp.Literal)
        and expression.this.this.args['is_string']
    ):
        return
    raise ValueError(f'potential overwrite forbidden: {query}')


def validate_select(select: exp.Select, query: str) -> None:
    if select.args.get('locks'):
        raise ValueError(f'potential overwrite forbidden: {query}')


def to_wasm(query: str) -> bytearray:
    parsed = parse_one(query, dialect='sqlite')
    if not isinstance(parsed, exp.Select):
        raise ValueError(  # noqa: TRY004
            f'potential overwrite forbidden: {query}'
        )
    validate_select(parsed, query)
    expressions = parsed.expressions
    data_offset = 0
    data_segments: list[str] = []
    result_types: list[str] = []
    result_values: list[str] = []
    for expression in expressions:
        validate_expression(expression, query)
        encoded = result_bytes(expression)
        data_segments.append(
            f'(data (i32.const {data_offset}) "{"".join(f"\\{byte:02x}" for byte in encoded)}")'
        )
        result_types.extend(['i64', 'i64'])
        result_values.extend([f'i64.const {data_offset}', f'i64.const {len(encoded)}'])
        data_offset += len(encoded)
    memory = '(memory (export "memory") 1) ' if data_segments else ''
    results = f'(result {" ".join(result_types)}) ' if result_types else ''
    return wat2wasm(
        f'(module {memory}{" ".join(data_segments)} '
        f'(func (export "run") {results}{" ".join(result_values)}))'
    )
