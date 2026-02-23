import mariadb
from typing import Any, Dict, List, Optional
from contextlib import contextmanager
import threading
from .interfaces import DatabaseConnection, DatabaseRepository
from utils.config import DatabaseConfig


class MariaDBConnection(DatabaseConnection):
    """MariaDB connection"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._local = threading.local()
        self._connection_created = False

    def _get_connection(self):
        """Get or create thread-local connection"""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
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
                self._local.connection = mariadb.connect(**connection_params)
                self._local.connection.autocommit = False
                self._connection_created = True
            except mariadb.Error as e:
                raise ConnectionError(f"Failed to connect to MariaDB: {e}")
        return self._local.connection

    def _get_cursor(self):
        """Get or create thread-local cursor"""
        if not hasattr(self._local, 'cursor') or self._local.cursor is None:
            conn = self._get_connection()
            self._local.cursor = conn.cursor()
        return self._local.cursor

    def connect(self) -> Any:
        """Establish MariaDB connection for current thread"""
        return self._get_connection()

    def disconnect(self) -> None:
        """Close MariaDB connection for current thread"""
        if hasattr(self._local, 'cursor') and self._local.cursor:
            try:
                self._local.cursor.close()
            except:
                pass
            self._local.cursor = None
        
        if hasattr(self._local, 'connection') and self._local.connection:
            try:
                self._local.connection.close()
            except:
                pass
            self._local.connection = None

    def ensure_connection(self):
        """Ensure connection is active for current thread"""
        self._get_connection()
        self._get_cursor()

    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor"""
        self.ensure_connection()
        cursor = None
        try:
            cursor = self._get_connection().cursor()
            yield cursor
        finally:
            if cursor:
                try:
                    cursor.close()
                except:
                    pass

    @contextmanager
    def transaction(self):
        """Transaction context manager"""
        conn = self._get_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            yield cursor
            conn.commit()
        except Exception as e:
            try:
                conn.rollback()
            except:
                pass
            raise e
        finally:
            if cursor:
                try:
                    cursor.close()
                except:
                    pass

    def execute_query(self, query: str, params: tuple = None) -> Any:
        """Execute SQL query with parameters"""
        self.ensure_connection()
        if params is not None and not isinstance(params, (tuple, dict)):
            params = (params,)
        
        cursor = self._local.cursor
        cursor.execute(query, params)
        return cursor

    def executemany(self, query: str, params: List[tuple]) -> Any:
        """Execute SQL query with multiple parameter sets"""
        self.ensure_connection()
        cursor = self._local.cursor
        cursor.executemany(query, params)
        return cursor

    def commit(self) -> None:
        """Commit transaction for current thread"""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.commit()

    def rollback(self) -> None:
        """Rollback transaction for current thread"""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.rollback()

    @property
    def is_connected(self) -> bool:
        """Check if connection is active for current thread"""
        try:
            if not hasattr(self._local, 'connection') or not self._local.connection:
                return False
            self._local.connection.ping(False)
            return True
        except (mariadb.Error, AttributeError):
            return False

    def get_server_info(self) -> Optional[str]:
        """Get MariaDB server version info"""
        try:
            if hasattr(self._local, 'connection'):
                return self._local.connection.get_server_info()
        except:
            pass
        return None

    def set_autocommit(self, autocommit: bool) -> None:
        """Set autocommit mode for current thread"""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.autocommit = autocommit

    def get_warnings(self) -> List[Any]:
        """Get warnings from last operation"""
        if hasattr(self._local, 'cursor') and self._local.cursor:
            return self._local.cursor.fetchwarnings()
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
