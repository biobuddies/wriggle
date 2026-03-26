"""Unit test Structured Query Language to WebAssembly integration."""
from wasmtime import Engine, Instance, Module, Store

from wriggle import select, to_wasm


def test_select_integration() -> None:
    store = Store(Engine())
    instance = Instance(store, Module(store.engine, to_wasm(select(7, 1.5, 'hi', -3))), [])
    integer, real, string_offset, string_length, negative = instance.exports(store)['run'](store)
    assert integer == 7
    assert real == 1.5
    assert (
        instance.exports(store)['memory']
        .read(store, string_offset, string_offset + string_length)
        .decode()
        == 'hi'
    )
    assert negative == -3
