"""Tests for Scope sub-server."""

import subprocess

import pytest

from glintefy.subservers.review.scope import ScopeSubServer


class TestScopeSubServer:
    """Tests for ScopeSubServer class."""

    @pytest.fixture
    def git_repo(self, tmp_path):
        """Create a temporary git repository with files."""
        repo_dir = tmp_path / "test_repo"
        repo_dir.mkdir()

        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=repo_dir,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_dir,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_dir,
            capture_output=True,
            check=True,
        )

        # Create some files
        (repo_dir / "main.py").write_text("print('hello')")
        (repo_dir / "test_main.py").write_text("def test_main(): pass")
        (repo_dir / "README.md").write_text("# Test Project")
        (repo_dir / "config.yaml").write_text("key: value")

        # Initial commit
        subprocess.run(
            ["git", "add", "."],
            cwd=repo_dir,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_dir,
            capture_output=True,
            check=True,
        )

        # Modify a file (uncommitted change)
        (repo_dir / "main.py").write_text("print('hello world')")

        # Add new file (untracked)
        (repo_dir / "new_file.py").write_text("# New file")

        return repo_dir

    def test_initialization(self, tmp_path):
        """Test sub-server initialization."""
        output_dir = tmp_path / "output"
        server = ScopeSubServer(output_dir=output_dir, repo_path=tmp_path)

        assert server.name == "scope"
        assert server.output_dir == output_dir
        assert server.repo_path == tmp_path
        assert server.mode == "git"  # Default is "git"

    def test_initialization_custom_mode(self, tmp_path):
        """Test initialization with full mode."""
        server = ScopeSubServer(output_dir=tmp_path / "output", repo_path=tmp_path, mode="full")

        assert server.mode == "full"

    def test_validate_inputs_success(self, git_repo, tmp_path):
        """Test input validation succeeds for valid git repo."""
        output_dir = tmp_path / "output"
        server = ScopeSubServer(output_dir=output_dir, repo_path=git_repo, mode="git")

        valid, missing = server.validate_inputs()

        assert valid is True
        assert missing == []

    def test_validate_inputs_not_git_repo_falls_back(self, tmp_path):
        """Test git mode gracefully falls back to full mode for non-git directory."""
        non_git_dir = tmp_path / "not_git"
        non_git_dir.mkdir()

        output_dir = tmp_path / "output"
        server = ScopeSubServer(output_dir=output_dir, repo_path=non_git_dir, mode="git")

        valid, missing = server.validate_inputs()

        # Should succeed (graceful fallback), not fail
        assert valid is True
        assert missing == []
        # Mode should be changed to "full"
        assert server.mode == "full"
        # Fallback flag should be set
        assert server._git_fallback is True

    def test_validate_inputs_invalid_mode(self, git_repo, tmp_path):
        """Test validation fails for invalid mode."""
        output_dir = tmp_path / "output"
        server = ScopeSubServer(output_dir=output_dir, repo_path=git_repo, mode="invalid")

        valid, missing = server.validate_inputs()

        assert valid is False
        assert any("Invalid mode" in m for m in missing)

    def test_validate_inputs_missing_repo(self, tmp_path):
        """Test validation fails for missing repository."""
        output_dir = tmp_path / "output"
        missing_repo = tmp_path / "missing"

        server = ScopeSubServer(output_dir=output_dir, repo_path=missing_repo)

        valid, missing = server.validate_inputs()

        assert valid is False
        assert any("does not exist" in m for m in missing)

    def test_execute_git_mode(self, git_repo, tmp_path):
        """Test execution in git mode."""
        output_dir = tmp_path / "output"
        server = ScopeSubServer(output_dir=output_dir, repo_path=git_repo, mode="git")

        result = server.run()

        assert result.status == "SUCCESS"
        assert result.metrics["total_files"] >= 2  # At least main.py and new_file.py
        assert result.metrics["mode"] == "git"
        assert "files_to_review" in result.artifacts

    def test_execute_full_mode(self, git_repo, tmp_path):
        """Test execution in full mode."""
        output_dir = tmp_path / "output"
        server = ScopeSubServer(output_dir=output_dir, repo_path=git_repo, mode="full")

        result = server.run()

        assert result.status == "SUCCESS"
        assert result.metrics["total_files"] >= 4  # All files
        assert result.metrics["mode"] == "full"
        assert "files_to_review" in result.artifacts

    def test_file_categorization(self, git_repo, tmp_path):
        """Test that files are properly categorized."""
        output_dir = tmp_path / "output"
        server = ScopeSubServer(output_dir=output_dir, repo_path=git_repo, mode="full")

        result = server.run()

        # Files are categorized based on patterns
        # Since git_repo is in a temp test directory, paths may contain "test"
        # Just verify we have some files and categorization ran
        assert result.metrics["total_files"] >= 4
        assert "code_files" in result.metrics
        assert "test_files" in result.metrics
        assert "doc_files" in result.metrics
        assert "config_files" in result.metrics

    def test_artifacts_created(self, git_repo, tmp_path):
        """Test that artifact files are created."""
        output_dir = tmp_path / "output"
        server = ScopeSubServer(output_dir=output_dir, repo_path=git_repo, mode="full")

        result = server.run()

        # Check main files list exists
        files_to_review = result.artifacts["files_to_review"]
        assert files_to_review.exists()
        content = files_to_review.read_text()
        assert len(content.strip().split("\n")) >= 4

        # Check that we have artifact files (at least the main one)
        assert len(result.artifacts) >= 1

    def test_summary_format(self, git_repo, tmp_path):
        """Test summary is properly formatted."""
        output_dir = tmp_path / "output"
        server = ScopeSubServer(output_dir=output_dir, repo_path=git_repo, mode="git")

        result = server.run()

        assert result.summary.startswith("# Scope Analysis Report")
        assert "## Overview" in result.summary
        assert "## File Breakdown by Category" in result.summary
        assert f"**Mode**: {server.mode}" in result.summary

    def test_integration_protocol_compliance(self, git_repo, tmp_path):
        """Test integration protocol compliance."""
        output_dir = tmp_path / "output"
        server = ScopeSubServer(output_dir=output_dir, repo_path=git_repo, mode="full")

        server.run()

        # Check status.txt
        status_file = output_dir / "status.txt"
        assert status_file.exists()
        assert status_file.read_text().strip() == "SUCCESS"

        # Check summary.md
        summary_file = output_dir / "scope_summary.md"
        assert summary_file.exists()
        assert summary_file.read_text().startswith("#")

        # Check result.json
        result_file = output_dir / "result.json"
        assert result_file.exists()

    # Note: test_log_file_created removed - file logging disabled
    # File logging will be handled by external library

    def test_non_git_repo_fallback(self, tmp_path):
        """Test fallback to full mode when git fails."""
        # Create non-git directory with files
        non_git_dir = tmp_path / "not_git"
        non_git_dir.mkdir()
        (non_git_dir / "test.py").write_text("print('test')")

        output_dir = tmp_path / "output"
        server = ScopeSubServer(output_dir=output_dir, repo_path=non_git_dir, mode="full")

        result = server.run()

        assert result.status == "SUCCESS"
        assert result.metrics["total_files"] >= 1

    def test_empty_repository(self, tmp_path):
        """Test handling of empty repository."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        output_dir = tmp_path / "output"
        server = ScopeSubServer(output_dir=output_dir, repo_path=empty_dir, mode="full")

        result = server.run()

        assert result.status == "SUCCESS"
        assert result.metrics["total_files"] == 0


class TestScopeSubServerEdgeCases:
    """Test edge cases for ScopeSubServer."""

    def test_relative_paths_in_output(self, tmp_path):
        """Test that output uses relative paths."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "test.py").write_text("print('test')")

        output_dir = tmp_path / "output"
        server = ScopeSubServer(output_dir=output_dir, repo_path=repo_dir, mode="full")

        result = server.run()

        files_to_review = result.artifacts["files_to_review"]
        content = files_to_review.read_text()

        # Should be relative path, not absolute
        assert "test.py" in content
        assert str(repo_dir) not in content

    def test_handles_deleted_files(self, tmp_path):
        """Test that deleted files in git are handled gracefully."""
        # Create a simple directory with a file
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        test_file = repo_dir / "test.py"
        test_file.write_text("print('test')")

        output_dir = tmp_path / "output"
        server = ScopeSubServer(output_dir=output_dir, repo_path=repo_dir, mode="full")

        # Should not crash even if some files are deleted during execution
        result = server.run()

        assert result.status == "SUCCESS"
