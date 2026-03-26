from decimal import Decimal
from math import isfinite

from sqlglot import exp, parse_one
from wasmtime import wat2wasm


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


def select(*expressions: int | float | str) -> str:
    if not expressions:
        raise TypeError('select() missing 1 required positional argument: expression')
    return f"{exp.select(*(exp.convert(expression) for expression in expressions)).sql(dialect='sqlite')};"


def string_bytes(expression: exp.Expression) -> bytes | None:
    if isinstance(expression, exp.Literal) and expression.args['is_string']:
        return expression.this.encode()
    return None


def signed_i64(expression: exp.Expression) -> int:
    integer = int(expression)
    minimum = -9223372036854775808  # signed 64-bit
    maximum = 9223372036854775807  # signed 64-bit
    if minimum <= integer <= maximum:
        return integer
    if integer < minimum:
        raise OverflowError(f'{integer} below signed 64-bit minimum {minimum}')
    raise OverflowError(f'{integer} above signed 64-bit maximum {maximum}')


def finite_f64(expression: exp.Expression) -> float:
    text = expression.sql(dialect='sqlite')
    real = float(expression)
    if isfinite(real):
        if Decimal(text) == Decimal(str(real)):
            return real
        raise OverflowError(f'{text} more precise than representable 64-bit float {real}')
    raise OverflowError(f'{text} outside finite 64-bit float range')


def result_type_value(expression: exp.Expression) -> tuple[str, str] | None:
    encoded = string_bytes(expression)
    if encoded is not None:
        return None
    if isinstance(expression, exp.Literal) and expression.is_int:
        return 'i64', f'i64.const {signed_i64(expression)}'
    if isinstance(expression, exp.Neg) and isinstance(expression.this, exp.Literal) and expression.this.is_int:
        return 'i64', f'i64.const {signed_i64(expression)}'
    return 'f64', f'f64.const {finite_f64(expression)}'


def to_wasm(query: str) -> bytes:
    expressions = parse_one(query, dialect='sqlite').expressions
    data_offset = 0
    data_segments: list[str] = []
    result_types: list[str] = []
    result_values: list[str] = []
    for expression in expressions:
        typed_value = result_type_value(expression)
        if typed_value is not None:
            result_type, result_value = typed_value
            result_types.append(result_type)
            result_values.append(result_value)
            continue
        encoded = string_bytes(expression)
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
