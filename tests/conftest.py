import pytest
from pathlib import Path
from expense_tracker.parsers.amex_excel import AmexExcelParser

@pytest.fixture
def parser() -> AmexExcelParser:
    """Create a parser instance for each test"""
    return AmexExcelParser()

@pytest.fixture
def sample_amex_file() -> Path:
    """Provide a path from a sample Amex statement"""
    return Path("tests/fixtures/sample_amex.xls")

@pytest.fixture
def sample_invalid_amex_file() -> Path:
    """Provide a path from an invalid sample Amex statement"""
    return Path("tests/fixtures/sample_invalid_amex.xls")