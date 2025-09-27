#!/usr/bin/env python3
"""
Test runner script for Realtime Notes API

This script provides convenient ways to run different types of tests
with appropriate configurations and reporting.
"""

import subprocess
import sys
import argparse
import os


def run_command(cmd):
    """Run a command and return the result"""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, env=os.environ.copy())

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    return result.returncode == 0


def run_unit_tests():
    """Run unit tests only"""
    cmd = [
        "python", "-m", "pytest",
        "tests/unit/",
        "-v",
        "--cov=api",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov/unit",
    ]
    return run_command(cmd)


def run_integration_tests():
    """Run integration tests only"""
    cmd = [
        "python", "-m", "pytest",
        "tests/integration/",
        "-v",
        "--cov=api",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov/integration",
    ]
    return run_command(cmd)


def run_all_tests():
    """Run all tests with coverage"""
    cmd = [
        "python", "-m", "pytest",
        "tests/",
        "-v",
        "--cov=api",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov/all",
        "--cov-fail-under=80",
    ]
    return run_command(cmd)


def run_fast_tests():
    """Run tests quickly (no coverage, parallel execution)"""
    cmd = [
        "python", "-m", "pytest",
        "tests/",
        "-v",
        "-x",  # Stop on first failure
        "--tb=short",
    ]
    return run_command(cmd)


def run_specific_test(test_pattern):
    """Run tests matching a specific pattern"""
    cmd = [
        "python", "-m", "pytest",
        "tests/",
        "-v",
        "-k", test_pattern,
        "--cov=api",
        "--cov-report=term-missing",
    ]
    return run_command(cmd)


def install_test_dependencies():
    """Install test dependencies"""
    cmd = ["pip", "install", "-r", "requirements-test.txt"]
    return run_command(cmd)


def main():
    parser = argparse.ArgumentParser(description="Run tests for Realtime Notes API")
    parser.add_argument(
        "test_type",
        choices=["unit", "integration", "all", "fast", "install"],
        nargs="?",
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument(
        "-k", "--keyword",
        help="Run tests matching keyword pattern"
    )
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install test dependencies before running tests"
    )

    args = parser.parse_args()

    # Change to project directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    success = True

    # Install dependencies if requested
    if args.install_deps or args.test_type == "install":
        print("Installing test dependencies...")
        success = install_test_dependencies()
        if not success:
            print("Failed to install test dependencies")
            sys.exit(1)

    if args.test_type == "install":
        print("Test dependencies installed successfully")
        return

    # Run specific tests if keyword provided
    if args.keyword:
        success = run_specific_test(args.keyword)
    elif args.test_type == "unit":
        success = run_unit_tests()
    elif args.test_type == "integration":
        success = run_integration_tests()
    elif args.test_type == "fast":
        success = run_fast_tests()
    else:  # all
        success = run_all_tests()

    if success:
        print("\n✅ Tests completed successfully!")

        # Show coverage report location if generated
        if args.test_type in ["unit", "integration", "all"] and not args.keyword:
            print(f"📊 HTML coverage report: htmlcov/{args.test_type}/index.html")
    else:
        print("\n❌ Tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()