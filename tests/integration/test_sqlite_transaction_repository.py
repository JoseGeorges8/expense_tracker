import pytest
from pathlib import Path
from datetime import date
from decimal import Decimal

from expense_tracker.database.connection import DatabaseConfig, DatabaseManager
from expense_tracker.repositories.sqlite_transaction_repository import SQLiteTransactionRepository
from expense_tracker.domain.models import Transaction
from expense_tracker.domain.enums import TransactionType
from expense_tracker.repositories.base import DuplicateTransactionError, TransactionNotFoundError

@pytest.fixture
def test_db(tmp_path):
    """
    Create a real test database.

    Use pytest's tmp_path fixture to create a temporary directory.
    Database is automatically cleaned up after each test.
    """

    db_path = tmp_path / "test.db"
    config = DatabaseConfig(db_path)
    db_manager = DatabaseManager(config)

    schema_path = Path("src/expense_tracker/database/schema.sql")
    with db_manager.transaction() as conn:
        with open(schema_path) as f:
            conn.executescript(f.read())

    yield db_manager

    # Cleanup (pytest does this automatically for tmp_path, but being explicit)
    db_manager.close()

@pytest.fixture
def repo(test_db):
    """Create a repository with a test database."""
    return SQLiteTransactionRepository(test_db)

@pytest.fixture
def sample_transaction():
    """Reusable sample transaction."""
    return Transaction(
        date=date(2025, 1, 15),
        description="Test Purchase",
        amount=Decimal("99.99"),
        type=TransactionType.DEBIT,
        account="test-amex",
        category="Shopping",
    )

@pytest.mark.integration
class TestSQLiteRepository:
    """Test suite for SQLite repository. Uses a real temp db."""

    def test_save_transaction(self, repo: SQLiteTransactionRepository, sample_transaction: Transaction):
        """Test saving creates a record with an ID."""
        # Act
        saved = repo.save(sample_transaction)

        # Assert
        assert saved.id is not None
        assert isinstance(saved.id, int)
        assert saved.id > 0
    
    def test_decimal_precision_preserved(self, repo: SQLiteTransactionRepository, sample_transaction: Transaction):
        # Arrange
        test_amounts = [
            Decimal("99.99"),
            Decimal("0.01"),
            Decimal("1234567.89"),
            Decimal("19.95"),
            Decimal("0.33"),
        ]

        # Multi-Act
        for amount in test_amounts:
            txn = sample_transaction
            txn.amount = amount

            saved = repo.save(txn)
            retrieved = repo.get_by_id(saved.id)

            # Multi-Assert
            assert retrieved.amount == amount, f"Lost precision for {amount}"
            assert isinstance(retrieved.amount, Decimal)

    def test_save_duplicate_raises_error(self, repo: SQLiteTransactionRepository, sample_transaction: Transaction):
        # Arrange
        repo.save(sample_transaction)

        # Act & Assert
        with pytest.raises(DuplicateTransactionError):
            repo.save(sample_transaction)

    def test_save_persists_all_fields(self, repo: SQLiteTransactionRepository, sample_transaction: Transaction):
        """Test all fields are saved correctly."""
        # Act
        saved = repo.save(sample_transaction)
        retrieved = repo.get_by_id(saved.id)

        # Assert
        assert retrieved is not None
        assert retrieved.date == sample_transaction.date
        assert retrieved.description == sample_transaction.description
        assert retrieved.amount == sample_transaction.amount
        assert retrieved.type == sample_transaction.type
        assert retrieved.account == sample_transaction.account
        assert retrieved.category == sample_transaction.category
    
    def test_get_by_id_returns_none_for_missing_id(self, repo: SQLiteTransactionRepository):
        # Act
        result = repo.get_by_id(999)
        assert result is None

    def test_get_all_returns_empty_list_initially(self, repo: SQLiteTransactionRepository):
        # Act
        transactions = repo.get_all()

        # Assert
        assert transactions == []

    def test_get_all_returns_all_transactions(self, repo: SQLiteTransactionRepository):
        # Arrange
        txn_1 = Transaction(
            date=date(2025, 1, 15),
            description="Test Purchase 1",
            amount=Decimal("99.99"),
            type=TransactionType.DEBIT,
            account="test-amex",
            category="Shopping",
        )
        txn_2 = Transaction(
            date=date(2025, 1, 15),
            description="Test Purchase 2",
            amount=Decimal("99.99"),
            type=TransactionType.DEBIT,
            account="test-amex",
            category="Shopping",
        )
        txn_3 = Transaction(
            date=date(2025, 1, 15),
            description="Test Purchase 3",
            amount=Decimal("99.99"),
            type=TransactionType.DEBIT,
            account="test-amex",
            category="Shopping",
        )

        repo.save_many([txn_1, txn_2, txn_3])

        # Act
        all_txns = repo.get_all()

        # Assert
        assert len(all_txns) == 3

    def test_get_all_filters_by_date_range(self, repo: SQLiteTransactionRepository):
        # Arrange
        jan_txn = Transaction(
            date=date(2025, 1, 15),
            description="January",
            amount=Decimal("100.00"),
            type=TransactionType.DEBIT,
            account="test",
        )
        feb_txn = Transaction(
            date=date(2025, 2, 15),
            description="February",
            amount=Decimal("200.00"),
            type=TransactionType.DEBIT,
            account="test",
        )
        
        repo.save(jan_txn)
        repo.save(feb_txn)
        
        # Act
        january_only = repo.get_all(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )
        
        # Assert
        assert len(january_only) == 1
        assert january_only[0].description == "January"

    def test_get_all_filters_by_transaction_type(self, repo: SQLiteTransactionRepository):
        """Test filtering by DEBIT vs CREDIT."""
        # Arrange
        debit = Transaction(
            date=date(2025, 1, 15),
            description="Purchase",
            amount=Decimal("50.00"),
            type=TransactionType.DEBIT,
            account="test",
        )
        credit = Transaction(
            date=date(2025, 1, 16),
            description="Refund",
            amount=Decimal("25.00"),
            type=TransactionType.CREDIT,
            account="test",
        )
        
        repo.save(debit)
        repo.save(credit)
        
        # Act
        debits_only = repo.get_all(transaction_type=TransactionType.DEBIT)
        credits_only = repo.get_all(transaction_type=TransactionType.CREDIT)
        
        # Assert
        assert len(debits_only) == 1
        assert debits_only[0].description == "Purchase"
        assert len(credits_only) == 1
        assert credits_only[0].description == "Refund"
    
    def test_get_all_filters_by_category(self, repo):
        """Test filtering by category."""
        # Arrange
        food = Transaction(
            date=date(2025, 1, 15),
            description="Restaurant",
            amount=Decimal("30.00"),
            type=TransactionType.DEBIT,
            account="test",
            category="Food & Dining",
        )
        shopping = Transaction(
            date=date(2025, 1, 16),
            description="Clothes",
            amount=Decimal("100.00"),
            type=TransactionType.DEBIT,
            account="test",
            category="Shopping",
        )
        
        repo.save(food)
        repo.save(shopping)
        
        # Act
        food_txns = repo.get_all(category="Food & Dining")
        
        # Assert
        assert len(food_txns) == 1
        assert food_txns[0].description == "Restaurant"
    
    def test_get_all_combines_multiple_filters(self, repo: SQLiteTransactionRepository):
        """Test using multiple filters together."""
        # Arrange
        target = Transaction(
            date=date(2025, 1, 15),
            description="Target Transaction",
            amount=Decimal("50.00"),
            type=TransactionType.DEBIT,
            account="test",
            category="Shopping",
        )
        non_target = Transaction(
            date=date(2025, 2, 15),  # Different month
            description="Not This One",
            amount=Decimal("50.00"),
            type=TransactionType.DEBIT,
            account="test",
            category="Shopping",
        )
        
        repo.save(target)
        repo.save(non_target)
        
        # Act
        results = repo.get_all(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            category="Shopping",
            transaction_type=TransactionType.DEBIT,
        )
        
        # Assert
        assert len(results) == 1
        assert results[0].description == "Target Transaction"
    
    def test_update_transaction(self, repo: SQLiteTransactionRepository, sample_transaction: Transaction):
        """Test updating a transaction."""
        # Arrange
        saved = repo.save(sample_transaction)
        original_category = saved.category
        
        # Act
        saved.category = "Updated Category"
        saved.notes = "Added notes"
        updated = repo.update(saved)
        
        # Assert
        assert updated.category == "Updated Category"
        assert updated.notes == "Added notes"
        
        # Verify in database
        retrieved = repo.get_by_id(saved.id)
        assert retrieved.category == "Updated Category"
        assert retrieved.category != original_category
    
    def test_update_nonexistent_transaction_raises_error(self, repo: SQLiteTransactionRepository):
        """Test updating a transaction that doesn't exist."""
        # Arrange
        fake_txn = Transaction(
            id=99999,  # Doesn't exist
            date=date(2025, 1, 15),
            description="Fake",
            amount=Decimal("10.00"),
            type=TransactionType.DEBIT,
            account="test",
        )
        
        # Act & Assert
        with pytest.raises(TransactionNotFoundError):
            repo.update(fake_txn)
    
    def test_delete_transaction(self, repo: SQLiteTransactionRepository, sample_transaction: Transaction):
        """Test deleting a transaction."""
        # Arrange
        saved = repo.save(sample_transaction)
        txn_id = saved.id
        
        # Act
        deleted = repo.delete(txn_id)
        
        # Assert
        assert deleted is True
        assert repo.get_by_id(txn_id) is None
    
    def test_delete_nonexistent_returns_false(self, repo):
        """Test deleting non-existent transaction returns False."""
        deleted = repo.delete(99999)
        assert deleted is False
    
    def test_exists_returns_true_for_duplicate(self, repo: SQLiteTransactionRepository, sample_transaction: Transaction):
        """Test exists() detects duplicates."""
        # Arrange
        repo.save(sample_transaction)
        
        # Act
        exists = repo.exists(
            date=sample_transaction.date,
            description=sample_transaction.description,
            amount=sample_transaction.amount,
            account=sample_transaction.account,
        )
        
        # Assert
        assert exists is True
    
    def test_exists_returns_false_for_new_transaction(self, repo: SQLiteTransactionRepository):
        """Test exists() returns False for new transactions."""
        exists = repo.exists(
            date=date(2025, 1, 15),
            description="Doesn't Exist",
            amount=100.00,
            account="test",
        )
        assert exists is False
    
    def test_save_many_transactions(self, repo: SQLiteTransactionRepository):
        """Test bulk save operation."""
        # Arrange
        transactions = [
            Transaction(
                date=date(2025, 1, i),
                description=f"Transaction {i}",
                amount=Decimal(str(i * 10)),
                type=TransactionType.DEBIT,
                account="test",
            )
            for i in range(1, 6)  # 5 transactions
        ]
        
        # Act
        saved = repo.save_many(transactions)
        
        # Assert
        assert len(saved) == 5
        assert all(txn.id is not None for txn in saved)
    
    def test_save_many_skips_duplicates(self, repo: SQLiteTransactionRepository):
        """Test save_many skips duplicates without error."""
        # Arrange
        txn1 = Transaction(
            date=date(2025, 1, 1),
            description="First",
            amount=Decimal("10.00"),
            type=TransactionType.DEBIT,
            account="test",
        )
        txn2 = Transaction(
            date=date(2025, 1, 2),
            description="Second",
            amount=Decimal("20.00"),
            type=TransactionType.DEBIT,
            account="test",
        )
        
        # Save txn1 first
        repo.save(txn1)
        
        # Act - try to save both (txn1 is duplicate)
        saved = repo.save_many([txn1, txn2])
        
        # Assert - only txn2 should be saved
        assert len(saved) == 1
        assert saved[0].description == "Second"
    
    def test_transactions_ordered_by_date_desc(self, repo: SQLiteTransactionRepository):
        """Test get_all returns newest transactions first."""
        # Arrange
        old = Transaction(
            date=date(2025, 1, 1),
            description="Old",
            amount=Decimal("10.00"),
            type=TransactionType.DEBIT,
            account="test",
        )
        new = Transaction(
            date=date(2025, 1, 31),
            description="New",
            amount=Decimal("10.00"),
            type=TransactionType.DEBIT,
            account="test",
        )
        
        repo.save(old)
        repo.save(new)
        
        # Act
        txns = repo.get_all()
        
        # Assert
        assert txns[0].description == "New"
        assert txns[1].description == "Old"

    