-- Expense Tracker Database Schema
-- SQLite 3.35+

-- Enable foreign key constraints
PRAGMA foreign_keys = ON;

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- Insert initial version
INSERT OR IGNORE INTO schema_version(version, description)
VALUES (1, 'Initial schema with transactions table');

-- Transactions table
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Core transaction data
    date DATE NOT NULL,
    description TEXT NOT NULL,
    amount TEXT NOT NULL, -- Using Decimal is causing issues when mapping between python and the sqlite db
    type TEXT NOT NULL CHECK(type IN ('Debit', 'Credit')),

    -- Source information
    account TEXT NOT NULL, -- e.g 'amex', 'cibc'
    raw_data TEXT, -- Original parsed data (JSON)

    -- Categorization
    category TEXT DEFAULT 'Uncategorized',

    -- metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Deduplication: unique constraint on key fields
    UNIQUE(date, description, amount, account)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_transactions_date
    ON transactions(date DESC);

CREATE INDEX IF NOT EXISTS idx_transactions_category
    ON transactions(category);

CREATE INDEX IF NOT EXISTS idx_transactions_type
    ON transactions(type);

CREATE INDEX IF NOT EXISTS idx_transactions_account
    ON transactions(account);

-- Composite index for monthly reports
CREATE INDEX IF NOT EXISTS idx_transactions_month
    ON transactions(date, category, type);

-- Trigger to update updated_at timestamp
CREATE TRIGGER IF NOT EXISTS update_transactions_timestamp
    AFTER UPDATE ON transactions
BEGIN 
    UPDATE transactions
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

-- View for monthly summaries
CREATE VIEW IF NOT EXISTS monthly_summary AS
SELECT
    strftime('%Y-%m', date) as month,
    type,
    category,
    COUNT(*) as transaction_count,
    SUM(amount) as total_amount
FROM transactions
GROUP BY month, type, category
ORDER BY month DESC, type, category;