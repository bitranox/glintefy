"""Tests for Scope sub-server configuration.

Tests focus on parameters actually supported by ScopeSubServer.
"""

from pathlib import Path


from glintefy.subservers.review.scope import ScopeSubServer


class TestScopeConfiguration:
    """Tests for ScopeSubServer configuration."""

    def test_mode_from_parameter(self, tmp_path):
        """Test mode is set from parameter."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "main.py").write_text("code")

        output_dir = tmp_path / "output"
        server = ScopeSubServer(
            output_dir=output_dir,
            repo_path=repo_dir,
            mode="full",
        )

        assert server.mode == "full"

    def test_default_mode_is_git(self, tmp_path):
        """Test default mode is git when no parameter provided."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "main.py").write_text("code")

        output_dir = tmp_path / "output"
        server = ScopeSubServer(
            output_dir=output_dir,
            repo_path=repo_dir,
        )

        # Default mode should be "git"
        assert server.mode == "git"

    def test_repo_path_is_set(self, tmp_path):
        """Test repo_path is properly set."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        output_dir = tmp_path / "output"
        server = ScopeSubServer(
            output_dir=output_dir,
            repo_path=repo_dir,
        )

        assert server.repo_path == repo_dir

    def test_repo_path_defaults_to_cwd(self, tmp_path):
        """Test repo_path defaults to current working directory if not provided."""
        output_dir = tmp_path / "output"
        server = ScopeSubServer(
            output_dir=output_dir,
        )

        assert server.repo_path == Path.cwd()

    def test_name_defaults_to_scope(self, tmp_path):
        """Test name defaults to 'scope'."""
        output_dir = tmp_path / "output"
        server = ScopeSubServer(
            output_dir=output_dir,
        )

        assert server.name == "scope"

    def test_custom_name(self, tmp_path):
        """Test custom name can be set."""
        output_dir = tmp_path / "output"
        server = ScopeSubServer(
            name="custom_scope",
            output_dir=output_dir,
        )

        assert server.name == "custom_scope"


class TestScopeConfigurationExecution:
    """Tests for ScopeSubServer execution with config."""

    def test_full_mode_execution(self, tmp_path):
        """Test execution in full mode."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "main.py").write_text("print('hello')")
        (repo_dir / "test_main.py").write_text("def test(): pass")

        output_dir = tmp_path / "output"
        server = ScopeSubServer(
            output_dir=output_dir,
            repo_path=repo_dir,
            mode="full",
        )

        result = server.run()

        assert result.status == "SUCCESS"
        assert result.metrics["mode"] == "full"
        assert result.metrics["total_files"] >= 2
