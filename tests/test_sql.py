"""Unit test Structured Query Language generation."""

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
    assert select(7, 'hi', -3) == "SELECT 7, 'hi', -3;"


def test_select_requires_expression() -> None:
    with raises(TypeError, match='missing 1 required positional argument: expression'):
        select()  # type: ignore[call-arg]
