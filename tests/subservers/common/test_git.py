"""Tests for git utilities."""

import pytest
import subprocess
from glintefy.subservers.common.git import GitOperations, GitOperationError


class TestGitOperations:
    """Tests for GitOperations class."""

    @pytest.fixture
    def git_repo(self, tmp_path):
        """Create a temporary git repository for testing."""
        repo_dir = tmp_path / "test_repo"
        repo_dir.mkdir()

        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=repo_dir,
            capture_output=True,
            check=True,
        )

        # Configure git
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_dir,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_dir,
            capture_output=True,
            check=True,
        )

        # Create initial commit
        test_file = repo_dir / "README.md"
        test_file.write_text("# Test Repository")
        subprocess.run(
            ["git", "add", "README.md"],
            cwd=repo_dir,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_dir,
            capture_output=True,
            check=True,
        )

        return repo_dir

    def test_is_git_repo_true(self, git_repo):
        """Test is_git_repo returns True for git repository."""
        assert GitOperations.is_git_repo(git_repo) is True

    def test_is_git_repo_false(self, tmp_path):
        """Test is_git_repo returns False for non-git directory."""
        non_git_dir = tmp_path / "not_a_repo"
        non_git_dir.mkdir()
        assert GitOperations.is_git_repo(non_git_dir) is False

    def test_get_repo_root(self, git_repo):
        """Test getting repository root."""
        # Create subdirectory
        subdir = git_repo / "src" / "subdir"
        subdir.mkdir(parents=True)

        root = GitOperations.get_repo_root(subdir)
        assert root == git_repo

    def test_get_repo_root_none_for_non_git(self, tmp_path):
        """Test get_repo_root returns None for non-git directory."""
        root = GitOperations.get_repo_root(tmp_path)
        assert root is None

    def test_get_current_branch(self, git_repo):
        """Test getting current branch name."""
        branch = GitOperations.get_current_branch(git_repo)
        assert branch in ("main", "master")  # Different git versions use different defaults

    def test_create_commit(self, git_repo):
        """Test creating a git commit."""
        # Create a new file
        new_file = git_repo / "test.py"
        new_file.write_text("print('hello')")

        # Commit the file
        sha = GitOperations.create_commit(
            ["test.py"],
            "Add test.py",
            path=git_repo,
        )

        # Verify commit was created
        assert len(sha) == 40  # Git SHA is 40 characters
        assert all(c in "0123456789abcdef" for c in sha)

    def test_create_commit_multiple_files(self, git_repo):
        """Test committing multiple files."""
        # Create files
        file1 = git_repo / "file1.txt"
        file2 = git_repo / "file2.txt"
        file1.write_text("content1")
        file2.write_text("content2")

        # Commit files
        sha = GitOperations.create_commit(
            ["file1.txt", "file2.txt"],
            "Add two files",
            path=git_repo,
        )

        assert len(sha) == 40

    def test_revert_changes(self, git_repo):
        """Test reverting changes to a file."""
        # Modify existing file
        readme = git_repo / "README.md"
        original_content = readme.read_text()
        readme.write_text("Modified content")

        # Verify modification
        assert readme.read_text() == "Modified content"

        # Revert changes
        GitOperations.revert_changes(["README.md"], path=git_repo)

        # Verify reversion
        assert readme.read_text() == original_content

    def test_get_diff(self, git_repo):
        """Test getting git diff."""
        # Create and commit a file
        test_file = git_repo / "test.txt"
        test_file.write_text("line 1")
        GitOperations.create_commit(["test.txt"], "Add test.txt", path=git_repo)

        # Modify file
        test_file.write_text("line 1\nline 2")

        # Get diff
        diff = GitOperations.get_diff(path=git_repo)

        assert "test.txt" in diff
        assert "+line 2" in diff or "line 2" in diff

    def test_get_status(self, git_repo):
        """Test getting git status."""
        # Create untracked file
        untracked = git_repo / "untracked.txt"
        untracked.write_text("untracked")

        status = GitOperations.get_status(path=git_repo)

        assert "untracked.txt" in status

    def test_get_uncommitted_files(self, git_repo):
        """Test getting list of uncommitted files."""
        # Modify existing file
        readme = git_repo / "README.md"
        readme.write_text("Modified")

        # Create new file
        new_file = git_repo / "new.txt"
        new_file.write_text("new")

        files = GitOperations.get_uncommitted_files(path=git_repo)

        assert "README.md" in files
        assert "new.txt" in files

    def test_get_file_history(self, git_repo):
        """Test getting file commit history."""
        # Create multiple commits for same file (use_prefix=False for clean messages)
        test_file = git_repo / "history.txt"
        test_file.write_text("version 1")
        GitOperations.create_commit(["history.txt"], "Version 1", path=git_repo, use_prefix=False)

        test_file.write_text("version 2")
        GitOperations.create_commit(["history.txt"], "Version 2", path=git_repo, use_prefix=False)

        history = GitOperations.get_file_history("history.txt", limit=5, path=git_repo)

        assert len(history) == 2
        assert history[0].message == "Version 2"  # Most recent first
        assert history[1].message == "Version 1"
        assert history[0].hash  # CommitInfo has typed attributes
        assert history[0].author
        assert history[0].date

    def test_get_last_commit_hash(self, git_repo):
        """Test getting last commit hash."""
        sha = GitOperations.get_last_commit_hash(path=git_repo)

        assert sha is not None
        assert len(sha) == 40
        assert all(c in "0123456789abcdef" for c in sha)

    def test_get_last_commit_hash_none_for_non_git(self, tmp_path):
        """Test get_last_commit_hash returns None for non-git directory."""
        sha = GitOperations.get_last_commit_hash(path=tmp_path)
        assert sha is None

    def test_commit_with_multiline_message(self, git_repo):
        """Test creating commit with multiline message."""
        # Create file
        test_file = git_repo / "multi.txt"
        test_file.write_text("content")

        # Commit with multiline message
        message = """Fix critical bug

This commit fixes the SQL injection vulnerability
by using parameterized queries.

Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>"""

        sha = GitOperations.create_commit(["multi.txt"], message, path=git_repo)
        assert len(sha) == 40

    def test_error_on_invalid_file(self, git_repo):
        """Test that committing non-existent file raises error."""
        with pytest.raises(GitOperationError):
            GitOperations.create_commit(
                ["nonexistent.txt"],
                "This should fail",
                path=git_repo,
            )


class TestGitOperationsWithoutRepo:
    """Test git operations without actual git repo (mocked)."""

    def test_is_git_repo_handles_missing_git(self, tmp_path, monkeypatch):
        """Test is_git_repo handles missing git executable."""

        def mock_run(*args, **kwargs):
            raise FileNotFoundError("git not found")

        monkeypatch.setattr(subprocess, "run", mock_run)

        assert GitOperations.is_git_repo(tmp_path) is False

    def test_is_git_repo_handles_timeout(self, tmp_path, monkeypatch):
        """Test is_git_repo handles subprocess timeout."""

        def mock_run(*args, **kwargs):
            raise subprocess.TimeoutExpired("git", 5)

        monkeypatch.setattr(subprocess, "run", mock_run)

        assert GitOperations.is_git_repo(tmp_path) is False
