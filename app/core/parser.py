"""Smart amount parser — converts text, suffixes (k/m), and simple math into Decimal."""

import re
from decimal import Decimal, InvalidOperation


def parse_amount(text: str) -> Decimal | None:
    """Parse user-entered amount supporting:
    - Raw numbers: '50000', '50 000', '50,000', '50.000'
    - Suffixes: '50k', '50к', '50тыс' -> 50 000; '1.5m', '1.5м', '1.5млн' -> 1 500 000
    - Math expressions: '25000+18000', '50k + 20k', '100k - 15k'

    Returns Decimal amount if valid and > 0, else None.
    """
    if not text:
        return None

    cleaned = text.strip().lower()

    # Reject explicitly negative numbers
    if cleaned.startswith("-"):
        return None

    # If simple expression containing +, -, * (with digits on both sides)
    if any(op in cleaned for op in ("+", "-", "*")):
        # Check if it has an operator not at the start
        if any(op in cleaned[1:] for op in ("+", "-", "*")):
            return _eval_simple_math(cleaned)

    return _parse_single_number(cleaned)


def _parse_single_number(token: str) -> Decimal | None:
    """Parse a single token with optional suffix (k, m, etc.)."""
    token = token.replace(" ", "").replace("сум", "").replace("uzs", "").strip()

    # Multiplier suffixes
    multiplier = Decimal("1")

    # Million: 1.5m, 1.5м, 1.5млн
    if re.search(r"(млн|m|м)$", token):
        token = re.sub(r"(млн|m|м)$", "", token)
        multiplier = Decimal("1000000")
    # Thousand: 50k, 50к, 50тыс, 50k
    elif re.search(r"(тыс|k|к)$", token):
        token = re.sub(r"(тыс|k|к)$", "", token)
        multiplier = Decimal("1000")
    # Billion: 1b, 1млрд
    elif re.search(r"(млрд|b|б)$", token):
        token = re.sub(r"(млрд|b|б)$", "", token)
        multiplier = Decimal("1000000000")

    # Replace comma with dot for decimals (1,5m -> 1.5m)
    token = token.replace(",", ".")

    try:
        val = Decimal(token) * multiplier
        if val > Decimal("0"):
            return val.quantize(Decimal("1"))
        return None
    except (InvalidOperation, ValueError):
        return None


def _eval_simple_math(expr: str) -> Decimal | None:
    """Safely evaluate simple arithmetic with suffixes e.g. '50k + 25000'."""
    # Split by operators while keeping them
    tokens = re.split(r"(\+|\-|\*)", expr)
    if not tokens:
        return None

    current_val: Decimal | None = None
    current_op = "+"

    for t in tokens:
        t = t.strip()
        if not t:
            continue
        if t in ("+", "-", "*"):
            current_op = t
        else:
            num = _parse_single_number(t)
            if num is None:
                return None
            if current_val is None:
                current_val = num
            else:
                if current_op == "+":
                    current_val += num
                elif current_op == "-":
                    current_val -= num
                elif current_op == "*":
                    current_val *= num

    if current_val is not None and current_val > Decimal("0"):
        return current_val.quantize(Decimal("1"))
    return None
