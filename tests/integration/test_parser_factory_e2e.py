import pytest
from pathlib import Path
from expense_tracker.parsers.factory import ParserFactory

@pytest.mark.integration
class TestParserFactoryE2E:

    def test_successful_parser_registration(self, sample_amex_file: Path):
        """Successfully registers the AmexExcelParser with ConfigLoader and a real file is parsed"""
        ParserFactory.load_parsers_from_config()
        
        parser = ParserFactory.create_parser('amex')

        transactions = parser.parse(sample_amex_file)

        # Assert - verify there are transactions
        assert len(transactions) > 0, "Should have at least one transaction"