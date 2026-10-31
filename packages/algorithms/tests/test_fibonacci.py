import pytest
from algorithm_lab.fibonacci import fibonacci
from hypothesis import given
from hypothesis import strategies as st


@pytest.mark.parametrize(
    "n, expected",
    [
        (0, 0),
        (1, 1),
        (2, 1),
        (3, 2),
        (10, 55),
        (20, 6765),
    ],
)
def test_fibonacci(n: int, expected: int) -> None:
    assert fibonacci(n) == expected


@given(st.integers(min_value=-1000, max_value=-1))
def test_fibonacci_negative_input_is_rejected(n: int) -> None:
    with pytest.raises(ValueError):
        fibonacci(n)


@given(st.integers(min_value=2, max_value=100))
def test_recurrence_relation(n: int) -> None:
    assert fibonacci(n) == fibonacci(n - 1) + fibonacci(n - 2)
