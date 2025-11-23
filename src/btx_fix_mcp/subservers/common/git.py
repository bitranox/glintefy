"""Git operations for sub-servers."""

import subprocess
from pathlib import Path

from btx_fix_mcp.config import get_timeout


class GitOperationError(Exception):
    """Raised when a git operation fails."""

    pass


class GitOperations:
    """Git operations for fix workflow.

    Provides methods for:
    - Checking git repository status
    - Creating commits
    - Reverting changes
    - Getting diffs
    - Managing files
    """

    @staticmethod
    def is_git_repo(path: Path | None = None) -> bool:
        """Check if directory is a git repository.

        Args:
            path: Directory to check (default: current directory)

        Returns:
            True if in a git repository, False otherwise

        Example:
            >>> GitOperations.is_git_repo()
            True
        """
        try:
            cmd = ["git"]
            if path:
                cmd.extend(["-C", str(path)])
            cmd.extend(["rev-parse", "--is-inside-work-tree"])

            timeout = get_timeout("git_quick_op", 5)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    @staticmethod
    def get_repo_root(path: Path | None = None) -> Path | None:
        """Get git repository root directory.

        Args:
            path: Starting directory (default: current directory)

        Returns:
            Path to repository root, or None if not in a git repo

        Example:
            >>> root = GitOperations.get_repo_root()
            >>> print(root)
            /home/user/project
        """
        try:
            cmd = ["git"]
            if path:
                cmd.extend(["-C", str(path)])
            cmd.extend(["rev-parse", "--show-toplevel"])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            )
            return Path(result.stdout.strip())
        except (subprocess.SubprocessError, FileNotFoundError):
            return None

    @staticmethod
    def get_current_branch(path: Path | None = None) -> str | None:
        """Get current git branch name.

        Args:
            path: Repository directory (default: current directory)

        Returns:
            Branch name, or None if not in a git repo

        Example:
            >>> GitOperations.get_current_branch()
            'main'
        """
        try:
            cmd = ["git"]
            if path:
                cmd.extend(["-C", str(path)])
            cmd.extend(["rev-parse", "--abbrev-ref", "HEAD"])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            )
            return result.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError):
            return None

    @staticmethod
    def create_commit(
        files: list[str],
        message: str,
        path: Path | None = None,
    ) -> str:
        """Create git commit with specified files.

        Args:
            files: List of file paths to commit
            message: Commit message
            path: Repository directory (default: current directory)

        Returns:
            Commit hash (SHA)

        Raises:
            GitOperationError: If commit fails

        Example:
            >>> sha = GitOperations.create_commit(
            ...     ["src/main.py"],
            ...     "fix: SQL injection vulnerability"
            ... )
            >>> print(sha)
            a1b2c3d4...
        """
        try:
            # Add files
            add_cmd = ["git", "add"] + files
            if path:
                add_cmd.insert(1, "-C")
                add_cmd.insert(2, str(path))

            subprocess.run(
                add_cmd,
                capture_output=True,
                timeout=10,
                check=True,
            )

            # Commit
            commit_cmd = ["git", "commit", "-m", message]
            if path:
                commit_cmd.insert(1, "-C")
                commit_cmd.insert(2, str(path))

            subprocess.run(
                commit_cmd,
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )

            # Get commit hash
            hash_cmd = ["git", "rev-parse", "HEAD"]
            if path:
                hash_cmd.insert(1, "-C")
                hash_cmd.insert(2, str(path))

            hash_result = subprocess.run(
                hash_cmd,
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            )

            return hash_result.stdout.strip()

        except subprocess.CalledProcessError as e:
            raise GitOperationError(f"Failed to create commit: {e.stderr}") from e
        except subprocess.TimeoutExpired as e:
            raise GitOperationError("Git commit timed out") from e

    @staticmethod
    def revert_changes(
        files: list[str],
        path: Path | None = None,
    ) -> None:
        """Revert changes to specified files.

        Args:
            files: List of file paths to revert
            path: Repository directory (default: current directory)

        Raises:
            GitOperationError: If revert fails

        Example:
            >>> GitOperations.revert_changes(["src/main.py"])
        """
        try:
            cmd = ["git", "checkout", "HEAD", "--"] + files
            if path:
                cmd.insert(1, "-C")
                cmd.insert(2, str(path))

            subprocess.run(
                cmd,
                capture_output=True,
                timeout=10,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise GitOperationError(f"Failed to revert changes: {e.stderr}") from e

    @staticmethod
    def get_diff(
        commit_range: str = "HEAD",
        path: Path | None = None,
    ) -> str:
        """Get git diff for specified range.

        Args:
            commit_range: Commit range (e.g., "HEAD", "HEAD~3..HEAD")
            path: Repository directory (default: current directory)

        Returns:
            Diff output as string

        Raises:
            GitOperationError: If diff fails

        Example:
            >>> diff = GitOperations.get_diff("HEAD~1..HEAD")
            >>> print(diff)
            diff --git a/src/main.py b/src/main.py
            ...
        """
        try:
            cmd = ["git", "diff", commit_range]
            if path:
                cmd.insert(1, "-C")
                cmd.insert(2, str(path))

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise GitOperationError(f"Failed to get diff: {e.stderr}") from e

    @staticmethod
    def get_status(path: Path | None = None) -> str:
        """Get git status output.

        Args:
            path: Repository directory (default: current directory)

        Returns:
            Git status output as string

        Raises:
            GitOperationError: If status fails

        Example:
            >>> status = GitOperations.get_status()
            >>> print(status)
            On branch main
            Changes not staged for commit:
            ...
        """
        try:
            cmd = ["git", "status"]
            if path:
                cmd.insert(1, "-C")
                cmd.insert(2, str(path))

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise GitOperationError(f"Failed to get status: {e.stderr}") from e

    @staticmethod
    def get_uncommitted_files(path: Path | None = None) -> list[str]:
        """Get list of uncommitted files (staged + unstaged + untracked).

        Args:
            path: Repository directory (default: current directory)

        Returns:
            List of file paths with uncommitted changes

        Example:
            >>> files = GitOperations.get_uncommitted_files()
            >>> print(files)
            ['src/main.py', 'tests/test_main.py', 'new_file.py']
        """
        try:
            # Get modified files (staged + unstaged)
            diff_cmd = ["git", "diff", "--name-only", "HEAD"]
            if path:
                diff_cmd.insert(1, "-C")
                diff_cmd.insert(2, str(path))

            diff_result = subprocess.run(
                diff_cmd,
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )

            # Get untracked files
            untracked_cmd = ["git", "ls-files", "--others", "--exclude-standard"]
            if path:
                untracked_cmd.insert(1, "-C")
                untracked_cmd.insert(2, str(path))

            untracked_result = subprocess.run(
                untracked_cmd,
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )

            # Combine and deduplicate
            modified = [f for f in diff_result.stdout.strip().split("\n") if f]
            untracked = [f for f in untracked_result.stdout.strip().split("\n") if f]

            return sorted(set(modified + untracked))

        except subprocess.CalledProcessError as e:
            raise GitOperationError(f"Failed to get uncommitted files: {e.stderr}") from e

    @staticmethod
    def get_file_history(
        file_path: str,
        limit: int = 10,
        path: Path | None = None,
    ) -> list[dict[str, str]]:
        """Get commit history for a file.

        Args:
            file_path: Path to file
            limit: Maximum number of commits to retrieve
            path: Repository directory (default: current directory)

        Returns:
            List of dicts with 'hash', 'author', 'date', 'message'

        Example:
            >>> history = GitOperations.get_file_history("src/main.py", limit=5)
            >>> for commit in history:
            ...     print(f"{commit['hash'][:7]} - {commit['message']}")
        """
        try:
            cmd = [
                "git",
                "log",
                f"-{limit}",
                "--format=%H|%an|%ad|%s",
                "--date=short",
                "--",
                file_path,
            ]
            if path:
                cmd.insert(1, "-C")
                cmd.insert(2, str(path))

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )

            commits = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("|")
                if len(parts) == 4:
                    commits.append(
                        {
                            "hash": parts[0],
                            "author": parts[1],
                            "date": parts[2],
                            "message": parts[3],
                        }
                    )

            return commits

        except subprocess.CalledProcessError as e:
            raise GitOperationError(f"Failed to get file history: {e.stderr}") from e

    @staticmethod
    def get_last_commit_hash(path: Path | None = None) -> str | None:
        """Get hash of the last commit.

        Args:
            path: Repository directory (default: current directory)

        Returns:
            Commit hash (SHA), or None if no commits

        Example:
            >>> sha = GitOperations.get_last_commit_hash()
            >>> print(sha)
            a1b2c3d4e5f6...
        """
        try:
            cmd = ["git", "rev-parse", "HEAD"]
            if path:
                cmd.insert(1, "-C")
                cmd.insert(2, str(path))

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None
