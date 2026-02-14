from abc import ABC, abstractmethod
from typing import List
from models.benchmark_results import BenchmarkResult


class BenchmarkStrategy(ABC):
    """Strategy pattern for different benchmark types"""

    @abstractmethod
    def execute(self) -> BenchmarkResult:
        """Execute the benchmark strategy"""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup after benchmark"""
        pass


class BenchmarkObserver(ABC):
    """Observer pattern for benchmark progress"""

    @abstractmethod
    def on_benchmark_start(self, test_name: str) -> None:
        """Called when benchmark starts"""
        pass

    @abstractmethod
    def on_iteration_complete(self, current: int, total: int) -> None:
        """Called after each iteration"""
        pass

    @abstractmethod
    def on_benchmark_complete(self, result: BenchmarkResult) -> None:
        """Called when benchmark completes"""
        pass


class BenchmarkSubject(ABC):
    """Subject for observer pattern"""

    def __init__(self):
        self._observers: List[BenchmarkObserver] = []

    def attach(self, observer: BenchmarkObserver) -> None:
        """Attach an observer"""
        self._observers.append(observer)

    def detach(self, observer: BenchmarkObserver) -> None:
        """Detach an observer"""
        self._observers.remove(observer)

    def notify_start(self, test_name: str) -> None:
        """Notify observers of benchmark start"""
        for observer in self._observers:
            observer.on_benchmark_start(test_name)

    def notify_iteration(self, current: int, total: int) -> None:
        """Notify observers of iteration completion"""
        for observer in self._observers:
            observer.on_iteration_complete(current, total)

    def notify_complete(self, result: BenchmarkResult) -> None:
        """Notify observers of benchmark completion"""
        for observer in self._observers:
            observer.on_benchmark_complete(result)
