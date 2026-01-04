from abc import ABC, abstractmethod
from typing import Optional

from expense_tracker.domain.models import Transaction

class CategorizationRule(ABC):
    """
    Abstract base class for all categorization rules.

    Implements Chain of Responsibility:
    - Each rule tries to categorize a transaction
    - If it can't it passes to the next rule
    - Rules are tried in priority order

    Usage:
        Create chain: specific -> general -> default
        ```
        user_rule = UserDefinedRule(...)
        keyword_rule = KeywordRule(...)
        default_rule = DefaultRule()
        
        user_rule.set_next(keyword_rule).set_next(default_rule)

        category = user_rule.categorize(transaction)
        ```
    """

    def __init__(self):
        self._next_rule: Optional['CategorizationRule'] = None


    def set_next(self, rule: 'CategorizationRule') -> 'CategorizationRule':
        """
        Set the next rule in the chain.

        Args:
            rule: The next rule to try if this one doesn't match

        Returns:
            The rule that was set (for chaining)

        Example:
            `rule1.set_next(rule2).set_next(rule3)`
        """
        self._next_rule = rule

    @abstractmethod
    def _matches(self, transaction: Transaction) -> bool:
        """
        Check if this rule matches the transaction.

        Subclasses implement their specific matching logic here.

        Args:
            transaction: Transaction to check

        Returns:
            True if this rule can categorize this transaction
        """
        pass


    @abstractmethod
    def _get_category(self, transaction: Transaction) -> str:
        """
        Get the category for the transaction

        Called only if _matches() returns True.

        Args:
            transaction: Transaction to categorize

        Returns:
            Category name
        """
        pass


    def categorize(self, transaction: Transaction) -> Optional[str]:
        """
        Attempt to categorize a transaction.

        This is the main method called by clients. It:
        1. Checks if a rule matches
        2. If yes, returns the category
        3. If no, tries the next rule in the chain

        Args:
            Transaction to categorize.

        Returns:
            Category name, or None i no rules matched
        """
        if self._matches(transaction):
            return self._get_category(transaction)
        
        if self._next_rule:
            return self._next_rule.categorize(transaction)
        

        return None
    
    def __repr__(self):
        return f"{self.__class__.__name__}()"






