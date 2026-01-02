from abc import ABC, abstractmethod
from typing import List
from expense_tracker.domain.models import Transaction

class StatementParser(ABC):
    """
    Abstract base class for all statement parsers.
    
    This implements the Strategy pattern - each bank gets its own
    concrete parser that implements this interface.
    """

    @abstractmethod
    def parse(self, filepath: str) -> List[Transaction]:
        """
        parse a statement file and return a list of transactions.
        
        Args:
            filepath: Path to the statement file
            
        Returns:
            List of Transaction objects
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        pass

    @abstractmethod
    def validate_file(self, filepath: str):
        """
        Validate that the file matches the expected format.
        
        Args:
            filepath: Path to the statement file

        Returns:
            Nothing if file is valid for this parser

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        pass