#!/usr/bin/env python3
"""
Initialize the expense tracker database.

Run this script to create the database schema and initial data.
"""
from pathlib import Path

from expense_tracker.database.connection import DatabaseConfig, DatabaseManager, execute_schema

def main():
    """initialize the database."""

    schema_file = Path(__file__).parent.parent / "src" / "expense_tracker" / "database" / "schema.sql"

    # Create database
    config = DatabaseConfig()
    print(f"Initializing database at: {config.db_path}")

    with DatabaseManager(config) as db:
        conn = db.get_connection()

        print(f"Executing schema from: {schema_file}")
        execute_schema(conn, schema_file)

        cursor = conn.execute(
            "SELECT version, description FROM schema_version ORDER BY version DESC LIMIT 1"
        )
        row = cursor.fetchone()

        if row:
            print(f"✓ Database initialized successfully!")
            print(f"  Schema version: {row['version']}")
            print(f"  Description: {row['description']}")
        else:
            print("✗ Database initialization may have failed")

if __name__ == "__main__":
    main()