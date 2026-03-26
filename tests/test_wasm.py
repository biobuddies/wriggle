"""Unit test WebAssembly generation."""

from pytest import mark, raises
from wasmtime import Engine, Instance, Module, Store

from wriggle import to_wasm


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
    offset, length = instance.exports(store)['run'](store)
    assert instance.exports(store)['memory'].read(store, offset, offset + length).decode() == string


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


@mark.parametrize(
    ('integer', 'message'),
    [
        (-9223372036854775809, 'below signed 64-bit minimum -9223372036854775808'),
        (9223372036854775808, 'above signed 64-bit maximum 9223372036854775807'),
    ],
)
def test_select_integer_out_of_signed_64_bit_range(integer: int, message: str) -> None:
    with raises(OverflowError, match=message):
        to_wasm(f'SELECT {integer};')
