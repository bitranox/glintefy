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

    def _save_if_exists(self, results: dict[str, Any], key: str, filename: str, artifact_key: str, artifacts: dict[str, Path]) -> None:
        """Save result if key exists in results."""
        if results.get(key):
            path = self._save_json(filename, results[key])
            artifacts[artifact_key] = path

    def _save_nested_if_exists(
        self,
        results: dict[str, Any],
        parent_key: str,
        child_key: str,
        filename: str,
        artifact_key: str,
        artifacts: dict[str, Path],
    ) -> None:
        """Save nested result if parent and child keys exist."""
        if results.get(parent_key, {}).get(child_key):
            path = self._save_json(filename, results[parent_key][child_key])
            artifacts[artifact_key] = path

    def _save_dict_results(self, results: dict[str, Any], artifacts: dict[str, Path]) -> None:
        """Save dictionary-based results from various analyzers.

        Args:
            results: Analyzer results
            artifacts: Artifacts dictionary to update
        """
        # Ruff static analysis
        self._save_nested_if_exists(results, "static", "ruff_json", "ruff_report.json", "ruff", artifacts)

        # Test analysis
        self._save_if_exists(results, "tests", "test_analysis.json", "test_analysis", artifacts)

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
        self._save_if_exists(results, "type_coverage", "type_coverage.json", "type_coverage", artifacts)

        # Dead code detection
        self._save_if_exists(results, "dead_code", "dead_code.json", "dead_code", artifacts)

        # Import cycles
        self._save_if_exists(results, "import_cycles", "import_cycles.json", "import_cycles", artifacts)

        # Docstring coverage
        self._save_if_exists(results, "docstring_coverage", "docstring_coverage.json", "docstring_coverage", artifacts)

        # Code churn
        self._save_if_exists(results, "code_churn", "code_churn.json", "code_churn", artifacts)

        # JavaScript/TypeScript analysis
        self._save_nested_if_exists(results, "js_analysis", "issues", "eslint_report.json", "eslint", artifacts)

        # Beartype runtime checking
        self._save_if_exists(results, "beartype", "beartype_check.json", "beartype", artifacts)

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
