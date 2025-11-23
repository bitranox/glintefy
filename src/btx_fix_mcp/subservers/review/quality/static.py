"""Static analysis module.

Analyzes code using:
- Ruff (linting)
- Pylint (duplication detection)
"""

import json
import subprocess
from typing import Any

from btx_fix_mcp.tools_venv import get_tool_path
from btx_fix_mcp.config import get_timeout

from .base import BaseAnalyzer


class StaticAnalyzer(BaseAnalyzer):
    """Static analysis using Ruff and Pylint."""

    def analyze(self, files: list[str]) -> dict[str, Any]:
        """Run static analysis on files.

        Returns:
            Dictionary with keys: static, duplication
        """
        return {
            "static": self._run_ruff(files),
            "duplication": self._detect_duplication(files),
        }

    def _run_ruff(self, files: list[str]) -> dict[str, Any]:
        """Run Ruff static analysis."""
        results = {"ruff": "", "ruff_json": []}
        if not files:
            return results

        ruff = str(get_tool_path("ruff"))
        try:
            timeout = get_timeout("tool_analysis", 60)
            result = subprocess.run(
                [ruff, "check", "--output-format=json"] + files,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            results["ruff"] = result.stdout
            if result.stdout.strip():
                try:
                    results["ruff_json"] = json.loads(result.stdout)
                except json.JSONDecodeError:
                    self.logger.warning("Invalid JSON output from Ruff")
        except subprocess.TimeoutExpired:
            self.logger.warning("Ruff analysis timed out")
        except FileNotFoundError:
            self.logger.warning("Ruff not found")
        except Exception as e:
            self.logger.warning(f"Error running Ruff: {e}")

        return results

    def _detect_duplication(self, files: list[str]) -> dict[str, Any]:
        """Detect code duplication using pylint."""
        results = {"duplicates": [], "raw_output": ""}
        if not files:
            return results

        # Get minimum duplicate lines threshold from config
        min_duplicate_lines = self.config.get("min_duplicate_lines", 6)

        pylint = str(get_tool_path("pylint"))
        try:
            timeout = get_timeout("tool_long", 120)
            result = subprocess.run(
                [
                    pylint,
                    "--disable=all",
                    "--enable=duplicate-code",
                    f"--min-similarity-lines={min_duplicate_lines}",
                ]
                + files,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            results["raw_output"] = result.stdout + result.stderr
            for line in result.stdout.split("\n"):
                if "Similar lines" in line or "duplicate-code" in line:
                    results["duplicates"].append(line.strip())
        except subprocess.TimeoutExpired:
            self.logger.warning("Pylint duplication check timed out")
        except FileNotFoundError:
            self.logger.warning("Pylint not found")
        except Exception as e:
            self.logger.warning(f"Error detecting duplication: {e}")

        return results
