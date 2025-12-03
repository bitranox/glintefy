"""Special analyzers for JavaScript/TypeScript and runtime type checking."""

import json
import subprocess
from logging import Logger
from pathlib import Path
from typing import Any

from glintefy.config import get_timeout, get_tool_config


class JavaScriptAnalyzer:
    """Analyzes JavaScript/TypeScript files using eslint."""

    def __init__(self, repo_path: Path, logger: Logger):
        """Initialize JavaScript analyzer.

        Args:
            repo_path: Repository root path
            logger: Logger instance
        """
        self.repo_path = repo_path
        self.logger = logger

    def analyze(self, files: list[str]) -> dict[str, Any]:
        """Analyze JavaScript/TypeScript files using eslint.

        Args:
            files: List of JS/TS file paths

        Returns:
            Dictionary with issues and raw output
        """
        results = {"issues": [], "raw_output": ""}
        if not files:
            return results

        try:
            eslint_timeout = get_timeout("tool_analysis", 120)
            result = subprocess.run(
                ["eslint", "--format=json"] + files,
                check=False,
                capture_output=True,
                text=True,
                timeout=eslint_timeout,
            )
            results["raw_output"] = result.stdout

            if result.stdout.strip():
                try:
                    eslint_results = json.loads(result.stdout)
                    for file_result in eslint_results:
                        for message in file_result.get("messages", []):
                            results["issues"].append(
                                {
                                    "file": file_result.get("filePath", ""),
                                    "line": message.get("line", 0),
                                    "severity": ("error" if message.get("severity") == 2 else "warning"),
                                    "message": message.get("message", ""),
                                    "rule": message.get("ruleId", ""),
                                }
                            )
                except json.JSONDecodeError:
                    self.logger.warning("Invalid JSON output from eslint")
        except FileNotFoundError:
            self.logger.warning("eslint not found")
        except Exception as e:
            self.logger.warning(f"eslint error: {e}")

        return results


class BeartypeAnalyzer:
    """Runs pytest with beartype to check runtime types."""

    def __init__(self, repo_path: Path, logger: Logger):
        """Initialize beartype analyzer.

        Args:
            repo_path: Repository root path
            logger: Logger instance
        """
        self.repo_path = repo_path
        self.logger = logger

    def analyze(self) -> dict[str, Any]:
        """Run pytest with beartype to check runtime types.

        Returns:
            Dictionary with test results and beartype check status
        """
        results = {"passed": True, "errors": [], "raw_output": "", "skipped": False}

        # Check if tests directory exists
        tests_dir = self.repo_path / "tests"
        if not tests_dir.exists() or not any(tests_dir.glob("test_*.py")):
            self.logger.info("No tests directory found, skipping beartype check")
            results["skipped"] = True
            results["raw_output"] = "Skipped: no tests directory found"
            return results

        try:
            # Check if beartype is available
            beartype_check_timeout = get_timeout("git_log", 20)
            beartype_check = subprocess.run(
                ["python", "-c", "import beartype; print('available')"],
                check=False,
                capture_output=True,
                text=True,
                timeout=beartype_check_timeout,
            )
            if beartype_check.returncode != 0:
                self.logger.info("Beartype not installed, skipping runtime type check")
                results["skipped"] = True
                results["raw_output"] = "Skipped: beartype not installed"
                return results

            results["raw_output"] = "Beartype available\n"

            # Get pytest config settings
            pytest_config = get_tool_config("pytest")
            testpaths = pytest_config.get("testpaths", ["tests"])
            test_path = testpaths[0] if testpaths else "tests"

            # Build pytest command
            pytest_cmd = ["python", "-m", "pytest", test_path, "-x", "--tb=short", "-q"]

            # Run full test suite with beartype
            pytest_beartype_timeout = get_timeout("beartype_check", 120)
            test_result = subprocess.run(
                pytest_cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=pytest_beartype_timeout,
                cwd=str(self.repo_path),
            )
            results["raw_output"] += test_result.stdout + test_result.stderr

            if test_result.returncode != 0 and "failed" in test_result.stdout.lower():
                results["passed"] = False
                for line in test_result.stdout.split("\n"):
                    if "FAILED" in line or "ERROR" in line:
                        results["errors"].append(line.strip())

        except FileNotFoundError:
            self.logger.warning("pytest not found for beartype check")
            results["skipped"] = True
        except subprocess.TimeoutExpired:
            self.logger.warning("beartype check timed out")
            results["passed"] = False
            results["errors"].append("Test run timed out")
        except Exception as e:
            self.logger.warning(f"beartype check error: {e}")

        return results
