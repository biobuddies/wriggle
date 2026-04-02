"""Unit test Structured Query Language to WebAssembly integration."""

# pyright: reportAttributeAccessIssue=false, reportCallIssue=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false

from sqlite3 import connect

from wasmtime import Engine, Instance, Module, Store

from wriggle import select, to_wasm


def test_select_integration() -> None:
    store = Store(Engine())
    instance = Instance(store, Module(store.engine, to_wasm(select(7, 1.5, 'hi', -3))), [])
    offsets_lengths = instance.exports(store)['run'](store)
    expressions = [
        instance.exports(store)['memory'].read(store, offset, offset + length).decode()
        for offset, length in zip(offsets_lengths[::2], offsets_lengths[1::2], strict=True)
    ]
    assert connect(':memory:').execute('SELECT ' + ', '.join(expressions)).fetchone() == (
        7,
        1.5,
        'hi',
        -3,
    )
