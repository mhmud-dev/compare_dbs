from dataclasses import dataclass, field
from typing import List, Dict, Any
from datetime import datetime
import statistics


@dataclass
class BenchmarkMetrics:
    """Metrics collected during benchmark"""

    timings: List[float] = field(default_factory=list)
    start_time: datetime = None
    end_time: datetime = None

    @property
    def total_time(self) -> float:
        """Total execution time in seconds"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0

    @property
    def average_time(self) -> float:
        """Average time per operation in milliseconds"""
        if self.timings:
            return statistics.mean(self.timings) * 1000
        return 0

    @property
    def median_time(self) -> float:
        """Median time per operation in milliseconds"""
        if self.timings:
            return statistics.median(self.timings) * 1000
        return 0

    @property
    def percentile_95(self) -> float:
        """95th percentile time in milliseconds"""
        if self.timings:
            return sorted(self.timings)[int(len(self.timings) * 0.95)] * 1000
        return 0

    @property
    def percentile_99(self) -> float:
        """99th percentile time in milliseconds"""
        if self.timings:
            return sorted(self.timings)[int(len(self.timings) * 0.99)] * 1000
        return 0

    @property
    def throughput(self) -> float:
        """Operations per second"""
        if self.total_time > 0:
            return len(self.timings) / self.total_time
        return 0


@dataclass
class BenchmarkResult:
    """Complete benchmark result"""

    database_type: str
    test_name: str
    iterations: int
    metrics: BenchmarkMetrics
    configuration: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            "database_type": self.database_type,
            "test_name": self.test_name,
            "iterations": self.iterations,
            "total_time": self.metrics.total_time,
            "average_time_ms": self.metrics.average_time,
            "median_time_ms": self.metrics.median_time,
            "p95_time_ms": self.metrics.percentile_95,
            "p99_time_ms": self.metrics.percentile_99,
            "throughput_qps": self.metrics.throughput,
            "timestamp": self.timestamp.isoformat(),
        }
