import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

# Type alias for clarity
Connection = sqlite3.Connection
Cursor = sqlite3.Cursor

class DatabaseConfig:
    """Database configuration settings."""

    def __init__(self, db_path: Path | str = "data/transactions.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def connection_string(self) -> str:
        """Return the database file path as a string"""
        return str(self.db_path.absolute())
    
def configure_connection(conn: Connection) -> None:
    """
    Apply standard configuration to a SQLite connection.
    
    This function is called by all connection creation methods
    to ensure consistent settings.
    
    Args:
        conn: SQLite connection to configure
    """
    # Enable foreign key constraints (OFF by default in SQLite!)
    conn.execute("PRAGMA foreign_keys = ON")
    
    # Return rows as dict-like objects instead of tuples
    conn.row_factory = sqlite3.Row
    
class DatabaseManager:
    """
    Manages SQLite database connections.

    Uses context managers for safe connection handling.
    Implements connection pooling for better performance.
    """

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._connection: Connection | None = None

    def get_connection(self) -> Connection:
        """
        Get or create a database connection.

        Returns:
            sqlite3.Connection: Active database connection
        """
        if self._connection is None:
            self._connection = self._create_connection()
        return self._connection
    
    def _create_connection(self) -> Connection:
        """
        Create a new SQLite connection with proper settings.
        
        Returns:
            sqlite3.Connection: Configured database connection
        """
        conn = sqlite3.connect(
            self.config.connection_string,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            check_same_thread=False, # Allow multi-threaded access
        )

        # Apply standard configuration
        configure_connection(conn)

        return conn
    
    def close(self) -> None:
        """Close the database connection if open."""
        if self._connection:
            self._connection.close()
            self._connection = None

    @contextmanager
    def transaction(self) -> Generator[Connection, None, None]: # Generator[YieldType, SendType, ReturnType]
        """
        Context manager for database transactions.

        Automatically commits on success, rolls back on exception.

        Usage: 
            with db_manager.transaction() as conn:
                conn.execute("INSERT INTO ...")
                conn.execute("UPDATE ...")
        """
        conn = self.get_connection()
        try:
            yield conn # Pause here, give conn to 'with' block
             # When 'with' block finishes, resume here
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def __enter__(self) -> "DatabaseManager":
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - close connection."""
        self.close()

def execute_schema(conn: Connection, schema_path: Path) -> None:
    """
    Execute a SQL schema file.

    Args:
        conn: Database connection
        schema_path: Path to .sql file
    """
    with open(schema_path) as f:
        schema = f.read()

    conn.executescript(schema)
    conn.commit()