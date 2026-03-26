"""SQL unit tests."""

from wriggle import select


def test_select_1() -> None:
    assert select(1) == 'SELECT 1;'
