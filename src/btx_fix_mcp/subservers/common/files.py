"""File I/O utilities for sub-servers."""

from pathlib import Path


def read_file(path: Path) -> str:
    """Read file with error handling.

    Args:
        path: File path

    Returns:
        File contents as string

    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file cannot be read
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    try:
        return path.read_text()
    except Exception as e:
        raise IOError(f"Failed to read {path}: {e}")


def write_file(path: Path, content: str) -> None:
    """Write file with error handling.

    Args:
        path: File path
        content: Content to write

    Raises:
        IOError: If file cannot be written
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    except Exception as e:
        raise IOError(f"Failed to write {path}: {e}")


def ensure_dir(path: Path) -> None:
    """Ensure directory exists.

    Args:
        path: Directory path
    """
    path.mkdir(parents=True, exist_ok=True)


def find_files(
    root: Path,
    pattern: str = "*",
    exclude_patterns: list[str] | None = None,
) -> list[Path]:
    """Find files matching pattern.

    Args:
        root: Root directory to search
        pattern: Glob pattern (e.g., "*.py", "**/*.js")
        exclude_patterns: Patterns to exclude using pathlib.match() syntax.
                         Patterns should already be normalized (e.g., "**/vendor/*" not "vendor/")

    Returns:
        List of matching file paths, sorted

    Pattern Syntax:
        *        - Matches one path component (e.g., "*.py")
        **       - Matches zero or more path components (e.g., "**/test/*")
        ?        - Matches one character

    Example:
        >>> from pathlib import Path
        >>> files = find_files(Path("src"), "*.py", ["**/test_*.py", "**/vendor/*"])
    """
    if not root.exists():
        return []

    exclude_patterns = exclude_patterns or [
        "**/node_modules/*",
        "**/.venv/*",
        "**/__pycache__/*",
        "**/dist/*",
        "**/build/*",
        "**/.git/*",
        "**/LLM-CONTEXT/*",
        "*.pyc",
        "*.pyo",
        "*.lock",
    ]

    files: list[Path] = []
    for file_path in root.rglob(pattern):
        if file_path.is_file():
            # Check exclusions - patterns should already be normalized
            excluded = any(file_path.match(excl) for excl in exclude_patterns)
            if not excluded:
                files.append(file_path)

    return sorted(files)


def count_lines(file_path: Path) -> int:
    """Count lines in a file.

    Args:
        file_path: Path to file

    Returns:
        Number of lines in file

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        with open(file_path) as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def get_file_extension(file_path: Path) -> str:
    """Get file extension without dot.

    Args:
        file_path: Path to file

    Returns:
        Extension without dot (e.g., "py", "js", "md")

    Example:
        >>> get_file_extension(Path("test.py"))
        'py'
        >>> get_file_extension(Path("README.md"))
        'md'
    """
    return file_path.suffix.lstrip(".")


def categorize_files(files: list[Path]) -> dict[str, list[Path]]:
    """Categorize files by type.

    Args:
        files: List of file paths

    Returns:
        Dictionary mapping category to file list
        Categories: CODE, TEST, DOCS, CONFIG, BUILD, OTHER

    Example:
        >>> files = [Path("src/main.py"), Path("test_main.py"), Path("README.md")]
        >>> categorize_files(files)
        {'CODE': [Path('src/main.py')], 'TEST': [Path('test_main.py')], 'DOCS': [Path('README.md')]}
    """
    categories: dict[str, list[Path]] = {
        "CODE": [],
        "TEST": [],
        "DOCS": [],
        "CONFIG": [],
        "BUILD": [],
        "OTHER": [],
    }

    for file_path in files:
        path_str = str(file_path).lower()
        name = file_path.name.lower()

        # Test files
        if any(keyword in path_str for keyword in ["test", "spec", "__tests__", "tests/"]) or name.startswith("test_"):
            categories["TEST"].append(file_path)

        # Documentation
        elif file_path.suffix.lower() in [".md", ".rst", ".txt", ".adoc"]:
            categories["DOCS"].append(file_path)

        # Config files
        elif any(keyword in name for keyword in ["config", ".json", ".yml", ".yaml", ".toml", ".ini"]):
            categories["CONFIG"].append(file_path)

        # Build files
        elif name in ["dockerfile", "makefile"] or ".dockerfile" in name or ".mk" in name:
            categories["BUILD"].append(file_path)

        # Code files
        elif file_path.suffix.lower() in [
            ".py",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".java",
            ".go",
            ".rs",
            ".cpp",
            ".c",
            ".rb",
            ".php",
        ]:
            categories["CODE"].append(file_path)

        # Other
        else:
            categories["OTHER"].append(file_path)

    return categories
