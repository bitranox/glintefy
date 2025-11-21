"""Type analysis module.

Analyzes code using:
- mypy (type coverage)
- vulture (dead code detection)
- interrogate (docstring coverage)
"""

import subprocess
from typing import Any

from btx_fix_mcp.tools_venv import get_tool_path

from .base import BaseAnalyzer


class TypeAnalyzer(BaseAnalyzer):
    """Type coverage and related analysis."""

    def analyze(self, files: list[str]) -> dict[str, Any]:
        """Run type analysis on files.

        Returns:
            Dictionary with keys: type_coverage, dead_code, docstring_coverage
        """
        return {
            "type_coverage": self._analyze_type_coverage(files),
            "dead_code": self._detect_dead_code(files),
            "docstring_coverage": self._analyze_docstring_coverage(files),
        }

    def _analyze_type_coverage(self, files: list[str]) -> dict[str, Any]:
        """Analyze type coverage using mypy."""
        results = {
            "coverage_percent": 0,
            "typed_functions": 0,
            "untyped_functions": 0,
            "errors": [],
            "raw_output": "",
        }
        if not files:
            return results

        mypy = str(get_tool_path("mypy"))
        try:
            result = subprocess.run(
                [mypy, "--ignore-missing-imports", "--show-error-codes", "--no-error-summary"] + files,
                capture_output=True,
                text=True,
                timeout=120,
            )
            results["raw_output"] = result.stdout + result.stderr

            # Count typed vs untyped (simple heuristic from mypy output)
            for line in result.stdout.split("\n"):
                if "error:" in line:
                    results["errors"].append(line.strip())
                if "note: def" in line and "-> " not in line:
                    results["untyped_functions"] += 1
                elif "note: def" in line:
                    results["typed_functions"] += 1

            total = results["typed_functions"] + results["untyped_functions"]
            if total > 0:
                results["coverage_percent"] = round((results["typed_functions"] / total) * 100, 1)
        except subprocess.TimeoutExpired:
            self.logger.warning("mypy timed out")
        except FileNotFoundError:
            self.logger.warning("mypy not found")
        except Exception as e:
            self.logger.warning(f"mypy error: {e}")

        return results

    def _detect_dead_code(self, files: list[str]) -> dict[str, Any]:
        """Detect dead code using vulture."""
        results = {"dead_code": [], "raw_output": ""}
        if not files:
            return results

        confidence = self.config.get("dead_code_confidence", 80)
        vulture = str(get_tool_path("vulture"))

        try:
            result = subprocess.run(
                [vulture, f"--min-confidence={confidence}"] + files,
                capture_output=True,
                text=True,
                timeout=60,
            )
            results["raw_output"] = result.stdout

            for line in result.stdout.split("\n"):
                if line.strip() and "unused" in line.lower():
                    # Parse: filename.py:123: unused variable 'x' (60% confidence)
                    parts = line.split(":")
                    if len(parts) >= 3:
                        results["dead_code"].append(
                            {
                                "file": self._get_relative_path(parts[0]),
                                "line": int(parts[1]) if parts[1].isdigit() else 0,
                                "message": ":".join(parts[2:]).strip(),
                            }
                        )
        except subprocess.TimeoutExpired:
            self.logger.warning("vulture timed out")
        except FileNotFoundError:
            self.logger.warning("vulture not found")
        except Exception as e:
            self.logger.warning(f"vulture error: {e}")

        return results

    def _analyze_docstring_coverage(self, files: list[str]) -> dict[str, Any]:
        """Analyze docstring coverage using interrogate."""
        results = {"coverage_percent": 0, "missing": [], "raw_output": ""}
        if not files:
            return results

        interrogate = str(get_tool_path("interrogate"))
        try:
            result = subprocess.run(
                [interrogate, "-v", "--fail-under=0"] + files,
                capture_output=True,
                text=True,
                timeout=60,
            )
            results["raw_output"] = result.stdout

            # Parse coverage from output
            for line in result.stdout.split("\n"):
                if "%" in line and ("PASSED" in line or "FAILED" in line):
                    # Extract percentage
                    import re

                    match = re.search(r"(\d+(?:\.\d+)?)\s*%", line)
                    if match:
                        results["coverage_percent"] = float(match.group(1))
                elif "missing" in line.lower() or "no docstring" in line.lower():
                    results["missing"].append(line.strip())
        except subprocess.TimeoutExpired:
            self.logger.warning("interrogate timed out")
        except FileNotFoundError:
            self.logger.warning("interrogate not found")
        except Exception as e:
            self.logger.warning(f"interrogate error: {e}")

        return results
