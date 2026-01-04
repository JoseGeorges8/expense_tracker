import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from expense_tracker.categorization.base import CategorizationRule
from expense_tracker.categorization.rules import (
    UserDefinedRule,
    KeywordRule,
    RegexRule,
    DefaultRule
)
from expense_tracker.categorization.categories import UNCATEGORIZED
from expense_tracker.domain.models import Transaction
from expense_tracker.config.settings import ConfigLoader

class CategorizationEngine:
    """
    Main engine for categorizing transactions.
    
    Builds a chain of rules in priority order:
    1. User-defined rules (from config)
    2. Built-in keyword rules
    3. Built-in regex rules  
    4. Default (Uncategorized)
    
    Usage:
        # Production - loads from ConfigLoader
        engine = CategorizationEngine()
        
        # Testing - inject custom config
        test_config = {"rules": [...]}
        engine = CategorizationEngine(config=test_config)
        
        # Categorize transactions
        category = engine.categorize(transaction)
        categorized = engine.categorize_many(transactions)
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        use_defaults: bool = True
    ):
        """
        Initialize categorization engine.
        
        Args:
            config: Optional config dict. If None, loads from ConfigLoader.
                Useful for testing with custom configs.
            use_defaults: Whether to include built-in default rules
        """
        self.use_defaults = use_defaults
        self._rule_chain: Optional[CategorizationRule] = None
        
        # Build the rule chain
        self._build_rule_chain(config)


    def _load_user_rules_config(
        self,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Load user rules configuration.

        Args:
            config: Optional config dict. If None, loads from the ConfigLoader.

        Returns:
            Config dictionary with rules
        """
        if config is not None:
            return config
        
        try:
            return ConfigLoader.load_config('categorization_rules.json')
        except FileNotFoundError:
            # User hasn't created custom rules yet - that's fine.
            return {"rules": []}
        
    def _load_builtin_rules_config(self) -> Dict[str, Any]:
        """
        Load build-in default rules.

        Returns:
            Config dictionaty with built-in rules
        """
        # Built-in rules are always in the package config/defaults folder
        builtin_path = Path(__file__).parent.parent / "config" / "defaults" / "rules.json"
        
        if not builtin_path.exists():
            return {"rules": []}
        
        import json
        try:
            with open(builtin_path) as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load built-in rules: {e}")
            return {"rules": []}
        
    def _build_rule_chain(
        self,
        user_config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Build the chain of responsibility for categorization rules.
        
        Priority order:
        1. User-defined rules (highest priority)
        2. Built-in default rules
        3. Default fallback (always matches)
        
        Args:
            user_config: Optional user config dict for testing
        """
        rules: List[CategorizationRule] = []

        user_rules_config = self._load_user_rules_config(user_config)
        user_rules = user_rules_config.get("rules", [])
        if user_rules:
            rules.append(UserDefinedRule(user_rules))

        if self.use_defaults:
            builtin_rules_config = self._load_builtin_rules_config()
            builtin_rules = builtin_rules_config.get("rules", [])
            if builtin_rules:
                rules.append(UserDefinedRule(builtin_rules))

        rules.append(DefaultRule(UNCATEGORIZED))

        if rules:
            self._rule_chain = rules[0]
            for i in range(len(rules) - 1):
                rules[i].set_next(rules[i+1])

    def categorize(self, transaction: Transaction) -> str:
        """
        Categorize a single transaction.

        Args:
            transaction: Transaction to categorize

        Returns:
            Category name

        Example:
            ```
            >>> engine = CategorizationEngine()
            >>> txn = Transaction(...)
            >>> category = engine.categorize(txn)
            >>> print(category)
            'Groceries'
            ```
        """
        if not self._rule_chain:
            raise RuntimeError("Rule chain not initialized")
        
        category = self._rule_chain.categorize(transaction)

        assert category is not None, "Rule chain should never return None"

        return category
    
    def categorize_many(
        self,
        transactions: List[Transaction],
        overwrite: bool = False
    ) -> List[Transaction]:
        """
        Categorize multiple transactions.
        
        Args:
            transactions: List of transactions to categorize
            overwrite: If True, re-categorize even if already categorized.
                      If False, only categorize Uncategorized transactions.
            
        Returns:
            List of transactions with categories assigned
            
        Example:
            >>> engine = CategorizationEngine()
            >>> transactions = [txn1, txn2, txn3]
            >>> categorized = engine.categorize_many(transactions)
        """
        categorized = []

        for txn in transactions:
            if not overwrite and txn.category and txn.category != UNCATEGORIZED:
                categorized.append(txn)
                continue

            category = self.categorize(txn)

            categorized_txn = Transaction(
                id=txn.id,
                date=txn.date,
                description=txn.description,
                amount=txn.amount,
                type=txn.type,
                account=txn.amount,
                raw_data=txn.raw_data,
                category=category
            )
            categorized.append(categorized_txn)

        return categorized

    def get_rule_chain_info(self) -> str:
        """
        Get information about the current rule chain.

        Useful for debugging and understanding which rules are active.

        Returns:
            String description of the current rule chain.
        """
        if not self._rule_chain:
            return "No rules loaded"
        
        rules = []
        current = self._rule_chain
        priority = 1

        while current:
            rules.append(f"{priority}. {current}")
            current = current._next_rule
            priority +=1

        return "\n".join(rules)
    

    def __repr__(self) -> str:
        num_rules = 0
        current = self._rule_chain
        while current:
            num_rules+=1
            current = current._next_rule

        return f"CategorizationEngine({num_rules} rules in chain)"


        
