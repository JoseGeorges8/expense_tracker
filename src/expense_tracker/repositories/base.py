from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

from expense_tracker.domain.models import Transaction
from expense_tracker.domain.enums import TransactionType

class DuplicateTransactionError(Exception):
    """Raised when attempting to save a duplicate transaction."""
    pass

class TransactionNotFoundError(Exception):
    """Raised when a transaction cannot be found."""
    pass

class TransactionRepository(ABC):
    """
    Abstract repository for transaction persistence.

    The repository pattern abstracts the data access, making it easy
    to swap storage backends in the future.
    """

    @abstractmethod
    def save(self, transaction: Transaction) -> Transaction:
        """
        Save a transaction to the repository.

        Args:
            transaction: Transaction to save

        Returns:
            Transaction with ID populated

        Raises:
            DuplicateTransactionError: If transaction already exists
        """
        pass

    @abstractmethod
    def save_many(self, transactions: List[Transaction]) -> List[Transaction]:
        """
        Save multiple transactions in a single operation.
        
        Args:
            transactions: List of transactions to save.

        Returns:
            List of saved transactions with IDs
        """
        pass

    @abstractmethod
    def get_by_id(self, transaction_id: int) -> Optional[Transaction]:
        """
        Retrieve a transaction by ID.
        
        Args:
            transaction_id: Transaction ID

        Returns:
            Transaction if found, None otherwise
        """
        pass

    @abstractmethod
    def get_all(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        transaction_type: Optional[TransactionType] = None,
        category: Optional[str] = None,
    ) -> List[Transaction]:
        """
        Retrieve transactions with optional filtering.

        Args:
            start_date: Filter transactions on or after this date
            end_date: Filter transactions on or before this date
            transaction_type: Filter by DEBIT or CREDIT
            category: Filter by category

        Returns:
            List ot matching transactions
        """
        pass

    @abstractmethod
    def update(self, transaction: Transaction) -> Transaction:
        """
        Update an existing transaction.
        
        Args:
            transaction: Transaction with updated values
            
        Returns:
            Updated transaction
            
        Raises:
            TransactionNotFoundError: If transaction doesn't exist
        """
        pass
    
    @abstractmethod
    def delete(self, transaction_id: int) -> bool:
        """
        Delete a transaction by ID.
        
        Args:
            transaction_id: ID of transaction to delete
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    def exists(
        self,
        date: date,
        description: str,
        amount: float,
        account: str,
    ) -> bool:
        """
        Check if a transaction already exists.
        
        Used for deduplication during imports.
        
        Args:
            date: Transaction date
            description: Transaction description
            amount: Transaction amount
            account: Account identifier
            
        Returns:
            True if transaction exists
        """
        pass