"""Unit tests for the smart amount parser."""

from decimal import Decimal
from app.core.parser import parse_amount


def test_standard_numbers():
    assert parse_amount("50000") == Decimal("50000")
    assert parse_amount("50 000") == Decimal("50000")
    assert parse_amount("1 500 000 сум") == Decimal("1500000")
    assert parse_amount("0") is None
    assert parse_amount("-5000") is None
    assert parse_amount("abc") is None


def test_suffixes_thousands():
    assert parse_amount("50k") == Decimal("50000")
    assert parse_amount("50к") == Decimal("50000")
    assert parse_amount("50тыс") == Decimal("50000")
    assert parse_amount("12.5k") == Decimal("12500")
    assert parse_amount("12,5к") == Decimal("12500")


def test_suffixes_millions():
    assert parse_amount("1.5m") == Decimal("1500000")
    assert parse_amount("1.5м") == Decimal("1500000")
    assert parse_amount("2млн") == Decimal("2000000")
    assert parse_amount("0.5m") == Decimal("500000")


def test_math_expressions():
    assert parse_amount("25000+18000") == Decimal("43000")
    assert parse_amount("50k + 20k") == Decimal("70000")
    assert parse_amount("1.5m - 200k") == Decimal("1300000")
    assert parse_amount("10k * 5") == Decimal("50000")
