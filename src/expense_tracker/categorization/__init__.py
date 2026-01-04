"""
Categorization system for expense tracking.

Provides automatic transaction categorization using a chain of
responsibility pattern with configurable rules.

Quick Start:
    >>> from expense_tracker.categorization import CategorizationEngine
    >>> 
    >>> engine = CategorizationEngine()
    >>> category = engine.categorize(transaction)
    >>> print(f"Categorized as: {category}")
"""
from expense_tracker.categorization.categorizer import CategorizationEngine
from expense_tracker.categorization.base import CategorizationRule
from expense_tracker.categorization.rules import (
    KeywordRule,
    RegexRule,
    UserDefinedRule,
    DefaultRule
)
from expense_tracker.categorization import categories

__all__ = [
    "CategorizationEngine",
    "CategorizationRule",
    "KeywordRule",
    "RegexRule",
    "UserDefinedRule",
    "DefaultRule",
    "categories",
]