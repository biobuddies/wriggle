from sqlglot import exp, parse_one
from wasmtime import wat2wasm


def literal_int(self: exp.Literal) -> int:
    if self.args['is_string']:
        raise TypeError(self)
    return int(self.this)


def neg_int(self: exp.Neg) -> int:
    return -int(self.this)


exp.Literal.__int__ = literal_int
exp.Neg.__int__ = neg_int


def select(*expressions: int | str) -> str:
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


def to_wasm(query: str) -> bytes:
    expressions = parse_one(query, dialect='sqlite').expressions
    data_offset = 0
    data_segments: list[str] = []
    result_types: list[str] = []
    result_values: list[str] = []
    for expression in expressions:
        encoded = string_bytes(expression)
        if encoded is None:
            result_types.append('i64')
            result_values.append(f'i64.const {signed_i64(expression)}')
            continue
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
