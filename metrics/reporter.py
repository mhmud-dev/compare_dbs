import pandas as pd
import matplotlib.pyplot as plt
from typing import List
from pathlib import Path
from datetime import datetime
from models.benchmark_results import BenchmarkResult


class ReportGenerator:
    """Generates reports from benchmark results"""

    def __init__(self, output_dir: str = "./reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_text_report(self, results: List[BenchmarkResult]) -> str:
        """Generate text report"""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("DATABASE BENCHMARK REPORT")
        report_lines.append("=" * 80)
        report_lines.append(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        report_lines.append("")

        # Group by database type
        grouped_results = {}
        for result in results:
            if result.database_type not in grouped_results:
                grouped_results[result.database_type] = []
            grouped_results[result.database_type].append(result)

        for db_type, db_results in grouped_results.items():
            report_lines.append(f"\n{'='*40}")
            report_lines.append(f"{db_type.upper()}")
            report_lines.append(f"{'='*40}")

            for result in db_results:
                report_lines.append(f"\nTest: {result.test_name}")
                report_lines.append(f"  Iterations: {result.iterations}")
                report_lines.append(f"  Total Time: {result.metrics.total_time:.2f} s")
                report_lines.append(
                    f"  Average Time: {result.metrics.average_time:.2f} ms"
                )
                report_lines.append(
                    f"  Median Time: {result.metrics.median_time:.2f} ms"
                )
                report_lines.append(
                    f"  95th Percentile: {result.metrics.percentile_95:.2f} ms"
                )
                report_lines.append(
                    f"  99th Percentile: {result.metrics.percentile_99:.2f} ms"
                )
                report_lines.append(
                    f"  Throughput: {result.metrics.throughput:.2f} ops/sec"
                )

        return "\n".join(report_lines)

    def generate_comparison_chart(self, results: List[BenchmarkResult]) -> None:
        """Generate comparison charts"""
        if not results:
            return
        test_groups = {}
        for result in results:
            if result.test_name not in test_groups:
                test_groups[result.test_name] = []
            test_groups[result.test_name].append(result)
        for test_name, test_results in test_groups.items():
            self._create_test_comparison_chart(test_name, test_results)

    def _create_test_comparison_chart(
        self, test_name: str, results: List[BenchmarkResult]
    ) -> None:
        """Create comparison chart for a specific test"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f"Benchmark Comparison: {test_name}", fontsize=16)
        db_types = [r.database_type for r in results]
        ax1 = axes[0, 0]
        metrics = ["average_time", "median_time"]
        metric_labels = ["Average", "Median"]
        for i, result in enumerate(results):
            avg_times = [result.metrics.average_time]
            med_times = [result.metrics.median_time]
            ax1.bar(
                i - 0.2,
                avg_times,
                width=0.4,
                label=f"{result.database_type} Avg",
                alpha=0.8,
            )
            ax1.bar(
                i + 0.2,
                med_times,
                width=0.4,
                label=f"{result.database_type} Med",
                alpha=0.8,
            )
        ax1.set_xlabel("Database")
        ax1.set_ylabel("Time (ms)")
        ax1.set_title("Insert Time Comparison")
        ax1.set_xticks(range(len(results)))
        ax1.set_xticklabels(db_types)
        ax2 = axes[0, 1]
        throughputs = [r.metrics.throughput for r in results]
        bars = ax2.bar(db_types, throughputs, alpha=0.7)
        for bar, throughput in zip(bars, throughputs):
            height = bar.get_height()
            ax2.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{throughput:.1f}",
                ha="center",
                va="bottom",
            )
        ax2.set_ylabel("Operations/Second")
        ax2.set_title("Throughput Comparison")
        ax3 = axes[1, 0]
        x = range(len(results))
        width = 0.35
        p95 = [r.metrics.percentile_95 for r in results]
        p99 = [r.metrics.percentile_99 for r in results]
        ax3.bar([i - width / 2 for i in x], p95, width, label="95th %", alpha=0.7)
        ax3.bar([i + width / 2 for i in x], p99, width, label="99th %", alpha=0.7)
        ax3.set_xlabel("Database")
        ax3.set_ylabel("Time (ms)")
        ax3.set_title("Percentile Performance")
        ax3.set_xticks(x)
        ax3.set_xticklabels(db_types)
        ax3.legend()
        ax4 = axes[1, 1]
        total_times = [r.metrics.total_time for r in results]
        bars = ax4.bar(
            db_types, total_times, alpha=0.7, color=["skyblue", "lightcoral"]
        )
        ax4.set_ylabel("Total Time (s)")
        ax4.set_title("Total Execution Time")
        plt.tight_layout()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.output_dir / f"comparison_{test_name}_{timestamp}.png"
        plt.savefig(filename, dpi=300, bbox_inches="tight")
        plt.close()
        print(f"Chart saved: {filename}")

    def save_results_to_csv(self, results: List[BenchmarkResult]) -> Path:
        """Save results to CSV file"""
        data = [result.to_dict() for result in results]
        df = pd.DataFrame(data)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.output_dir / f"benchmark_results_{timestamp}.csv"
        df.to_csv(filename, index=False)
        return filename
