"""Unit test Structured Query Language generation."""

from math import inf

from pytest import mark, raises

from wriggle import select


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
    assert select(integer) == f'SELECT {integer};'


@mark.parametrize(
    'real',
    [
        -1.5,
        0.0,
        1.25,
        5e-324,
        1e3,
        1.7976931348623157e308,
    ],
)
def test_select_float(real: float) -> None:
    assert select(real) == f'SELECT {real};'


@mark.parametrize(
    ('real', 'query'),
    [
        (-0.0, 'SELECT -0.0;'),
        (inf, 'SELECT inf;'),
        (-inf, 'SELECT -Infinity;'),
    ],
)
def test_select_weird_float(real: float, query: str) -> None:
    assert select(real) == query


@mark.parametrize(
    'string',
    [
        '',
        'hello',
        "it's",
        'μL',
    ],
)
def test_select_string(string: str) -> None:
    assert select(string) == "SELECT '%s';" % string.replace("'", "''")


def test_select_variadic_positional_arguments() -> None:
    assert select(7, 1.5, 'hi', -3) == "SELECT 7, 1.5, 'hi', -3;"


def test_select_requires_expression() -> None:
    with raises(TypeError, match='missing 1 required positional argument: expression'):
        select()  # type: ignore[call-arg]
