"""
token_shredder - Benchmark
Performance analytics and metrics
"""
import time
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class BenchmarkResult:
    file_path: str
    format: str
    processing_time_ms: float
    source_tokens: int
    output_tokens: int
    tokens_saved: int
    tokens_saved_pct: float
    quality_score: float


class Benchmark:
    def __init__(self):
        self.results: List[BenchmarkResult] = []
    
    def record(self, result: BenchmarkResult):
        self.results.append(result)
    
    def summary(self) -> Dict:
        if not self.results:
            return {}
        
        total_saved = sum(r.tokens_saved for r in self.results)
        avg_savings = sum(r.tokens_saved_pct for r in self.results) / len(self.results)
        avg_time = sum(r.processing_time_ms for r in self.results) / len(self.results)
        
        return {
            'files_processed': len(self.results),
            'total_tokens_saved': total_saved,
            'average_savings_pct': round(avg_savings, 1),
            'average_processing_time_ms': round(avg_time, 1),
        }
