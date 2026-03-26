from sqlglot import parse_one
from wasmtime import wat2wasm


def select(expression: int) -> str:
    return f'SELECT {expression};'


def to_wasm(query: str) -> bytes:
    [expression] = parse_one(query, dialect='sqlite').expressions
    return wat2wasm(
        f'(module (func (export "run") (result i64) i64.const {int(expression.this)}))'
    )
