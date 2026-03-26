"""Integration tests."""

from pytest import mark
from wasmtime import Engine, Instance, Module, Store

from wriggle import select, to_wasm


@mark.parametrize(
    'integer',
    [
        -9223372036854775807,  # 1 - 2**63
        0,
        1,
        9223372036854775807,  # 2**63 - 1
    ],
)
def test_select_integer(integer: int) -> None:
    store = Store(Engine())
    instance = Instance(store, Module(store.engine, to_wasm(select(integer))), [])
    assert instance.exports(store)['run'](store) == integer
