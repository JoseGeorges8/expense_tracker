"""
Service layer models - DTOs for service operations.

These models represent the results of service operations, not domain entities.
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import List
from expense_tracker.domain.models import Transaction

@dataclass
class ImportResult:
    """
    Result of importing a statement file.
    
    Provides detailed feedback about what happened during import:
    - How many transactions were processed
    - Which ones were new vs duplicates
    - Any errors encountered
    """
    total_parsed: int
    new_transactions: int
    duplicates_skipped: int
    errors: int = 0

    imported: List[Transaction] = field(default_factory=List)
    skipped: List[Transaction] = field(default_factory=List)
    error_messages: List[str] = field(default_factory=list)

    filepath: str = ""
    financial_institution: str = ""

    @property
    def success(self) -> bool:
        """Import is successful if at least one transaction is imported"""
        return self.new_transactions > 0
    
    @property
    def partial_success(self) -> bool:
        """Some transactions imported but some failed"""
        return self.new_transactions > 0 and self.errors > 0
    
    def __str__(self) -> str:
        "Human-readable summary"
        lines = [
            f"Import summary for {self.financial_institution}:",
            f" 📄 File: {self.filepath}",
            f" ✅ New transactions: {self.new_transactions}",
            f" ⏭️ Duplicates Skipped: {self.duplicates_skipped}"
        ]

        if self.errors:
            lines.append(f"  ❌ Errors: {self.errors}")

        return "\n".join(lines)
    
    def __post_init__(self):
        """Validate counts match lists"""
        if self.new_transactions != len(self.imported):
            raise ValueError(
                f"Count mismatch: new_transactions={self.new_transactions} "
                f"but len(imported)={len(self.imported)}"
            )
        if self.duplicates_skipped != len(self.skipped):
            raise ValueError(
                f"Count mismatch: duplicates_skipped={self.duplicates_skipped} "
                f"but len(skipped)={len(self.skipped)}"
            )

@dataclass
class MonthlySummary:
    """
    Summary of transactions for a specific month.
    
    Aggregates income, expenses, and net flow for reporting.
    """

    year: int
    month: int

    debits: List[Transaction] = field(default_factory=List)
    credits: List[Transaction] = field(default_factory=List)

    @property
    def start_date(self) -> date:
        """First day of the month"""
        return date(self.year, self.month, 1)
    
    @property
    def total_debits(self) -> Decimal:
        """Total amount spent (outgoing)"""
        return sum(t.amount for t in self.debits)
    
    @property
    def total_credits(self) -> Decimal:
        """Total amount received (incoming)"""
        return sum(t.amount for t in self.credits)
    
    @property
    def net_flow(self) -> Decimal:
        """Net cash flow (credits - debits)"""
        return self.total_credits - self.total_debits

    @property
    def total_transactions(self) -> int:
        return len(self.debits) + len(self.credits)

    @property
    def top_spending_categories(self) -> List[tuple[str, Decimal]]:
        """Categories sorted by spending amount (descending)"""
        return sorted(
            self.debit_by_category.items(),
            key=lambda x: x[1],
            reverse=True
        )

    @property
    def debits_by_category(self) -> dict[str, Decimal]:
        """Calculate credit totals by category"""
        from collections import defaultdict
        totals = defaultdict(Decimal)
        for txn in self.debits:
            category = txn.category or "Uncategorized"
            totals[category] += txn.amount
        return dict(totals)

    @property
    def credits_by_category(self) -> dict[str, Decimal]:
        """Calculate credit totals by category"""
        from collections import defaultdict
        totals = defaultdict(Decimal)
        for txn in self.credits:
            category = txn.category or "Uncategorized"
            totals[category] += txn.amount
        return dict(totals)
    
    def __str__(self) -> str:
        """Human-readable summary"""
        month_name = date(self.year, self.month, 1).strftime("%B %Y")
        
        lines = [
            f"📊 Monthly Summary - {month_name}",
            f"",
            f"Transactions: {self.transaction_count}",
            f"  💸 Debits:  ${self.total_debits:,.2f} ({len(self.debits)} transactions)",
            f"  💰 Credits: ${self.total_credits:,.2f} ({len(self.credits)} transactions)",
            f"  {'📈' if self.net_flow >= 0 else '📉'} Net:     ${self.net_flow:,.2f}",
        ]
        
        if self.debit_by_category:
            lines.append(f"\nTop Spending Categories:")
            for category, amount in self.top_spending_categories[:5]:
                lines.append(f"  • {category}: ${amount:,.2f}")
        
        return "\n".join(lines)