from typing import List, Dict, Any
from models.benchmark_results import BenchmarkResult
from benchmark.interfaces import BenchmarkObserver


class MetricsCollector(BenchmarkObserver):
    """Collects and stores benchmark metrics"""

    def __init__(self):
        self.results: List[BenchmarkResult] = []
        self.current_test = None

    def on_benchmark_start(self, test_name: str) -> None:
        """Handle benchmark start"""
        self.current_test = test_name
        print(f"\n[Collector] Started collecting metrics for: {test_name}")

    def on_iteration_complete(self, current: int, total: int) -> None:
        """Handle iteration completion"""
        if current % 100 == 0 or current == total:
            print(f"  [Progress] {current}/{total} ({current/total*100:.1f}%)")

    def on_benchmark_complete(self, result: BenchmarkResult) -> None:
        """Handle benchmark completion"""
        self.results.append(result)
        print(f"[Collector] Completed: {result.database_type} - {result.test_name}")
        print(f"  Average: {result.metrics.average_time:.2f} ms")
        print(f"  Throughput: {result.metrics.throughput:.2f} ops/sec")

    def get_results_by_database(self, database_type: str) -> List[BenchmarkResult]:
        """Get results filtered by database type"""
        return [r for r in self.results if r.database_type == database_type]

    def get_comparison_data(self) -> Dict[str, Any]:
        """Get data for comparison between databases"""
        comparison = {}
        for result in self.results:
            db_type = result.database_type
            test_name = result.test_name
            if db_type not in comparison:
                comparison[db_type] = {}
            comparison[db_type][test_name] = result.to_dict()
        return comparison
