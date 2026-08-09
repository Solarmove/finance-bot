from enum import StrEnum


class TransactionKind(StrEnum):
    EXPENSE = "expense"
    INCOME = "income"


class TransactionSource(StrEnum):
    TELEGRAM = "telegram"
    API = "api"
