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


def select(expression: int) -> str:
    return f'SELECT {expression};'


def to_wasm(query: str) -> bytes:
    [expression] = parse_one(query, dialect='sqlite').expressions
    return wat2wasm(f'(module (func (export "run") (result i64) i64.const {int(expression)}))')
