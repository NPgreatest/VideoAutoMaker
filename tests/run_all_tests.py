#!/usr/bin/env python3
"""
Main test runner for the videogen test suite.
This script runs all tests in the organized test structure.
"""

import sys
import unittest
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_unit_tests():
    """Run all unit tests"""
    print("🧪 Running Unit Tests...")
    print("=" * 50)
    
    # Discover and run unit tests
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent / "unit"
    suite = loader.discover(start_dir, pattern="test_*.py")
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_integration_tests():
    """Run all integration tests"""
    print("\n🔗 Running Integration Tests...")
    print("=" * 50)
    
    # Discover and run integration tests
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent / "integration"
    suite = loader.discover(start_dir, pattern="test_*.py")
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_all_tests():
    """Run all tests"""
    print("🚀 Running Videogen Test Suite")
    print("=" * 60)
    print("This test suite includes:")
    print("  📁 Unit Tests: Individual component testing")
    print("  🔗 Integration Tests: Full pipeline testing")
    print("  🎭 Mock APIs: All expensive API calls are mocked")
    print("  📊 Test Data: Organized JSON and fixture data")
    print("=" * 60)
    
    # Run unit tests
    unit_success = run_unit_tests()
    
    # Run integration tests
    integration_success = run_integration_tests()
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print(f"  Unit Tests: {'✅ PASSED' if unit_success else '❌ FAILED'}")
    print(f"  Integration Tests: {'✅ PASSED' if integration_success else '❌ FAILED'}")
    
    overall_success = unit_success and integration_success
    print(f"\n🎯 Overall Result: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    if overall_success:
        print("\n🎉 All tests passed! The videogen pipeline is working correctly.")
        print("\nTo run the actual pipeline with real APIs:")
        print("  1. Set up your API keys in .env file")
        print("  2. Run: python videogen/pipeline/pipeline.py")
        print("  3. Or use the CLI: python -m videogen.cli.main")
    else:
        print("\n❌ Some tests failed. Check the output above for details.")
    
    return overall_success


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
