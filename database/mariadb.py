import mariadb
from typing import Any, Dict, List, Optional
from contextlib import contextmanager
from .interfaces import DatabaseConnection, DatabaseRepository
from utils.config import DatabaseConfig


class MariaDBConnection(DatabaseConnection):
    """MariaDB connection"""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._connection = None
        self._cursor = None

    def connect(self) -> Any:
        """Establish MariaDB connection"""
        try:
            connection_params = {
                "host": self.config.host,
                "port": self.config.port,
                "user": self.config.user,
                "password": self.config.password,
                "database": self.config.database,
                "autocommit": False,
                "connect_timeout": 30,
                "ssl": False,
                "local_infile": False,
            }
            self._connection = mariadb.connect(**connection_params)
            return self._connection
        except mariadb.Error as e:
            raise ConnectionError(f"Failed to connect to MariaDB: {e}")

    def disconnect(self) -> None:
        """Close MariaDB connection"""
        if self._cursor:
            try:
                self._cursor.close()
            except:
                pass
            self._cursor = None
        if self._connection:
            try:
                self._connection.close()
            except:
                pass
            self._connection = None

    def ensure_connection(self):
        """Ensure connection is active with minimal overhead"""
        if not self._connection:
            self.connect()
        if not self._cursor:
            self._cursor = self._connection.cursor()

    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor"""
        self.ensure_connection()
        cursor = None
        try:
            cursor = self._connection.cursor()
            yield cursor
        finally:
            if cursor:
                cursor.close()

    @contextmanager
    def transaction(self):
        """Transaction context manager"""
        self.ensure_connection()
        cursor = None
        try:
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
        self.ensure_connection()
        if params is not None and not isinstance(params, (tuple, dict)):
            params = (params,)
        self._cursor.execute(query, params)
        return self._cursor

    def executemany(self, query: str, params: List[tuple]) -> Any:
        """Execute SQL query with multiple parameter sets"""
        self.ensure_connection()
        self._cursor.executemany(query, params)
        return self._cursor

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
        try:
            if not self._connection:
                return False
            self._connection.ping(False)
            return True
        except (mariadb.Error, AttributeError):
            return False

    def get_server_info(self) -> Optional[str]:
        """Get MariaDB server version info"""
        try:
            return self._connection.get_server_info()
        except:
            return None

    def set_autocommit(self, autocommit: bool) -> None:
        """Set autocommit mode"""
        if self._connection:
            self._connection.autocommit = autocommit

    def get_warnings(self) -> List[Any]:
        """Get warnings from last operation"""
        if self._cursor:
            return self._cursor.fetchwarnings()
        return []


class MariaDBRepository(DatabaseRepository):
    """Repository implementation for MariaDB"""

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
        with self.connection.transaction() as cursor:
            cursor.execute(query, tuple(data.values()))
            return cursor.lastrowid

    def insert_batch(self, table_name: str, data: List[Dict[str, Any]]) -> int:
        """Insert multiple rows in batch"""
        if not data:
            return 0
        columns = list(data[0].keys())
        if len(data) == 1:
            return self.insert_row(table_name, data[0])
        if len(data) <= 10:
            placeholders = ", ".join(["%s"] * len(columns))
            query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
            values = [tuple(row.values()) for row in data]
            with self.connection.transaction() as cursor:
                cursor.executemany(query, values)
                return len(data)
        placeholders = ", ".join(["%s"] * len(columns))
        multi_placeholders = ", ".join([f"({placeholders})" for _ in data])
        query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES {multi_placeholders}"
        flat_values = []
        for row in data:
            flat_values.extend(row.values())
        with self.connection.transaction() as cursor:
            cursor.execute(query, flat_values)
            return len(data)

    def get_table_size(self, table_name: str) -> int:
        """Get row count of table"""
        query = f"SELECT COUNT(*) FROM {table_name}"
        with self.connection.transaction() as cursor:
            cursor.execute(query)
            return cursor.fetchone()[0]
