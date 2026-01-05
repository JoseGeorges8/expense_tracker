from pathlib import Path
from typing import Optional, List
from datetime import date
from calendar import monthrange
from expense_tracker.parsers.factory import ParserFactory
from expense_tracker.repositories.base import TransactionRepository
from expense_tracker.domain.enums import TransactionType
from expense_tracker.domain.models import Transaction
from expense_tracker.services.models import ImportResult, MonthlySummary
from expense_tracker.categorization import CategorizationEngine

class TransactionService:

    def __init__(
        self, 
        repository: TransactionRepository, 
        categorization_engine: Optional[CategorizationEngine] = None,
    ):
        self.repository = repository
        self._categorization_engine: Optional[CategorizationEngine] = categorization_engine

    @property
    def categorization_engine(self) -> CategorizationEngine:
        """Lazy-load categorization engine"""
        if self._categorization_engine is None:
            self._categorization_engine = CategorizationEngine()
        return self._categorization_engine

    def import_statement(
        self,
        filepath: Path,
        financial_institution: str,
        dry_run: bool = False,
        categorize: bool = False,
    ) -> ImportResult:
        """
        Import transactions from a statement file
        
        Args:
            filepath: The path to the statement file
            financial_institution: the institution the statement is from
            dry_run: Preview without saving
            categorize: Automatically categorize transactions during import

        Returns:
            An ImportResult.
        """
        parser = ParserFactory.create_parser(financial_institution)
        transactions = parser.parse(filepath)

        if categorize:
            transactions = self.categorization_engine.categorize_many(
                transactions, 
                overwrite=True
            )

        if dry_run:
            # Check duplicates WITHOUT saving
            new_transactions = []
            skipped = []
            for txn in transactions:
                if self.repository.exists(
                    date=txn.date,
                    account=txn.account,
                    description=txn.description,
                    amount=float(txn.amount)
                ):
                    skipped.append(txn)
                else:
                    new_transactions.append(txn)
        else:
            new_transactions = self.repository.save_many(transactions)
            
            # Determining which were skipped
            new_ids = {id(t) for t in new_transactions}
            skipped = [t for t in transactions if id(t) not in new_ids]
    
        return ImportResult(
            total_parsed=len(transactions),
            new_transactions=len(new_transactions),
            duplicates_skipped=len(skipped),
            imported=new_transactions,
            skipped=skipped,
            filepath=str(filepath), 
            financial_institution=financial_institution,
        )

    def get_transactions(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        transaction_type: Optional[TransactionType] = None,
        account: Optional[str] = None,
    ) -> List[Transaction]:
        """
        Query transactions with optional filters.
        
        Args:
            start_date: Include transactions on or after this date
            end_date: Include transactions on or before this date
            transaction_type: Filter by DEBIT or CREDIT
            account: Filter by account identifier (e.g., 'amex', 'chase')
        
        Returns:
            List of transactions matching all provided filters
            
        Example:
            ### Get all January 2025 expenses
            transactions = service.get_transactions(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 31),
                transaction_type=TransactionType.DEBIT
            )
        """
        transactions = self.repository.get_all(
            start_date=start_date,
            end_date=end_date,
            transaction_type=transaction_type,
            account=account
        )
        return transactions

    def get_monthly_summary(
        self, 
        year: int, 
        month: int
    ) -> MonthlySummary:
        """Get summary for a specific month"""
        start_date = date(year, month, 1)
        _, last_day = monthrange(year, month)  # Gets the last day of month
        end_date = date(year, month, last_day)
        
        transactions = self.repository.get_all(
            start_date=start_date,
            end_date=end_date
        )

        debits = [t for t in transactions if t.type == TransactionType.DEBIT]
        credits = [t for t in transactions if t.type == TransactionType.CREDIT]
        
        return MonthlySummary(
            year=year,
            month=month,
            debits=debits,
            credits=credits,
        )
    
    def categorize_transactions(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        overwrite: bool = False
    ) -> int:
        """
        Categorize existing transactions in the database.

        Args:
            start_date: Only categorize transactions on or after this date
            end_date: Only categorize transactions on or before this date
            overwrite: If True, re-categorize already categorized transactions

        Returns:
            Number of transactions categorized

        Example:
                ```
            # Categorize all uncategorized transactions
            count = service.categorize_transactions()
            
            # Re-categorize everything from January
            count = service.categorize_transactions(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 31),
                overwrite=True
            )
            ```
        """

        transactions = self.repository.get_all(
            start_date=start_date,
            end_date=end_date
        )

        if not transactions:
            return 0
            
        
        categorized = self.categorization_engine.categorize_many(
            transactions,
            overwrite=overwrite
        )

        # Filter to only update what needs updating
        to_update = [
            txn for txn in categorized 
            if overwrite or txn.category != "Uncategorized"
        ]

        updated = self.repository.update_many(to_update)

        return len(updated)

        
