#!/usr/bin/env python3
"""Template for profiling your own application.

Copy this file and customize the `run_my_workload()` function
to match your application's typical usage patterns.

Usage:
    1. Copy this template: cp docs/examples/profile_my_app_template.py profile_my_app.py
    2. Edit `run_my_workload()` to run your application
    3. Run: python profile_my_app.py
    4. Analyze: python -m glintefy review cache
"""

from __future__ import annotations

import cProfile
from pathlib import Path


def run_my_workload():
    """CUSTOMIZE THIS: Replace with your application's typical workload.

    This function should simulate realistic usage of your application.
    The more realistic the workload, the better the cache recommendations.

    Examples:
        # CLI application
        from my_app import main
        main(["--input", "data/sample.csv", "--output", "results/"])

        # Web application
        from my_app import app, test_client
        client = test_client()
        for i in range(100):
            client.get(f"/api/users/{i}")
            client.post("/api/data", json={"key": "value"})

        # Data processing
        from my_pipeline import process_files
        files = list(Path("data/sample").glob("*.csv"))
        process_files(files)

        # Test suite (quick fallback)
        import pytest
        pytest.main(["tests/", "-v"])
    """
    # Replace this with your actual application code
    print("Running workload...")

    # Example: Import and run your application
    # from my_app import run_application
    # run_application()

    # Or run specific operations
    # from my_module import MyClass
    # obj = MyClass()
    # for i in range(1000):
    #     obj.do_something(i)

    print("✓ Workload complete")


def main():
    """Profile the workload and save results."""
    # Start profiling
    profiler = cProfile.Profile()
    profiler.enable()

    try:
        # Run your workload
        run_my_workload()

    except Exception as e:
        print(f"⚠️  Workload raised exception: {e}")
        print("Profiling data will still be saved.")
        import traceback

        traceback.print_exc()

    finally:
        # Stop profiling
        profiler.disable()

    # Save profiling data to expected location
    output_dir = Path("LLM-CONTEXT/glintefy/review/perf")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "test_profile.prof"
    profiler.dump_stats(output_path)

    print(f"\n✓ Profiling data saved to: {output_path}")
    print("\nNext steps:")
    print("  1. Run cache analysis: python -m glintefy review cache")
    print("  2. Review results: cat LLM-CONTEXT/glintefy/review/cache/existing_cache_evaluations.json")


if __name__ == "__main__":
    main()
