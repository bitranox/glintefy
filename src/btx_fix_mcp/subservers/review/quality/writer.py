"""Results persistence for quality analysis."""

import json
from pathlib import Path
from typing import Any

from btx_fix_mcp.subservers.common.chunked_writer import (
    cleanup_chunked_issues,
    write_chunked_issues,
)


class ResultsWriter:
    """Writes analysis results to files."""

    def __init__(self, output_dir: Path, report_dir: Path | None = None):
        """Initialize results writer.

        Args:
            output_dir: Directory to save results to
            report_dir: Directory for chunked issue files (default: output_dir's parent/report)
        """
        self.output_dir = output_dir
        self.report_dir = report_dir or (output_dir.parent / "report")

    def save_all_results(self, results: dict[str, Any], all_issues: list[dict]) -> dict[str, Path]:
        """Save all analysis results to files.

        Args:
            results: Raw analyzer results
            all_issues: Compiled issues list

        Returns:
            Dictionary mapping artifact names to file paths
        """
        artifacts = {}

        self._save_list_results(results, artifacts)
        self._save_text_results(results, artifacts)
        self._save_dict_results(results, artifacts)
        self._save_issues(all_issues, artifacts)

        return artifacts

    def _save_list_results(self, results: dict[str, Any], artifacts: dict[str, Path]) -> None:
        """Save list-based results (complexity, maintainability, etc.).

        Args:
            results: Analyzer results
            artifacts: Artifacts dictionary to update
        """
        list_keys = [
            "complexity",
            "maintainability",
            "function_issues",
            "halstead",
            "raw_metrics",
            "cognitive",
        ]

        for key in list_keys:
            if key in results and results[key]:
                path = self._save_json(f"{key}.json", results[key])
                artifacts[key] = path

    def _save_text_results(self, results: dict[str, Any], artifacts: dict[str, Path]) -> None:
        """Save text-based results (duplication analysis).

        Args:
            results: Analyzer results
            artifacts: Artifacts dictionary to update
        """
        if results.get("duplication", {}).get("raw_output"):
            path = self._save_text("duplication_analysis.txt", results["duplication"]["raw_output"])
            artifacts["duplication"] = path

    def _save_dict_results(self, results: dict[str, Any], artifacts: dict[str, Path]) -> None:
        """Save dictionary-based results from various analyzers.

        Args:
            results: Analyzer results
            artifacts: Artifacts dictionary to update
        """
        # Ruff static analysis
        if results.get("static", {}).get("ruff_json"):
            path = self._save_json("ruff_report.json", results["static"]["ruff_json"])
            artifacts["ruff"] = path

        # Test analysis
        if results.get("tests"):
            path = self._save_json("test_analysis.json", results["tests"])
            artifacts["test_analysis"] = path

        # Architecture analysis
        if results.get("architecture"):
            arch_data = {
                "god_objects": results["architecture"].get("god_objects", []),
                "highly_coupled": results["architecture"].get("highly_coupled", []),
                "module_structure": dict(results["architecture"].get("module_structure", {})),
            }
            path = self._save_json("architecture_analysis.json", arch_data)
            artifacts["architecture"] = path

        # Type coverage
        if results.get("type_coverage"):
            path = self._save_json("type_coverage.json", results["type_coverage"])
            artifacts["type_coverage"] = path

        # Dead code detection
        if results.get("dead_code"):
            path = self._save_json("dead_code.json", results["dead_code"])
            artifacts["dead_code"] = path

        # Import cycles
        if results.get("import_cycles"):
            path = self._save_json("import_cycles.json", results["import_cycles"])
            artifacts["import_cycles"] = path

        # Docstring coverage
        if results.get("docstring_coverage"):
            path = self._save_json("docstring_coverage.json", results["docstring_coverage"])
            artifacts["docstring_coverage"] = path

        # Code churn
        if results.get("code_churn"):
            path = self._save_json("code_churn.json", results["code_churn"])
            artifacts["code_churn"] = path

        # JavaScript/TypeScript analysis
        if results.get("js_analysis", {}).get("issues"):
            path = self._save_json("eslint_report.json", results["js_analysis"])
            artifacts["eslint"] = path

        # Beartype runtime checking
        if results.get("beartype"):
            path = self._save_json("beartype_check.json", results["beartype"])
            artifacts["beartype"] = path

    def _save_issues(self, all_issues: list[dict], artifacts: dict[str, Path]) -> None:
        """Save compiled issues list in chunked format.

        Args:
            all_issues: List of all issues
            artifacts: Artifacts dictionary to update
        """
        if not all_issues:
            return

        # Get unique issue types from this sub-server's issues
        issue_types = list({issue.get("type", "unknown") for issue in all_issues})

        # Cleanup old chunked files for these issue types
        cleanup_chunked_issues(
            output_dir=self.report_dir,
            issue_types=issue_types,
            prefix="issues",
        )

        # Write chunked issues
        written_files = write_chunked_issues(
            issues=all_issues,
            output_dir=self.report_dir,
            prefix="issues",
        )

        if written_files:
            artifacts["issues"] = written_files[0]  # First chunk for reference

    def _save_json(self, filename: str, data: Any) -> Path:
        """Save data as JSON file.

        Args:
            filename: Name of file to create
            data: Data to serialize as JSON

        Returns:
            Path to created file
        """
        path = self.output_dir / filename
        path.write_text(json.dumps(data, indent=2))
        return path

    def _save_text(self, filename: str, text: str) -> Path:
        """Save text content to file.

        Args:
            filename: Name of file to create
            text: Text content to write

        Returns:
            Path to created file
        """
        path = self.output_dir / filename
        path.write_text(text)
        return path
