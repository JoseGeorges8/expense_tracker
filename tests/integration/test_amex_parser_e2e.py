import pytest
from pathlib import Path
from decimal import Decimal
from expense_tracker.parsers.amex_excel import AmexExcelParser
from expense_tracker.domain.enums import TransactionType

@pytest.mark.integration
@pytest.mark.amex 
class TestAmexParserE2E:
    """End-to-end tests with real Excel file"""

    def test_parse_complete_statement(self, amex_parser: AmexExcelParser, sample_amex_file: Path):
        """
        Test parsing a complete Amex statement with mixed transactions.
        
        This is an integration test that:
        - Reads an actual Excel file
        - Parses all rows
        - Validates the complete output
        """
        # Act
        transactions = amex_parser.parse(sample_amex_file)

        # Assert - verify there are transactions
        assert len(transactions) > 0, "Should have at least one transaction"

        debits = [t for t in transactions if t.type == TransactionType.DEBIT]
        credits = [t for t in transactions if t.type == TransactionType.CREDIT]

        assert len(debits) > 0, "Should have at least one debit transaction"
        assert len(credits) > 0, "Should have at least one credit transaction"

        # Assert - verify all the transactions have required data
        for transaction in transactions:
            assert transaction.date is not None, "All transactions must have a date"
            assert transaction.description, "All transactions must have a description"
            assert transaction.amount > 0, "All amounts should be positive"
            assert transaction.account == "amex", "All should be from Amex account"

    def test_parse_statement_with_known_totals(self, amex_parser: AmexExcelParser, sample_amex_file: Path):
        """
        Test that parsed totals match expected values from the statement.
        
        This validates the parser's accuracy end-to-end.
        """
        # Arrange 
        expected_transaction_count = 68
        expected_debit_transaction_count = 59
        expected_credit_transaction_count = 9
        expected_debit_amount = Decimal('3827.15')
        expected_credit_amount = Decimal('2401.42')
       
        # Act
        transactions = amex_parser.parse(sample_amex_file)

        debits = [t for t in transactions if t.type == TransactionType.DEBIT]
        credits = [t for t in transactions if t.type == TransactionType.CREDIT]

        debit_total_amount = sum(debit.amount for debit in debits)
        credit_total_amount = sum(credit.amount for credit in credits)

        # Assert
        assert len(transactions) == expected_transaction_count, f"Transaction count mismatch: expected {expected_transaction_count}, got {len(transactions)}"
        assert len(debits) == expected_debit_transaction_count,  f"Debit count mismatch: expected {expected_debit_transaction_count}, got {len(debits)}"
        assert len(credits) == expected_credit_transaction_count,  f"Credit count mismatch: expected {expected_credit_transaction_count}, got {len(credits)}"
        assert debit_total_amount == expected_debit_amount,  f"Debit amount mismatch: expected {expected_debit_amount}, got {debit_total_amount}"
        assert credit_total_amount == expected_credit_amount,  f"Credit amount mismatch: expected {expected_credit_amount}, got {credit_total_amount}"

    def test_parser_rejects_invalid_file(self, amex_parser: AmexExcelParser, sample_invalid_amex_file: Path):
        """
        Test that parser properly rejects non-Amex files.
        
        This is still integration because it tests file validation.
        """
        # Act & Assert
        with pytest.raises(ValueError):
            amex_parser.parse(sample_invalid_amex_file)
