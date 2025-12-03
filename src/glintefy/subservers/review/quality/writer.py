"""Results persistence for quality analysis."""

import json
from pathlib import Path
from typing import Any

from glintefy.subservers.common.chunked_writer import (
    cleanup_chunked_issues,
    write_chunked_issues,
)

from .analyzer_results import QualityAnalysisResults
from .issues import Issue


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

    def save_all_results(self, results: QualityAnalysisResults, all_issues: list[Issue]) -> dict[str, Path]:
        """Save all analysis results to files.

        Args:
            results: Typed analyzer results
            all_issues: List of Issue dataclass instances

        Returns:
            Dictionary mapping artifact names to file paths
        """
        artifacts: dict[str, Path] = {}

        self._save_list_results(results, artifacts)
        self._save_text_results(results, artifacts)
        self._save_dict_results(results, artifacts)
        self._save_issues(all_issues, artifacts)

        return artifacts

    def _save_list_results(self, results: QualityAnalysisResults, artifacts: dict[str, Path]) -> None:
        """Save list-based results (complexity, maintainability, etc.).

        Args:
            results: Typed analyzer results
            artifacts: Artifacts dictionary to update
        """
        list_mappings = [
            ("complexity", results.complexity),
            ("maintainability", results.maintainability),
            ("function_issues", results.function_issues),
            ("halstead", results.halstead),
            ("raw_metrics", results.raw_metrics),
            ("cognitive", results.cognitive),
        ]

        for key, data_list in list_mappings:
            if data_list:
                # Sort by relevant metric for each result type
                if key in ("complexity", "cognitive"):
                    data_list = sorted(data_list, key=lambda x: x.complexity, reverse=True)
                elif key == "function_issues":
                    data_list = sorted(data_list, key=lambda x: x.value, reverse=True)
                elif key == "maintainability":
                    # Lower MI = harder to maintain, so sort ascending (worst first)
                    data_list = sorted(data_list, key=lambda x: x.mi)
                elif key == "halstead":
                    # Higher effort = more difficult, so sort descending (hardest first)
                    data_list = sorted(data_list, key=lambda x: x.effort, reverse=True)
                # Convert dataclass items to dicts for JSON serialization
                serialized = [item.to_dict() for item in data_list]
                path = self._save_json(f"{key}.json", serialized)
                artifacts[key] = path

    def _save_text_results(self, results: QualityAnalysisResults, artifacts: dict[str, Path]) -> None:
        """Save text-based results (duplication analysis).

        Args:
            results: Typed analyzer results
            artifacts: Artifacts dictionary to update
        """
        if results.duplication.raw_output:
            path = self._save_text("duplication_analysis.txt", results.duplication.raw_output)
            artifacts["duplication"] = path

    def _save_dict_results(self, results: QualityAnalysisResults, artifacts: dict[str, Path]) -> None:
        """Save dictionary-based results from various analyzers.

        Args:
            results: Typed analyzer results
            artifacts: Artifacts dictionary to update
        """
        # Ruff static analysis
        if results.static.ruff_json:
            # Convert Pydantic models to dicts for JSON serialization
            ruff_dicts = [d.model_dump() for d in results.static.ruff_json]
            path = self._save_json("ruff_report.json", ruff_dicts)
            artifacts["ruff"] = path

        # Test analysis
        if results.tests.test_files or results.tests.total_tests > 0:
            path = self._save_json("test_analysis.json", results.tests.to_dict())
            artifacts["test_analysis"] = path

        # Architecture analysis
        if results.architecture.god_objects or results.architecture.highly_coupled:
            path = self._save_json("architecture_analysis.json", results.architecture.to_dict())
            artifacts["architecture"] = path

        # Type coverage - check for non-zero typed functions
        if results.type_coverage.typed_functions > 0 or results.type_coverage.untyped_functions > 0:
            path = self._save_json("type_coverage.json", results.type_coverage.model_dump())
            artifacts["type_coverage"] = path

        # Dead code detection
        if results.dead_code.dead_code:
            path = self._save_json("dead_code.json", results.dead_code.to_dict())
            artifacts["dead_code"] = path

        # Import cycles
        if results.import_cycles.cycles:
            path = self._save_json("import_cycles.json", results.import_cycles.to_dict())
            artifacts["import_cycles"] = path

        # Docstring coverage - check for non-zero coverage
        if results.docstring_coverage.coverage_percent > 0 or results.docstring_coverage.missing:
            path = self._save_json("docstring_coverage.json", results.docstring_coverage.model_dump())
            artifacts["docstring_coverage"] = path

        # Code churn
        if results.code_churn.files or results.code_churn.high_churn_files:
            path = self._save_json("code_churn.json", results.code_churn.to_dict())
            artifacts["code_churn"] = path

        # JavaScript/TypeScript analysis
        if results.js_analysis.get("issues"):
            path = self._save_json("eslint_report.json", results.js_analysis["issues"])
            artifacts["eslint"] = path

        # Beartype runtime checking
        if results.beartype:
            path = self._save_json("beartype_check.json", results.beartype)
            artifacts["beartype"] = path

    def _save_issues(self, all_issues: list[Issue], artifacts: dict[str, Path]) -> None:
        """Save compiled issues list in chunked format.

        Converts Issue dataclasses to dicts at serialization boundary.

        Args:
            all_issues: List of Issue dataclass instances
            artifacts: Artifacts dictionary to update
        """
        if not all_issues:
            return

        # Get unique issue types before conversion (typed access)
        issue_types = list({issue.type for issue in all_issues})

        # Cleanup old chunked files for these issue types
        cleanup_chunked_issues(
            output_dir=self.report_dir,
            issue_types=issue_types,
            prefix="issues",
        )

        # Convert dataclasses to dicts at serialization boundary
        issues_dicts = [issue.to_dict() for issue in all_issues]

        # Write chunked issues
        written_files = write_chunked_issues(
            issues=issues_dicts,
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
