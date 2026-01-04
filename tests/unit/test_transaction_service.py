import pytest
from datetime import date
from decimal import Decimal
from typing import List
from pathlib import Path

from expense_tracker.domain.models import Transaction
from expense_tracker.domain.enums import TransactionType
from expense_tracker.services.transaction_service import TransactionService
from expense_tracker.services.models import ImportResult, MonthlySummary
from expense_tracker.repositories.base import TransactionRepository

@pytest.fixture
def mock_repository(mocker) -> TransactionRepository:
    """Create a mock repository"""
    return mocker.Mock() # Creates a mock object with no real behaviour

@pytest.fixture
def service(mock_repository) -> TransactionService:
    """Create service with mocked repository"""
    return TransactionService(repository=mock_repository)

@pytest.fixture
def sample_transactions() -> List[Transaction]:
    """Sample transactions for tests"""
    return [
        Transaction(
            date=date(2025, 1, 15),
            description="Coffee Shop",
            amount=Decimal("4.50"),
            type=TransactionType.DEBIT,
            account="amex",
        ),
        Transaction(
            date=date(2025, 1, 16),
            description="Salary",
            amount=Decimal("5000.00"),
            type=TransactionType.CREDIT,
            account="amex",
        ),
    ]

@pytest.mark.unit
class TestTransactionServiceQuery:
    """Test query operations"""
    
    def test_get_transactions_calls_repository(
            self,
            service: TransactionService,
            mock_repository: TransactionRepository,
            sample_transactions: List[Transaction]
    ):
        """Test that get_transactions delegates to repository"""

        # Arrange
        mock_repository.get_all.return_value = sample_transactions
        # Act
        result = service.get_transactions()

        # Assert
        mock_repository.get_all.assert_called_once_with(
            start_date=None,
            end_date=None,
            transaction_type=None,
            account=None
        )
        assert result == sample_transactions
        assert len(result) == 2

    def test_get_transactions_calls_repository_with_filters(
            self,
            service: TransactionService,
            mock_repository: TransactionRepository,
            sample_transactions: List[Transaction]
    ):
        """Test that get_transactions delegates to repository"""

        # Arrange
        mock_repository.get_all.return_value = sample_transactions
        start_date = date(2025, 1, 1)
        end_date = date(2025, 1, 31)
        transaction_type = TransactionType.DEBIT
        account = "amex"

        # Act
        result = service.get_transactions(
            start_date=start_date,
            end_date=end_date,
            transaction_type=transaction_type,
            account=account
        )

        # Assert
        mock_repository.get_all.assert_called_once_with(
            start_date=start_date,
            end_date=end_date,
            transaction_type=transaction_type,
            account=account
        )
        assert result == sample_transactions
        assert len(result) == 2

@pytest.mark.unit
class TestTransactionServiceImport:
    """Test import operations"""

    def test_import_dry_run_doesnt_save(
        self,
        service: TransactionService,
        mock_repository: TransactionRepository,
        sample_transactions: List[Transaction],
        mocker
    ):
        """Test the import doesn't actually save when in dry-run mode"""
        # Arrange
        mock_parser = mocker.Mock()
        mock_parser.parse.return_value = sample_transactions

        mocker.patch(
            'expense_tracker.parsers.factory.ParserFactory.create_parser',
            return_value=mock_parser
        )
        mock_repository.exists.return_value = False

        filepath = Path('sample_statement.xls')
        financial_institution='amex'    

        # Act
        result = service.import_statement(
            filepath=filepath,
            financial_institution=financial_institution,
            dry_run=True
        )

        # Assert
        from expense_tracker.parsers.factory import ParserFactory
        ParserFactory.create_parser.assert_called_once_with(financial_institution)

        mock_parser.parse.assert_called_once_with(filepath)
        mock_repository.exists.assert_called()
        mock_repository.save_many.assert_not_called()
        assert result.total_parsed == 2
        assert result.errors == 0
        assert result.duplicates_skipped == 0
        assert result.new_transactions == 2
        assert result.imported == sample_transactions
        assert result.filepath == str(filepath)
        assert result.financial_institution == financial_institution


    def test_import_statement_success(
            self,
            service: TransactionService,
            mock_repository: TransactionRepository,
            sample_transactions: List[Transaction],
            mocker
    ):
        """Test successful statement import"""

        # Arrange
        mock_parser = mocker.Mock()
        mock_parser.parse.return_value = sample_transactions

        mocker.patch(
            'expense_tracker.parsers.factory.ParserFactory.create_parser',
            return_value=mock_parser
        )

        mock_repository.save_many.return_value = sample_transactions

        filepath = Path('sample_statement.xls')
        financial_institution='amex'

        # Act
        result: ImportResult = service.import_statement(
            filepath=filepath,
            financial_institution=financial_institution
        )

        # Assert
        from expense_tracker.parsers.factory import ParserFactory
        ParserFactory.create_parser.assert_called_once_with(financial_institution)

        mock_parser.parse.assert_called_once_with(filepath)

        mock_repository.save_many.assert_called_once_with(sample_transactions)
        
        assert result.total_parsed == 2
        assert result.errors == 0
        assert result.duplicates_skipped == 0
        assert result.new_transactions == 2
        assert result.imported == sample_transactions
        assert result.filepath == str(filepath)
        assert result.financial_institution == financial_institution


    def test_import_statement_with_duplicates(
            self,
            service: TransactionService,
            mock_repository: TransactionRepository,
            sample_transactions: List[Transaction],
            mocker
    ):
        """Test successful statement import"""

        # Arrange
        mock_parser = mocker.Mock()
        mock_parser.parse.return_value = sample_transactions

        mocker.patch(
            'expense_tracker.parsers.factory.ParserFactory.create_parser',
            return_value=mock_parser
        )

        mock_repository.save_many.return_value = [sample_transactions[0]]

        filepath = Path('sample_statement.xls')
        financial_institution='amex'

        # Act
        result: ImportResult = service.import_statement(
            filepath=filepath,
            financial_institution=financial_institution
        )

        # Assert
        from expense_tracker.parsers.factory import ParserFactory
        ParserFactory.create_parser.assert_called_once_with(financial_institution)

        mock_parser.parse.called_once_with(filepath)

        mock_repository.save_many.assert_called_once_with(sample_transactions)
        
        assert result.total_parsed == 2
        assert result.errors == 0
        assert result.duplicates_skipped == 1
        assert result.new_transactions == 1
        assert result.imported == [sample_transactions[0]]
        assert result.skipped == [sample_transactions[1]]
        assert result.filepath == str(filepath)
        assert result.financial_institution == financial_institution

@pytest.mark.unit
class TestTransactionServiceMonthlySummary:

    def test_get_transactions_for_month(
            self,
            service: TransactionService,
            mock_repository: TransactionRepository,
            sample_transactions: List[Transaction]
    ):
        # Arrange
        mock_repository.get_all.return_value = sample_transactions
        year = 2025
        month = 1

        # Act
        result: MonthlySummary = service.get_monthly_summary(
            year=year,
            month=month,
        )

        # Assert
        start_date = date(year, month, 1)
        end_date = date(year, month, 31) # Jan has 31 days
        
        mock_repository.get_all.assert_called_once_with(
            start_date=start_date,
            end_date=end_date
        )

        assert result.month == month
        assert result.year == year
        assert len(result.credits) == 1
        assert len(result.debits) == 1
        assert result.total_credits == Decimal("5000.00")
        assert result.total_debits == Decimal("4.50")
        assert result.net_flow == Decimal("4995.50")

        
    def test_get_monthly_summary_february_leap_year(
            self,
            service: TransactionService,
            mock_repository,
        ):
            """Test that February in leap year uses correct end date"""
            
            # Arrange
            mock_repository.get_all.return_value = []
            
            # Act
            service.get_monthly_summary(2024, 2)  # 2024 is a leap year
            
            # Assert - February 2024 should have 29 days
            mock_repository.get_all.assert_called_once_with(
                start_date=date(2024, 2, 1),
                end_date=date(2024, 2, 29),
            )
