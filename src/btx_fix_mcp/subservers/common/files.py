"""File I/O utilities for sub-servers."""

from pathlib import Path, PurePosixPath


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
        raise OSError(f"Failed to read {path}: {e}") from e


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
        raise OSError(f"Failed to write {path}: {e}") from e


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
        # Virtual environments
        "**/.venv/**/*",
        ".venv/**/*",
        "**/venv/**/*",
        "venv/**/*",
        "**/.env/**/*",
        "**/env/**/*",
        "**/.virtualenv/**/*",
        "**/virtualenv/**/*",
        # Dependency directories
        "**/vendor/**/*",
        "**/node_modules/**/*",
        "**/__pycache__/**/*",
        "__pycache__/**/*",
        "**/.tox/**/*",
        ".tox/**/*",
        "**/.nox/**/*",
        ".nox/**/*",
        "**/.pytest_cache/**/*",
        ".pytest_cache/**/*",
        "**/.mypy_cache/**/*",
        ".mypy_cache/**/*",
        "**/.ruff_cache/**/*",
        ".ruff_cache/**/*",
        # Build artifacts
        "**/dist/**/*",
        "dist/**/*",
        "**/build/**/*",
        "build/**/*",
        "**/*.egg-info/**/*",
        "*.egg-info/**/*",
        # Version control
        "**/.git/**/*",
        ".git/**/*",
        # Compiled/generated files
        "*.pyc",
        "*.pyo",
        "*.lock",
        "*.min.js",
        "*.min.css",
        # Project-specific
        "**/LLM-CONTEXT/**/*",
        "LLM-CONTEXT/**/*",
        "**/scripts/**/*",
        "scripts/**/*",
        # IDE and editor configs
        "**/.claude/**/*",
        ".claude/**/*",
        "**/.devcontainer/**/*",
        ".devcontainer/**/*",
        "**/.idea/**/*",
        ".idea/**/*",
        "**/.vscode/**/*",
        ".vscode/**/*",
        # CI/CD and tooling configs
        "**/.github/**/*",
        ".github/**/*",
        "**/.qlty/**/*",
        ".qlty/**/*",
        # Config files at root
        "*.example",
        "codecov.yml",
        ".snyk",
    ]

    # Normalize patterns to POSIX-style so matching is consistent across OSes
    normalized_excludes = [p.replace("\\", "/") for p in exclude_patterns]

    files: list[Path] = []
    for file_path in root.rglob(pattern):
        if file_path.is_file():
            # Check exclusions using multiple methods for reliability
            path_posix = file_path.as_posix()
            rel_posix = file_path.relative_to(root).as_posix()
            excluded = False
            for excl in normalized_excludes:
                # Method 1: Path.match() for glob patterns
                posix_path = PurePosixPath(path_posix)
                if posix_path.match(excl) or PurePosixPath(rel_posix).match(excl):
                    excluded = True
                    break
                # Method 2: Check if path contains excluded directory
                # Extract directory name from pattern like "**/.mypy_cache/**/*" -> ".mypy_cache"
                if "**" in excl:
                    parts = excl.replace("**", "").strip("/").split("/")
                    dir_name = next((p for p in parts if p and not p.startswith("*")), None)
                    if dir_name and f"/{dir_name}/" in f"/{path_posix}/":
                        excluded = True
                        break
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


TEST_KEYWORDS = ["test", "spec", "__tests__", "tests/"]
DOCS_EXTENSIONS = {".md", ".rst", ".txt", ".adoc"}
CONFIG_KEYWORDS = ["config", ".json", ".yml", ".yaml", ".toml", ".ini"]
BUILD_FILES = {"dockerfile", "makefile"}
BUILD_PATTERNS = {".dockerfile", ".mk"}
CODE_EXTENSIONS = {
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
}


def _is_test_file(file_path: Path) -> bool:
    """Check if file is a test file."""
    path_str = str(file_path).lower()
    name = file_path.name.lower()

    if name.startswith("test_"):
        return True

    for keyword in TEST_KEYWORDS:
        if keyword in path_str:
            return True

    return False


def _is_docs_file(file_path: Path) -> bool:
    """Check if file is a documentation file."""
    return file_path.suffix.lower() in DOCS_EXTENSIONS


def _is_config_file(file_path: Path) -> bool:
    """Check if file is a configuration file."""
    name = file_path.name.lower()

    for keyword in CONFIG_KEYWORDS:
        if keyword in name:
            return True

    return False


def _is_build_file(file_path: Path) -> bool:
    """Check if file is a build file."""
    name = file_path.name.lower()

    if name in BUILD_FILES:
        return True

    for pattern in BUILD_PATTERNS:
        if pattern in name:
            return True

    return False


def _is_code_file(file_path: Path) -> bool:
    """Check if file is a source code file."""
    return file_path.suffix.lower() in CODE_EXTENSIONS


def _determine_category(file_path: Path) -> str:
    """Determine the category for a file."""
    if _is_test_file(file_path):
        return "TEST"
    if _is_docs_file(file_path):
        return "DOCS"
    if _is_config_file(file_path):
        return "CONFIG"
    if _is_build_file(file_path):
        return "BUILD"
    if _is_code_file(file_path):
        return "CODE"
    return "OTHER"


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
        category = _determine_category(file_path)
        categories[category].append(file_path)

    return categories
