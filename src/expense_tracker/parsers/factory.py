import json
import importlib
from typing import Optional, Dict, Type, Any
from expense_tracker.parsers.base import StatementParser
from expense_tracker.config.settings import ConfigLoader

class ParserFactory:
    """
    Factory for creating statement parsers.

    Uses a registry pattern to map financial institution identifiers to statement parser Classes.
    """

    _locked = False
    _registry: Dict[str, Type[StatementParser]] = {}

    @classmethod
    def register(cls, fi_name: str, parser_class: Type[StatementParser]) -> None:
        """
        Register a parser for a specific bank

        Args:
            fi_name: Unique identifier for the Financial Institution (e.g, 'amex', 'cibc')
            parser_class: The parser class
        
        Raises:
            ValueError: If parser is already registered
            TypeError: If parser_class doesn't inherit from StatementParser
            RuntimeError: If the parser registry is locked


        Example:
            ParserFactory.register('amex', AmexExcelParser)        
        """

        if cls._locked:
            raise RuntimeError("Registry is locked, cannot add more parsers")
        
        if fi_name in cls._registry:
            raise ValueError(f"Parser for '{fi_name}' is already registered")
        
        if not issubclass(parser_class, StatementParser):
            raise TypeError(f"{parser_class} must inherit from StatementParser")
        
        cls._registry[fi_name] = parser_class

    @classmethod
    def lock_registry(cls):
        """Prevent further registration (call after app initialization)"""
        cls._locked = True

    @classmethod
    def create_parser(cls, fi: str) -> StatementParser:
        """
        Create a parser instance for the specified Financial Institution.

        Args:
            fi: Finantial Institution identifier (e.g., 'amex', 'cibc')

        Returns:
            Instantiated parser ready to use

        Raises:
            ValueError: If no parser registered for this bank

        Example:
            ParserFactory.create_parser('amex')
            transactions = parser.parse('statement.xlsx)
        """
        if fi not in cls._registry:
            available = ', '.join(cls._registry.keys())
            raise ValueError(
                f"No parser registered for '{fi}'. "
                f"Available parsers: {available}"
            )
        
        return cls._registry[fi]()
    
    @classmethod
    def get_available_banks(cls) -> list[str]:
        """Return list of all registered bank identifiers"""
        return list(cls._registry.keys())

    @classmethod
    def load_parsers_from_config(
        cls, 
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Load and register parsers from configuration
        
        Args:
            config: Optional config dict. If None, loads from ConfigLoader.
                Useful for testing with custom configs.

            Example (production):
                ParserFactory.load_parsers_from_config()

            Example (testing): 
                test_config = {"parsers": [...]}
                ParserFactory.load_parsers_from_config(config=test_config)
        """
        if config is None:
            config = ConfigLoader.load_parsers_config()

        for parser_config in config['parsers']:
            module_path, class_name = str(parser_config['class']).rsplit('.', 1)
            module = importlib.import_module(module_path)
            parser_class = getattr(module, class_name)

            cls.register(parser_config['financial_institution'], parser_class)

        cls.lock_registry()