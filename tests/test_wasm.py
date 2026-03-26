"""WebAssembly unit tests."""

from pytest import mark
from wasmtime import Engine, Instance, Module, Store

from wriggle import to_wasm


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
    instance = Instance(store, Module(store.engine, to_wasm(f'SELECT {integer};')), [])
    assert instance.exports(store)['run'](store) == integer


@mark.parametrize('string', ['', 'hello', "it's", 'μL'])
def test_select_string(string: str) -> None:
    store = Store(Engine())
    instance = Instance(
        store,
        Module(store.engine, to_wasm("SELECT '%s';" % string.replace("'", "''"))),
        [],
    )
    length = instance.exports(store)['run'](store)
    assert instance.exports(store)['memory'].read(store, 0, length).decode() == string


def test_select_variadic_positional_arguments() -> None:
    store = Store(Engine())
    instance = Instance(store, Module(store.engine, to_wasm("SELECT 7, 'hi', -3;")), [])
    integer, string_offset, string_length, negative = instance.exports(store)['run'](store)
    assert integer == 7
    assert (
        instance.exports(store)['memory']
        .read(store, string_offset, string_offset + string_length)
        .decode()
        == 'hi'
    )
    assert negative == -3
