#!/usr/bin/env python3
"""
Test runner script for Charlie Chat API.

This script provides convenient commands for running different types of tests.
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n🧪 {description}")
    print("=" * 50)
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=False)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Charlie Chat API Test Runner")
    parser.add_argument(
        "test_type",
        choices=["unit", "integration", "all", "session-state", "coverage"],
        help="Type of tests to run"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Run tests in verbose mode"
    )
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Run with coverage reporting"
    )
    
    args = parser.parse_args()
    
    # Base pytest command
    base_cmd = "python -m pytest"
    
    if args.verbose:
        base_cmd += " -v"
    
    if args.coverage:
        base_cmd += " --cov=app --cov-report=html --cov-report=term"
    
    # Test type specific commands
    commands = {
        "unit": f"{base_cmd} tests/unit/ -m unit",
        "integration": f"{base_cmd} tests/integration/ -m integration",
        "all": f"{base_cmd} tests/",
        "session-state": f"{base_cmd} tests/unit/test_chat_service_session_state.py -v",
        "coverage": f"{base_cmd} tests/ --cov=app --cov-report=html --cov-report=term"
    }
    
    cmd = commands[args.test_type]
    
    # Run the tests
    success = run_command(cmd, f"Running {args.test_type} tests")
    
    if not success:
        sys.exit(1)
    
    print(f"\n🎉 All {args.test_type} tests passed!")


if __name__ == "__main__":
    main()
