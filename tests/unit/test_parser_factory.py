import pytest
from expense_tracker.parsers.factory import ParserFactory
from expense_tracker.parsers.amex_excel import AmexExcelParser

@pytest.mark.unit
class TestParserFactoryConfig:

    def setup_method(self):
        """Clear registry before each test"""
        ParserFactory._registry = {}
        ParserFactory._locked = False


    def test_load_parsers_from_custom_config(self):
        """Test loading parsers with injected config (no file I/O)"""

        # Arrange
        test_config =   {
            "parsers": [
                {
                    "financial_institution": "amex",
                    "class": "expense_tracker.parsers.amex_excel.AmexExcelParser",
                    "extensions": [".xlsx", ".xls"]
                }
            ]
        }

        # Act
        ParserFactory.load_parsers_from_config(config=test_config)

        # Assert
        assert "amex" in ParserFactory._registry
        assert ParserFactory._registry["amex"] == AmexExcelParser
        assert ParserFactory._locked is True

    def test_load_parsers_with_invalid_module_path(self):
        """Test error handling for invalid parser class"""
        test_config = {
            "parsers": [
                {
                    "bank": "fake",
                    "class": "nonexistent.module.FakeParser"
                }
            ]
        }
        
        with pytest.raises(ModuleNotFoundError):
            ParserFactory.load_parsers_from_config(config=test_config)

    def test_load_parsers_with_malformed_config(self):
        """Test handling of malformed config"""
        bad_config = {
            "parsers": [
                {
                    "bank": "amex"
                    # Missing 'class' key!
                }
            ]
        }
        
        with pytest.raises(KeyError):
            ParserFactory.load_parsers_from_config(config=bad_config)

@pytest.mark.unit
class TestParserFactorRegistry:

    def setup_method(self):
        """Clear registry before each test"""
        ParserFactory._registry = {}
        ParserFactory._locked = False

    def test_successful_registry(self):
        ParserFactory.register('amex', AmexExcelParser)

        assert "amex" in ParserFactory._registry
        assert ParserFactory._registry["amex"] == AmexExcelParser
        assert ParserFactory._locked is False

    def test_failure_register_after_lock(self):
        ParserFactory.lock_registry()

        with pytest.raises(RuntimeError):
            ParserFactory.register('amex', AmexExcelParser)

    def test_failure_register_with_same_parser(self):
        ParserFactory.register('amex', AmexExcelParser)

        with pytest.raises(ValueError):
            ParserFactory.register('amex', AmexExcelParser)

    def test_failure_register_with_invalid_parser(self):
        with pytest.raises(TypeError):
            ParserFactory.register('amex', ParserFactory) # Any class thats not a StatementParser

@pytest.mark.unit
class TestParserFactoryCreateParser:

    def setup_method(self):
        """Clear registry before each test"""
        ParserFactory._registry = {}
        ParserFactory._locked = False

    def test_succesful_parser_creation(self):
        ParserFactory.register('amex', AmexExcelParser)
        parser = ParserFactory.create_parser('amex')

        assert parser.__class__ is AmexExcelParser

    def test_failure_on_unregistered_parser(self):
        with pytest.raises(ValueError):
            ParserFactory.create_parser('unregistered-parser')

        

