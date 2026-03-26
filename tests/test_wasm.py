"""Unit test WebAssembly generation."""

from math import copysign

from pytest import mark, raises
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
    instance = Instance(store, Module(store.engine, to_wasm(f'SELECT {integer};')), [])
    assert instance.exports(store)['run'](store) == integer


@mark.parametrize('real', [-1.5, 0.0, 1.25, 1e3])
def test_select_float(real: float) -> None:
    store = Store(Engine())
    instance = Instance(store, Module(store.engine, to_wasm(f'SELECT {real};')), [])
    assert instance.exports(store)['run'](store) == real


@mark.parametrize(
    ('query', 'real'),
    [
        ('SELECT 5e-324;', 5e-324),
        ('SELECT 1.7976931348623157e308;', 1.7976931348623157e308),
    ],
)
def test_select_float_boundary_values(query: str, real: float) -> None:
    store = Store(Engine())
    instance = Instance(store, Module(store.engine, to_wasm(query)), [])
    assert instance.exports(store)['run'](store) == real


def test_select_negative_zero_float() -> None:
    store = Store(Engine())
    instance = Instance(store, Module(store.engine, to_wasm(select(-0.0))), [])
    assert copysign(1.0, instance.exports(store)['run'](store)) == -1.0


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
    instance = Instance(store, Module(store.engine, to_wasm("SELECT 7, 1.5, 'hi', -3;")), [])
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


@mark.parametrize(
    ('query', 'message'),
    [
        ('SELECT 1.7976931348623159e308;', '1.7976931348623159e308 outside finite 64-bit float range'),
        ('SELECT -1.7976931348623159e308;', '-1.7976931348623159e308 outside finite 64-bit float range'),
        (
            'SELECT 1.0000000000000001;',
            '1.0000000000000001 more precise than representable 64-bit float 1.0',
        ),
    ],
)
def test_select_float_out_of_f64_range(query: str, message: str) -> None:
    with raises(OverflowError, match=message):
        to_wasm(query)


@mark.parametrize('real', [float('inf'), float('-inf')])
def test_select_infinite_float_not_supported(real: float) -> None:
    with raises(TypeError, match='float\\(\\) argument must be a string or a real number, not'):
        to_wasm(select(real))
