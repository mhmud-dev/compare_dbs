from dataclasses import dataclass
from typing import Dict, Any, List
import json
import random
from datetime import datetime


@dataclass
class TestDataGenerator:
    """Generates test data for benchmarks"""

    @staticmethod
    def generate_row(test_name: str, index: int) -> Dict[str, Any]:
        """Generate a single row of test data"""
        return {
            "test_name": test_name,
            "col1": f"test_value_{index}",
            "col2": index,
            "col3": index * random.uniform(0.5, 2.0),
            "col4": f"Long text data for row {index} " * random.randint(1, 3),
            "metadata": json.dumps(
                {
                    "index": index,
                    "type": "test",
                    "timestamp": datetime.now().isoformat(),
                    "random_data": random.randint(1000, 9999),
                }
            ),
        }

    @staticmethod
    def generate_batch(test_name: str, size: int) -> List[Dict[str, Any]]:
        """Generate a batch of test data"""
        return [TestDataGenerator.generate_row(test_name, i) for i in range(size)]
