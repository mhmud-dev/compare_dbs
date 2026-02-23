import threading
import psycopg2
from psycopg2 import extras
from typing import Any, Dict, List
from contextlib import contextmanager
from .interfaces import DatabaseConnection, DatabaseRepository
from utils.config import DatabaseConfig


class PostgreSQLConnectionPool:
    """Thread-safe connection pool for PostgreSQL"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def __init__(self, config: DatabaseConfig, min_conn: int = 10, max_conn: int = 1000):
        if not hasattr(self, 'initialized'):
            self.config = config
            self.min_conn = min_conn
            self.max_conn = max_conn
            self._pool = None
            self._local = threading.local()
            self.initialized = True
            self._init_pool()
    
    def _init_pool(self):
        """Initialize connection pool"""
        try:
            self._pool = psycopg2.pool.ThreadedConnectionPool(
                self.min_conn,
                self.max_conn,
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
                options="-c statement_timeout=30000"
            )
        except Exception as e:
            raise ConnectionError(f"Failed to create connection pool: {e}")
    
    @contextmanager
    def get_connection(self):
        """Get connection from pool with thread-local caching"""
        conn = None
        try:
            if hasattr(self._local, 'conn') and self._local.conn and not self._local.conn.closed:
                conn = self._local.conn
            else:
                conn = self._pool.getconn()
                self._local.conn = conn
            
            yield conn
        except Exception as e:
            if conn:
                self._pool.putconn(conn, close=True)
                if hasattr(self._local, 'conn'):
                    delattr(self._local, 'conn')
            raise e
    
    def return_connection(self, conn, close=False):
        """Return connection to pool"""
        if conn:
            try:
                self._pool.putconn(conn, close=close)
                if hasattr(self._local, 'conn') and self._local.conn == conn:
                    delattr(self._local, 'conn')
            except Exception:
                pass
    
    def close_all(self):
        """Close all connections in pool"""
        if self._pool:
            self._pool.closeall()


class PostgreSQLConnection(DatabaseConnection):
    """PostgreSQL connection using connection pool for multi-threading"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._pool = PostgreSQLConnectionPool(config)
        self._local = threading.local()
    
    def connect(self) -> Any:
        """Connection is handled by pool - returns None as we don't maintain persistent connection"""
        return None
    
    def disconnect(self) -> None:
        """Return connection to pool if exists"""
        if hasattr(self._local, 'conn'):
            self._pool.return_connection(self._local.conn)
            delattr(self._local, 'conn')
    
    @contextmanager
    def get_cursor(self, commit: bool = False):
        """Get cursor with automatic connection management"""
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                if commit:
                    conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()
    
    @contextmanager
    def transaction(self):
        """Transaction context manager"""
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()
    
    def execute_query(self, query: str, params: tuple = None) -> List[tuple]:
        """Execute query and return results"""
        with self.get_cursor(commit=False) as cursor:
            cursor.execute(query, params or ())
            if cursor.description:  # SELECT query
                return cursor.fetchall()
            return []  # Non-SELECT query
    
    def execute_values(self, query: str, values: List[tuple], page_size: int = 1000):
        """Execute batch insert with execute_values"""
        with self.transaction() as cursor:
            extras.execute_values(
                cursor, query, values, template=None, page_size=page_size
            )
    
    def executemany(self, query: str, values: List[tuple], page_size: int = 1000):
        """Execute many with optimal batch size"""
        if not values:
            return
        if query.strip().upper().startswith('INSERT'):
            self.execute_values(query, values, page_size)
        else:
            with self.transaction() as cursor:
                cursor.executemany(query, values)

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
        """Check if current thread has active connection"""
        return hasattr(self._local, 'conn') and not self._local.conn.closed

class PostgreSQLRepository(DatabaseRepository):
    """PostgreSQL repository - simplified for fair comparison with MariaDB"""

    def __init__(self, connection: PostgreSQLConnection):
        self.connection = connection

    def create_table(self, table_name: str, schema: str = None) -> None:
        """Create table in PostgreSQL"""
        if schema:
            query = schema
        else:
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
        query = f"TRUNCATE TABLE {table_name} RESTART IDENTITY"
        with self.connection.transaction() as cursor:
            cursor.execute(query)

    def insert_row(self, table_name: str, data: Dict[str, Any]) -> int:
        """Insert single row and return ID"""
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders}) RETURNING id"

        with self.connection.transaction() as cursor:
            cursor.execute(query, tuple(data.values()))
            result = cursor.fetchone()
            return result[0] if result else None

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