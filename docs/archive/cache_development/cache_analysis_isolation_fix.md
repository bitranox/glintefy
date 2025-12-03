# Cache Analysis Isolation Fix

## 🚨 Problem: Current Implementation is NOT Isolated

### Issues Identified

1. **Module Monkey-Patching:** Modifies live modules in memory
2. **Parallel Task Interference:** Other code sees cached versions
3. **Time Measurement Contamination:** Parallel tests affect measurements

---

## ✅ Solution: Subprocess Isolation

### Architecture: Isolated Test Execution

```
Main Process (Cache Analyzer)
    │
    ├─→ Subprocess 1: Batch Screening
    │   - Import modules fresh
    │   - Apply ALL caches
    │   - Run test suite
    │   - Return cache_info() stats
    │   - Exit (clean slate)
    │
    ├─→ Subprocess 2: Individual Validation (Candidate 1 - Baseline)
    │   - Import modules fresh (no cache)
    │   - Run test suite
    │   - Return timing
    │   - Exit
    │
    ├─→ Subprocess 3: Individual Validation (Candidate 1 - Cached)
    │   - Import modules fresh
    │   - Apply cache to candidate_1
    │   - Run test suite
    │   - Return timing + cache_info()
    │   - Exit
    │
    └─→ Repeat for remaining candidates...
```

**Key Benefit:** Each subprocess has **isolated memory space**. Monkey-patching doesn't affect parent or siblings.

---

## 🔧 Implementation Changes

### 1. Create Subprocess Test Runner

**New File:** `src/glintefy/subservers/review/cache/subprocess_runner.py`

```python
"""Subprocess-based test execution for isolation.

Runs pytest in separate processes to avoid module contamination.
"""

import importlib
import json
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path


def apply_cache_and_run_tests(
    module_path: str,
    function_name: str,
    cache_size: int,
    repo_path: Path,
    timeout: int = 300,
) -> dict:
    """Apply cache to function and run tests in CURRENT process.

    This function is called by subprocess, not directly by analyzer.

    Returns:
        Dict with timing, cache_info, and exit code
    """
    import time

    try:
        # Import module and apply cache
        module = importlib.import_module(module_path)
        original_func = getattr(module, function_name)
        cached_func = lru_cache(maxsize=cache_size)(original_func)
        setattr(module, function_name, cached_func)

        # Run tests
        start = time.perf_counter()
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
            cwd=repo_path,
            capture_output=True,
            timeout=timeout,
        )
        elapsed = time.perf_counter() - start

        # Get cache statistics
        cache_info = cached_func.cache_info()

        return {
            "success": result.returncode == 0,
            "elapsed": elapsed,
            "hits": cache_info.hits,
            "misses": cache_info.misses,
            "maxsize": cache_info.maxsize,
            "currsize": cache_info.currsize,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def run_tests_baseline(repo_path: Path, timeout: int = 300) -> dict:
    """Run tests WITHOUT caching in CURRENT process.

    Returns:
        Dict with timing and exit code
    """
    import time

    try:
        start = time.perf_counter()
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
            cwd=repo_path,
            capture_output=True,
            timeout=timeout,
        )
        elapsed = time.perf_counter() - start

        return {
            "success": result.returncode == 0,
            "elapsed": elapsed,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def run_in_subprocess(target_func: str, args: dict) -> dict:
    """Run a function in a separate subprocess for isolation.

    Args:
        target_func: Function name to call ('apply_cache_and_run_tests' or 'run_tests_baseline')
        args: Arguments to pass to the function

    Returns:
        Result from the function
    """
    # Create temporary script to run in subprocess
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        script = f"""
import json
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path.cwd()))

from glintefy.subservers.review.cache.subprocess_runner import {target_func}

# Parse arguments
args = {repr(args)}

# Run function
result = {target_func}(**args)

# Print result as JSON (stdout)
print(json.dumps(result))
"""
        f.write(script)
        script_path = f.name

    try:
        # Run script in subprocess
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=args.get('timeout', 300) + 30,  # Extra time for overhead
        )

        # Parse JSON output
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
        else:
            return {
                "success": False,
                "error": f"Subprocess failed: {result.stderr}",
            }

    finally:
        # Clean up temp script
        Path(script_path).unlink(missing_ok=True)
```

---

### 2. Update BatchScreener to Use Subprocess

**File:** `src/glintefy/subservers/review/cache/batch_screener.py`

```python
# OLD CODE (PROBLEMATIC)
def _apply_caches(self, candidates):
    """Apply caches - MODIFIES LIVE MODULES ❌"""
    for candidate in candidates:
        module = importlib.import_module(candidate.module_path)
        original_func = getattr(module, candidate.function_name)
        cached_func = lru_cache(maxsize=self.cache_size)(original_func)
        setattr(module, candidate.function_name, cached_func)  # ❌ Monkey-patch


# NEW CODE (ISOLATED)
def screen_candidates(self, candidates, repo_path):
    """Screen all candidates in isolated subprocess."""
    from glintefy.subservers.review.cache.subprocess_runner import run_in_subprocess

    # Build batch screening script
    script_args = {
        "candidates": [
            {
                "module_path": c.module_path,
                "function_name": c.function_name,
                "cache_size": self.cache_size,
            }
            for c in candidates
        ],
        "repo_path": str(repo_path),
        "timeout": self.test_timeout,
    }

    # Run in subprocess (isolated)
    result = run_in_subprocess("run_batch_screening", script_args)

    # Parse results
    # ...
```

---

### 3. Update IndividualValidator to Use Subprocess

**File:** `src/glintefy/subservers/review/cache/individual_validator.py`

```python
# OLD CODE (PROBLEMATIC)
def _measure_with_cache(self, candidate, repo_path):
    """MODIFIES LIVE MODULE ❌"""
    module = importlib.import_module(candidate.module_path)
    original_func = getattr(module, candidate.function_name)
    cached_func = lru_cache(maxsize=self.cache_size)(original_func)
    setattr(module, candidate.function_name, cached_func)  # ❌

    # Run tests - CONTAMINATED!
    result = subprocess.run(["pytest", "tests/"])


# NEW CODE (ISOLATED)
def _measure_with_cache(self, candidate, repo_path):
    """Run tests WITH cache in isolated subprocess."""
    from glintefy.subservers.review.cache.subprocess_runner import run_in_subprocess

    args = {
        "module_path": candidate.module_path,
        "function_name": candidate.function_name,
        "cache_size": self.cache_size,
        "repo_path": str(repo_path),
        "timeout": self.test_timeout,
    }

    # Run in subprocess (isolated)
    result = run_in_subprocess("apply_cache_and_run_tests", args)

    if result["success"]:
        return (result["elapsed"], result)  # Clean timing
    return (None, None)
```

---

## 🎯 Benefits of Subprocess Isolation

| Issue | Before (Monkey-Patching) | After (Subprocess) |
|-------|--------------------------|---------------------|
| **Module Contamination** | ❌ Affects parent process | ✅ Isolated memory space |
| **Parallel Task Safety** | ❌ Other code sees cached funcs | ✅ No interference |
| **Time Measurement** | ❌ Affected by parallel tasks | ✅ Clean subprocess |
| **State Cleanup** | ❌ Manual restoration needed | ✅ Auto-cleanup on exit |
| **Test Isolation** | ❌ Cache pollution between runs | ✅ Fresh imports each time |

---

## 🔬 Addressing Parallel Test Runners

### Problem: pytest-xdist Parallel Execution

If the test suite uses `pytest -n auto` (parallel test execution), timing can be affected by:
- CPU contention
- Cache line bouncing
- Non-deterministic scheduling

### Solution: Disable Parallelism for Measurement

```python
def _run_test_suite(self, repo_path):
    """Run pytest WITHOUT parallel execution for stable timing."""
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "tests/",
            "-v",
            "--tb=short",
            "-n", "0",  # ← DISABLE pytest-xdist parallelism
        ],
        cwd=repo_path,
        capture_output=True,
        timeout=self.test_timeout,
    )
    return result.returncode == 0
```

**Alternative:** Detect if project uses `-n auto` and warn user:

```python
# Check if pytest.ini or pyproject.toml configures parallel execution
if "-n" in pytest_config:
    log_warning(
        "Test suite configured for parallel execution. "
        "Cache timing may be less accurate. "
        "Consider disabling -n flag for cache analysis."
    )
```

---

## 📊 Performance Impact of Subprocesses

### Cost Analysis

**Subprocess Overhead:**
- Process creation: ~50-100ms per subprocess
- Module imports: ~200-500ms (depends on project size)
- Pytest startup: ~1-2s

**For 5 candidates with 3 runs each:**
```
Old approach (in-process):
  - Batch screening: 1 test run = 10s
  - Individual (5 candidates × 2 runs): 10 test runs = 100s
  - Total: ~110s

New approach (subprocess):
  - Batch screening: 1 subprocess = 10s + 2s overhead = 12s
  - Individual (5 candidates × 2 runs × 3 repeats): 30 subprocesses = 300s + 60s overhead = 360s
  - Total: ~372s
```

**Overhead:** +238% execution time

### Optimization: Subprocess Pooling

To reduce overhead, reuse subprocesses:

```python
from multiprocessing import Pool

# Create process pool (reuses workers)
with Pool(processes=4) as pool:
    # Run all measurements in parallel
    results = pool.starmap(
        run_isolated_test,
        [(candidate, repo_path) for candidate in survivors]
    )
```

**With pooling:**
- Amortizes process creation cost
- Runs validations in parallel
- Reduces total time to ~90s (20% overhead vs original)

---

## 🎯 Recommended Implementation

### Hybrid Approach: In-Process + Isolation

```python
class CacheSubServer:
    def __init__(self, isolation_mode: str = "auto"):
        """
        isolation_mode:
            - "subprocess": Always use subprocess isolation (safest)
            - "inprocess": Use monkey-patching (faster, risky)
            - "auto": Detect if other tasks are running (smart)
        """
        self.isolation_mode = isolation_mode

    def _should_use_subprocess(self):
        """Decide whether to use subprocess isolation."""
        if self.isolation_mode == "subprocess":
            return True
        if self.isolation_mode == "inprocess":
            return False

        # Auto mode: Check if running in background
        # (e.g., MCP server with multiple clients)
        return self._detect_concurrent_execution()
```

**Config:**
```toml
[review.cache]
# Isolation mode for cache testing
# "subprocess" = safest (isolated processes)
# "inprocess" = fastest (monkey-patching, risky)
# "auto" = detect concurrent execution (smart default)
isolation_mode = "auto"
```

---

## ✅ Final Recommendation

**Implement subprocess isolation** because:

1. ✅ **Correctness > Speed:** 238% overhead is acceptable for accurate measurements
2. ✅ **Safety:** No module contamination or parallel task interference
3. ✅ **Clean State:** Each test run starts fresh
4. ✅ **Reproducible:** Eliminates non-deterministic timing issues

**With pooling optimization**, overhead drops to ~20%, making it practical for production use.
