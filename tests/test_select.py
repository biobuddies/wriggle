"""Unit test select()."""

from math import copysign

from pytest import mark, raises
from wasmtime import Engine, Instance, Module, Store

from wriggle import current_time_utc, select, to_wasm


VALID_LITERALS = [
    -9223372036854775808,
    0,
    1,
    9223372036854775807,
    -1.5,
    -0.0,
    0.0,
    1.25,
    5e-324,
    1e3,
    1.7976931348623157e308,
    '',
    'hello',
    "it's",
    'μL',
]

INVALID_SELECT_LITERALS = [
    (-9223372036854775809, 'below signed 64-bit minimum -9223372036854775808'),
    (9223372036854775808, 'above signed 64-bit maximum 9223372036854775807'),
    (float('inf'), 'inf outside finite 64-bit float range'),
    (float('-inf'), '-Infinity outside finite 64-bit float range'),
]

INVALID_WASM_QUERIES = [
    ('SELECT 1.7976931348623159e308;', '1.7976931348623159e308 outside finite 64-bit float range'),
    ('SELECT -1.7976931348623159e308;', '-1.7976931348623159e308 outside finite 64-bit float range'),
    (
        'SELECT 1.0000000000000001;',
        '1.0000000000000001 more precise than representable 64-bit float 1.0',
    ),
]


def run_scalar(query: str) -> int | float | str:
    store = Store(Engine())
    instance = Instance(store, Module(store.engine, to_wasm(query)), [])
    result = instance.exports(store)['run'](store)
    if isinstance(result, (tuple, list)):
        offset, length = result
        return instance.exports(store)['memory'].read(store, offset, offset + length).decode()
    return result


@mark.parametrize('literal', VALID_LITERALS)
def test_sql_scalar(literal: int | float | str) -> None:
    assert select(literal) == 'SELECT %s' % (
        "'%s'" % literal.replace("'", "''") if isinstance(literal, str) else literal
    )


def test_sql_variadic_positional_arguments() -> None:
    assert select(7, 1.5, 'hi', -3) == "SELECT 7, 1.5, 'hi', -3"


def test_sql_current_time_utc() -> None:
    assert select(current_time_utc()) == "SELECT STRFTIME('%Y-%m-%d %H:%M:%SZ', 'now')"


def test_sql_no_arguments() -> None:
    with raises(TypeError, match='missing 1 required positional argument: expression'):
        select()  # type: ignore[call-arg]


@mark.parametrize('literal', VALID_LITERALS)
def test_wasm_scalar(literal: int | float | str) -> None:
    result = run_scalar(select(literal))
    if type(literal) is float and literal == 0.0 and copysign(1.0, literal) == -1.0:
        assert isinstance(result, float)
        assert result == 0.0
        assert copysign(1.0, result) == -1.0
        return
    assert result == literal


def test_wasm_select_list() -> None:
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


@mark.parametrize(('literal', 'message'), INVALID_SELECT_LITERALS)
def test_select_rejects_unsupported_literal(literal: int | float, message: str) -> None:
    with raises(OverflowError, match=message):
        select(literal)


@mark.parametrize(('literal', 'message'), INVALID_SELECT_LITERALS)
def test_to_wasm_select_rejects_unsupported_literal(literal: int | float, message: str) -> None:
    with raises(OverflowError, match=message):
        to_wasm(select(literal))


@mark.parametrize(('query', 'message'), INVALID_WASM_QUERIES)
def test_to_wasm_rejects_unsupported_query_literal(query: str, message: str) -> None:
    with raises(OverflowError, match=message):
        to_wasm(query)


def test_to_wasm_rejects_current_time_utc() -> None:
    with raises(
        TypeError,
        match=r"STRFTIME\('%Y-%m-%d %H:%M:%SZ', 'now'\) is not a supported constant SELECT expression",
    ):
        to_wasm(select(current_time_utc()))
