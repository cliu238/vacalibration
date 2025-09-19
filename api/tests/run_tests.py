#!/usr/bin/env python3
"""
Test runner script for VA-Calibration API test suite.
Provides convenient commands for running different test categories.
"""

import sys
import subprocess
import argparse
import os


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n🧪 {description}")
    print(f"Running: {' '.join(cmd)}")
    print("-" * 60)

    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)) + "/..")
    if result.returncode != 0:
        print(f"❌ {description} failed with return code {result.returncode}")
        return False
    else:
        print(f"✅ {description} passed")
        return True


def main():
    parser = argparse.ArgumentParser(description="VA-Calibration API Test Runner")
    parser.add_argument(
        "test_type",
        choices=[
            "all", "unit", "integration", "health", "calibrate",
            "datasets", "conversions", "workflows", "coverage",
            "smoke", "security", "performance"
        ],
        help="Type of tests to run"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Run tests in verbose mode"
    )
    parser.add_argument(
        "--no-cov",
        action="store_true",
        help="Skip coverage reporting"
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run tests in parallel (where supported)"
    )

    args = parser.parse_args()

    # Base pytest command
    base_cmd = ["poetry", "run", "pytest"]

    if args.verbose:
        base_cmd.append("-v")

    if args.parallel:
        base_cmd.extend(["-n", "auto"])  # Requires pytest-xdist

    # Coverage options
    if not args.no_cov and args.test_type in ["all", "unit", "coverage"]:
        base_cmd.extend([
            "--cov=app",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-fail-under=80"
        ])

    success = True

    if args.test_type == "all":
        # Run all test categories
        success &= run_command(
            base_cmd + ["tests/unit", "tests/integration"],
            "All Tests"
        )

    elif args.test_type == "unit":
        success &= run_command(
            base_cmd + ["tests/unit"],
            "Unit Tests"
        )

    elif args.test_type == "integration":
        success &= run_command(
            base_cmd + ["tests/integration", "-m", "integration"],
            "Integration Tests"
        )

    elif args.test_type == "health":
        success &= run_command(
            base_cmd + ["tests/unit/test_health_check.py"],
            "Health Check Tests"
        )

    elif args.test_type == "calibrate":
        success &= run_command(
            base_cmd + ["tests/unit/test_calibrate.py"],
            "Calibration Tests"
        )

    elif args.test_type == "datasets":
        success &= run_command(
            base_cmd + ["tests/unit/test_datasets.py"],
            "Dataset Tests"
        )

    elif args.test_type == "conversions":
        success &= run_command(
            base_cmd + ["tests/unit/test_conversions.py"],
            "Conversion & Validation Tests"
        )

    elif args.test_type == "workflows":
        success &= run_command(
            base_cmd + ["tests/integration/test_workflows.py"],
            "Workflow Integration Tests"
        )

    elif args.test_type == "coverage":
        success &= run_command(
            base_cmd + [
                "tests/",
                "--cov=app",
                "--cov-report=html:htmlcov",
                "--cov-report=xml:coverage.xml",
                "--cov-report=term-missing"
            ],
            "Coverage Analysis"
        )
        if success:
            print("\n📊 Coverage report generated:")
            print("  - HTML: htmlcov/index.html")
            print("  - XML: coverage.xml")

    elif args.test_type == "smoke":
        # Quick smoke tests - basic functionality
        success &= run_command(
            base_cmd + [
                "tests/unit/test_health_check.py::TestHealthCheckEndpoint::test_health_check_success_with_r_ready",
                "tests/unit/test_calibrate.py::TestCalibrateEndpoint::test_calibrate_with_example_data",
                "-x"  # Stop on first failure
            ],
            "Smoke Tests"
        )

    elif args.test_type == "security":
        # Security-focused tests
        success &= run_command(
            base_cmd + [
                "tests/",
                "-k", "security or malicious or injection",
                "-v"
            ],
            "Security Tests"
        )

    elif args.test_type == "performance":
        # Performance tests
        success &= run_command(
            base_cmd + [
                "tests/",
                "-k", "performance or large_dataset or concurrent",
                "-v"
            ],
            "Performance Tests"
        )

    # Final result
    if success:
        print("\n🎉 All tests completed successfully!")
        return 0
    else:
        print("\n💥 Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())