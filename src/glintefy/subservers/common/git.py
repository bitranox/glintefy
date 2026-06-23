"""Git operations for sub-servers."""

import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from glintefy.config import (
    get_branch_template,
    get_commit_prefix,
    get_create_branch,
    get_sign_commits,
    get_timeout,
)


class GitOperationError(Exception):
    """Raised when a git operation fails."""


@dataclass(slots=True)
class CommitInfo:
    """Typed representation of a git commit."""

    hash: str
    author: str
    date: str
    message: str

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


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

            git_is_repo_timeout = get_timeout("git_quick_op", 10)
            result = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=git_is_repo_timeout,
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

            start_dir = str(path) if path else None
            git_root_timeout = get_timeout("git_quick_op", 10, start_dir)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=git_root_timeout,
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

            start_dir = str(path) if path else None
            git_branch_timeout = get_timeout("git_quick_op", 10, start_dir)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=git_branch_timeout,
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
        use_prefix: bool = True,
        sign: bool | None = None,
    ) -> str:
        """Create git commit with specified files.

        Args:
            files: List of file paths to commit
            message: Commit message
            path: Repository directory (default: current directory)
            use_prefix: If True, prepend commit_prefix from config (default: True)
            sign: Override for GPG signing (None = use config)

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
            start_dir = str(path) if path else None
            timeout_commit = get_timeout("git_commit", 60, start_dir)

            # Add files
            add_cmd = ["git", "add"] + files
            if path:
                add_cmd.insert(1, "-C")
                add_cmd.insert(2, str(path))

            timeout_add = get_timeout("git_quick_op", 20, start_dir)
            subprocess.run(
                add_cmd,
                capture_output=True,
                timeout=timeout_add,
                check=True,
            )

            # Build commit message with optional prefix
            if use_prefix:
                prefix = get_commit_prefix(start_dir)
                if prefix and not message.startswith(prefix):
                    message = f"{prefix} {message}"

            # Build commit command
            commit_cmd = ["git", "commit", "-m", message]

            # Handle GPG signing
            should_sign = sign if sign is not None else get_sign_commits(start_dir)
            if should_sign:
                commit_cmd.append("-S")

            if path:
                commit_cmd.insert(1, "-C")
                commit_cmd.insert(2, str(path))

            subprocess.run(
                commit_cmd,
                capture_output=True,
                text=True,
                timeout=timeout_commit,
                check=True,
            )

            # Get commit hash
            hash_cmd = ["git", "rev-parse", "HEAD"]
            if path:
                hash_cmd.insert(1, "-C")
                hash_cmd.insert(2, str(path))

            timeout_hash = get_timeout("git_quick_op", 10, start_dir)
            hash_result = subprocess.run(
                hash_cmd,
                capture_output=True,
                text=True,
                timeout=timeout_hash,
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

            start_dir = str(path) if path else None
            git_revert_timeout = get_timeout("git_quick_op", 20, start_dir)
            subprocess.run(
                cmd,
                capture_output=True,
                timeout=git_revert_timeout,
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

            start_dir = str(path) if path else None
            git_diff_timeout = get_timeout("git_diff", 60, start_dir)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=git_diff_timeout,
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

            start_dir = str(path) if path else None
            git_status_timeout = get_timeout("git_status", 20, start_dir)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=git_status_timeout,
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
            start_dir = str(path) if path else None
            git_files_timeout = get_timeout("git_quick_op", 20, start_dir)

            # Get modified files (staged + unstaged)
            diff_cmd = ["git", "diff", "--name-only", "HEAD"]
            if path:
                diff_cmd.insert(1, "-C")
                diff_cmd.insert(2, str(path))

            diff_result = subprocess.run(
                diff_cmd,
                capture_output=True,
                text=True,
                timeout=git_files_timeout,
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
                timeout=git_files_timeout,
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
    ) -> list[CommitInfo]:
        """Get commit history for a file.

        Args:
            file_path: Path to file
            limit: Maximum number of commits to retrieve
            path: Repository directory (default: current directory)

        Returns:
            List of CommitInfo dataclass instances

        Example:
            >>> history = GitOperations.get_file_history("src/main.py", limit=5)
            >>> for commit in history:
            ...     print(f"{commit.hash[:7]} - {commit.message}")
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

            start_dir = str(path) if path else None
            git_log_timeout = get_timeout("git_log", 20, start_dir)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=git_log_timeout,
                check=True,
            )

            commits: list[CommitInfo] = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("|")
                if len(parts) == 4:
                    commits.append(
                        CommitInfo(
                            hash=parts[0],
                            author=parts[1],
                            date=parts[2],
                            message=parts[3],
                        )
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

            start_dir = str(path) if path else None
            git_hash_timeout = get_timeout("git_quick_op", 10, start_dir)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=git_hash_timeout,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    @staticmethod
    def create_fix_branch(
        issue_id: str,
        path: Path | None = None,
        checkout: bool = True,
    ) -> str:
        """Create a new branch for fixing an issue using config template.

        Args:
            issue_id: Issue identifier to use in branch name
            path: Repository directory (default: current directory)
            checkout: If True, checkout the new branch (default: True)

        Returns:
            Name of the created branch

        Raises:
            GitOperationError: If branch creation fails

        Example:
            >>> branch = GitOperations.create_fix_branch("ISSUE-123")
            >>> print(branch)
            fix/ISSUE-123
        """
        start_dir = str(path) if path else None

        # Check if branch creation is enabled
        if not get_create_branch(start_dir):
            raise GitOperationError("Branch creation is disabled in config (git.create_branch = false)")

        # Get branch name from template
        template = get_branch_template(start_dir)
        branch_name = template.format(issue_id=issue_id)

        try:
            git_branch_op_timeout = get_timeout("git_quick_op", 10, start_dir)

            # Create branch
            create_cmd = ["git", "branch", branch_name]
            if path:
                create_cmd.insert(1, "-C")
                create_cmd.insert(2, str(path))

            subprocess.run(
                create_cmd,
                capture_output=True,
                text=True,
                timeout=git_branch_op_timeout,
                check=True,
            )

            # Optionally checkout
            if checkout:
                checkout_cmd = ["git", "checkout", branch_name]
                if path:
                    checkout_cmd.insert(1, "-C")
                    checkout_cmd.insert(2, str(path))

                subprocess.run(
                    checkout_cmd,
                    capture_output=True,
                    text=True,
                    timeout=git_branch_op_timeout,
                    check=True,
                )

            return branch_name

        except subprocess.CalledProcessError as e:
            raise GitOperationError(f"Failed to create branch: {e.stderr}") from e
        except subprocess.TimeoutExpired as e:
            raise GitOperationError("Git branch operation timed out") from e

    @staticmethod
    def should_create_branch(path: Path | None = None) -> bool:
        """Check if branch creation is enabled in config.

        Args:
            path: Repository directory to determine config context

        Returns:
            True if create_branch is enabled in config
        """
        start_dir = str(path) if path else None
        return get_create_branch(start_dir)

    @staticmethod
    def should_auto_commit(path: Path | None = None) -> bool:
        """Check if auto-commit is enabled in config.

        Args:
            path: Repository directory to determine config context

        Returns:
            True if auto_commit is enabled in config
        """
        from glintefy.config import get_auto_commit

        start_dir = str(path) if path else None
        return get_auto_commit(start_dir)
