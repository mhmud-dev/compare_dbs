from abc import ABC, abstractmethod
from typing import Any, Dict, List


class DatabaseConnection(ABC):
    """Abstract base class for database connections"""

    @abstractmethod
    def connect(self) -> Any:
        """Establish database connection"""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close database connection"""
        pass

    @abstractmethod
    def execute_query(self, query: str, params: tuple = None) -> Any:
        """Execute a SQL query"""
        pass

    @abstractmethod
    def commit(self) -> None:
        """Commit transaction"""
        pass

    @abstractmethod
    def rollback(self) -> None:
        """Rollback transaction"""
        pass


class DatabaseRepository(ABC):
    """Repository pattern for database operations"""

    @abstractmethod
    def create_table(self, table_name: str, schema: str) -> None:
        """Create a table"""
        pass

    @abstractmethod
    def drop_table(self, table_name: str) -> None:
        """Drop a table"""
        pass

    @abstractmethod
    def truncate_table(self, table_name: str) -> None:
        """Truncate a table"""
        pass

    @abstractmethod
    def insert_row(self, table_name: str, data: Dict[str, Any]) -> int:
        """Insert a single row"""
        pass

    @abstractmethod
    def update_row(self, table_name: str, row_id: int, data: Dict[str, Any]) -> bool:
        """update a single row"""
        pass

    @abstractmethod
    def insert_batch(self, table_name: str, data: List[Dict[str, Any]]) -> int:
        """Insert multiple rows"""
        pass

    @abstractmethod
    def get_table_size(self, table_name: str) -> int:
        """Get number of rows in table"""
        pass


class ConnectionFactory(ABC):
    """Abstract factory for creating database connections"""

    @abstractmethod
    def create_connection(self, config: Any) -> DatabaseConnection:
        """Create a database connection"""
        pass

    @abstractmethod
    def create_repository(self, connection: DatabaseConnection) -> DatabaseRepository:
        """Create a repository for the connection"""
        pass
