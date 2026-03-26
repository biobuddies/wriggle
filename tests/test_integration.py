"""Unit test Structured Query Language to WebAssembly integration."""

from pytest import mark
from wasmtime import Engine, Instance, Module, Store

from wriggle import select, to_wasm


@mark.parametrize(
    'integer',
    [
        -9223372036854775808,  # -2**63
        0,
        1,
        9223372036854775807,  # 2**63 - 1
    ],
)
def test_select_integer(integer: int) -> None:
    store = Store(Engine())
    instance = Instance(store, Module(store.engine, to_wasm(select(integer))), [])
    assert instance.exports(store)['run'](store) == integer


@mark.parametrize('string', ['', 'hello', "it's", 'μL'])
def test_select_string(string: str) -> None:
    store = Store(Engine())
    instance = Instance(store, Module(store.engine, to_wasm(select(string))), [])
    offset, length = instance.exports(store)['run'](store)
    assert instance.exports(store)['memory'].read(store, offset, offset + length).decode() == string


def test_select_variadic_positional_arguments() -> None:
    store = Store(Engine())
    instance = Instance(store, Module(store.engine, to_wasm(select(7, 'hi', -3))), [])
    integer, string_offset, string_length, negative = instance.exports(store)['run'](store)
    assert integer == 7
    assert (
        instance.exports(store)['memory']
        .read(store, string_offset, string_offset + string_length)
        .decode()
        == 'hi'
    )
    assert negative == -3
