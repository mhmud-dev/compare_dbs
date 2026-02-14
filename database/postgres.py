import psycopg2
from psycopg2 import OperationalError, extras
from typing import Any, Dict, List
from contextlib import contextmanager
from .interfaces import DatabaseConnection, DatabaseRepository
from utils.config import DatabaseConfig


class PostgreSQLConnection(DatabaseConnection):
    """Optimized PostgreSQL specific connection implementation with proper error handling"""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._connection = None
        self._cursor = None

    def connect(self) -> Any:
        """Establish PostgreSQL connection with optimizations"""
        try:
            self._connection = psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5,
                connect_timeout=30,
            )
            self._connection.autocommit = False
            return self._connection
        except OperationalError as e:
            raise ConnectionError(f"Failed to connect to PostgreSQL: {e}")

    def disconnect(self) -> None:
        """Close PostgreSQL connection"""
        if self._cursor:
            self._cursor.close()
            self._cursor = None
        if self._connection and not self._connection.closed:
            self._connection.close()

    def ensure_connection(self):
        """Ensure connection is active with minimal overhead"""
        if not self._connection or self._connection.closed:
            self.connect()
        if not self._cursor or self._cursor.closed:
            self._cursor = self._connection.cursor()

    def check_and_reset_transaction(self):
        """Check if transaction is in error state and reset if needed"""
        try:
            if self._connection:
                with self._connection.cursor() as check_cursor:
                    check_cursor.execute("SELECT 1")
        except psycopg2.InternalError as e:
            if "current transaction is aborted" in str(e):
                self._connection.rollback()
                if self._cursor:
                    self._cursor.close()
                self._cursor = self._connection.cursor()

    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor with error handling"""
        cursor = None
        try:
            self.ensure_connection()
            self.check_and_reset_transaction()
            cursor = self._connection.cursor()
            yield cursor
        except Exception as e:
            if cursor:
                cursor.close()
            raise e
        finally:
            if cursor:
                cursor.close()

    @contextmanager
    def transaction(self):
        """Transaction context manager with proper error handling"""
        cursor = None
        try:
            self.ensure_connection()
            self.check_and_reset_transaction()
            cursor = self._connection.cursor()
            yield cursor
            self._connection.commit()
        except Exception as e:
            if self._connection:
                self._connection.rollback()
                if self._cursor:
                    self._cursor.close()
                    self._cursor = None
            raise e
        finally:
            if cursor:
                cursor.close()

    def execute_query(self, query: str, params: tuple = None) -> Any:
        """Execute SQL query with parameters and error handling"""
        self.ensure_connection()
        self.check_and_reset_transaction()
        try:
            self._cursor.execute(query, params or ())
            return self._cursor
        except Exception as e:
            if "current transaction is aborted" in str(e):
                self._connection.rollback()
                self._cursor = self._connection.cursor()
                self._cursor.execute(query, params or ())
                return self._cursor
            raise e

    def execute_values(
        self, query: str, values: List[tuple], page_size: int = 100
    ) -> None:
        """Execute INSERT with VALUES for maximum performance"""
        with self.transaction() as cursor:
            extras.execute_values(
                cursor, query, values, template=None, page_size=page_size
            )

    def commit(self) -> None:
        """Commit transaction"""
        if self._connection:
            try:
                self._connection.commit()
            except Exception as e:
                if "current transaction is aborted" in str(e):
                    self._connection.rollback()
                raise e

    def rollback(self) -> None:
        """Rollback transaction"""
        if self._connection:
            self._connection.rollback()
            if self._cursor:
                self._cursor.close()
                self._cursor = None

    @property
    def is_connected(self) -> bool:
        """Check if connection is active"""
        return self._connection and not self._connection.closed


class PostgreSQLRepository(DatabaseRepository):
    """PostgreSQL repository with proper transaction error handling"""

    def __init__(self, connection: PostgreSQLConnection):
        self.connection = connection

    def create_table(self, table_name: str, schema: str) -> None:
        """Create table in PostgreSQL"""
        try:
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
        except Exception as e:
            self.connection.rollback()
            raise e

    def drop_table(self, table_name: str) -> None:
        """Drop table"""
        try:
            query = f"DROP TABLE IF EXISTS {table_name}"
            with self.connection.transaction() as cursor:
                cursor.execute(query)
        except Exception as e:
            self.connection.rollback()
            raise e

    def truncate_table(self, table_name: str) -> None:
        """Truncate table"""
        try:
            query = f"TRUNCATE TABLE {table_name} RESTART IDENTITY"
            with self.connection.transaction() as cursor:
                cursor.execute(query)
        except Exception as e:
            self.connection.rollback()
            raise e

    def insert_row(self, table_name: str, data: Dict[str, Any]) -> int:
        """Insert single row"""
        try:
            columns = ", ".join(data.keys())
            placeholders = ", ".join(["%s"] * len(data))
            query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders}) RETURNING id"

            with self.connection.transaction() as cursor:
                cursor.execute(query, tuple(data.values()))
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            self.connection.rollback()
            raise e

    def insert_batch(self, table_name: str, data: List[Dict[str, Any]]) -> int:
        """Insert multiple rows in batch"""
        if not data:
            return 0
        try:
            if len(data) <= 10:
                columns = ", ".join(data[0].keys())
                placeholders = ", ".join(["%s"] * len(data[0]))
                query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
                values = [tuple(row.values()) for row in data]
                with self.connection.transaction() as cursor:
                    cursor.executemany(query, values)
                    return len(data)
            return self.insert_batch_optimized(table_name, data)
        except Exception as e:
            self.connection.rollback()
            raise e

    def insert_batch_optimized(
        self, table_name: str, data: List[Dict[str, Any]]
    ) -> int:
        """Optimized batch insert using execute_values"""
        if not data:
            return 0
        try:
            columns = list(data[0].keys())
            values = [tuple(row.values()) for row in data]

            query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES %s"
            page_size = 1000 if len(data) > 1000 else 100

            self.connection.execute_values(query, values, page_size)
            return len(data)
        except Exception as e:
            self.connection.rollback()
            raise e

    def get_table_size(self, table_name: str) -> int:
        """Get row count of table"""
        try:
            query = f"SELECT COUNT(*) FROM {table_name}"
            with self.connection.transaction() as cursor:
                cursor.execute(query)
                return cursor.fetchone()[0]
        except Exception as e:
            self.connection.rollback()
            raise e
