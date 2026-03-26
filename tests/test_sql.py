"""SQL unit tests."""

from pytest import mark, raises

from wriggle import select


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
    assert select(integer) == f'SELECT {integer};'


def test_select_requires_expression() -> None:
    with raises(TypeError, match='missing 1 required positional argument'):
        select()  # type: ignore[call-arg]
