import pytest
from datetime import date
from decimal import Decimal

from expense_tracker.domain.enums import TransactionType
from expense_tracker.domain.models import Transaction
from expense_tracker.categorization.categorizer import CategorizationEngine

@pytest.fixture
def sample_transaction():
    return Transaction(
        date=date(2025, 1, 15),
        description="LOBLAWS OTTAWA",
        amount=Decimal("45.67"),
        type=TransactionType.DEBIT,
        account="amex"
)

@pytest.mark.unit
class TestCategorizationEngineConfig:
    """Test config loading pattern"""

    def test_load_with_custom_config(self, sample_transaction: Transaction):
        """Test loading with injected config"""

        # Arrange
        test_config = {
            "rules": [
                {
                    "category": "Groceries",
                    "type": "keyword",
                    "patterns": ["loblaws", "metro"]
                }
            ]
        }
        engine = CategorizationEngine(config=test_config)

        # Act
        category = engine.categorize(transaction=sample_transaction)

        # Assert
        assert category == "Groceries"

    def test_load_without_config_doesnt_crash(self, sample_transaction: Transaction):
        """Test that the engine works even without user config file."""

        # Act
        engine = CategorizationEngine()
        category = engine.categorize(sample_transaction)

        # Assert
        assert category is not None
        assert isinstance(category, str)

    def test_user_rules_override_builtin(self, sample_transaction: Transaction):
        """Test that user config has highest priority."""

        # Arrange
        test_config = {
            "rules": [
                {
                    "category": "My Groceries Category", 
                    "type": "keyword",
                    "patterns": ["loblaws"] # Loblaws is builtin as 'Groceries'
                }
            ]
        }
        engine = CategorizationEngine(config=test_config)

        # Act
        category = engine.categorize(transaction=sample_transaction)

        # Assert
        assert category == "My Groceries Category"

    def test_disable_builtin_rules(self, sample_transaction: Transaction):
        """Test disabling built-in default rules."""

        # Arrange
        test_config = {
            "rules": [
                {
                    "category": "My Groceries Category", 
                    "type": "keyword",
                    "patterns": ["custom store"]
                }
            ]
        }
        engine = CategorizationEngine(config=test_config, use_defaults=False)

        # Act
        category = engine.categorize(transaction=sample_transaction)

        # Assert
        assert category == "Uncategorized"

    def test_empty_config(self, sample_transaction: Transaction):
        """Test with empty config (only default rule)."""
        # Arrange
        empty_config = {"rules": []}
        
        # Act
        engine = CategorizationEngine(config=empty_config, use_defaults=False)
        category = engine.categorize(sample_transaction)
        
        # Assert - should fall to default
        assert category == "Uncategorized"

    def test_multiple_user_rules(self):
        """Test multiple user-defined rules in priority order."""
        # Arrange
        user_config = {
            "rules": [
                {
                    "category": "Premium Groceries",
                    "type": "keyword",
                    "patterns": ["whole foods"]
                },
                {
                    "category": "Regular Groceries",
                    "type": "keyword",
                    "patterns": ["loblaws", "metro"]
                },
                {
                    "category": "Discount Groceries",
                    "type": "keyword",
                    "patterns": ["no frills"]
                }
            ]
        }
        
        engine = CategorizationEngine(config=user_config)
        
        # Act & Assert - each should match the right category
        whole_foods = Transaction(
            date=date(2025, 1, 1),
            description="WHOLE FOODS",
            amount=Decimal("100.00"),
            type=TransactionType.DEBIT,
            account="amex"
        )
        assert engine.categorize(whole_foods) == "Premium Groceries"
        
        loblaws = Transaction(
            date=date(2025, 1, 2),
            description="LOBLAWS",
            amount=Decimal("50.00"),
            type=TransactionType.DEBIT,
            account="amex"
        )
        assert engine.categorize(loblaws) == "Regular Groceries"
        
        no_frills = Transaction(
            date=date(2025, 1, 3),
            description="NO FRILLS",
            amount=Decimal("30.00"),
            type=TransactionType.DEBIT,
            account="amex"
        )
        assert engine.categorize(no_frills) == "Discount Groceries"


@pytest.mark.unit
class TestCategorizationEngineChain:
    """Test the rule chain behavior."""

    def test_rule_chain_info(self):
        """Test getting info about active rules."""
        # Arrange
        config = {
            "rules": [
                {"category": "Test", "type": "keyword", "patterns": ["test"]}
            ]
        }
        
        # Act
        engine = CategorizationEngine(config=config)
        info = engine.get_rule_chain_info()
        
        # Assert
        assert isinstance(info, str)
        assert "UserDefinedRule" in info
        assert "DefaultRule" in info

    def test_categorize_many(self):
        """Test batch categorization"""
        # Act
        config = {
            "rules": [
                {"category": "Groceries", "type": "keyword", "patterns": ["loblaws"]},
                {"category": "Gas", "type": "keyword", "patterns": ["shell"]},
            ]
        }

        transactions = [
            Transaction(
                date=date(2026, 1, 1),
                description="LOBLAWS",
                amount=Decimal("9.99"),
                account="amex",
                type=TransactionType.DEBIT
            ),
            Transaction(
                date=date(2026, 1, 1),
                description="SHELL",
                amount=Decimal("9.99"),
                account="amex",
                type=TransactionType.DEBIT
            ),
            Transaction(
                date=date(2026, 1, 1),
                description="AMAZON",
                amount=Decimal("9.99"),
                account="amex",
                type=TransactionType.DEBIT
            ),
        ]

        engine = CategorizationEngine(config=config, use_defaults=False)

        # Act
        categorized = engine.categorize_many(transactions)

        assert len(categorized) == 3
        assert categorized[0].category == "Groceries"
        assert categorized[1].category == "Gas"
        assert categorized[2].category == "Uncategorized"

    def test_engine_respects_overwrite_flag(self):
        """Test the overwrite flag is being respected"""

        # Act
        config = {
            "rules": [
                {"category": "New Category", "type": "keyword", "patterns": ["loblaws"]},
            ]
        }

        already_categorized = Transaction(
            date=date(2025, 1, 1),
            description="LOBLAWS",
            amount=Decimal("50.00"),
            type=TransactionType.DEBIT,
            account="amex",
            category="Old Category"
        )

        uncategorized = Transaction(
                date=date(2025, 1, 2),
                description="LOBLAWS",
                amount=Decimal("30.00"),
                type=TransactionType.DEBIT,
                account="amex",
                category="Uncategorized"
        )

        engine = CategorizationEngine(config=config, use_defaults=False)

        # Act - Overwrite = False
        categorized = engine.categorize_many(transactions=[already_categorized, uncategorized], overwrite=False)

        # Assert - Overwrite = False
        assert categorized[0].category == 'Old Category'
        assert categorized[1].category == 'New Category'

        # Act - Overwrite = True
        categorized = engine.categorize_many(transactions=[already_categorized, uncategorized], overwrite=True)

        # Assert - Overwrite = True
        assert categorized[0].category == 'New Category'
        assert categorized[1].category == 'New Category'


    def test_transaction_type_categorization(self):
        # Arrange
        config = {
            "rules": [
                {
                    "category": "Shopping",
                    "type": "keyword",
                    "transaction_type": "Debit",
                    "patterns": ["amazon"]
                }, 
                {
                    "category": "Refunds",
                    "type": "keyword",
                    "transaction_type": "Credit",
                    "patterns": ["amazon"]
                }
            ]
        }

        debit = Transaction(
            date=date(2025, 1, 1),
            description="amazon",
            amount=Decimal("50.00"),
            type=TransactionType.DEBIT,
            account="amex",
        )

        credit = Transaction(
                date=date(2025, 1, 2),
                description="amazon",
                amount=Decimal("30.00"),
                type=TransactionType.CREDIT,
                account="amex",
        )

        engine = CategorizationEngine(config=config)
        
        # Act & Assert
        assert engine.categorize(debit) == "Shopping"
        assert engine.categorize(credit) == "Refunds"
