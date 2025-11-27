"""Static analysis module.

Analyzes code using:
- Ruff (linting)
- Pylint (duplication detection)
"""

import json
import subprocess
from typing import Any

from btx_fix_mcp.tools_venv import get_tool_path
from btx_fix_mcp.config import get_timeout, get_tool_config

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

        # Get ruff config settings
        ruff_config = get_tool_config("ruff")
        line_length = ruff_config.get("line_length", 88)
        target_version = ruff_config.get("target_version", "py313")
        select_rules = ruff_config.get("select", ["E", "F", "W", "I", "N", "UP", "B", "C4", "SIM"])
        ignore_rules = ruff_config.get("ignore", ["E501"])
        # Note: fix and unsafe_fixes are intentionally not used - analysis mode only reports issues

        ruff = str(get_tool_path("ruff"))
        try:
            ruff_timeout = get_timeout("tool_analysis", 60)

            # Build command with config options
            cmd = [
                ruff,
                "check",
                "--output-format=json",
                f"--line-length={line_length}",
                f"--target-version={target_version}",
            ]

            # Add select rules
            if select_rules:
                cmd.append(f"--select={','.join(select_rules)}")

            # Add ignore rules
            if ignore_rules:
                cmd.append(f"--ignore={','.join(ignore_rules)}")

            # Note: auto_fix and unsafe_fixes are not used for analysis
            # They would be used in a fix workflow

            result = subprocess.run(
                cmd + files,
                capture_output=True,
                text=True,
                timeout=ruff_timeout,
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

        # Get minimum duplicate lines threshold from quality config
        min_duplicate_lines = self.config.get("min_duplicate_lines", 6)

        # Get pylint duplication settings from tools.pylint config
        pylint_config = get_tool_config("pylint")
        ignore_comments = pylint_config.get("ignore_comments", True)
        ignore_docstrings = pylint_config.get("ignore_docstrings", True)
        ignore_imports = pylint_config.get("ignore_imports", True)
        ignore_signatures = pylint_config.get("ignore_signatures", True)

        pylint = str(get_tool_path("pylint"))
        try:
            pylint_timeout = get_timeout("tool_long", 120)
            cmd = [
                pylint,
                "--disable=all",
                "--enable=duplicate-code",
                f"--min-similarity-lines={min_duplicate_lines}",
            ]
            # Add ignore flags based on config
            if ignore_comments:
                cmd.append("--ignore-comments=y")
            if ignore_docstrings:
                cmd.append("--ignore-docstrings=y")
            if ignore_imports:
                cmd.append("--ignore-imports=y")
            if ignore_signatures:
                cmd.append("--ignore-signatures=y")

            result = subprocess.run(
                cmd + files,
                capture_output=True,
                text=True,
                timeout=pylint_timeout,
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
