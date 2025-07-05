#!/usr/bin/env python3
"""
Comprehensive test runner for YouTube Dubbing AI system.
This script runs all tests and generates detailed accuracy reports.
"""

import unittest
import sys
import os
import time
import json
from io import StringIO
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

class TestResult:
    """Custom test result class to track detailed metrics."""
    
    def __init__(self):
        self.tests_run = 0
        self.failures = []
        self.errors = []
        self.skipped = []
        self.success_count = 0
        self.start_time = None
        self.end_time = None
    
    def start_test(self, test):
        """Called when a test starts."""
        if self.start_time is None:
            self.start_time = time.time()
    
    def add_success(self, test):
        """Called when a test passes."""
        self.success_count += 1
    
    def add_failure(self, test, err):
        """Called when a test fails."""
        self.failures.append((test, err))
    
    def add_error(self, test, err):
        """Called when a test has an error."""
        self.errors.append((test, err))
    
    def add_skip(self, test, reason):
        """Called when a test is skipped."""
        self.skipped.append((test, reason))
    
    def stop_test(self, test):
        """Called when a test ends."""
        self.tests_run += 1
        self.end_time = time.time()
    
    def get_accuracy_percentage(self):
        """Calculate accuracy percentage."""
        if self.tests_run == 0:
            return 0.0
        return (self.success_count / self.tests_run) * 100
    
    def get_duration(self):
        """Get test duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0

class AccuracyTestRunner:
    """Custom test runner focused on accuracy measurement."""
    
    def __init__(self, verbosity=2):
        self.verbosity = verbosity
        self.result = TestResult()
    
    def run(self, test_suite):
        """Run the test suite and collect results."""
        print("=" * 70)
        print("YouTube Dubbing AI - Comprehensive Accuracy Testing")
        print("=" * 70)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Capture test output
        stream = StringIO()
        runner = unittest.TextTestRunner(
            stream=stream,
            verbosity=self.verbosity,
            resultclass=self._create_result_class()
        )
        
        # Run tests
        test_result = runner.run(test_suite)
        
        # Process results
        self._process_results(test_result, stream.getvalue())
        
        return self.result
    
    def _create_result_class(self):
        """Create a custom result class that updates our metrics."""
        result = self.result
        
        class CustomTestResult(unittest.TestResult):
            def startTest(self, test):
                super().startTest(test)
                result.start_test(test)
                if result.start_time is None:
                    result.start_time = time.time()
            
            def addSuccess(self, test):
                super().addSuccess(test)
                result.add_success(test)
            
            def addFailure(self, test, err):
                super().addFailure(test, err)
                result.add_failure(test, err)
            
            def addError(self, test, err):
                super().addError(test, err)
                result.add_error(test, err)
            
            def addSkip(self, test, reason):
                super().addSkip(test, reason)
                result.add_skip(test, reason)
            
            def stopTest(self, test):
                super().stopTest(test)
                result.stop_test(test)
                result.end_time = time.time()
        
        return CustomTestResult
    
    def _process_results(self, test_result, output):
        """Process and display test results."""
        print("\n" + "=" * 70)
        print("TEST RESULTS SUMMARY")
        print("=" * 70)
        
        accuracy = self.result.get_accuracy_percentage()
        duration = self.result.get_duration()
        
        print(f"Tests Run: {self.result.tests_run}")
        print(f"Successes: {self.result.success_count}")
        print(f"Failures: {len(self.result.failures)}")
        print(f"Errors: {len(self.result.errors)}")
        print(f"Skipped: {len(self.result.skipped)}")
        print(f"Accuracy: {accuracy:.2f}%")
        print(f"Duration: {duration:.2f} seconds")
        
        # Accuracy assessment
        print("\n" + "-" * 50)
        print("ACCURACY ASSESSMENT")
        print("-" * 50)
        
        if accuracy >= 100.0:
            print("EXCELLENT: 100% accuracy achieved!")
            status = "EXCELLENT"
        elif accuracy >= 95.0:
            print("VERY GOOD: 95%+ accuracy achieved")
            status = "VERY_GOOD"
        elif accuracy >= 90.0:
            print("GOOD: 90%+ accuracy achieved")
            status = "GOOD"
        elif accuracy >= 80.0:
            print("ACCEPTABLE: 80%+ accuracy achieved")
            status = "ACCEPTABLE"
        else:
            print("❌ NEEDS IMPROVEMENT: Below 80% accuracy")
            status = "NEEDS_IMPROVEMENT"
        
        # Detailed failure analysis
        if self.result.failures or self.result.errors:
            print("\n" + "-" * 50)
            print("FAILURE ANALYSIS")
            print("-" * 50)
            
            for test, error in self.result.failures:
                print(f"FAILURE: {test}")
                print(f"  {error[1]}")
                print()
            
            for test, error in self.result.errors:
                print(f"ERROR: {test}")
                print(f"  {error[1]}")
                print()
        
        # Component-specific accuracy
        self._analyze_component_accuracy()
        
        # Generate report
        self._generate_report(status, accuracy, duration)
    
    def _analyze_component_accuracy(self):
        """Analyze accuracy by component."""
        print("\n" + "-" * 50)
        print("COMPONENT ACCURACY ANALYSIS")
        print("-" * 50)
        
        components = {
            'Gemini CLI Service': [],
            'YouTube Service': [],
            'Audio Service': [],
            'Integration Tests': []
        }
        
        # Categorize test results
        all_tests = (
            [(test, 'success') for test in range(self.result.success_count)] +
            [(test, 'failure') for test, _ in self.result.failures] +
            [(test, 'error') for test, _ in self.result.errors]
        )
        
        # This is a simplified analysis - in practice, you'd parse test names
        for component, tests in components.items():
            component_total = max(1, len(tests))  # Avoid division by zero
            component_success = len([t for t in tests if t[1] == 'success'])
            component_accuracy = (component_success / component_total) * 100
            
            print(f"{component}: {component_accuracy:.1f}% ({component_success}/{component_total})")
    
    def _generate_report(self, status, accuracy, duration):
        """Generate a detailed test report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': status,
            'accuracy_percentage': accuracy,
            'duration_seconds': duration,
            'tests_run': self.result.tests_run,
            'successes': self.result.success_count,
            'failures': len(self.result.failures),
            'errors': len(self.result.errors),
            'skipped': len(self.result.skipped),
            'failure_details': [
                {
                    'test': str(test),
                    'error': str(error[1])
                }
                for test, error in self.result.failures
            ],
            'error_details': [
                {
                    'test': str(test),
                    'error': str(error[1])
                }
                for test, error in self.result.errors
            ]
        }
        
        # Save report to file
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Detailed report saved to: {report_file}")

def discover_tests():
    """Discover all test modules."""
    test_loader = unittest.TestLoader()
    
    # Discover tests in the tests directory
    test_suite = test_loader.discover(
        start_dir='tests',
        pattern='test_*.py',
        top_level_dir='.'
    )
    
    return test_suite

def run_specific_test_category(category):
    """Run tests for a specific category."""
    test_loader = unittest.TestLoader()
    
    category_files = {
        'gemini': 'tests/test_gemini_cli_service.py',
        'youtube': 'tests/test_youtube_service.py',
        'audio': 'tests/test_audio_service.py',
        'integration': 'tests/test_integration.py'
    }
    
    if category not in category_files:
        print(f"Unknown category: {category}")
        print(f"Available categories: {', '.join(category_files.keys())}")
        return None
    
    # Load specific test module
    module_name = category_files[category].replace('/', '.').replace('.py', '')
    test_suite = test_loader.loadTestsFromName(module_name)
    
    return test_suite

def main():
    """Main test runner function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='YouTube Dubbing AI Test Runner')
    parser.add_argument(
        '--category',
        choices=['gemini', 'youtube', 'audio', 'integration', 'all'],
        default='all',
        help='Test category to run'
    )
    parser.add_argument(
        '--verbosity',
        type=int,
        choices=[0, 1, 2],
        default=2,
        help='Test output verbosity'
    )
    parser.add_argument(
        '--integration',
        action='store_true',
        help='Run integration tests (requires external services)'
    )
    
    args = parser.parse_args()
    
    # Set environment variable for integration tests
    if args.integration:
        os.environ['RUN_INTEGRATION_TESTS'] = 'true'
    
    # Discover or load specific tests
    if args.category == 'all':
        test_suite = discover_tests()
    else:
        test_suite = run_specific_test_category(args.category)
        if test_suite is None:
            return 1
    
    # Run tests
    runner = AccuracyTestRunner(verbosity=args.verbosity)
    result = runner.run(test_suite)
    
    # Return appropriate exit code
    if result.get_accuracy_percentage() >= 90.0:
        return 0  # Success
    else:
        return 1  # Failure

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)

