import psycopg2
from psycopg2 import OperationalError
from typing import Any, Dict, List
from contextlib import contextmanager
from .interfaces import DatabaseConnection, DatabaseRepository
from utils.config import DatabaseConfig


class PostgreSQLConnection(DatabaseConnection):
    """PostgreSQL specific connection implementation"""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._connection = None

    def connect(self) -> Any:
        """Establish PostgreSQL connection"""
        try:
            self._connection = psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                # Performance optimizations
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5,
            )
            return self._connection
        except OperationalError as e:
            raise ConnectionError(f"Failed to connect to PostgreSQL: {e}")

    def disconnect(self) -> None:
        """Close PostgreSQL connection"""
        if self._connection and not self._connection.closed:
            self._connection.close()

    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor"""
        cursor = None
        try:
            if not self._connection or not self.is_connected:
                self.connect()
            cursor = self._connection.cursor()
            yield cursor
        finally:
            if cursor:
                cursor.close()

    @contextmanager
    def transaction(self):
        """Context manager for transaction handling"""
        cursor = None
        try:
            if not self._connection or self._connection.closed:
                self.connect()
            cursor = self._connection.cursor()
            yield cursor
            self._connection.commit()
        except Exception as e:
            if self._connection:
                self._connection.rollback()
            raise e
        finally:
            if cursor:
                cursor.close()

    def execute_query(self, query: str, params: tuple = None) -> Any:
        """Execute SQL query with parameters"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor

    def commit(self) -> None:
        """Commit transaction"""
        if self._connection:
            self._connection.commit()

    def rollback(self) -> None:
        """Rollback transaction"""
        if self._connection:
            self._connection.rollback()

    @property
    def is_connected(self) -> bool:
        """Check if connection is active"""
        return self._connection and not self._connection.closed


class PostgreSQLRepository(DatabaseRepository):
    """Simplified PostgreSQL repository without cursor fetch issues"""

    def __init__(self, connection: PostgreSQLConnection):
        self.connection = connection

    def create_table(self, table_name: str, schema: str) -> None:
        """Create table in PostgreSQL"""
        query = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id SERIAL PRIMARY KEY,
            test_name VARCHAR(100),
            col1 VARCHAR(255),
            col2 INTEGER,
            col3 DOUBLE PRECISION,
            col4 TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSONB
        )
        """
        with self.connection.transaction() as cursor:
            cursor.execute(query)

    def drop_table(self, table_name: str) -> None:
        """Drop table"""
        query = f"DROP TABLE IF EXISTS {table_name}"
        with self.connection.transaction() as cursor:
            cursor.execute(query)

    def truncate_table(self, table_name: str) -> None:
        """Truncate table"""
        query = f"TRUNCATE TABLE {table_name}"
        with self.connection.transaction() as cursor:
            cursor.execute(query)

    def insert_row(self, table_name: str, data: Dict[str, Any]) -> int:
        """Insert single row"""
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

        cursor = self.connection.execute_query(query, tuple(data.values()))
        self.connection.commit()
        return cursor.lastrowid

    def insert_batch(self, table_name: str, data: List[Dict[str, Any]]) -> int:
        """Insert multiple rows in batch"""
        if not data:
            return 0
        columns = ", ".join(data[0].keys())
        placeholders = ", ".join(["%s"] * len(data[0]))
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        values = [tuple(row.values()) for row in data]
        with self.connection.transaction() as cursor:
            if len(values) == 1:
                cursor.execute(query, values[0])
            else:
                cursor.executemany(query, values)
            return cursor.rowcount

    def get_table_size(self, table_name: str) -> int:
        """Get row count of table"""
        query = f"SELECT COUNT(*) FROM {table_name}"
        with self.connection.transaction() as cursor:
            cursor.execute(query)
            result = cursor.fetchone()
            return result[0] if result else 0
