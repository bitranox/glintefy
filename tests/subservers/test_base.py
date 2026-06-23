"""Tests for BaseSubServer and SubServerResult."""

import pytest
from pathlib import Path
from glintefy.subservers.base import BaseSubServer, SubServerResult


class TestSubServerResult:
    """Tests for SubServerResult class."""

    def test_result_creation_success(self):
        """Test creating a successful result."""
        result = SubServerResult(
            status="SUCCESS",
            summary="All tests passed",
            artifacts={"report": Path("/tmp/report.md")},
            metrics={"files_processed": 10},
        )

        assert result.status == "SUCCESS"
        assert result.summary == "All tests passed"
        assert result.artifacts == {"report": Path("/tmp/report.md")}
        assert result.metrics == {"files_processed": 10}
        assert result.errors == []
        assert result.timestamp is not None

    def test_result_creation_with_errors(self):
        """Test creating a failed result with errors."""
        errors = ["File not found", "Parse error"]
        result = SubServerResult(
            status="FAILED",
            summary="Execution failed",
            artifacts={},
            errors=errors,
        )

        assert result.status == "FAILED"
        assert result.errors == errors

    def test_invalid_status_raises_error(self):
        """Test that invalid status raises ValueError."""
        with pytest.raises(ValueError, match="Invalid status"):
            SubServerResult(
                status="INVALID",
                summary="Test",
                artifacts={},
            )

    def test_to_dict(self):
        """Test converting result to dictionary."""
        result = SubServerResult(
            status="SUCCESS",
            summary="Test summary",
            artifacts={"file1": Path("/tmp/test.txt")},
            metrics={"count": 5},
        )

        result_dict = result.to_dict()
        assert result_dict["status"] == "SUCCESS"
        assert result_dict["summary"] == "Test summary"
        assert result_dict["artifacts"]["file1"] == "/tmp/test.txt"
        assert result_dict["metrics"]["count"] == 5


class DummySubServer(BaseSubServer):
    """Dummy sub-server for testing."""

    def validate_inputs(self) -> tuple[bool, list[str]]:
        """Check if input.txt exists."""
        required_file = self.input_dir / "input.txt"
        if required_file.exists():
            return True, []
        return False, ["input.txt"]

    def execute(self) -> SubServerResult:
        """Simple execution that reads input and creates output."""
        input_file = self.input_dir / "input.txt"
        content = input_file.read_text()

        output_file = self.output_dir / "output.txt"
        output_file.write_text(f"Processed: {content}")

        return SubServerResult(
            status="SUCCESS",
            summary=f"# {self.name} Complete\n\nProcessed successfully",
            artifacts={"output": output_file},
            metrics={"input_length": len(content)},
        )


class FailingSubServer(BaseSubServer):
    """Sub-server that always fails during execution."""

    def validate_inputs(self) -> tuple[bool, list[str]]:
        """Inputs always valid."""
        return True, []

    def execute(self) -> SubServerResult:
        """Raise an exception."""
        raise RuntimeError("Intentional failure")


class TestBaseSubServer:
    """Tests for BaseSubServer class."""

    def test_initialization(self, tmp_path):
        """Test sub-server initialization."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()

        server = DummySubServer("test", input_dir, output_dir)

        assert server.name == "test"
        assert server.input_dir == input_dir
        assert server.output_dir == output_dir
        assert output_dir.exists()  # Should be created

    def test_save_status(self, tmp_path):
        """Test saving status file."""
        server = DummySubServer("test", tmp_path / "in", tmp_path / "out")

        server.save_status("IN_PROGRESS")
        status_file = server.output_dir / "status.txt"
        assert status_file.exists()
        assert status_file.read_text() == "IN_PROGRESS"

    def test_save_status_invalid(self, tmp_path):
        """Test that invalid status raises error."""
        server = DummySubServer("test", tmp_path / "in", tmp_path / "out")

        with pytest.raises(ValueError, match="Invalid status"):
            server.save_status("INVALID")

    def test_save_summary(self, tmp_path):
        """Test saving summary file."""
        server = DummySubServer("test", tmp_path / "in", tmp_path / "out")

        summary = "# Test Summary\n\nAll good!"
        server.save_summary(summary)

        summary_file = server.output_dir / "test_summary.md"
        assert summary_file.exists()
        assert summary_file.read_text() == summary

    def test_save_json(self, tmp_path):
        """Test saving JSON file."""
        server = DummySubServer("test", tmp_path / "in", tmp_path / "out")

        data = {"key": "value", "count": 42}
        server.save_json("data.json", data)

        json_file = server.output_dir / "data.json"
        assert json_file.exists()

        import json

        loaded = json.loads(json_file.read_text())
        assert loaded == data

    def test_run_success(self, tmp_path):
        """Test successful execution via run()."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()

        # Create input file
        input_file = input_dir / "input.txt"
        input_file.write_text("Hello World")

        server = DummySubServer("test", input_dir, output_dir)
        result = server.run()

        # Check result
        assert result.status == "SUCCESS"
        assert "Processed successfully" in result.summary
        assert result.metrics["input_length"] == 11

        # Check files created
        assert (output_dir / "status.txt").exists()
        assert (output_dir / "test_summary.md").exists()
        assert (output_dir / "result.json").exists()
        assert (output_dir / "output.txt").exists()

        # Check status file
        assert (output_dir / "status.txt").read_text() == "SUCCESS"

    def test_run_missing_input(self, tmp_path):
        """Test run() with missing inputs."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        # Don't create input.txt

        server = DummySubServer("test", input_dir, output_dir)
        result = server.run()

        # Check result
        assert result.status == "FAILED"
        assert "Missing inputs: input.txt" in result.summary
        assert "input.txt" in result.errors[0]

        # Check status
        assert (output_dir / "status.txt").read_text() == "FAILED"

    def test_run_execution_exception(self, tmp_path):
        """Test run() with execution exception."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()

        server = FailingSubServer("test", input_dir, output_dir)
        result = server.run()

        # Check result
        assert result.status == "FAILED"
        assert "Intentional failure" in result.summary
        assert len(result.errors) > 0

        # Check status
        assert (output_dir / "status.txt").read_text() == "FAILED"


class TestIntegrationProtocol:
    """Test compliance with integration protocol."""

    def test_protocol_files_created(self, tmp_path):
        """Test that required protocol files are created."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()

        # Create input
        (input_dir / "input.txt").write_text("test")

        server = DummySubServer("myserver", input_dir, output_dir)
        server.run()

        # Check required files exist
        assert (output_dir / "status.txt").exists()
        assert (output_dir / "myserver_summary.md").exists()

    def test_status_values(self, tmp_path):
        """Test that status.txt contains valid values."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()

        # Create input
        (input_dir / "input.txt").write_text("test")

        server = DummySubServer("test", input_dir, output_dir)
        server.run()

        status = (output_dir / "status.txt").read_text()
        assert status in ("SUCCESS", "FAILED", "PARTIAL")

    def test_summary_is_markdown(self, tmp_path):
        """Test that summary is markdown formatted."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()

        # Create input
        (input_dir / "input.txt").write_text("test")

        server = DummySubServer("test", input_dir, output_dir)
        server.run()

        summary = (output_dir / "test_summary.md").read_text()
        assert summary.startswith("#")  # Markdown heading
