import pytest
from pathlib import Path
from datetime import date
from decimal import Decimal
from pathlib import Path

from expense_tracker.parsers.cibc_costco_credit import CIBCCostcoCreditCardParser
from expense_tracker.domain.enums import TransactionType

@pytest.mark.unit
@pytest.mark.cibcCostcoCreditCard 
class TestCIBCCostcoParserValidation:
    """Test file validation"""
    
    def test_validate_nonexistent_file(self, cibc_costco_parser: CIBCCostcoCreditCardParser):
        """Test validation fails for non-existent file"""
        with pytest.raises(FileNotFoundError):
            cibc_costco_parser.validate_file("nonexistent.pdf")
    
    def test_validate_non_pdf_file(self, cibc_costco_parser: CIBCCostcoCreditCardParser, tmp_path: Path):
        """Test validation fails for non-PDF file"""
        # Create an actual .txt file so it passes the existence check
        txt_file = tmp_path / "statement.txt"
        txt_file.write_text("not a pdf")

        with pytest.raises(ValueError, match="File must be a PDF"):
            cibc_costco_parser.validate_file(str(txt_file))
    
    def test_validate_wrong_statement_type(self, cibc_costco_parser: CIBCCostcoCreditCardParser):
        """Test validation fails for non-CIBC statement"""
        wrong_pdf = Path("tests/fixtures/amex_statement.pdf")
        
        if wrong_pdf.exists():
            with pytest.raises(ValueError, match="Not a CIBC Costco statement"):
                cibc_costco_parser.validate_file(wrong_pdf)
    
    def test_validate_correct_statement(self, cibc_costco_parser: CIBCCostcoCreditCardParser, sample_cibc_costco_credit_card_file: Path):
        """Test validation succeeds for CIBC statement"""
        if sample_cibc_costco_credit_card_file.exists():
            # Should not raise
            cibc_costco_parser.validate_file(sample_cibc_costco_credit_card_file)


@pytest.mark.unit
@pytest.mark.cibcCostcoCreditCard 
class TestCIBCCostcoParserDateParsing:
    """Test date parsing logic"""
    
    def test_parse_date_with_year(self, cibc_costco_parser: CIBCCostcoCreditCardParser):
        """Test parsing date with year set"""
        cibc_costco_parser.statement_year = 2025
        
        result = cibc_costco_parser._parse_date("Dec 10")
        
        assert result == date(2025, 12, 10)
    
    def test_parse_date_different_months(self, cibc_costco_parser: CIBCCostcoCreditCardParser):
        """Test parsing dates from different months"""
        cibc_costco_parser.statement_year = 2025
        
        assert cibc_costco_parser._parse_date("Nov 27") == date(2025, 11, 27)
        assert cibc_costco_parser._parse_date("Dec 5") == date(2025, 12, 5)
        assert cibc_costco_parser._parse_date("Jan 1") == date(2025, 1, 1)
    
    def test_parse_date_no_year(self, cibc_costco_parser: CIBCCostcoCreditCardParser):
        """Test parsing fails gracefully without year"""
        cibc_costco_parser.statement_year = None
        
        result = cibc_costco_parser._parse_date("Dec 10")
        
        assert result is None
    
    def test_parse_date_invalid_format(self, cibc_costco_parser: CIBCCostcoCreditCardParser):
        """Test parsing handles invalid dates"""
        cibc_costco_parser.statement_year = 2025
        
        result = cibc_costco_parser._parse_date("Invalid")
        
        assert result is None


@pytest.mark.unit
@pytest.mark.cibcCostcoCreditCard 
class TestCIBCCostcoParserAmountParsing:
    """Test amount parsing logic"""
    
    def test_parse_simple_amount(self, cibc_costco_parser: CIBCCostcoCreditCardParser):
        """Test parsing simple amount"""
        result = cibc_costco_parser._parse_amount("100.00")
        assert result == Decimal("100.00")
    
    def test_parse_amount_with_comma(self, cibc_costco_parser: CIBCCostcoCreditCardParser):
        """Test parsing amount with comma separator"""
        result = cibc_costco_parser._parse_amount("2,933.53")
        assert result == Decimal("2933.53")
    
    def test_parse_amount_with_dollar_sign(self, cibc_costco_parser: CIBCCostcoCreditCardParser):
        """Test parsing amount with dollar sign"""
        result = cibc_costco_parser._parse_amount("$87.15")
        assert result == Decimal("87.15")
    
    def test_parse_negative_amount(self, cibc_costco_parser: CIBCCostcoCreditCardParser):
        """Test parsing negative amount"""
        result = cibc_costco_parser._parse_amount("-45.19")
        assert result == Decimal("-45.19")
    
    def test_parse_amount_with_all_formatting(self, cibc_costco_parser: CIBCCostcoCreditCardParser):
        """Test parsing amount with multiple formats"""
        result = cibc_costco_parser._parse_amount("$2,933.53")
        assert result == Decimal("2933.53")
    
    def test_parse_invalid_amount(self, cibc_costco_parser: CIBCCostcoCreditCardParser):
        """Test parsing invalid amount raises error"""
        with pytest.raises(ValueError):
            cibc_costco_parser._parse_amount("invalid")


@pytest.mark.unit
@pytest.mark.cibcCostcoCreditCard 
class TestCIBCCostcoParserPaymentLines:
    """Test payment line parsing"""
    
    def test_parse_payment_line(self, cibc_costco_parser: CIBCCostcoCreditCardParser):
        """Test parsing a standard payment line"""
        cibc_costco_parser.statement_year = 2025
        
        line = "Nov 27 Nov 28 PAYMENT THANK YOU/PAIEMENT MERCI 2,933.53"
        
        txn = cibc_costco_parser._parse_payment_line(line)
        
        assert txn is not None
        assert txn.date == date(2025, 11, 27)
        assert "PAYMENT THANK YOU" in txn.description
        assert txn.amount == Decimal("2933.53")
        assert txn.type == TransactionType.CREDIT
        assert txn.account == "cibc-costco-credit"
    
    def test_parse_multiple_payments(self, cibc_costco_parser: CIBCCostcoCreditCardParser):
        """Test parsing multiple payment lines"""
        cibc_costco_parser.statement_year = 2025
        
        lines = [
            "Nov 27 Nov 28 PAYMENT THANK YOU/PAIEMENT MERCI 2,933.53",
            "Dec 05 Dec 08 PAYMENT THANK YOU/PAIEMENT MERCI 554.13",
            "Dec 16 Dec 17 PAYMENT THANK YOU/PAIEMENT MERCI 519.96",
        ]
        
        transactions = [cibc_costco_parser._parse_payment_line(line) for line in lines]
        
        assert all(txn is not None for txn in transactions)
        assert sum(txn.amount for txn in transactions) == Decimal("4007.62")


@pytest.mark.unit
@pytest.mark.cibcCostcoCreditCard 
class TestCIBCCostcoParserChargeLines:
    """Test charge line parsing"""
    
    def test_parse_simple_charge(self, cibc_costco_parser: CIBCCostcoCreditCardParser):
        """Test parsing a simple charge"""
        cibc_costco_parser.statement_year = 2025

        line = "Dec 10 Dec 11 ZEHRS KINSVILLE #572 KINGSVILLE ON Retail and Grocery 87.15"

        txn = cibc_costco_parser._parse_charge_line(line)

        assert txn is not None
        assert txn.date == date(2025, 12, 10)
        assert "ZEHRS KINSVILLE" in txn.description
        assert txn.amount == Decimal("87.15")
        assert txn.type == TransactionType.DEBIT
    
    def test_parse_charge_with_bonus_marker(self, cibc_costco_parser: CIBCCostcoCreditCardParser):
        """Test parsing charge with Ý bonus marker"""
        cibc_costco_parser.statement_year = 2025

        line = "Ý Dec 07 Dec 08 DALDONGNAE 9 MISSISSAUGA ON Restaurants 102.15"

        txn = cibc_costco_parser._parse_charge_line(line)

        assert txn is not None
        assert "DALDONGNAE 9" in txn.description
        assert txn.date == date(2025, 12, 7)
        assert txn.amount == Decimal("102.15")
    
    def test_parse_charge_without_category(self, cibc_costco_parser: CIBCCostcoCreditCardParser):
        """Test parsing charge without category"""
        cibc_costco_parser.statement_year = 2025
        
        line = "Nov 27 Nov 28 STEAMGAMES.COM 4259522 BELLEVUE WA 16.51"
        
        txn = cibc_costco_parser._parse_charge_line(line)
        
        assert txn is not None
        assert txn.category is None
    
    def test_parse_negative_charge_is_credit(self, cibc_costco_parser: CIBCCostcoCreditCardParser):
        """Test that negative charges are credits"""
        cibc_costco_parser.statement_year = 2025
        
        line = "Dec 17 Dec 18 WWW COSTCO CA OTTAWA ON Retail and Grocery -413.24"
        
        txn = cibc_costco_parser._parse_charge_line(line)
        
        assert txn is not None
        assert txn.type == TransactionType.CREDIT
        assert txn.amount == Decimal("413.24")  # Should be positive