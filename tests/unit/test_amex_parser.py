import pytest
import pandas as pd
from datetime import datetime
from pathlib import Path
from decimal import Decimal 
from expense_tracker.parsers.amex_excel import AmexExcelParser
from expense_tracker.domain.enums import TransactionType

@pytest.fixture
def sample_non_amex_file() -> Path:
    """Provide a path from a wrong extension sample Amex file"""
    return Path("tests/fixtures/sample_amex.txt")

@pytest.mark.unit
@pytest.mark.amex 
class TestAmexParserValidation:

    def test_validate_file_does_not_exist(self, parser: AmexExcelParser):
        with pytest.raises(FileNotFoundError):
            parser.validate_file('non_existent.xls')

    def test_validate_file_incorrect_extension(self, parser: AmexExcelParser, sample_non_amex_file: Path):
        with pytest.raises(ValueError, match=f"File must be .xlsx or .xls, got {sample_non_amex_file.suffix}"):
            parser.validate_file(sample_non_amex_file)

    def test_validate_file_no_header(self, parser: AmexExcelParser, sample_invalid_amex_file: Path):
        with pytest.raises(ValueError, match="Could not find a header row in the file"):
            parser.validate_file(sample_invalid_amex_file)

    def test_validate_file_correct(self, parser: AmexExcelParser, sample_amex_file: Path):
        parser.validate_file(sample_amex_file)

@pytest.mark.unit
@pytest.mark.amex 
class TestAmexParserCreditRows:

    def test_parse_credit_refund_transaction(self, parser: AmexExcelParser):
        """Test parsing a grey row refund transaction"""

        # Arrange
        row_data = pd.Series({
            'Date': '12 Dec. 2025',
            'Date Processed': '12 Dec. 2025',
            'Description': pd.NA, # Nan for credit rows
            'Cardmember': '-$24.55', # Amount is here for credits
            'Merchant Address': 'AMZN MKTP CA',
            'Additional Information': None
        })

        # Act
        transaction = parser._parse_row(row_data)

        # Assert
        assert transaction.description == 'AMZN MKTP CA'
        assert transaction.amount == Decimal('24.55')
        assert transaction.type == TransactionType.CREDIT
        assert transaction.account == 'amex'

@pytest.mark.unit
@pytest.mark.amex 
class TestAmexParserDebitRows:

    def test_parse_debit_transaction(self, parser: AmexExcelParser):
        """Test parsing debit transaction"""

        # Arrange
        row_data = pd.Series({
            'Date': '11 Dec. 2025',
            'Amount': '$12.99',
            'Description': 'MEMBERSHIP FEE INSTALLMENT', # Nan for credit rows
            'Cardmember': 'JOHN SMITH', # Amount is here for credits
            'Merchant Address': None,
            'Additional Information': 'MEMBERSHIP FEE INSTALLMENT'
        })

        # Act
        transaction = parser._parse_row(row_data)

        # Assert
        assert transaction.date == datetime.strptime('11-12-2025', '%d-%m-%Y').date()
        assert transaction.description == 'MEMBERSHIP FEE INSTALLMENT'
        assert transaction.amount == Decimal('12.99')
        assert transaction.type == TransactionType.DEBIT
        assert transaction.account == 'amex'
    


    