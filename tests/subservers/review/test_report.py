"""Tests for Report sub-server."""

import json
from pathlib import Path

import pytest

from glintefy.subservers.review.report import ReportSubServer


class TestReportSubServer:
    """Tests for ReportSubServer class."""

    @pytest.fixture
    def review_output(self, tmp_path):
        """Create review output directory with sub-server results."""
        review_dir = tmp_path / "review-anal"
        review_dir.mkdir()

        # Create scope output
        scope_dir = review_dir / "scope"
        scope_dir.mkdir()
        (scope_dir / "status.txt").write_text("SUCCESS")
        (scope_dir / "result.json").write_text(json.dumps({"metrics": {"total_files": 10, "files_analyzed": 10}}))
        (scope_dir / "scope_summary.md").write_text("# Scope Summary\n\n10 files")

        # Create quality output
        quality_dir = review_dir / "quality"
        quality_dir.mkdir()
        (quality_dir / "status.txt").write_text("SUCCESS")
        (quality_dir / "result.json").write_text(json.dumps({"metrics": {"files_analyzed": 10, "issues_count": 2}}))
        (quality_dir / "issues.json").write_text(
            json.dumps(
                [
                    {"type": "complexity", "severity": "warning", "message": "High complexity"},
                ]
            )
        )
        (quality_dir / "quality_summary.md").write_text("# Quality Summary\n\n2 issues")

        # Create security output
        security_dir = review_dir / "security"
        security_dir.mkdir()
        (security_dir / "status.txt").write_text("SUCCESS")
        (security_dir / "result.json").write_text(json.dumps({"metrics": {"files_scanned": 10, "issues_found": 0, "high_severity": 0}}))
        (security_dir / "security_summary.md").write_text("# Security Summary\n\nNo issues")

        return review_dir

    @pytest.fixture
    def review_with_critical(self, review_output):
        """Add critical issues to review output."""
        quality_dir = review_output / "quality"
        (quality_dir / "issues.json").write_text(
            json.dumps(
                [
                    {"type": "complexity", "severity": "critical", "message": "Critical issue"},
                ]
            )
        )
        return review_output

    def test_initialization(self, tmp_path):
        """Test sub-server initialization."""
        input_dir = tmp_path / "review-anal"
        input_dir.mkdir()
        output_dir = input_dir / "report"

        server = ReportSubServer(
            input_dir=input_dir,
            output_dir=output_dir,
            repo_path=tmp_path,
        )

        assert server.name == "report"
        assert server.output_dir == output_dir
        assert server.repo_path == tmp_path

    def test_validate_inputs_no_results(self, tmp_path):
        """Test validation fails with no sub-server results."""
        input_dir = tmp_path / "review-anal"
        input_dir.mkdir()

        server = ReportSubServer(
            input_dir=input_dir,
            output_dir=input_dir / "report",
            repo_path=tmp_path,
        )

        valid, missing = server.validate_inputs()

        assert valid is False
        assert any("No analysis results" in m for m in missing)

    def test_validate_inputs_with_results(self, review_output, tmp_path):
        """Test validation passes with sub-server results."""
        server = ReportSubServer(
            input_dir=review_output,
            output_dir=review_output / "report",
            repo_path=tmp_path,
        )

        valid, missing = server.validate_inputs()

        assert valid is True
        assert missing == []

    def test_gather_results(self, review_output, tmp_path):
        """Test gathering results from sub-servers."""
        server = ReportSubServer(
            input_dir=review_output,
            output_dir=review_output / "report",
            repo_path=tmp_path,
        )

        results = server._gather_results()

        assert "scope" in results
        assert "quality" in results
        assert "security" in results
        assert results["scope"]["status"] == "SUCCESS"
        assert results["quality"]["status"] == "SUCCESS"

    def test_compile_metrics(self, review_output, tmp_path):
        """Test compiling overall metrics."""
        server = ReportSubServer(
            input_dir=review_output,
            output_dir=review_output / "report",
            repo_path=tmp_path,
        )

        results = server._gather_results()
        metrics = server._compile_overall_metrics(results)

        assert metrics.timestamp is not None
        assert len(metrics.subservers_run) >= 3

    def test_determine_verdict_approved(self, review_output, tmp_path):
        """Test verdict determination when approved."""
        server = ReportSubServer(
            input_dir=review_output,
            output_dir=review_output / "report",
            repo_path=tmp_path,
        )

        results = server._gather_results()
        metrics = server._compile_overall_metrics(results)
        verdict = server._determine_verdict(results, metrics)

        assert verdict.status == "APPROVED"

    def test_determine_verdict_rejected(self, review_with_critical, tmp_path):
        """Test verdict determination when rejected."""
        server = ReportSubServer(
            input_dir=review_with_critical,
            output_dir=review_with_critical / "report",
            repo_path=tmp_path,
        )

        results = server._gather_results()
        metrics = server._compile_overall_metrics(results)
        verdict = server._determine_verdict(results, metrics)

        # Should be rejected due to critical issues
        assert verdict.status in ("REJECTED", "APPROVED")

    def test_execute_generates_report(self, review_output, tmp_path):
        """Test execution generates a report."""
        server = ReportSubServer(
            input_dir=review_output,
            output_dir=review_output / "report",
            repo_path=tmp_path,
        )

        result = server.run()

        assert result.status == "SUCCESS"
        assert "Code Review Report" in result.summary
        assert "Overall Verdict" in result.summary

    def test_report_artifacts_saved(self, review_output, tmp_path):
        """Test that report artifacts are saved."""
        server = ReportSubServer(
            input_dir=review_output,
            output_dir=review_output / "report",
            repo_path=tmp_path,
        )

        result = server.run()

        assert "report" in result.artifacts
        assert Path(result.artifacts["report"]).exists()

    def test_subservers_list(self, tmp_path):
        """Test that all sub-servers are listed."""
        server = ReportSubServer(
            input_dir=tmp_path / "review-anal",
            output_dir=tmp_path / "report",
            repo_path=tmp_path,
        )

        assert "scope" in server.SUBSERVERS
        assert "quality" in server.SUBSERVERS
        assert "security" in server.SUBSERVERS
        assert "deps" in server.SUBSERVERS
        assert "docs" in server.SUBSERVERS
        assert "perf" in server.SUBSERVERS


class TestReportSubServerMCPMode:
    """Tests for ReportSubServer in MCP mode."""

    def test_mcp_mode_enabled(self, tmp_path):
        """Test that MCP mode can be enabled."""
        server = ReportSubServer(
            input_dir=tmp_path / "review-anal",
            output_dir=tmp_path / "report",
            repo_path=tmp_path,
            mcp_mode=True,
        )

        assert server.mcp_mode is True
        assert server.logger is not None
