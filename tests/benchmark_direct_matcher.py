"""
Performance Benchmarks for Direct Matching Layer

This module contains performance benchmarks for the Direct Matching layer,
testing various scenarios with large datasets and complex matching operations.
"""

import time
import statistics
import random
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

from src.core.matching.direct_matcher import DirectMatcher, DirectMatchResult
from src.core.domains.cooking.direct_matcher import CookingDirectMatcher
from src.core.domains.manufacturing.direct_matcher import MfgDirectMatcher


@dataclass
class BenchmarkResult:
    """Result of a benchmark test."""
    test_name: str
    iterations: int
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    median_time: float
    std_dev: float
    throughput: float  # operations per second
    memory_usage: float  # approximate memory usage in MB


class DirectMatcherBenchmark:
    """Benchmark suite for Direct Matching layer."""
    
    def __init__(self):
        """Initialize benchmark suite."""
        self.cooking_matcher = CookingDirectMatcher()
        self.mfg_matcher = MfgDirectMatcher()
        
        # Generate test datasets
        self.cooking_ingredients = self._generate_cooking_ingredients()
        self.cooking_equipment = self._generate_cooking_equipment()
        self.mfg_materials = self._generate_mfg_materials()
        self.mfg_tools = self._generate_mfg_tools()
    
    def _generate_cooking_ingredients(self, count: int = 1000) -> List[str]:
        """Generate test cooking ingredients."""
        base_ingredients = [
            "flour", "sugar", "salt", "pepper", "butter", "oil", "garlic", "onion",
            "tomato", "cheese", "milk", "egg", "chicken", "beef", "pork", "fish",
            "rice", "pasta", "bread", "herbs", "spices", "vegetables", "fruits",
            "nuts", "seeds", "cream", "yogurt", "honey", "vinegar", "soy sauce"
        ]
        
        ingredients = []
        for i in range(count):
            base = random.choice(base_ingredients)
            # Add variations
            if random.random() < 0.3:
                base = base.capitalize()  # Case variation
            if random.random() < 0.2:
                base = f"{base} "  # Whitespace variation
            if random.random() < 0.1:
                base = base.replace('a', 'e')  # Typo variation
            ingredients.append(base)
        
        return ingredients
    
    def _generate_cooking_equipment(self, count: int = 1000) -> List[str]:
        """Generate test cooking equipment."""
        base_equipment = [
            "knife", "cutting board", "pan", "pot", "skillet", "wok", "oven",
            "stove", "microwave", "blender", "food processor", "mixer", "whisk",
            "spatula", "tongs", "ladle", "spoon", "fork", "grater", "peeler"
        ]
        
        equipment = []
        for i in range(count):
            base = random.choice(base_equipment)
            # Add variations
            if random.random() < 0.3:
                base = base.upper()  # Case variation
            if random.random() < 0.2:
                base = f" {base}"  # Whitespace variation
            if random.random() < 0.1:
                base = base.replace('i', 'y')  # Typo variation
            equipment.append(base)
        
        return equipment
    
    def _generate_mfg_materials(self, count: int = 1000) -> List[str]:
        """Generate test manufacturing materials."""
        base_materials = [
            "steel", "aluminum", "copper", "brass", "bronze", "iron", "titanium",
            "stainless steel", "carbon steel", "alloy", "plastic", "polymer",
            "ceramic", "composite", "wood", "glass", "rubber", "fiber"
        ]
        
        materials = []
        for i in range(count):
            base = random.choice(base_materials)
            # Add variations
            if random.random() < 0.3:
                base = base.title()  # Case variation
            if random.random() < 0.2:
                base = f"{base} "  # Whitespace variation
            if random.random() < 0.1:
                base = base.replace('e', 'a')  # Typo variation
            materials.append(base)
        
        return materials
    
    def _generate_mfg_tools(self, count: int = 1000) -> List[str]:
        """Generate test manufacturing tools."""
        base_tools = [
            "drill", "mill", "lathe", "grinder", "sander", "polisher", "cutter",
            "saw", "shear", "press", "punch", "die", "mold", "fixture", "jig",
            "clamp", "vise", "chuck", "collet", "mandrel", "reamer", "tap"
        ]
        
        tools = []
        for i in range(count):
            base = random.choice(base_tools)
            # Add variations
            if random.random() < 0.3:
                base = base.upper()  # Case variation
            if random.random() < 0.2:
                base = f" {base} "  # Whitespace variation
            if random.random() < 0.1:
                base = base.replace('r', 'l')  # Typo variation
            tools.append(base)
        
        return tools
    
    def benchmark_single_match(self, matcher: DirectMatcher, requirement: str, 
                             capabilities: List[str], iterations: int = 100) -> BenchmarkResult:
        """Benchmark single requirement matching against capabilities."""
        times = []
        
        for _ in range(iterations):
            start_time = time.perf_counter()
            results = matcher.match(requirement, capabilities)
            end_time = time.perf_counter()
            times.append(end_time - start_time)
        
        return self._calculate_benchmark_result(
            "single_match", iterations, times, len(capabilities)
        )
    
    def benchmark_multiple_requirements(self, matcher: DirectMatcher, 
                                      requirements: List[str], capabilities: List[str],
                                      iterations: int = 10) -> BenchmarkResult:
        """Benchmark multiple requirements matching against capabilities."""
        times = []
        
        for _ in range(iterations):
            start_time = time.perf_counter()
            all_results = []
            for req in requirements:
                results = matcher.match(req, capabilities)
                all_results.extend(results)
            end_time = time.perf_counter()
            times.append(end_time - start_time)
        
        return self._calculate_benchmark_result(
            "multiple_requirements", iterations, times, 
            len(requirements) * len(capabilities)
        )
    
    def benchmark_domain_specific_matching(self, matcher: DirectMatcher,
                                         test_data: Dict[str, List[str]],
                                         iterations: int = 10) -> Dict[str, BenchmarkResult]:
        """Benchmark domain-specific matching methods."""
        results = {}
        
        for category, items in test_data.items():
            if category == "ingredients" and hasattr(matcher, 'match_ingredients'):
                times = []
                for _ in range(iterations):
                    start_time = time.perf_counter()
                    matcher.match_ingredients(items[:10], items[10:100])
                    end_time = time.perf_counter()
                    times.append(end_time - start_time)
                results[category] = self._calculate_benchmark_result(
                    f"domain_specific_{category}", iterations, times, 90
                )
            
            elif category == "equipment" and hasattr(matcher, 'match_equipment'):
                times = []
                for _ in range(iterations):
                    start_time = time.perf_counter()
                    matcher.match_equipment(items[:10], items[10:100])
                    end_time = time.perf_counter()
                    times.append(end_time - start_time)
                results[category] = self._calculate_benchmark_result(
                    f"domain_specific_{category}", iterations, times, 90
                )
            
            elif category == "materials" and hasattr(matcher, 'match_materials'):
                times = []
                for _ in range(iterations):
                    start_time = time.perf_counter()
                    matcher.match_materials(items[:10], items[10:100])
                    end_time = time.perf_counter()
                    times.append(end_time - start_time)
                results[category] = self._calculate_benchmark_result(
                    f"domain_specific_{category}", iterations, times, 90
                )
            
            elif category == "tools" and hasattr(matcher, 'match_tools'):
                times = []
                for _ in range(iterations):
                    start_time = time.perf_counter()
                    matcher.match_tools(items[:10], items[10:100])
                    end_time = time.perf_counter()
                    times.append(end_time - start_time)
                results[category] = self._calculate_benchmark_result(
                    f"domain_specific_{category}", iterations, times, 90
                )
        
        return results
    
    def benchmark_levenshtein_distance(self, iterations: int = 1000) -> BenchmarkResult:
        """Benchmark Levenshtein distance calculation."""
        times = []
        
        # Generate test string pairs
        test_pairs = []
        for _ in range(iterations):
            str1 = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=random.randint(5, 50)))
            str2 = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=random.randint(5, 50)))
            test_pairs.append((str1, str2))
        
        for str1, str2 in test_pairs:
            start_time = time.perf_counter()
            self.cooking_matcher._levenshtein_distance(str1, str2)
            end_time = time.perf_counter()
            times.append(end_time - start_time)
        
        return self._calculate_benchmark_result(
            "levenshtein_distance", iterations, times, iterations
        )
    
    def benchmark_memory_usage(self, matcher: DirectMatcher, 
                             capabilities: List[str], iterations: int = 100) -> BenchmarkResult:
        """Benchmark memory usage during matching operations."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        times = []
        for _ in range(iterations):
            start_time = time.perf_counter()
            results = matcher.match("test_requirement", capabilities)
            end_time = time.perf_counter()
            times.append(end_time - start_time)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_usage = final_memory - initial_memory
        
        result = self._calculate_benchmark_result(
            "memory_usage", iterations, times, len(capabilities)
        )
        result.memory_usage = memory_usage
        return result
    
    def _calculate_benchmark_result(self, test_name: str, iterations: int, 
                                  times: List[float], operations: int) -> BenchmarkResult:
        """Calculate benchmark result statistics."""
        total_time = sum(times)
        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        median_time = statistics.median(times)
        std_dev = statistics.stdev(times) if len(times) > 1 else 0.0
        throughput = operations / total_time if total_time > 0 else 0.0
        
        return BenchmarkResult(
            test_name=test_name,
            iterations=iterations,
            total_time=total_time,
            avg_time=avg_time,
            min_time=min_time,
            max_time=max_time,
            median_time=median_time,
            std_dev=std_dev,
            throughput=throughput,
            memory_usage=0.0  # Will be set separately for memory tests
        )
    
    def run_all_benchmarks(self) -> Dict[str, Any]:
        """Run all benchmark tests and return results."""
        results = {
            "cooking_domain": {},
            "manufacturing_domain": {},
            "algorithms": {}
        }
        
        print("Running Direct Matcher Benchmarks...")
        print("=" * 50)
        
        # Cooking domain benchmarks
        print("\nCooking Domain Benchmarks:")
        print("-" * 30)
        
        # Single match benchmarks
        small_capabilities = self.cooking_ingredients[:100]
        medium_capabilities = self.cooking_ingredients[:500]
        large_capabilities = self.cooking_ingredients[:1000]
        
        results["cooking_domain"]["small_single_match"] = self.benchmark_single_match(
            self.cooking_matcher, "flour", small_capabilities
        )
        results["cooking_domain"]["medium_single_match"] = self.benchmark_single_match(
            self.cooking_matcher, "flour", medium_capabilities
        )
        results["cooking_domain"]["large_single_match"] = self.benchmark_single_match(
            self.cooking_matcher, "flour", large_capabilities
        )
        
        # Multiple requirements benchmarks
        small_requirements = self.cooking_ingredients[:10]
        results["cooking_domain"]["multiple_requirements"] = self.benchmark_multiple_requirements(
            self.cooking_matcher, small_requirements, medium_capabilities
        )
        
        # Domain-specific benchmarks
        cooking_data = {
            "ingredients": self.cooking_ingredients,
            "equipment": self.cooking_equipment
        }
        results["cooking_domain"]["domain_specific"] = self.benchmark_domain_specific_matching(
            self.cooking_matcher, cooking_data
        )
        
        # Manufacturing domain benchmarks
        print("\nManufacturing Domain Benchmarks:")
        print("-" * 30)
        
        # Single match benchmarks
        small_mfg_capabilities = self.mfg_materials[:100]
        medium_mfg_capabilities = self.mfg_materials[:500]
        large_mfg_capabilities = self.mfg_materials[:1000]
        
        results["manufacturing_domain"]["small_single_match"] = self.benchmark_single_match(
            self.mfg_matcher, "steel", small_mfg_capabilities
        )
        results["manufacturing_domain"]["medium_single_match"] = self.benchmark_single_match(
            self.mfg_matcher, "steel", medium_mfg_capabilities
        )
        results["manufacturing_domain"]["large_single_match"] = self.benchmark_single_match(
            self.mfg_matcher, "steel", large_mfg_capabilities
        )
        
        # Multiple requirements benchmarks
        small_mfg_requirements = self.mfg_materials[:10]
        results["manufacturing_domain"]["multiple_requirements"] = self.benchmark_multiple_requirements(
            self.mfg_matcher, small_mfg_requirements, medium_mfg_capabilities
        )
        
        # Domain-specific benchmarks
        mfg_data = {
            "materials": self.mfg_materials,
            "tools": self.mfg_tools
        }
        results["manufacturing_domain"]["domain_specific"] = self.benchmark_domain_specific_matching(
            self.mfg_matcher, mfg_data
        )
        
        # Algorithm benchmarks
        print("\nAlgorithm Benchmarks:")
        print("-" * 30)
        
        results["algorithms"]["levenshtein_distance"] = self.benchmark_levenshtein_distance()
        
        # Memory usage benchmarks
        results["cooking_domain"]["memory_usage"] = self.benchmark_memory_usage(
            self.cooking_matcher, medium_capabilities
        )
        results["manufacturing_domain"]["memory_usage"] = self.benchmark_memory_usage(
            self.mfg_matcher, medium_mfg_capabilities
        )
        
        return results
    
    def print_benchmark_results(self, results: Dict[str, Any]):
        """Print benchmark results in a formatted way."""
        print("\n" + "=" * 80)
        print("BENCHMARK RESULTS SUMMARY")
        print("=" * 80)
        
        for domain, domain_results in results.items():
            if domain == "algorithms":
                continue
                
            print(f"\n{domain.upper()} DOMAIN:")
            print("-" * 40)
            
            for test_name, result in domain_results.items():
                if isinstance(result, dict):
                    print(f"\n  {test_name}:")
                    for sub_test, sub_result in result.items():
                        self._print_single_result(f"    {sub_test}", sub_result)
                else:
                    self._print_single_result(f"  {test_name}", result)
        
        print(f"\nALGORITHMS:")
        print("-" * 40)
        for test_name, result in results["algorithms"].items():
            self._print_single_result(f"  {test_name}", result)
    
    def _print_single_result(self, test_name: str, result: BenchmarkResult):
        """Print a single benchmark result."""
        print(f"{test_name}:")
        print(f"    Iterations: {result.iterations}")
        print(f"    Total Time: {result.total_time:.4f}s")
        print(f"    Average Time: {result.avg_time:.6f}s")
        print(f"    Min Time: {result.min_time:.6f}s")
        print(f"    Max Time: {result.max_time:.6f}s")
        print(f"    Median Time: {result.median_time:.6f}s")
        print(f"    Std Dev: {result.std_dev:.6f}s")
        print(f"    Throughput: {result.throughput:.2f} ops/sec")
        if result.memory_usage > 0:
            print(f"    Memory Usage: {result.memory_usage:.2f} MB")


def main():
    """Run all benchmarks and print results."""
    benchmark = DirectMatcherBenchmark()
    results = benchmark.run_all_benchmarks()
    benchmark.print_benchmark_results(results)
    
    # Save results to file
    import json
    with open("benchmark_results.json", "w") as f:
        # Convert results to JSON-serializable format
        json_results = {}
        for domain, domain_results in results.items():
            json_results[domain] = {}
            for test_name, result in domain_results.items():
                if isinstance(result, dict):
                    json_results[domain][test_name] = {}
                    for sub_test, sub_result in result.items():
                        json_results[domain][test_name][sub_test] = {
                            "test_name": sub_result.test_name,
                            "iterations": sub_result.iterations,
                            "total_time": sub_result.total_time,
                            "avg_time": sub_result.avg_time,
                            "min_time": sub_result.min_time,
                            "max_time": sub_result.max_time,
                            "median_time": sub_result.median_time,
                            "std_dev": sub_result.std_dev,
                            "throughput": sub_result.throughput,
                            "memory_usage": sub_result.memory_usage
                        }
                else:
                    json_results[domain][test_name] = {
                        "test_name": result.test_name,
                        "iterations": result.iterations,
                        "total_time": result.total_time,
                        "avg_time": result.avg_time,
                        "min_time": result.min_time,
                        "max_time": result.max_time,
                        "median_time": result.median_time,
                        "std_dev": result.std_dev,
                        "throughput": result.throughput,
                        "memory_usage": result.memory_usage
                    }
        
        json.dump(json_results, f, indent=2)
    
    print(f"\nBenchmark results saved to 'benchmark_results.json'")


if __name__ == "__main__":
    main()
