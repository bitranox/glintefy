"""Tests for integration protocol validation."""

import pytest
from glintefy.subservers.common.protocol import IntegrationProtocol


class TestValidateOutputs:
    """Tests for validate_outputs method."""

    def test_valid_outputs(self, tmp_path):
        """Test validation with all required files present."""
        output_dir = tmp_path / "scope"
        output_dir.mkdir()

        # Create required files
        (output_dir / "status.txt").write_text("SUCCESS")
        (output_dir / "scope_summary.md").write_text("# Scope Analysis\n\nComplete!")

        valid, violations = IntegrationProtocol.validate_outputs(output_dir, "scope")

        assert valid is True
        assert violations == []

    def test_missing_status_file(self, tmp_path):
        """Test validation fails when status.txt is missing."""
        output_dir = tmp_path / "scope"
        output_dir.mkdir()

        (output_dir / "scope_summary.md").write_text("# Scope Analysis")

        valid, violations = IntegrationProtocol.validate_outputs(output_dir, "scope")

        assert valid is False
        assert any("status.txt" in v for v in violations)

    def test_missing_summary_file(self, tmp_path):
        """Test validation fails when summary is missing."""
        output_dir = tmp_path / "scope"
        output_dir.mkdir()

        (output_dir / "status.txt").write_text("SUCCESS")

        valid, violations = IntegrationProtocol.validate_outputs(output_dir, "scope")

        assert valid is False
        assert any("scope_summary.md" in v for v in violations)

    def test_invalid_status_value(self, tmp_path):
        """Test validation fails with invalid status value."""
        output_dir = tmp_path / "scope"
        output_dir.mkdir()

        (output_dir / "status.txt").write_text("INVALID_STATUS")
        (output_dir / "scope_summary.md").write_text("# Scope Analysis")

        valid, violations = IntegrationProtocol.validate_outputs(output_dir, "scope")

        assert valid is False
        assert any("Invalid status" in v for v in violations)

    def test_empty_summary_file(self, tmp_path):
        """Test validation fails when summary is empty."""
        output_dir = tmp_path / "scope"
        output_dir.mkdir()

        (output_dir / "status.txt").write_text("SUCCESS")
        (output_dir / "scope_summary.md").write_text("")

        valid, violations = IntegrationProtocol.validate_outputs(output_dir, "scope")

        assert valid is False
        assert any("empty" in v.lower() for v in violations)

    def test_summary_without_markdown_heading(self, tmp_path):
        """Test validation fails when summary doesn't start with #."""
        output_dir = tmp_path / "scope"
        output_dir.mkdir()

        (output_dir / "status.txt").write_text("SUCCESS")
        (output_dir / "scope_summary.md").write_text("Not a markdown heading")

        valid, violations = IntegrationProtocol.validate_outputs(output_dir, "scope")

        assert valid is False
        assert any("markdown heading" in v for v in violations)

    def test_require_result_json(self, tmp_path):
        """Test requiring result.json file."""
        output_dir = tmp_path / "scope"
        output_dir.mkdir()

        (output_dir / "status.txt").write_text("SUCCESS")
        (output_dir / "scope_summary.md").write_text("# Scope Analysis")

        # Without result.json
        valid, violations = IntegrationProtocol.validate_outputs(output_dir, "scope", require_result_json=True)

        assert valid is False
        assert any("result.json" in v for v in violations)

        # With result.json
        (output_dir / "result.json").write_text("{}")
        valid, violations = IntegrationProtocol.validate_outputs(output_dir, "scope", require_result_json=True)

        assert valid is True


class TestValidateStatusFile:
    """Tests for validate_status_file method."""

    def test_valid_status_success(self, tmp_path):
        """Test validation of SUCCESS status."""
        status_file = tmp_path / "status.txt"
        status_file.write_text("SUCCESS")

        valid, error = IntegrationProtocol.validate_status_file(status_file)

        assert valid is True
        assert error is None

    def test_valid_status_failed(self, tmp_path):
        """Test validation of FAILED status."""
        status_file = tmp_path / "status.txt"
        status_file.write_text("FAILED")

        valid, error = IntegrationProtocol.validate_status_file(status_file)

        assert valid is True
        assert error is None

    def test_valid_status_in_progress(self, tmp_path):
        """Test validation of IN_PROGRESS status."""
        status_file = tmp_path / "status.txt"
        status_file.write_text("IN_PROGRESS")

        valid, error = IntegrationProtocol.validate_status_file(status_file)

        assert valid is True
        assert error is None

    def test_valid_status_partial(self, tmp_path):
        """Test validation of PARTIAL status."""
        status_file = tmp_path / "status.txt"
        status_file.write_text("PARTIAL")

        valid, error = IntegrationProtocol.validate_status_file(status_file)

        assert valid is True
        assert error is None

    def test_invalid_status(self, tmp_path):
        """Test validation fails for invalid status."""
        status_file = tmp_path / "status.txt"
        status_file.write_text("INVALID")

        valid, error = IntegrationProtocol.validate_status_file(status_file)

        assert valid is False
        assert "Invalid status" in error

    def test_empty_status_file(self, tmp_path):
        """Test validation fails for empty file."""
        status_file = tmp_path / "status.txt"
        status_file.write_text("")

        valid, error = IntegrationProtocol.validate_status_file(status_file)

        assert valid is False
        assert "empty" in error

    def test_nonexistent_status_file(self, tmp_path):
        """Test validation fails for nonexistent file."""
        status_file = tmp_path / "status.txt"

        valid, error = IntegrationProtocol.validate_status_file(status_file)

        assert valid is False
        assert "does not exist" in error


class TestValidateSummaryFile:
    """Tests for validate_summary_file method."""

    def test_valid_summary(self, tmp_path):
        """Test validation of valid summary."""
        summary_file = tmp_path / "scope_summary.md"
        summary_file.write_text("# Scope Analysis\n\nComplete!")

        valid, error = IntegrationProtocol.validate_summary_file(summary_file)

        assert valid is True
        assert error is None

    def test_summary_without_heading(self, tmp_path):
        """Test validation fails without markdown heading."""
        summary_file = tmp_path / "scope_summary.md"
        summary_file.write_text("Not a heading")

        valid, error = IntegrationProtocol.validate_summary_file(summary_file)

        assert valid is False
        assert "markdown heading" in error

    def test_empty_summary(self, tmp_path):
        """Test validation fails for empty summary."""
        summary_file = tmp_path / "scope_summary.md"
        summary_file.write_text("")

        valid, error = IntegrationProtocol.validate_summary_file(summary_file)

        assert valid is False
        assert "empty" in error

    def test_nonexistent_summary(self, tmp_path):
        """Test validation fails for nonexistent file."""
        summary_file = tmp_path / "scope_summary.md"

        valid, error = IntegrationProtocol.validate_summary_file(summary_file)

        assert valid is False
        assert "does not exist" in error


class TestCreateFiles:
    """Tests for create_status_file and create_summary_file."""

    def test_create_status_file(self, tmp_path):
        """Test creating status file."""
        IntegrationProtocol.create_status_file(tmp_path, "SUCCESS")

        status_file = tmp_path / "status.txt"
        assert status_file.exists()
        assert status_file.read_text() == "SUCCESS"

    def test_create_status_file_invalid(self, tmp_path):
        """Test creating status file with invalid status."""
        with pytest.raises(ValueError, match="Invalid status"):
            IntegrationProtocol.create_status_file(tmp_path, "INVALID")

    def test_create_summary_file(self, tmp_path):
        """Test creating summary file."""
        content = "# Test Summary\n\nAll good!"
        IntegrationProtocol.create_summary_file(tmp_path, "test", content)

        summary_file = tmp_path / "test_summary.md"
        assert summary_file.exists()
        assert summary_file.read_text() == content

    def test_create_summary_file_empty_content(self, tmp_path):
        """Test creating summary file with empty content."""
        with pytest.raises(ValueError, match="cannot be empty"):
            IntegrationProtocol.create_summary_file(tmp_path, "test", "")

    def test_create_summary_file_without_heading(self, tmp_path):
        """Test creating summary file without markdown heading."""
        with pytest.raises(ValueError, match="markdown heading"):
            IntegrationProtocol.create_summary_file(tmp_path, "test", "No heading")


class TestGetStatus:
    """Tests for get_status method."""

    def test_get_status_success(self, tmp_path):
        """Test getting SUCCESS status."""
        (tmp_path / "status.txt").write_text("SUCCESS")

        status = IntegrationProtocol.get_status(tmp_path)
        assert status == "SUCCESS"

    def test_get_status_failed(self, tmp_path):
        """Test getting FAILED status."""
        (tmp_path / "status.txt").write_text("FAILED")

        status = IntegrationProtocol.get_status(tmp_path)
        assert status == "FAILED"

    def test_get_status_nonexistent(self, tmp_path):
        """Test getting status from nonexistent file."""
        status = IntegrationProtocol.get_status(tmp_path)
        assert status is None

    def test_get_status_invalid(self, tmp_path):
        """Test getting invalid status."""
        (tmp_path / "status.txt").write_text("INVALID")

        status = IntegrationProtocol.get_status(tmp_path)
        assert status is None


class TestCheckAllSubservers:
    """Tests for check_all_subservers method."""

    def test_check_all_success(self, tmp_path):
        """Test checking multiple sub-servers."""
        # Create scope subserver
        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "status.txt").write_text("SUCCESS")
        (scope_dir / "scope_summary.md").write_text("# Scope")

        # Create quality subserver
        quality_dir = tmp_path / "quality"
        quality_dir.mkdir()
        (quality_dir / "status.txt").write_text("SUCCESS")
        (quality_dir / "quality_summary.md").write_text("# Quality")

        results = IntegrationProtocol.check_all_subservers(tmp_path, ["scope", "quality"])

        assert len(results) == 2
        assert results["scope"]["valid"] is True
        assert results["scope"]["status"] == "SUCCESS"
        assert results["quality"]["valid"] is True
        assert results["quality"]["status"] == "SUCCESS"

    def test_check_with_failure(self, tmp_path):
        """Test checking sub-servers with one failing."""
        # Good subserver
        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()
        (scope_dir / "status.txt").write_text("SUCCESS")
        (scope_dir / "scope_summary.md").write_text("# Scope")

        # Bad subserver (missing summary)
        quality_dir = tmp_path / "quality"
        quality_dir.mkdir()
        (quality_dir / "status.txt").write_text("FAILED")

        results = IntegrationProtocol.check_all_subservers(tmp_path, ["scope", "quality"])

        assert results["scope"]["valid"] is True
        assert results["quality"]["valid"] is False
        assert len(results["quality"]["violations"]) > 0


class TestWaitForCompletion:
    """Tests for wait_for_completion method."""

    def test_wait_immediate_completion(self, tmp_path):
        """Test wait when already completed."""
        (tmp_path / "status.txt").write_text("SUCCESS")

        completed, status = IntegrationProtocol.wait_for_completion(tmp_path, timeout_seconds=1, poll_interval=0.1)

        assert completed is True
        assert status == "SUCCESS"

    def test_wait_still_in_progress(self, tmp_path):
        """Test wait when stuck in progress."""
        (tmp_path / "status.txt").write_text("IN_PROGRESS")

        completed, status = IntegrationProtocol.wait_for_completion(tmp_path, timeout_seconds=0.5, poll_interval=0.1)

        assert completed is False
        assert status == "IN_PROGRESS"

    def test_wait_no_status_file(self, tmp_path):
        """Test wait when status file doesn't exist."""
        completed, status = IntegrationProtocol.wait_for_completion(tmp_path, timeout_seconds=0.5, poll_interval=0.1)

        assert completed is False
        assert status is None
