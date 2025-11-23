"""Tests for Docs sub-server."""

import pytest

from btx_fix_mcp.subservers.review.docs import DocsSubServer


class TestDocsSubServer:
    """Tests for DocsSubServer class."""

    @pytest.fixture
    def project_with_docs(self, tmp_path):
        """Create a project with documentation."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Create README
        (project_dir / "README.md").write_text("# Test Project\n\nA test project.")

        # Create LICENSE
        (project_dir / "LICENSE").write_text("MIT License")

        # Create src directory
        src_dir = project_dir / "src"
        src_dir.mkdir()

        # Create Python file with docstrings
        (src_dir / "module.py").write_text('''
"""Module docstring."""


def documented_function():
    """This function has a docstring."""
    pass


def undocumented_function():
    pass


class DocumentedClass:
    """This class has a docstring."""
    pass
''')

        return project_dir

    @pytest.fixture
    def scope_output(self, project_with_docs, tmp_path):
        """Create scope output directory."""
        scope_dir = tmp_path / "scope"
        scope_dir.mkdir()

        # Create files list
        (scope_dir / "files_code.txt").write_text("src/module.py")

        return scope_dir

    def test_initialization(self, tmp_path):
        """Test sub-server initialization."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()

        server = DocsSubServer(
            input_dir=input_dir,
            output_dir=output_dir,
            repo_path=tmp_path,
        )

        assert server.name == "docs"
        assert server.output_dir == output_dir
        assert server.repo_path == tmp_path
        assert server.check_docstrings is True
        assert server.check_project_docs is True
        assert server.min_coverage == 80

    def test_initialization_custom_options(self, tmp_path):
        """Test initialization with custom options."""
        server = DocsSubServer(
            input_dir=tmp_path / "input",
            output_dir=tmp_path / "output",
            repo_path=tmp_path,
            check_docstrings=False,
            check_project_docs=False,
            min_coverage=50,
        )

        assert server.check_docstrings is False
        assert server.check_project_docs is False
        assert server.min_coverage == 50

    def test_validate_inputs_no_files(self, tmp_path):
        """Test validation fails with no files list."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        server = DocsSubServer(
            input_dir=input_dir,
            output_dir=tmp_path / "output",
            repo_path=tmp_path,
        )

        valid, missing = server.validate_inputs()

        assert valid is False
        assert any("No files list" in m for m in missing)

    def test_validate_inputs_with_files(self, scope_output, tmp_path):
        """Test validation passes with files list."""
        server = DocsSubServer(
            input_dir=scope_output,
            output_dir=tmp_path / "output",
            repo_path=tmp_path,
        )

        valid, missing = server.validate_inputs()

        assert valid is True
        assert missing == []

    def test_check_project_docs_with_readme(self, project_with_docs, tmp_path):
        """Test project docs check with README."""
        server = DocsSubServer(
            input_dir=tmp_path / "input",
            output_dir=tmp_path / "output",
            repo_path=project_with_docs,
        )

        result = server._check_project_docs()

        assert result["readme"] is True
        assert result["license"] is True

    def test_check_project_docs_missing(self, tmp_path):
        """Test project docs check without README."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        server = DocsSubServer(
            input_dir=tmp_path / "input",
            output_dir=tmp_path / "output",
            repo_path=empty_dir,
        )

        result = server._check_project_docs()

        assert result["readme"] is False
        assert len(result["issues"]) >= 1

    def test_find_missing_docstrings(self, project_with_docs, tmp_path):
        """Test finding missing docstrings."""
        server = DocsSubServer(
            input_dir=tmp_path / "input",
            output_dir=tmp_path / "output",
            repo_path=project_with_docs,
        )

        files = [str(project_with_docs / "src" / "module.py")]
        issues = server._find_missing_docstrings(files)

        # Should find undocumented_function as missing
        assert len(issues) >= 1
        names = [i.name for i in issues]
        assert "undocumented_function" in names

    def test_execute_with_docs(self, project_with_docs, scope_output, tmp_path):
        """Test execution with documentation."""
        # Update scope to use project files
        (scope_output / "files_code.txt").write_text("src/module.py")

        server = DocsSubServer(
            input_dir=scope_output,
            output_dir=tmp_path / "output",
            repo_path=project_with_docs,
        )

        result = server.run()

        assert result.status in ("SUCCESS", "PARTIAL")
        assert "Documentation Analysis" in result.summary
        # README and LICENSE exist, so project_docs_found should be >= 2
        assert result.metrics.get("project_docs_found", 0) >= 2

    def test_mindset_loaded(self, tmp_path):
        """Test that docs mindset is loaded."""
        server = DocsSubServer(
            input_dir=tmp_path / "input",
            output_dir=tmp_path / "output",
            repo_path=tmp_path,
        )

        assert server.mindset is not None
        assert server.mindset.name == "docs"

    def test_summary_includes_mindset(self, project_with_docs, scope_output, tmp_path):
        """Test that summary includes mindset information."""
        (scope_output / "files_code.txt").write_text("src/module.py")

        server = DocsSubServer(
            input_dir=scope_output,
            output_dir=tmp_path / "output",
            repo_path=project_with_docs,
        )

        result = server.run()

        assert "Reviewer Mindset" in result.summary
        assert "Verdict" in result.summary


class TestDocsSubServerMCPMode:
    """Tests for DocsSubServer in MCP mode."""

    def test_mcp_mode_enabled(self, tmp_path):
        """Test that MCP mode can be enabled."""
        server = DocsSubServer(
            input_dir=tmp_path / "input",
            output_dir=tmp_path / "output",
            repo_path=tmp_path,
            mcp_mode=True,
        )

        assert server.mcp_mode is True
        assert server.logger is not None
