"""Temporary source code modification for cache testing.

This module provides utilities to temporarily add @lru_cache decorators
to source files for testing, then revert changes.

Why source modification instead of monkey-patching:
- subprocess.run() creates fresh Python interpreter
- Fresh interpreter imports from DISK, not parent's memory
- Monkey-patches in parent are invisible to subprocess
- Source modifications persist across process boundary

Safety mechanism:
- Creates backup copy of each modified file
- Restores original files on cleanup (even on crash)
- Uses context manager for automatic cleanup
- No git dependency required
"""

import ast
import atexit
import re
from pathlib import Path


class SourcePatcher:
    """Temporarily modify source code to add cache decorators.

    Uses file backup/restore for safe modification without git dependency.
    """

    # Class-level tracking for emergency cleanup
    _active_patchers: list["SourcePatcher"] = []

    def __init__(self, repo_path: Path):
        """Initialize source patcher.

        Args:
            repo_path: Repository root path
        """
        self.repo_path = repo_path
        self.backups: dict[Path, str] = {}  # file_path -> original_content
        self._session_active = False

    def start(self) -> tuple[bool, str | None]:
        """Start modification session.

        Returns:
            (success, error_message)
        """
        if self._session_active:
            return (False, "Session already active")

        if not self.repo_path.exists():
            return (False, f"Repository path does not exist: {self.repo_path}")

        if not self.repo_path.is_dir():
            return (False, f"Repository path is not a directory: {self.repo_path}")

        self._session_active = True
        self.backups = {}

        # Register for emergency cleanup
        SourcePatcher._active_patchers.append(self)

        return (True, None)

    def end(self) -> None:
        """End modification session (restore all modified files)."""
        if self._session_active:
            self._restore_all_files()
            self._session_active = False

            # Unregister from emergency cleanup
            if self in SourcePatcher._active_patchers:
                SourcePatcher._active_patchers.remove(self)

    def apply_cache_decorator(
        self,
        file_path: Path,
        function_name: str,
        cache_size: int,
    ) -> bool:
        """Add @lru_cache decorator to function in source file.

        Args:
            file_path: Path to Python source file
            function_name: Name of function to decorate
            cache_size: LRU cache maxsize

        Returns:
            True if successfully applied, False otherwise
        """
        if not file_path.exists():
            return False

        try:
            source = file_path.read_text()

            # Backup original content if not already backed up
            if file_path not in self.backups:
                self.backups[file_path] = source

            # Parse AST to verify function exists
            tree = ast.parse(source)
            func_exists = False
            func_line = None

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == function_name:
                    func_exists = True
                    func_line = node.lineno
                    break

            if not func_exists:
                return False

            # Add lru_cache import if needed
            modified_source = self._ensure_lru_cache_import(source)

            # Add decorator before function definition
            modified_source = self._add_decorator(
                modified_source,
                function_name,
                cache_size,
                func_line,
            )

            # Write modified source
            file_path.write_text(modified_source)

            return True

        except Exception:
            return False

    def _restore_all_files(self) -> None:
        """Restore all modified files to their original content."""
        for file_path, original_content in self.backups.items():
            try:
                file_path.write_text(original_content)
            except Exception:
                # Best effort restoration
                pass

        self.backups.clear()

    def _ensure_lru_cache_import(self, source: str) -> str:
        """Ensure 'from functools import lru_cache' is in source.

        Args:
            source: Python source code

        Returns:
            Modified source with import added if needed
        """
        # Check if already imported
        if "from functools import lru_cache" in source:
            return source

        # Check for partial import (from functools import ...)
        if re.search(r"from\s+functools\s+import\s+", source):
            # Add to existing import
            source = re.sub(
                r"(from\s+functools\s+import\s+)([^\n]+)",
                r"\1lru_cache, \2",
                source,
                count=1,
            )
            return source

        # Add new import at top (after docstring if present)
        lines = source.split("\n")

        # Find insertion point (after module docstring)
        insert_idx = 0
        in_docstring = False

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Detect docstring start
            if i == 0 and (stripped.startswith('"""') or stripped.startswith("'''")):
                in_docstring = True
                quote = '"""' if stripped.startswith('"""') else "'''"

                # Single-line docstring
                if stripped.endswith(quote) and len(stripped) > 3:
                    in_docstring = False
                    insert_idx = i + 1
                continue

            # Detect docstring end
            if in_docstring and (stripped.endswith('"""') or stripped.endswith("'''")):
                in_docstring = False
                insert_idx = i + 1
                continue

            # Skip blank lines and comments at top
            if not in_docstring and stripped and not stripped.startswith("#"):
                insert_idx = i
                break

        # Insert import
        lines.insert(insert_idx, "from functools import lru_cache")

        return "\n".join(lines)

    def _add_decorator(
        self,
        source: str,
        function_name: str,
        cache_size: int,
        func_line: int | None = None,
    ) -> str:
        """Add @lru_cache decorator before function definition.

        Args:
            source: Python source code
            function_name: Name of function to decorate
            cache_size: LRU cache maxsize
            func_line: Line number of function (1-indexed)

        Returns:
            Modified source with decorator added
        """
        lines = source.split("\n")

        # Find function definition
        for i, line in enumerate(lines):
            # Match function definition
            if re.match(rf"^\s*def\s+{re.escape(function_name)}\s*\(", line):
                # Get indentation of function
                indent_match = re.match(r"^(\s*)", line)
                indent = indent_match.group(1) if indent_match else ""

                # Insert decorator on line before
                decorator = f"{indent}@lru_cache(maxsize={cache_size})"
                lines.insert(i, decorator)

                return "\n".join(lines)

        # Function not found (shouldn't happen if AST validation passed)
        return source

    def backup_file(self, file_path: Path) -> bool:
        """Create backup of file for later restoration.

        Args:
            file_path: File to backup

        Returns:
            True if backup created successfully
        """
        if file_path in self.backups:
            return True  # Already backed up

        try:
            self.backups[file_path] = file_path.read_text()
            return True
        except Exception:
            return False

    def restore_file(self, file_path: Path) -> bool:
        """Restore file from backup.

        Args:
            file_path: File to restore

        Returns:
            True if restored successfully
        """
        if file_path not in self.backups:
            return False

        try:
            file_path.write_text(self.backups[file_path])
            del self.backups[file_path]
            return True
        except Exception:
            return False

    def __enter__(self) -> "SourcePatcher":
        """Context manager entry."""
        success, error = self.start()
        if not success:
            raise RuntimeError(f"Failed to start SourcePatcher: {error}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - always restore files."""
        self.end()


# Emergency cleanup on interpreter exit
def _emergency_cleanup():
    """Restore all modified files if interpreter exits unexpectedly."""
    for patcher in SourcePatcher._active_patchers[:]:
        try:
            patcher._restore_all_files()
        except Exception:
            pass


atexit.register(_emergency_cleanup)
