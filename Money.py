"""Exact money handling.

All amounts are stored as integer pesewas (1 GHS = 100 pesewas), so no
floating-point arithmetic is ever used and nothing is ever rounded.
"""

from decimal import Decimal, InvalidOperation


class MoneyError(ValueError):
    pass


def parse_amount(text) -> int:
    """Convert a string like '50', '50.5' or '50.25' to pesewas.

    Amounts with more than 2 decimal places are rejected rather than rounded.
    Zero and negative amounts are rejected by the caller, not here, so that
    the error message can say what the amount was for.
    """
    try:
        value = Decimal(str(text).strip())
    except InvalidOperation:
        raise MoneyError(f"'{text}' is not a valid amount")
    if not value.is_finite():
        raise MoneyError(f"'{text}' is not a valid amount")
    pesewas = value * 100
    if pesewas != pesewas.to_integral_value():
        raise MoneyError(f"'{text}' has more than 2 decimal places")
    return int(pesewas)


def format_amount(pesewas: int) -> str:
    sign = "-" if pesewas < 0 else ""
    whole, frac = divmod(abs(pesewas), 100)
    return f"{sign}GHS {whole}.{frac:02d}"
