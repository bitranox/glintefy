"""Temporary source code modification for cache testing.

This module provides utilities to temporarily add @lru_cache decorators
to source files for testing, then revert changes.

Why source modification instead of monkey-patching:
- subprocess.run() creates fresh Python interpreter
- Fresh interpreter imports from DISK, not parent's memory
- Monkey-patches in parent are invisible to subprocess
- Source modifications persist across process boundary

Safety mechanism:
- Uses temporary git branch for all modifications
- Isolated from main branch (no conflicts with concurrent edits)
- Clean rollback via git branch deletion
- No risk of losing concurrent changes

IMPORTANT: Requires git repository and clean working tree.
"""

import ast
import re
import subprocess
import tempfile
from pathlib import Path


class SourcePatcher:
    """Temporarily modify source code to add cache decorators.

    Uses git branches for complete isolation from other operations.
    """

    def __init__(self, repo_path: Path):
        """Initialize source patcher.

        Args:
            repo_path: Repository root path
        """
        self.repo_path = repo_path
        self.branch_name = None
        self.original_branch = None
        self.backups: dict[Path, Path] = {}  # For file-level backup/restore

    def start(self) -> tuple[bool, str | None]:
        """Start modification session (create git branch).

        Returns:
            (success, error_message)
        """
        try:
            # Check if repo is a git repository
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                return (False, "Not a git repository")

            # Get current branch
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            self.original_branch = result.stdout.strip()

            # Check for uncommitted changes
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )

            if result.stdout.strip():
                return (False, "Working tree not clean (uncommitted changes)")

            # Create temporary branch
            branch_suffix = tempfile.mktemp(prefix='', suffix='', dir='').replace('/', '')[-8:]
            self.branch_name = f"cache-analysis-{branch_suffix}"

            result = subprocess.run(
                ["git", "checkout", "-b", self.branch_name],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                return (False, f"Failed to create branch: {result.stderr}")

            return (True, None)

        except subprocess.CalledProcessError as e:
            self._cleanup_branch()
            return (False, f"Git error: {e}")
        except Exception as e:
            self._cleanup_branch()
            return (False, f"Failed to start: {e}")

    def end(self) -> None:
        """End modification session (delete git branch and restore original)."""
        if self.branch_name and self.original_branch:
            self._cleanup_branch()

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

            # Commit change to branch
            subprocess.run(
                ["git", "add", str(file_path)],
                cwd=self.repo_path,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", f"Cache analysis: Add @lru_cache to {function_name}"],
                cwd=self.repo_path,
                capture_output=True,
            )

            return True

        except Exception:
            return False

    def _cleanup_branch(self) -> None:
        """Cleanup temporary git branch and restore original."""
        if not self.branch_name or not self.original_branch:
            return

        try:
            # Checkout original branch (discards all changes)
            subprocess.run(
                ["git", "checkout", "-f", self.original_branch],
                cwd=self.repo_path,
                capture_output=True,
            )

            # Delete temporary branch
            subprocess.run(
                ["git", "branch", "-D", self.branch_name],
                cwd=self.repo_path,
                capture_output=True,
            )

        except Exception:
            # Best effort cleanup
            pass
        finally:
            self.branch_name = None
            self.original_branch = None

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
            import shutil
            backup_path = file_path.with_suffix(file_path.suffix + ".cache_backup")
            shutil.copy2(file_path, backup_path)
            self.backups[file_path] = backup_path
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
            import shutil
            backup_path = self.backups[file_path]
            if backup_path.exists():
                shutil.copy2(backup_path, file_path)
                backup_path.unlink()
            del self.backups[file_path]
            return True
        except Exception:
            return False

    def restore_all_files(self) -> None:
        """Restore all backed-up files."""
        for file_path in list(self.backups.keys()):
            self.restore_file(file_path)
