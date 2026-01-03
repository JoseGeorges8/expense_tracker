from dataclasses import dataclass
from decimal import Decimal
from datetime import date
from typing import Optional
from expense_tracker.domain.enums import TransactionType

@dataclass
class Transaction:
    """Core domain model representing a single transaction"""
    date: date
    description: str
    amount: Decimal
    type: TransactionType
    account: str
    category: Optional[str] = None
    raw_data: Optional[str] = None
    id: Optional[str] = None

    def __hash__(self):
        """Hash for duplicate detection"""
        return hash((self.date, self.description, self.amount, self.type))
    
    @property
    def signed_amount(self):
        """Return amount with sign for net calculations"""
        return self.amount if self.type == TransactionType.CREDIT else -self.amount
    
    def __repr__(self):
        sign = "+" if self.type == TransactionType.CREDIT else "-"
        return f"Transaction({self.date}, {self.description[:30]}, {sign}${self.amount})"