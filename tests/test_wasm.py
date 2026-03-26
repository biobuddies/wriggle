"""WebAssembly unit tests."""

from wasmtime import Engine, Instance, Module, Store

from wriggle import to_wasm


def test_select_1() -> None:
    store = Store(Engine())
    instance = Instance(store, Module(store.engine, to_wasm('SELECT 1;')), [])
    assert instance.exports(store)['run'](store) == 1
