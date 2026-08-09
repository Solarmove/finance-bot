from decimal import Decimal


def money(value: Decimal, currency: str) -> str:
    return f"{value:,.2f} {currency}".replace(",", " ")
