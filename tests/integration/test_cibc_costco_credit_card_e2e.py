import pytest
from typing import List
from decimal import Decimal
from pathlib import Path

from expense_tracker.parsers.cibc_costco_credit import CIBCCostcoCreditCardParser
from expense_tracker.domain.enums import TransactionType
from expense_tracker.domain.models import Transaction

@pytest.mark.integration
@pytest.mark.cibcCostcoCreditCard 
class TestCIBCCostcoParserFullParse:
    """Integration tests with real PDF"""
    
    def test_parse_complete_statement(self, cibc_costco_parser: CIBCCostcoCreditCardParser, sample_cibc_costco_credit_card_file: Path):
        """Test parsing complete statement"""
        if not sample_cibc_costco_credit_card_file.exists():
            pytest.skip("Sample statement not available")
        
        transactions: List[Transaction] = cibc_costco_parser.parse(sample_cibc_costco_credit_card_file)
        
        # Basic assertions
        assert len(transactions) > 0, "Should have transactions"
        
        # Check we have both credits and debits
        credit_transactions = [t for t in transactions if t.type == TransactionType.CREDIT]
        debit_transactions = [t for t in transactions if t.type == TransactionType.DEBIT]
        
        assert len(credit_transactions) > 0, "Should have credit transactions"
        assert len(debit_transactions) > 0, "Should have debit transactions"
        
        # All transactions should have required fields
        for txn in transactions:
            assert txn.date is not None
            assert txn.description
            assert txn.amount > 0
            assert txn.account == "cibc-costco-credit"
    
    def test_parse_known_totals(self, cibc_costco_parser: CIBCCostcoCreditCardParser, sample_cibc_costco_credit_card_file: Path):
        """Test that parsed totals match expected values"""
        if not sample_cibc_costco_credit_card_file.exists():
            pytest.skip("Sample statement not available")

        transactions = cibc_costco_parser.parse(sample_cibc_costco_credit_card_file)

        # From your statement - only actual payments (not refunds)
        expected_payments = Decimal("4007.62")

        # Filter for actual payments (contain "PAYMENT" in description)
        payments = [
            t for t in transactions
            if t.type == TransactionType.CREDIT and "PAYMENT" in t.description.upper()
        ]
        actual_payments = sum(t.amount for t in payments)

        assert actual_payments == expected_payments
    
    def test_parse_finds_known_transactions(self, cibc_costco_parser: CIBCCostcoCreditCardParser, sample_cibc_costco_credit_card_file: Path):
        """Test that specific known transactions are found"""
        if not sample_cibc_costco_credit_card_file.exists():
            pytest.skip("Sample statement not available")
        
        transactions = cibc_costco_parser.parse(sample_cibc_costco_credit_card_file)
        
        # Look for specific transactions from your statement
        zehrs = [t for t in transactions if "ZEHRS" in t.description]
        costco = [t for t in transactions if "COSTCO" in t.description]
        
        assert len(zehrs) > 0, "Should find ZEHRS transactions"
        assert len(costco) > 0, "Should find COSTCO transactions"


@pytest.mark.unit
@pytest.mark.cibcCostcoCreditCard 
class TestCIBCCostcoParserEdgeCases:
    """Test edge cases and error handling"""
    
    def test_skip_header_lines(self, cibc_costco_parser: CIBCCostcoCreditCardParser):
        """Test that header lines are skipped"""
        headers = [
            "Trans Post",
            "date date Description",
            "Card number 5268 XXXX XXXX 8577",
            "Ý",
        ]
        
        for header in headers:
            assert cibc_costco_parser._should_skip_line(header)
    
    def test_dont_skip_transaction_lines(self, cibc_costco_parser: CIBCCostcoCreditCardParser):
        """Test that valid transaction lines aren't skipped"""
        valid_lines = [
            "Dec 10 Dec 11 ZEHRS KINSVILLE #572 KINGSVILLE ON Retail and Grocery 87.15",
            "Nov 27 Nov 28 PAYMENT THANK YOU/PAIEMENT MERCI 2,933.53",
        ]
        
        for line in valid_lines:
            assert not cibc_costco_parser._should_skip_line(line)
    
    def test_parse_malformed_line_returns_none(self, cibc_costco_parser: CIBCCostcoCreditCardParser):
        """Test that malformed lines return None gracefully"""
        cibc_costco_parser.statement_year = 2025
        
        malformed = [
            "Not a transaction line",
            "Dec 10",  # Missing rest
            "DESCRIPTION ONLY 100.00",  # Missing dates
        ]
        
        for line in malformed:
            result = cibc_costco_parser._parse_charge_line(line)
            assert result is None