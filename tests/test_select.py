"""Unit test select()."""

# pyright: reportAny=false, reportAttributeAccessIssue=false, reportCallIssue=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false

from math import copysign
from sqlite3 import connect

from pytest import mark, raises
from wasmtime import Engine, Instance, Module, Store

from wriggle import datetimez, datez, select, timez, to_wasm

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
    # Integer range
    ('SELECT -9223372036854775809;', 'below signed 64-bit minimum -9223372036854775808'),
    ('SELECT 9223372036854775808', 'above signed 64-bit maximum 9223372036854775807'),
    # Float range and precision
    ('SELECT 1.7976931348623159e308', '1.7976931348623159e308 outside finite 64-bit float range'),
    (
        'SELECT -1.7976931348623159e308;',
        '-1.7976931348623159e308 outside finite 64-bit float range',
    ),
    (
        'SELECT 1.0000000000000001;',
        '1.0000000000000001 more precise than representable 64-bit float 1.0',
    ),
]


def run_expressions(query: str) -> list[str]:
    store = Store(Engine())
    instance = Instance(
        store,
        Module(store.engine, to_wasm(query)),  # pyrefly: ignore[bad-argument-type]
        [],
    )
    result = instance.exports(store)['run'](store)  # pyrefly: ignore[not-callable]
    offsets_lengths = result if isinstance(result, (tuple, list)) else [result]
    memory = instance.exports(store)['memory']
    return [
        memory.read(store, offset, offset + length).decode()  # pyrefly: ignore[missing-attribute]
        for offset, length in zip(offsets_lengths[::2], offsets_lengths[1::2], strict=True)
    ]


def execute(query: str) -> tuple[int | float | str, ...]:
    return connect(':memory:').execute(query).fetchone()


def run_scalar(query: str) -> int | float | str:
    return execute('SELECT ' + run_expressions(query)[0])[0]


@mark.parametrize('literal', VALID_LITERALS)
def test_sql_scalar(literal: float | str) -> None:
    assert select(literal) == 'SELECT %s' % (
        "'%s'" % literal.replace("'", "''") if isinstance(literal, str) else literal
    )


def test_sql_variadic_positional_arguments() -> None:
    assert select(7, 1.5, 'hi', -3) == "SELECT 7, 1.5, 'hi', -3"


def test_sql_datez() -> None:
    assert select(datez()) == "SELECT STRFTIME('%Y-%m-%dZ', 'now')"
    assert select(datez('2026-01-01')) == "SELECT STRFTIME('%Y-%m-%dZ', '2026-01-01')"


def test_sql_timez() -> None:
    assert select(timez()) == "SELECT STRFTIME('%H:%M:%SZ', 'now')"
    assert select(timez('2026-01-01')) == "SELECT STRFTIME('%H:%M:%SZ', '2026-01-01')"


def test_sql_datetimez() -> None:
    assert select(datetimez()) == "SELECT STRFTIME('%Y-%m-%d %H:%M:%SZ', 'now')"
    assert select(datetimez('2026-01-01')) == "SELECT STRFTIME('%Y-%m-%d %H:%M:%SZ', '2026-01-01')"


def test_sql_no_arguments() -> None:
    with raises(TypeError, match='missing 1 required positional argument: expression'):
        select()  # type: ignore[call-arg]


@mark.parametrize('literal', VALID_LITERALS)
def test_wasm_scalar(literal: float | str) -> None:
    result = run_scalar(select(literal))
    if type(literal) is float and literal == 0.0 and copysign(1.0, literal) == -1.0:
        assert isinstance(result, float)
        assert result == 0.0
        assert copysign(1.0, result) == -1.0
        return
    assert result == literal


def test_wasm_select_list() -> None:
    assert execute('SELECT ' + ', '.join(run_expressions("SELECT 7, 1.5, 'hi', -3;"))) == (
        7,
        1.5,
        'hi',
        -3,
    )


@mark.parametrize(('literal', 'message'), INVALID_SELECT_LITERALS)
def test_select_rejects_unsupported_literal(literal: float, message: str) -> None:
    with raises(OverflowError, match=message):
        select(literal)


@mark.parametrize(('query', 'message'), INVALID_WASM_QUERIES)
def test_wasm_rejects_unsupported_query_literal(query: str, message: str) -> None:
    with raises(OverflowError, match=message):
        to_wasm(query)


def test_wasm_forbids_overwrites() -> None:
    with raises(
        ValueError,
        match=(
            r'potential overwrite forbidden: UPDATE measurements SET recorded_at = '
            r"'2026-01-01 00:00:00Z'"
        ),
    ):
        to_wasm("UPDATE measurements SET recorded_at = '2026-01-01 00:00:00Z'")
    with raises(
        ValueError,
        match=r'potential overwrite forbidden: SELECT recorded_at FROM measurements FOR UPDATE',
    ):
        to_wasm('SELECT recorded_at FROM measurements FOR UPDATE')
    with raises(
        ValueError, match=r"potential overwrite forbidden: SELECT load_extension\('eval'\)"
    ):
        to_wasm("SELECT load_extension('eval')")


def test_wasm_datez() -> None:
    assert (
        run_scalar("SELECT STRFTIME('%Y-%m-%dZ', 'now')")
        == execute("SELECT STRFTIME('%Y-%m-%dZ', 'now')")[0]
    )


def test_wasm_timez() -> None:
    assert (
        run_scalar("SELECT STRFTIME('%H:%M:%SZ', 'now')")
        == execute("SELECT STRFTIME('%H:%M:%SZ', 'now')")[0]
    )


def test_wasm_datetimez() -> None:
    assert (
        run_scalar("SELECT STRFTIME('%Y-%m-%d %H:%M:%SZ', 'now')")
        == execute("SELECT STRFTIME('%Y-%m-%d %H:%M:%SZ', 'now')")[0]
    )
