import argparse
import sys
from pathlib import Path
import os
from utils.config import ConfigManager
from benchmark.benchmark_runner import BenchmarkRunner


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Database Benchmark Tool - Compare MariaDB vs PostgreSQL"
    )

    parser.add_argument(
        "--test",
        type=str,
        choices=["single", "batch", "all"],
        default="all",
        help="Test type to run (default: all)",
    )

    parser.add_argument(
        "--iterations",
        type=int,
        default=1000,
        help="Number of iterations per test (default: 1000)",
    )

    parser.add_argument(
        "--warmup",
        type=int,
        default=100,
        help="Number of warmup iterations (default: 100)",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="./benchmark_results",
        help="Output directory for reports (default: ./benchmark_results)",
    )

    parser.add_argument(
        "--db",
        type=str,
        choices=["postgres", "mariadb"],
        default="postgres",
        help="Test DB (default: postgres)",
    )

    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_args()
    print("\n" + "=" * 80)
    print("DATABASE BENCHMARK TOOL")
    print("=" * 80)
    try:
        config_manager = ConfigManager(args.iterations, args.warmup)
        runner = BenchmarkRunner(config_manager, args.db)
        runner.report_generator.output_dir = Path(args.output_dir)
        os.makedirs(args.output_dir, exist_ok=True)
        if args.test == "single" or args.test == "all":
            runner.run_single_insert_benchmark()
        if args.test == "batch" or args.test == "all":
            runner.run_batch_insert_benchmark()
        runner.generate_reports()
    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
