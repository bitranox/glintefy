"""Tests for file utilities."""

import pytest
from pathlib import Path
from glintefy.subservers.common.files import (
    read_file,
    write_file,
    ensure_dir,
    find_files,
    count_lines,
    get_file_extension,
    categorize_files,
)


class TestReadWrite:
    """Tests for read_file and write_file."""

    def test_write_and_read_file(self, tmp_path):
        """Test writing and reading a file."""
        file_path = tmp_path / "test.txt"
        content = "Hello World!"

        write_file(file_path, content)
        assert file_path.exists()

        read_content = read_file(file_path)
        assert read_content == content

    def test_write_creates_parent_dirs(self, tmp_path):
        """Test that write_file creates parent directories."""
        file_path = tmp_path / "subdir" / "nested" / "file.txt"
        write_file(file_path, "content")

        assert file_path.exists()
        assert file_path.parent.exists()

    def test_read_nonexistent_file_raises_error(self, tmp_path):
        """Test that reading nonexistent file raises FileNotFoundError."""
        file_path = tmp_path / "nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            read_file(file_path)


class TestEnsureDir:
    """Tests for ensure_dir."""

    def test_ensure_dir_creates_directory(self, tmp_path):
        """Test that ensure_dir creates directory."""
        dir_path = tmp_path / "new_dir"
        ensure_dir(dir_path)

        assert dir_path.exists()
        assert dir_path.is_dir()

    def test_ensure_dir_nested(self, tmp_path):
        """Test that ensure_dir creates nested directories."""
        dir_path = tmp_path / "a" / "b" / "c"
        ensure_dir(dir_path)

        assert dir_path.exists()

    def test_ensure_dir_existing(self, tmp_path):
        """Test that ensure_dir works on existing directory."""
        dir_path = tmp_path / "existing"
        dir_path.mkdir()

        ensure_dir(dir_path)  # Should not raise error
        assert dir_path.exists()


class TestFindFiles:
    """Tests for find_files."""

    def test_find_all_files(self, tmp_path):
        """Test finding all files."""
        # Create test files
        (tmp_path / "file1.txt").write_text("test")
        (tmp_path / "file2.py").write_text("test")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file3.js").write_text("test")

        files = find_files(tmp_path, "*")
        assert len(files) == 3

    def test_find_by_pattern(self, tmp_path):
        """Test finding files by pattern."""
        # Create test files
        (tmp_path / "test.py").write_text("test")
        (tmp_path / "test.js").write_text("test")
        (tmp_path / "README.md").write_text("test")

        python_files = find_files(tmp_path, "*.py")
        assert len(python_files) == 1
        assert python_files[0].suffix == ".py"

    def test_find_recursive(self, tmp_path):
        """Test recursive file finding."""
        # Create nested structure
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("test")
        (tmp_path / "src" / "utils").mkdir()
        (tmp_path / "src" / "utils" / "helper.py").write_text("test")

        files = find_files(tmp_path, "**/*.py")
        assert len(files) == 2

    def test_exclusion_patterns(self, tmp_path):
        """Test that exclusion patterns work."""
        # Create files
        (tmp_path / "main.py").write_text("test")
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "lib.py").write_text("test")
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "cache.pyc").write_text("test")

        files = find_files(tmp_path, "*")
        # Should only find main.py (node_modules and __pycache__ excluded)
        assert len(files) == 1
        assert files[0].name == "main.py"

    def test_custom_exclusions(self, tmp_path):
        """Test custom exclusion patterns."""
        # Create files
        (tmp_path / "keep.txt").write_text("test")
        (tmp_path / "exclude.txt").write_text("test")

        files = find_files(tmp_path, "*.txt", exclude_patterns=["**/exclude.txt"])
        assert len(files) == 1
        assert files[0].name == "keep.txt"

    def test_nonexistent_directory(self, tmp_path):
        """Test finding files in nonexistent directory."""
        files = find_files(tmp_path / "nonexistent", "*")
        assert files == []


class TestCountLines:
    """Tests for count_lines."""

    def test_count_lines_single_line(self, tmp_path):
        """Test counting lines in single-line file."""
        file_path = tmp_path / "single.txt"
        file_path.write_text("Single line")

        assert count_lines(file_path) == 1

    def test_count_lines_multiple(self, tmp_path):
        """Test counting multiple lines."""
        file_path = tmp_path / "multi.txt"
        file_path.write_text("Line 1\nLine 2\nLine 3\n")

        assert count_lines(file_path) == 3

    def test_count_lines_empty(self, tmp_path):
        """Test counting lines in empty file."""
        file_path = tmp_path / "empty.txt"
        file_path.write_text("")

        assert count_lines(file_path) == 0

    def test_count_lines_nonexistent(self, tmp_path):
        """Test counting lines in nonexistent file."""
        file_path = tmp_path / "nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            count_lines(file_path)


class TestGetFileExtension:
    """Tests for get_file_extension."""

    def test_python_extension(self):
        """Test getting .py extension."""
        assert get_file_extension(Path("test.py")) == "py"

    def test_javascript_extension(self):
        """Test getting .js extension."""
        assert get_file_extension(Path("script.js")) == "js"

    def test_markdown_extension(self):
        """Test getting .md extension."""
        assert get_file_extension(Path("README.md")) == "md"

    def test_no_extension(self):
        """Test file without extension."""
        assert get_file_extension(Path("Makefile")) == ""

    def test_multiple_dots(self):
        """Test file with multiple dots."""
        assert get_file_extension(Path("file.test.py")) == "py"


class TestCategorizeFiles:
    """Tests for categorize_files."""

    def test_categorize_code_files(self):
        """Test categorizing code files."""
        files = [
            Path("src/main.py"),
            Path("src/utils.js"),
            Path("src/helper.go"),
        ]

        categories = categorize_files(files)
        assert len(categories["CODE"]) == 3
        assert len(categories["TEST"]) == 0

    def test_categorize_test_files(self):
        """Test categorizing test files."""
        files = [
            Path("test_main.py"),
            Path("tests/test_utils.py"),
            Path("src/main.spec.js"),
        ]

        categories = categorize_files(files)
        assert len(categories["TEST"]) == 3
        assert len(categories["CODE"]) == 0

    def test_categorize_docs(self):
        """Test categorizing documentation files."""
        files = [
            Path("README.md"),
            Path("docs/guide.rst"),
            Path("CHANGELOG.txt"),
        ]

        categories = categorize_files(files)
        assert len(categories["DOCS"]) == 3

    def test_categorize_config(self):
        """Test categorizing config files."""
        files = [
            Path("config.yml"),
            Path("settings.json"),
            Path("pyproject.toml"),
        ]

        categories = categorize_files(files)
        assert len(categories["CONFIG"]) == 3

    def test_categorize_build(self):
        """Test categorizing build files."""
        files = [
            Path("Dockerfile"),
            Path("Makefile"),
            Path("build.mk"),
        ]

        categories = categorize_files(files)
        assert len(categories["BUILD"]) == 3

    def test_categorize_mixed(self):
        """Test categorizing mixed files."""
        files = [
            Path("src/main.py"),  # CODE
            Path("test_main.py"),  # TEST
            Path("README.md"),  # DOCS
            Path("config.json"),  # CONFIG
            Path("Dockerfile"),  # BUILD
            Path("data.csv"),  # OTHER
        ]

        categories = categorize_files(files)
        assert len(categories["CODE"]) == 1
        assert len(categories["TEST"]) == 1
        assert len(categories["DOCS"]) == 1
        assert len(categories["CONFIG"]) == 1
        assert len(categories["BUILD"]) == 1
        assert len(categories["OTHER"]) == 1

    def test_categorize_empty_list(self):
        """Test categorizing empty list."""
        categories = categorize_files([])
        assert all(len(files) == 0 for files in categories.values())
