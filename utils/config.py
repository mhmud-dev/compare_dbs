from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from dataclasses import dataclass


class DatabaseConfig(BaseModel):
    user: str
    password: str
    host: str
    port: int
    database: str
    table: str


class MariaDBConfig(DatabaseConfig, BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MARIADB_", env_file=".env", extra="allow"
    )


class PostgresConfig(DatabaseConfig, BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="POSTGRES_", env_file=".env", extra="allow"
    )


@dataclass
class BenchmarkConfig:
    """Benchmark configuration"""

    iterations: int = 1000
    warmup_iterations: int = 100
    batch_sizes: tuple = (10, 100, 1000, 5000)
    workers: tuple = (5, 10, 15, 20)
    test_scenarios: tuple = ("single_insert", "batch_insert", "concurrent_insert")
    result_output_dir: str = "./results"

    def validate(self) -> None:
        """Validate configuration"""
        if self.iterations <= 0:
            raise ValueError("Iterations must be positive")
        if self.warmup_iterations < 0:
            raise ValueError("Warmup iterations cannot be negative")


class ConfigManager:
    """Manages application configuration"""

    def __init__(self, iterations=1000, warmup_iterations=100):
        self.posgres_config: PostgresConfig = PostgresConfig()
        self.mariadb_config: MariaDBConfig = MariaDBConfig()
        self.benchmark_config: BenchmarkConfig = BenchmarkConfig(
            iterations=iterations, warmup_iterations=warmup_iterations
        )

    def load_benchmark_config(self) -> BenchmarkConfig:
        """Load benchmark configuration"""
        return BenchmarkConfig(iterations=1000, warmup_iterations=100)


postgres_config = PostgresConfig()
mariadb_config = MariaDBConfig()
