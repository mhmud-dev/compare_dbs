import time
from abc import ABC, abstractmethod
from .interfaces import BenchmarkStrategy, BenchmarkSubject
from database.interfaces import DatabaseRepository
from models.benchmark_results import BenchmarkResult, BenchmarkMetrics
from models.test_data import TestDataGenerator


class BaseBenchmark(BenchmarkStrategy, BenchmarkSubject, ABC):
    """Base class for all benchmarks"""

    def __init__(
        self,
        repository: DatabaseRepository,
        database_type: str,
        test_name: str,
        table_name: str,
        iterations: int,
        warmup_iterations: int = 100,
    ):
        super().__init__()
        self.repository = repository
        self.database_type = database_type
        self.test_name = test_name
        self.iterations = iterations
        self.warmup_iterations = warmup_iterations
        self.table_name = table_name
        self.data_generator = TestDataGenerator()

    def _setup(self) -> None:
        """Setup benchmark environment"""
        self.repository.create_table(self.table_name, "")

    def _teardown(self) -> None:
        """Teardown benchmark environment"""
        self.repository.truncate_table(self.table_name)

    def _warmup(self) -> None:
        """Warmup phase to avoid cold start"""
        print(f"  Warming up ({self.warmup_iterations} iterations)...")
        for i in range(self.warmup_iterations):
            data = self.data_generator.generate_row(self.test_name, i)
            self.repository.insert_row(self.table_name, data)
        self.repository.truncate_table(self.table_name)

    @abstractmethod
    def _execute_benchmark(self, metrics: BenchmarkMetrics) -> None:
        """Execute the specific benchmark logic"""
        pass

    def execute(self) -> BenchmarkResult:
        """Execute the benchmark"""
        print(f"\n{'='*60}")
        print(f"Starting {self.database_type.upper()} - {self.test_name}")
        print(f"{'='*60}")

        self.notify_start(self.test_name)

        # Setup
        self._setup()

        # Warmup
        self._warmup()

        # Prepare metrics
        metrics = BenchmarkMetrics()
        metrics.start_time = time.time()

        # Execute benchmark
        self._execute_benchmark(metrics)

        # Finalize metrics
        metrics.end_time = time.time()

        # Create result
        result = BenchmarkResult(
            database_type=self.database_type,
            test_name=self.test_name,
            iterations=self.iterations,
            metrics=metrics,
            configuration={
                "warmup_iterations": self.warmup_iterations,
                "table_name": self.table_name,
            },
        )

        # Notify completion
        self.notify_complete(result)

        # Cleanup
        self._teardown()

        return result

    def cleanup(self) -> None:
        """Cleanup resources"""
        self.repository.drop_table(self.table_name)
