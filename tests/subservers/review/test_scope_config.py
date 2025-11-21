"""Tests for Scope sub-server configuration.

Note: lib_layered_config reads from system config directories, not project-local
config files. These tests focus on parameter-based configuration.
"""

from pathlib import Path

import pytest

from btx_fix_mcp.subservers.review.scope import ScopeSubServer


class TestScopeConfiguration:
    """Tests for configuration loading and merging."""

    def test_exclude_patterns_from_parameters(self, tmp_path):
        """Test exclude patterns from constructor parameters."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "main.py").write_text("code")
        (repo_dir / "vendor" / "lib.py").parent.mkdir()
        (repo_dir / "vendor" / "lib.py").write_text("vendor code")

        output_dir = tmp_path / "output"
        server = ScopeSubServer(
            output_dir=output_dir,
            repo_path=repo_dir,
            mode="full",
            exclude_patterns=["vendor/"],
        )

        result = server.run()

        # Vendor files should be excluded
        files_content = result.artifacts["files_to_review"].read_text()
        assert "main.py" in files_content
        assert "vendor" not in files_content

    def test_include_patterns_from_parameters(self, tmp_path):
        """Test include patterns from constructor parameters."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "main.py").write_text("code")
        (repo_dir / "script.js").write_text("js code")
        (repo_dir / "README.md").write_text("docs")

        output_dir = tmp_path / "output"
        server = ScopeSubServer(
            output_dir=output_dir,
            repo_path=repo_dir,
            mode="full",
            include_patterns=["**/*.py"],  # Only Python files
        )

        result = server.run()

        # Only Python files should be included
        files_content = result.artifacts["files_to_review"].read_text()
        assert "main.py" in files_content
        assert "script.js" not in files_content
        assert "README.md" not in files_content

    def test_parameters_override_defaults(self, tmp_path):
        """Test that parameters override default config values."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "main.py").write_text("code")
        (repo_dir / "vendor" / "lib.py").parent.mkdir()
        (repo_dir / "vendor" / "lib.py").write_text("vendor code")

        output_dir = tmp_path / "output"
        # Parameter overrides any default - no exclusions
        server = ScopeSubServer(
            output_dir=output_dir,
            repo_path=repo_dir,
            mode="full",
            exclude_patterns=[],  # Explicitly no exclusions
        )

        result = server.run()

        # Vendor should be included (no exclusions)
        files_content = result.artifacts["files_to_review"].read_text()
        assert "main.py" in files_content
        assert "vendor/lib.py" in files_content

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

        # Default mode should be "git" from defaultconfig.toml or hardcoded default
        assert server.mode == "git"

    def test_config_shown_in_summary(self, tmp_path):
        """Test that configuration is shown in summary."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "main.py").write_text("code")

        output_dir = tmp_path / "output"
        server = ScopeSubServer(
            output_dir=output_dir,
            repo_path=repo_dir,
            mode="full",
            exclude_patterns=["dist/", "*.min.js"],
        )

        result = server.run()

        # Config should appear in summary
        assert "## Configuration" in result.summary
        assert "dist/" in result.summary
        assert "*.min.js" in result.summary

    def test_empty_exclude_patterns(self, tmp_path):
        """Test with explicitly empty exclude patterns."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "main.py").write_text("code")

        output_dir = tmp_path / "output"
        server = ScopeSubServer(
            output_dir=output_dir,
            repo_path=repo_dir,
            mode="full",
            exclude_patterns=[],  # Explicitly no exclusions
        )

        result = server.run()
        assert result.status == "SUCCESS"
        # Should use no exclusions beyond defaults

    def test_complex_patterns(self, tmp_path):
        """Test complex glob patterns."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "src" / "main.py").parent.mkdir()
        (repo_dir / "src" / "main.py").write_text("code")
        (repo_dir / "tests" / "test_main.py").parent.mkdir()
        (repo_dir / "tests" / "test_main.py").write_text("test")
        (repo_dir / "docs" / "README.md").parent.mkdir()
        (repo_dir / "docs" / "README.md").write_text("docs")

        output_dir = tmp_path / "output"
        server = ScopeSubServer(
            output_dir=output_dir,
            repo_path=repo_dir,
            mode="full",
            include_patterns=["src/**/*.py", "tests/**/*.py"],  # Only Python in src/tests
        )

        result = server.run()

        files_content = result.artifacts["files_to_review"].read_text()
        assert "src/main.py" in files_content
        assert "tests/test_main.py" in files_content
        assert "docs/README.md" not in files_content


class TestConfigurationIntegration:
    """Integration tests for configuration with orchestrator scenarios."""

    def test_orchestrator_passes_config(self, tmp_path):
        """Simulate orchestrator passing configuration to sub-server."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "app.py").write_text("code")
        (repo_dir / "vendor" / "lib.js").parent.mkdir()
        (repo_dir / "vendor" / "lib.js").write_text("vendor")

        # Orchestrator reads config and passes to sub-server
        orchestrator_config = {
            "exclude_patterns": ["vendor/", "node_modules/"],
            "mode": "full",
        }

        # Orchestrator creates sub-server with config
        output_dir = tmp_path / "output"
        server = ScopeSubServer(
            output_dir=output_dir,
            repo_path=repo_dir,
            mode=orchestrator_config["mode"],
            exclude_patterns=orchestrator_config["exclude_patterns"],
        )

        result = server.run()

        files_content = result.artifacts["files_to_review"].read_text()
        assert "app.py" in files_content
        assert "vendor" not in files_content

    def test_multiple_sub_servers_same_params(self, tmp_path):
        """Test multiple sub-servers using same parameters."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "app.py").write_text("code")

        # Shared config
        shared_config = {
            "mode": "full",
            "exclude_patterns": ["dist/"],
        }

        # Sub-server 1
        output_dir1 = tmp_path / "output1"
        server1 = ScopeSubServer(
            output_dir=output_dir1,
            repo_path=repo_dir,
            mode=shared_config["mode"],
            exclude_patterns=shared_config["exclude_patterns"],
        )
        result1 = server1.run()

        # Sub-server 2 (different instance, same config)
        output_dir2 = tmp_path / "output2"
        server2 = ScopeSubServer(
            output_dir=output_dir2,
            repo_path=repo_dir,
            mode=shared_config["mode"],
            exclude_patterns=shared_config["exclude_patterns"],
        )
        result2 = server2.run()

        # Both should have same mode
        assert server1.mode == server2.mode == "full"
        assert result1.metrics["mode"] == result2.metrics["mode"]
