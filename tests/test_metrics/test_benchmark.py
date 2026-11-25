"""
token_shredder - Test Benchmark
"""
import pytest
from token_shredder.metrics.benchmark import Benchmark, BenchmarkResult


def test_benchmark_instantiation():
    benchmark = Benchmark()
    assert benchmark is not None


def test_benchmark_record():
    benchmark = Benchmark()
    result = BenchmarkResult(
        file_path="test.pdf",
        format="pdf",
        processing_time_ms=100.0,
        source_tokens=1000,
        output_tokens=500,
        tokens_saved=500,
        tokens_saved_pct=50.0,
        quality_score=95.0,
    )
    benchmark.record(result)
    assert len(benchmark.results) == 1


def test_benchmark_summary():
    benchmark = Benchmark()
    benchmark.record(BenchmarkResult(
        file_path="test.pdf",
        format="pdf",
        processing_time_ms=100.0,
        source_tokens=1000,
        output_tokens=500,
        tokens_saved=500,
        tokens_saved_pct=50.0,
        quality_score=95.0,
    ))
    summary = benchmark.summary()
    assert summary['files_processed'] == 1
    assert summary['total_tokens_saved'] == 500
