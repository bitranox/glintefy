#!/usr/bin/env python3
"""Profile your application to collect cache usage statistics.

This script wraps your application with cProfile to collect real-world
performance data, which can then be used by cache analysis to make
data-driven optimization recommendations.

Usage:
    # Basic usage - profile and analyze
    python -m glintefy.scripts.profile_application

    # Custom workload function
    python -m glintefy.scripts.profile_application --workload my_module:my_workload_func

    # Save to custom location
    python -m glintefy.scripts.profile_application --output custom/profile.prof

    # Profile then immediately analyze
    python -m glintefy.scripts.profile_application --analyze

Examples:
    # Profile a CLI application
    python -m glintefy.scripts.profile_application --workload my_app:main

    # Profile a test suite
    python -m glintefy.scripts.profile_application --workload tests.conftest:run_all_tests

    # Profile with custom output location
    python -m glintefy.scripts.profile_application \\
        --output my_profiles/prod_workload.prof \\
        --workload my_app:simulate_production
"""

from __future__ import annotations

import argparse
import cProfile
import importlib
import pstats
import sys
from collections.abc import Callable
from pathlib import Path


def default_workload():
    """Default workload: Run the glintefy test suite.

    This is a reasonable default that exercises most code paths.
    """
    import pytest

    print("Running default workload (test suite)...")
    pytest.main(
        [
            "tests/",
            "-v",
            "--tb=short",
            "-q",
        ]
    )


def load_workload_function(workload_spec: str):
    """Load a workload function from module:function specification.

    Args:
        workload_spec: String in format "module.path:function_name"

    Returns:
        Callable workload function

    Example:
        >>> func = load_workload_function("my_app:main")
        >>> func()  # Runs my_app.main()
    """
    if ":" not in workload_spec:
        raise ValueError(f"Invalid workload spec '{workload_spec}'. Expected format: 'module.path:function_name'")

    module_path, func_name = workload_spec.rsplit(":", 1)

    try:
        module = importlib.import_module(module_path)
    except ImportError as e:
        raise ImportError(f"Failed to import module '{module_path}': {e}") from e

    try:
        func = getattr(module, func_name)
    except AttributeError as e:
        raise AttributeError(f"Module '{module_path}' has no function '{func_name}'") from e

    if not callable(func):
        raise TypeError(f"{module_path}:{func_name} is not callable")

    return func


def profile_workload(
    workload_func: Callable[[], None],
    output_path: Path,
) -> pstats.Stats:
    """Profile a workload function and save results.

    Args:
        workload_func: Function to profile
        output_path: Where to save profiling data

    Returns:
        pstats.Stats object with profiling results
    """
    print("Starting profiling...")
    print(f"Workload: {workload_func.__module__}.{workload_func.__name__}")

    profiler = cProfile.Profile()
    profiler.enable()

    try:
        workload_func()
    except Exception as e:
        print(f"\n[WARN]  Workload raised exception: {e}", file=sys.stderr)
        print("Profiling data will still be saved.", file=sys.stderr)
    finally:
        profiler.disable()

    # Create output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save profiling data
    profiler.dump_stats(output_path)
    print(f"\n[OK] Profiling data saved to: {output_path}")

    # Create stats object for analysis
    stats = pstats.Stats(profiler)

    return stats


def print_profile_summary(stats: pstats.Stats, top_n: int = 20):
    """Print a summary of profiling results.

    Args:
        stats: pstats.Stats object
        top_n: Number of top functions to show
    """
    print("\n" + "=" * 70)
    print(f"TOP {top_n} FUNCTIONS BY CUMULATIVE TIME")
    print("=" * 70)

    stats.sort_stats("cumulative")
    stats.print_stats(top_n)

    print("\n" + "=" * 70)
    print(f"TOP {top_n} FUNCTIONS BY TOTAL TIME")
    print("=" * 70)

    stats.sort_stats("time")
    stats.print_stats(top_n)


def run_cache_analysis():
    """Run cache analysis using the saved profiling data."""
    print("\n" + "=" * 70)
    print("RUNNING CACHE ANALYSIS")
    print("=" * 70)

    try:
        from glintefy.servers.review import ReviewMCPServer

        server = ReviewMCPServer(repo_path=Path.cwd())
        result = server.run_cache()

        print("\n" + result["summary"])

        if result["status"] == "SUCCESS":
            print("\n[OK] Cache analysis completed successfully")
        else:
            print(f"\n[WARN]  Cache analysis status: {result['status']}")

    except Exception as e:
        print(f"\n[FAIL] Cache analysis failed: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Profile your application for cache optimization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--workload",
        type=str,
        help=("Workload function to profile in format 'module.path:function_name'. Default: runs test suite"),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("LLM-CONTEXT/glintefy/review/perf/test_profile.prof"),
        help="Output path for profiling data (default: %(default)s)",
    )

    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print profiling summary after completion",
    )

    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Run cache analysis immediately after profiling",
    )

    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Number of top functions to show in summary (default: %(default)s)",
    )

    args = parser.parse_args()

    # Load workload function
    if args.workload:
        try:
            workload_func = load_workload_function(args.workload)
        except (ImportError, AttributeError, ValueError, TypeError) as e:
            print(f"[FAIL] Error loading workload: {e}", file=sys.stderr)
            return 1
    else:
        workload_func = default_workload

    # Profile workload
    try:
        stats = profile_workload(workload_func, args.output)
    except Exception as e:
        print(f"[FAIL] Profiling failed: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    # Print summary if requested
    if args.summary:
        print_profile_summary(stats, top_n=args.top)

    # Run cache analysis if requested
    if args.analyze:
        run_cache_analysis()

    return 0


if __name__ == "__main__":
    sys.exit(main())
