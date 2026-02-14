from .interfaces import ConnectionFactory, DatabaseConnection, DatabaseRepository
from .mariadb import MariaDBConnection, MariaDBRepository
from .postgres import PostgreSQLConnection, PostgreSQLRepository
from utils.config import ConfigManager


class DatabaseConnectionFactory(ConnectionFactory):
    """Concrete factory for creating database connections"""

    def __init__(self, benchmark_db: str):
        self.benchmark_db = benchmark_db

    def create_connection(self, config: ConfigManager) -> DatabaseConnection:
        """Create appropriate database connection based on config"""
        if self.benchmark_db == "mariadb":
            return MariaDBConnection(config.mariadb_config)
        elif self.benchmark_db == "postgres":
            return PostgreSQLConnection(config.posgres_config)
        else:
            raise ValueError(f"Unsupported database driver: {self.benchmark_db}")

    def create_repository(self, connection: DatabaseConnection) -> DatabaseRepository:
        """Create appropriate repository for the connection"""
        if isinstance(connection, MariaDBConnection):
            return MariaDBRepository(connection)
        elif isinstance(connection, PostgreSQLConnection):
            return PostgreSQLRepository(connection)
        else:
            raise ValueError(f"Unsupported connection type: {type(connection)}")
