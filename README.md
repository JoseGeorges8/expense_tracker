# Expense Tracker CLI

A command-line tool for importing, categorizing, and analyzing personal expenses (and incomes) from bank and credit card statements.

## Overview

Expense Tracker helps you gain insights into your spending habits by:
- Importing transactions from multiple financial institutions
- Automatically categorizing expenses and income
- Generating monthly reports and summaries
- Tracking trends over time

## Architecture

### Design Patterns

The project follows clean architecture principles with clear separation of concerns:

- **Strategy Pattern**: Pluggable parsers for different bank statement formats
- **Factory Pattern**: Dynamic parser selection based on bank type
- **Repository Pattern**: Abstracted data access layer for flexibility
- **Chain of Responsibility**: Extensible categorization rule system
- **Builder Pattern**: Flexible report generation with various output formats

### Layered Architecture
```
CLI Layer (Typer commands)
    ↓
Service Layer (Business logic orchestration)
    ↓
Domain Layer (Core models and business rules)
    ↓
Repository Layer (Data persistence)
```

## Key Design Decisions

### Transaction Model

Transactions use an explicit `TransactionType` enum (DEBIT/CREDIT) rather than signed amounts. This approach:
- Makes business intent clearer in code
- Simplifies parser normalization across different bank formats
- Enables distinct categorization logic for income vs. expenses
- Improves report readability and aggregation logic

### Categorization System

Uses a chain of responsibility pattern allowing multiple rule types:
- Keyword matching for simple cases
- Regex patterns for complex matching
- User-defined rules loaded from configuration
- Falls back to "Uncategorized" when no rules match

### Data Storage

SQLite for local storage with a repository abstraction that allows:
- Easy migration to PostgreSQL if needed
- Testability through mock repositories
- Transaction deduplication
- Historical data queries

## Technology Stack

### Core Dependencies

- **Python 3.10+**: Modern Python features and type hints
- **Typer**: CLI framework with elegant API and automatic help generation
- **Rich**: Beautiful terminal output and formatting
- **Pandas**: Data manipulation and analysis
- **openpyxl**: Excel file parsing (XLSX format)

### Development Tools

- **Poetry**: Dependency management and packaging
- **Pytest**: Testing framework
- **Ruff**: Fast Python linter

## Project Structure
```
expense_tracker/
├── domain/          # Core business models and enums
├── parsers/         # Bank statement parsers
├── categorization/  # Transaction categorization rules
├── repositories/    # Data access layer
├── services/        # Business logic orchestration
├── reporting/       # Report generation and formatting
└── cli.py          # Command-line interface
```

## Extensibility

The architecture is designed for easy extension:

- **New Banks**: Add a parser class implementing `StatementParser`
- **New Categories**: Update `categories.py` and rules configuration
- **New Report Formats**: Add a formatter implementing the format interface
- **New Storage**: Implement `TransactionRepository` for different databases

## Future Considerations

- Budget tracking and alerts
- Multi-currency support
- Machine learning for smarter categorization
- Web dashboard for visualization
- Export to tax preparation software formats