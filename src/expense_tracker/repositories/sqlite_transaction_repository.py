import json
import sqlite3
from datetime import date
from decimal import Decimal
from typing import List, Optional

from expense_tracker.database.connection import DatabaseManager
from expense_tracker.domain.models import Transaction
from expense_tracker.domain.enums import TransactionType
from expense_tracker.repositories.base import TransactionRepository, DuplicateTransactionError, TransactionNotFoundError

class SQLiteTransactionRepository(TransactionRepository):
    """
    SQLite implementation of the TransactionRepository.

    Handles all database operations for transactions using raw SQL.
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def save(self, transaction: Transaction) -> Transaction:
        """Save a single transaction."""

        # Check for duplicates
        if self.exists(
            transaction.date,
            transaction.description,
            transaction.amount,
            transaction.account
        ):
            raise DuplicateTransactionError(
                f"Transaction already exists: {transaction.description} ({transaction.amount})"
                f"on {transaction.date}"
            )
        
        # Convert transaction to database row
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO transactions (
                    date, description, amount, type, account,
                    category, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    transaction.date,
                    transaction.description,
                    str(transaction.amount), # Store as string for precision
                    transaction.type.value,
                    transaction.account,
                    transaction.category,
                    json.dumps(transaction.raw_data) if transaction.raw_data else None,
                ),
            )

            transaction.id = cursor.lastrowid

        return transaction
    
    def save_many(self, transactions: List[Transaction]) -> List[Transaction]:
        """Save multiple transactions efficiently"""
        saved = []

        with self.db.transaction() as conn:
            for txn in transactions:
                if self.exists(txn.date, txn.description, txn.amount, txn.account):
                    continue

                cursor = conn.execute(
                     """
                    INSERT INTO transactions (
                        date, description, amount, type, account,
                        category, raw_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        txn.date,
                        txn.description,
                        str(txn.amount),
                        txn.type.value,
                        txn.account,
                        txn.category,
                        json.dumps(txn.raw_data) if txn.raw_data else None,
                    ),
                )
                txn.id = cursor.lastrowid
                saved.append(txn)

        return saved
    
    def get_by_id(self, transaction_id: int) -> Optional[Transaction]:
        """Retrieve a transaction by ID, or None if it doesn't exist"""
        conn = self.db.get_connection()
        cursor = conn.execute(
            "SELECT * FROM transactions WHERE id = ?",
            (transaction_id,)
        )
        row = cursor.fetchone()

        if row is None:
            return None
        
        return self._row_to_transaction(row)
    
    def get_all(
            self, 
            start_date: Optional[date] = None, 
            end_date: Optional[date] = None, 
            transaction_type: TransactionType = None, 
            category: str = None
    ) -> List[Transaction]:
        """Retrieve transactions with optional filtering."""
        query = "SELECT * FROM transactions WHERE 1=1"
        params = []

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        if transaction_type:
            query += " AND type = ?"
            params.append(transaction_type.value)

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY date DESC"

        conn = self.db.get_connection()
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        return [self._row_to_transaction(row) for row in rows]
    
    def update(self, transaction: Transaction) -> Transaction:
        """Update an existing transaction."""
        if transaction.id is None:
            raise ValueError("Cannot update transaction without ID")
        
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                UPDATE transactions
                SET description = ?, amount = ?, type = ?,
                    category = ?
                WHERE id = ?
                """,
                (
                    transaction.description,
                    str(transaction.amount),
                    transaction.type.value,
                    transaction.category,
                    transaction.id,
                )
            )

            if cursor.rowcount == 0:
                raise TransactionNotFoundError(
                    f"Transaction with ID {transaction.id} not found"
                )
            
        return transaction
    
    def delete(self, transaction_id: int) -> bool:
        """Delete a transaction by ID."""
        with self.db.transaction() as conn:
            cursor = conn.execute(
                "DELETE FROM transactions WHERE id = ?",
                (transaction_id,)
            )
            return cursor.rowcount > 0
        
    def exists(
            self, 
            date: date, 
            description: str, 
            amount: Decimal,
            account: str,
        ) -> bool:
        """Check if a transaction exists for deduplication"""
        conn = self.db.get_connection()
        cursor = conn.execute(
            """
            SELECT 1 FROM transactions
            WHERE date = ? AND description = ? AND amount = ? AND account = ?
            """,
            (date, description, str(amount), account),
        )
        return cursor.fetchone() is not None
    
    def _row_to_transaction(self, row: sqlite3.Row) -> Transaction:
        """Convert database row to Transaction object."""
        return Transaction(
            id=row["id"],
            date=row["date"],
            description=row["description"],
            amount=Decimal(row["amount"]),
            type=TransactionType(row["type"]),
            account=row["account"],
            category=row["category"] or "Uncategorized",
            raw_data=json.loads(row["raw_data"]) if row["raw_data"] else None,
        )