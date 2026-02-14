from datetime import datetime
from utils.config import ConfigManager
from database.connection_factory import DatabaseConnectionFactory
from benchmark.strategies import SingleInsertBenchmark, BatchInsertBenchmark
from metrics.collector import MetricsCollector
from metrics.reporter import ReportGenerator


class BenchmarkRunner:
    """Main orchestrator for running benchmarks"""

    def __init__(self, config_manager: ConfigManager, benchmark_db: str):
        self.benchmark_db = benchmark_db
        if self.benchmark_db == "mariadb":
            self.db_config = config_manager.mariadb_config
        elif self.benchmark_db == "postgres":
            self.db_config = config_manager.posgres_config
        else:
            raise ValueError(f"benchmark db {benchmark_db} is not valid")
        self.config_manager = config_manager
        self.connection_factory = DatabaseConnectionFactory(benchmark_db)
        self.metrics_collector = MetricsCollector()
        self.report_generator = ReportGenerator()
        self.benchmark_config = config_manager.benchmark_config

    def run_single_insert_benchmark(self) -> None:
        """Run single insert benchmark for all databases"""
        print("\n" + "=" * 80)
        print("RUNNING SINGLE INSERT BENCHMARK")
        print("=" * 80)
        connection = self.connection_factory.create_connection(self.config_manager)
        repository = self.connection_factory.create_repository(connection)
        benchmark = SingleInsertBenchmark(
            repository=repository,
            database_type=self.db_config.database,
            test_name="single_insert",
            table_name=self.db_config.table,
            iterations=self.benchmark_config.iterations,
            warmup_iterations=self.benchmark_config.warmup_iterations,
        )
        benchmark.attach(self.metrics_collector)
        try:
            connection.connect()
            benchmark.execute()
        finally:
            benchmark.cleanup()
            connection.disconnect()

    def run_batch_insert_benchmark(self) -> None:
        """Run batch insert benchmark for all databases"""
        print("\n" + "=" * 80)
        print("RUNNING BATCH INSERT BENCHMARK")
        print("=" * 80)
        connection = self.connection_factory.create_connection(self.config_manager)
        repository = self.connection_factory.create_repository(connection)
        for batch_size in self.benchmark_config.batch_sizes:
            benchmark = BatchInsertBenchmark(
                repository=repository,
                database_type=self.db_config.database,
                test_name=f"batch_insert_{batch_size}",
                table_name=self.db_config.table,
                iterations=self.benchmark_config.iterations,
                warmup_iterations=self.benchmark_config.warmup_iterations,
                batch_size=batch_size,
            )
            benchmark.attach(self.metrics_collector)
            try:
                connection.connect()
                benchmark.execute()
            finally:
                benchmark.cleanup()
                connection.disconnect()

    def generate_reports(self) -> None:
        """Generate all reports"""
        results = self.metrics_collector.results
        if not results:
            print("No results to generate reports!")
            return
        text_report = self.report_generator.generate_text_report(results)
        print("\n" + text_report)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.report_generator.output_dir / f"report_{timestamp}.txt"
        with open(report_file, "w") as f:
            f.write(text_report)
        print(f"\nText report saved: {report_file}")
        self.report_generator.generate_comparison_chart(results)
        csv_file = self.report_generator.save_results_to_csv(results)
        print(f"CSV results saved: {csv_file}")

    def run_all_benchmarks(self) -> None:
        """Run all configured benchmarks"""
        print("Starting comprehensive database benchmark suite...")
        self.run_single_insert_benchmark()
        self.run_batch_insert_benchmark()
        self.generate_reports()
        print("\n" + "=" * 80)
        print("BENCHMARK COMPLETED SUCCESSFULLY!")
        print("=" * 80)
