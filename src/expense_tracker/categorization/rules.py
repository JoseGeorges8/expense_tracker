import re
from typing import Dict, List, Optional

from expense_tracker.categorization.base import CategorizationRule
from expense_tracker.domain.models import Transaction
from expense_tracker.domain.enums import TransactionType


class KeywordRule(CategorizationRule):
    """
    Rule that matches keywords in transaction descriptions.
    
    
    Features:
    - Case-insensitive matching
    - Can match multiple keywords per category
    - Can be transaction-type specific (debit vs credit)

    Example:
        ```
        # Match "STARBUCKS" or "TIM HORTONS" -> "Food & Dining"
        rule = KeywordRule({
            "Food & Dining": ["starbucks", "tim hortons"]
        })
        ```
    """

    def __init__(
            self,
            keyword_map: Dict[str, List[str]],
            transaction_type: Optional[TransactionType] = None
        ):
        """
        Initialize keyword rule
        
        Args:
            keyword_map: Dict mapping categories to list of keywords.
                Example: `{"Groceries": ["loblaws", "metro", "walmart"]}`
            transaction_type: Optional filter for DEBIT or CREDIT only
        """
        super().__init__()
        self.keyword_map = keyword_map
        self.transaction_type = transaction_type
        
        # Pre-process keywords to lowercase for case-insensitive matching
        self._normalized_map: Dict[str, List[str]] = {}
        for category, keywords in keyword_map.items():
            self._normalized_map[category] = [kw.lower() for kw in keywords]

    
    def _matches(self, transaction: Transaction) -> bool:
        """Check if any keyword matches the description"""

        if self.transaction_type and transaction.type != self.transaction_type:
            return False
        
        description_lower = transaction.description.lower()

        for _, keywords in self._normalized_map.items():
            for keyword in keywords:
                if keyword in description_lower:
                    return True
                
        return False
    
    def _get_category(self, transaction: Transaction) -> str:
        """Return the category for the matched keyword."""

        description_lower = transaction.description.lower()

        for category, keywords in self._normalized_map.items():
            for keyword in keywords:
                if keyword in description_lower:
                    return category

        # _matches must have made a whoopsie                
        raise RuntimeError("_get_category called but no match found")
    
    def __repr__(self):
        num_categories = len(self.keyword_map)
        type_filter = f", type={self.transaction_type.value}" if self.transaction_type else ""
        return f"KeywordRule({num_categories} categories{type_filter})"
        

class RegexRule(CategorizationRule):
    """
    Rule that matches regex patterns in descriptions.
    
    More powerful than KeywordRule - can match complex patterns.
    
    Example:
        # Match Amazon variations: AMZN, AMAZON, Amazon.ca
        rule = RegexRule({
            "Shopping": [r"^AMZN", r"AMAZON.*", r"Amazon\.ca"]
        })
    """

    def __init__(
        self,
        pattern_map: Dict[str, List[str]],
        transaction_type: Optional[TransactionType] = None
    ):
        """
        Initialize regex rule.
        
        Args:
            pattern_map: Dict mapping categories to regex patterns
                Example: {"Shopping": [r"^AMZN.*", r"AMAZON"]}
            transaction_type: Optional filter for DEBIT or CREDIT only
        """
        super().__init__()
        self.pattern_map = pattern_map
        self.transaction_type = transaction_type

        self._compiled_patterns: Dict[str, List[re.Pattern]] = {}
        for category, patterns in pattern_map.items():
            self._compiled_patterns[category] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]

    def _matches(self, transaction: Transaction) -> bool:
        """Check if any pattern matches the description"""

        if self.transaction_type and self.transaction_type != transaction.type:
            return False
        
        for _, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(transaction.description):
                    return True
                
        return False
    
    def _get_category(self, transaction: Transaction) -> str:
        """Return the category for the matched pattern"""

        for category, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(transaction.description):
                    return category
        
        raise RuntimeError("_get_category called but no match found")
    
    def __repr__(self) -> str:
        num_categories = len(self.pattern_map)
        type_filter = f", type={self.transaction_type.value}" if self.transaction_type else ""
        return f"RegexRule({num_categories} categories{type_filter})"


class UserDefinedRule(CategorizationRule):
    """
    Rule that uses user-defined mappings from config.
    
    Loaded from config/categorization_rules.json and has
    highest priority in the chain.
    
    Supports both keyword and regex patterns with transaction type filters.
    
    Config format:
        {
            "rules": [
                {
                    "category": "Groceries",
                    "patterns": ["loblaws", "metro"],
                    "type": "keyword",
                    "transaction_type": "Debit"  // optional
                },
                {
                    "category": "Refunds", 
                    "patterns": ["^AMZN.*REFUND"],
                    "type": "regex",
                    "transaction_type": "Credit"
                }
            ]
        }
    """
    def __init__(
        self, 
        rules_config: List[Dict]
    ):
        """
        Initialize with user-defined rules from config.
        
        Args:
            rules_config: List of rule definitions from JSON config
        """
        super().__init__()
        self.rules = rules_config
        
        self._keyword_rules: List[KeywordRule] = []
        self._regex_rules: List[RegexRule] = []

        for rule_def in self.rules:
            category = rule_def["category"]
            patterns = rule_def["patterns"]
            rule_type = rule_def.get("type", "keyword")

            txn_type = None
            if "transaction_type" in rule_def:
                txn_type = TransactionType(rule_def["transaction_type"])

            if rule_type == "keyword":
                self._keyword_rules.append(
                    KeywordRule({category: patterns}, txn_type)
                )
            elif rule_type == "regex":
                self._regex_rules.append(
                    RegexRule({category: patterns}, txn_type)
                )
            
    def _matches(self, transaction: Transaction) -> bool:
        """Check if any user-defined rule matched."""

        for rule in self._keyword_rules:
            if rule._matches(transaction):
                return True
            
        for rule in self._regex_rules:
            if rule._matches(transaction):
                return True
            
        return False
    
    def _get_category(self, transaction: Transaction) -> str:
        "Get category from the fist matching rule"
        
        for rule in self._keyword_rules:
            if rule._matches(transaction):
                return rule._get_category(transaction)
            
        for rule in self._regex_rules:
            if rule._matches(transaction):
                return rule._get_category(transaction)
                        
        raise RuntimeError("_get_category called but no match found")


    def __repr__(self) -> str:
        num_rules = len(self.rules)
        return f"UserDefinedRule({num_rules} rules)"

class DefaultRule(CategorizationRule):
    """
    Fallback rule that always matches.

    Should be the last rule in the chain.
    Returns the defined default category for every transaction.
    """

    def __init__(self, default_category = 'Uncategorized'):
        """
        Initialize the default rule.

        Args:
            default_category: The default category to return
        """
        super().__init__()
        self.default_category = default_category

    def _matches(self, _: Transaction) -> bool:
        """Always matches"""
        return True
    
    def _get_category(self, _: Transaction) -> str:
        """Only returns the default category."""
        return self.default_category

    def __repr__(self) -> str:
        return f"DefaultRule('{self.default_category}')"