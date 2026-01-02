from enum import Enum

class TransactionType(Enum):
    """Represents whether money is coming in or out"""
    DEBIT = "Debit" # out
    CREDIT = "Credit" # in