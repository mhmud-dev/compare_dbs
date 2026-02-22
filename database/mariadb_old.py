import mysql.connector
from mysql.connector import Error
from typing import Any, Dict, List
from contextlib import contextmanager
from .interfaces import DatabaseConnection, DatabaseRepository
from utils.config import DatabaseConfig


class MariaDBConnection(DatabaseConnection):
    """Optimized MariaDB specific connection implementation"""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._connection = None
        self._cursor = None

    def connect(self) -> Any:
        """Establish MariaDB connection with optimizations"""
        try:
            self._connection = mysql.connector.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                autocommit=False,
                # Performance optimizations
                buffered=True,
                consume_results=True,
                connection_timeout=30,
                pool_name=None,
                pool_size=1,
                use_pure=True,
            )
            return self._connection
        except Error as e:
            raise ConnectionError(f"Failed to connect to MariaDB: {e}")

    def disconnect(self) -> None:
        """Close MariaDB connection"""
        if self._cursor:
            self._cursor.close()
            self._cursor = None
        if self._connection and self._connection.is_connected():
            self._connection.close()

    def ensure_connection(self):
        """Ensure connection is active with minimal overhead"""
        if not self._connection or not self._connection.is_connected():
            self.connect()
        if not self._cursor:
            self._cursor = self._connection.cursor()

    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor - use cached cursor when possible"""
        self.ensure_connection()
        try:
            yield self._cursor
        except Exception as e:
            self._cursor = None
            raise e

    @contextmanager
    def transaction(self):
        """Optimized transaction handling"""
        self.ensure_connection()
        try:
            yield self._cursor
            self._connection.commit()
        except Exception as e:
            self._connection.rollback()
            self._cursor = None
            raise e

    def execute_query(self, query: str, params: tuple = None) -> Any:
        """Execute SQL query with parameters - direct execution without extra context"""
        self.ensure_connection()
        self._cursor.execute(query, params or ())
        return self._cursor

    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """Execute many with optimized settings"""
        self.ensure_connection()
        self._cursor.executemany(query, params_list)
        return self._cursor.rowcount

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
        return self._connection and self._connection.is_connected()


class MariaDBRepository(DatabaseRepository):
    """Optimized repository implementation for MariaDB"""

    def __init__(self, connection: MariaDBConnection):
        self.connection = connection

    def create_table(self, table_name: str, schema: str) -> None:
        """Create table in MariaDB"""
        query = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INT AUTO_INCREMENT PRIMARY KEY,
            test_name VARCHAR(100),
            col1 VARCHAR(255),
            col2 INT,
            col3 FLOAT,
            col4 TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSON
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        self.connection.execute_query(query)
        self.connection.commit()

    def drop_table(self, table_name: str) -> None:
        """Drop table"""
        query = f"DROP TABLE IF EXISTS {table_name}"
        self.connection.execute_query(query)
        self.connection.commit()

    def truncate_table(self, table_name: str) -> None:
        """Truncate table"""
        query = f"TRUNCATE TABLE {table_name}"
        self.connection.execute_query(query)
        self.connection.commit()

    def insert_row(self, table_name: str, data: Dict[str, Any]) -> int:
        """Insert single row - optimized for minimal overhead"""
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        cursor = self.connection.execute_query(query, tuple(data.values()))
        self.connection.commit()
        return cursor.lastrowid

    def insert_batch(self, table_name: str, data: List[Dict[str, Any]]) -> int:
        """Insert multiple rows in batch with optimized transaction handling"""
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

    def insert_batch_optimized(
        self, table_name: str, data: List[Dict[str, Any]]
    ) -> int:
        """Ultra-optimized batch insert for MariaDB using multi-row INSERT syntax"""
        if not data:
            return 0
        columns = ", ".join(data[0].keys())
        placeholders = ", ".join(["%s"] * len(data[0]))
        multi_placeholders = ", ".join([f"({placeholders})" for _ in data])
        query = f"INSERT INTO {table_name} ({columns}) VALUES {multi_placeholders}"
        flat_values = [value for row in data for value in row.values()]
        with self.connection.transaction() as cursor:
            cursor.execute(query, flat_values)
            return cursor.rowcount

    def get_table_size(self, table_name: str) -> int:
        """Get row count of table"""
        query = f"SELECT COUNT(*) FROM {table_name}"
        cursor = self.connection.execute_query(query)
        result = cursor.fetchone()
        return result[0] if result else 0
