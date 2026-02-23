import time
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
from benchmark.base_benchmark import BaseBenchmark
from models.benchmark_results import BenchmarkMetrics, BenchmarkResult


class SingleInsertBenchmark(BaseBenchmark):
    """Benchmark for single row inserts"""

    def _execute_benchmark(self, metrics: BenchmarkMetrics) -> None:
        """Execute single insert benchmark"""
        print(f"  Running single insert benchmark ({self.iterations} iterations)...")

        for i in range(self.iterations):
            iteration_start = time.time()
            data = self.data_generator.generate_row(self.test_name, i)
            self.repository.insert_row(self.table_name, data)
            iteration_time = time.time() - iteration_start
            metrics.timings.append(iteration_time)
            self.notify_iteration(i + 1, self.iterations)


class BatchInsertBenchmark(BaseBenchmark):
    """Benchmark for batch inserts"""

    def __init__(self, batch_size: int = 100, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.batch_size = batch_size

    def _execute_benchmark(self, metrics: BenchmarkMetrics) -> None:
        """Execute batch insert benchmark"""
        print(f"  Running batch insert benchmark (batch size: {self.batch_size})...")

        total_batches = (self.iterations + self.batch_size - 1) // self.batch_size

        for batch_num in range(total_batches):
            iteration_start = time.time()
            start_idx = batch_num * self.batch_size
            end_idx = min(start_idx + self.batch_size, self.iterations)
            batch_data = self.data_generator.generate_batch(
                self.test_name, end_idx - start_idx
            )
            self.repository.insert_batch(self.table_name, batch_data)
            batch_time = time.time() - iteration_start
            per_row_time = batch_time / len(batch_data) if batch_data else 0

            for _ in batch_data:
                metrics.timings.append(per_row_time)
            self.notify_iteration(batch_num + 1, total_batches)


class ConcurrentInsertBenchmark(BaseBenchmark):
    """Benchmark for concurrent inserts"""

    def __init__(self, max_workers: int = 5, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_workers = max_workers

    def _insert_worker(
        self, worker_id: int, num_inserts: int, metrics: BenchmarkMetrics
    ) -> List[float]:
        """Worker function for concurrent inserts"""
        worker_timings = []
        for i in range(num_inserts):
            iteration_start = time.time()
            data = self.data_generator.generate_row(
                f"{self.test_name}_worker{worker_id}", worker_id * 1000 + i
            )
            self.repository.insert_row(self.table_name, data)
            iteration_time = time.time() - iteration_start
            worker_timings.append(iteration_time)
            self.notify_iteration(i + 1, self.iterations)
        return worker_timings

    def _execute_benchmark(self, metrics: BenchmarkMetrics) -> None:
        """Execute concurrent insert benchmark"""
        print(f"  Running concurrent insert benchmark ({self.max_workers} workers)...")

        inserts_per_worker = self.iterations // self.max_workers

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []

            # Submit worker tasks
            for worker_id in range(self.max_workers):
                future = executor.submit(
                    self._insert_worker, worker_id, inserts_per_worker, metrics
                )
                futures.append(future)

            # Collect results
            for future in as_completed(futures):
                worker_timings = future.result()
                metrics.timings.extend(worker_timings)


class FillTables(BatchInsertBenchmark):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.batch_size = 1000

    def execute(self) -> BenchmarkResult:
        """Execute the benchmark"""
        print(f"\n{'='*60}")
        print(f"Starting {self.database_type.upper()} - {self.test_name}")
        print(f"{'='*60}")
        self.notify_start(self.test_name)
        # Setup
        self._setup()
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
        return result
