#!/usr/bin/env python3
# ABOUTME: Test runner script for comprehensive testing with different test suites and configurations
# ABOUTME: Supports unit tests, integration tests, performance tests, and compatibility tests

import sys
import subprocess
import argparse
import os
from pathlib import Path
import time


class TestRunner:
    """Comprehensive test runner for MCP Manager."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_commands = {
            "unit": [
                "python", "-m", "pytest", "tests/",
                "-m", "unit",
                "--tb=short",
                "-v"
            ],
            "integration": [
                "python", "-m", "pytest", "tests/integration/",
                "--tb=short",
                "-v",
                "--timeout=30"
            ],
            "performance": [
                "python", "-m", "pytest", "tests/performance/",
                "--tb=short",
                "-v", 
                "--timeout=60"
            ],
            "compatibility": [
                "python", "-m", "pytest", "tests/compatibility/",
                "--tb=short",
                "-v",
                "--timeout=45"
            ],
            "smoke": [
                "python", "-m", "pytest",
                "-m", "smoke",
                "--tb=short",
                "-v",
                "--timeout=15"
            ],
            "all": [
                "python", "-m", "pytest", "tests/",
                "--tb=short",
                "-v",
                "--timeout=60"
            ],
            "coverage": [
                "python", "-m", "pytest", "tests/",
                "--cov=src/mcp_manager",
                "--cov-report=html:htmlcov",
                "--cov-report=xml:coverage.xml", 
                "--cov-report=term-missing",
                "--cov-fail-under=80",
                "--tb=short",
                "-v"
            ],
            "fast": [
                "python", "-m", "pytest", "tests/",
                "-m", "not slow and not performance",
                "--tb=line",
                "-x"  # Stop on first failure
            ]
        }
    
    def run_test_suite(self, suite_name, extra_args=None):
        """Run a specific test suite."""
        if suite_name not in self.test_commands:
            print(f"Unknown test suite: {suite_name}")
            print(f"Available suites: {list(self.test_commands.keys())}")
            return False
        
        command = self.test_commands[suite_name].copy()
        if extra_args:
            command.extend(extra_args)
        
        print(f"\n{'='*60}")
        print(f"Running {suite_name} tests")
        print(f"Command: {' '.join(command)}")
        print(f"{'='*60}\n")
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                check=False,
                capture_output=False
            )
            
            duration = time.time() - start_time
            
            if result.returncode == 0:
                print(f"\n✅ {suite_name} tests PASSED in {duration:.2f}s")
                return True
            else:
                print(f"\n❌ {suite_name} tests FAILED in {duration:.2f}s (exit code: {result.returncode})")
                return False
                
        except KeyboardInterrupt:
            print(f"\n🛑 {suite_name} tests interrupted by user")
            return False
        except Exception as e:
            print(f"\n💥 Error running {suite_name} tests: {e}")
            return False
    
    def run_parallel_tests(self, suite_name, num_workers=None):
        """Run tests in parallel using pytest-xdist."""
        if not num_workers:
            import multiprocessing
            num_workers = min(multiprocessing.cpu_count(), 4)
        
        command = self.test_commands.get(suite_name, self.test_commands["all"]).copy()
        command.extend(["-n", str(num_workers)])
        
        print(f"\n{'='*60}")
        print(f"Running {suite_name} tests in parallel ({num_workers} workers)")
        print(f"{'='*60}\n")
        
        start_time = time.time()
        
        try:
            result = subprocess.run(command, cwd=self.project_root, check=False)
            duration = time.time() - start_time
            
            if result.returncode == 0:
                print(f"\n✅ Parallel {suite_name} tests PASSED in {duration:.2f}s")
                return True
            else:
                print(f"\n❌ Parallel {suite_name} tests FAILED in {duration:.2f}s")
                return False
        except Exception as e:
            print(f"\n💥 Error running parallel {suite_name} tests: {e}")
            return False
    
    def setup_test_environment(self):
        """Set up test environment."""
        print("Setting up test environment...")
        
        # Check if we're in the right directory
        if not (self.project_root / "pyproject.toml").exists():
            print("❌ Not in project root directory")
            return False
        
        # Check if pytest is installed
        try:
            subprocess.run([sys.executable, "-m", "pytest", "--version"], 
                         check=True, capture_output=True)
        except subprocess.CalledProcessError:
            print("❌ pytest not installed. Install with: pip install -e .[testing]")
            return False
        
        print("✅ Test environment ready")
        return True
    
    def run_comprehensive_test_suite(self):
        """Run comprehensive test suite with all test types."""
        print("🚀 Starting comprehensive test suite...")
        
        if not self.setup_test_environment():
            return False
        
        test_suites = ["smoke", "unit", "integration", "performance", "compatibility"]
        results = {}
        
        for suite in test_suites:
            print(f"\n🏃 Running {suite} tests...")
            results[suite] = self.run_test_suite(suite)
        
        # Summary
        print(f"\n{'='*60}")
        print("COMPREHENSIVE TEST RESULTS")
        print(f"{'='*60}")
        
        for suite, passed in results.items():
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"{suite:15} {status}")
        
        total_passed = sum(results.values())
        total_tests = len(results)
        
        print(f"\nOverall: {total_passed}/{total_tests} test suites passed")
        
        if total_passed == total_tests:
            print("🎉 All test suites PASSED!")
            return True
        else:
            print("💥 Some test suites FAILED!")
            return False


def main():
    parser = argparse.ArgumentParser(description="Run MCP Manager tests")
    parser.add_argument(
        "suite",
        nargs="?",
        default="fast",
        choices=["unit", "integration", "performance", "compatibility", 
                 "smoke", "all", "coverage", "fast", "comprehensive"],
        help="Test suite to run"
    )
    parser.add_argument(
        "--parallel", "-p",
        action="store_true",
        help="Run tests in parallel"
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        help="Number of parallel workers"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--failfast", "-x", 
        action="store_true",
        help="Stop on first failure"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        help="Test timeout in seconds"
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    if not runner.setup_test_environment():
        sys.exit(1)
    
    # Build extra arguments
    extra_args = []
    if args.verbose:
        extra_args.append("-vv")
    if args.failfast:
        extra_args.append("-x")
    if args.timeout:
        extra_args.extend(["--timeout", str(args.timeout)])
    
    # Run tests
    if args.suite == "comprehensive":
        success = runner.run_comprehensive_test_suite()
    elif args.parallel:
        success = runner.run_parallel_tests(args.suite, args.workers)
    else:
        success = runner.run_test_suite(args.suite, extra_args)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()