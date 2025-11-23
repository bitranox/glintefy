"""Scope sub-server: Determine review scope.

This sub-server analyzes the repository to determine which files need review.
It can work in two modes:
1. Git mode: Review uncommitted changes
2. Full mode: Review all files in the repository
"""

from pathlib import Path

from btx_fix_mcp.config import get_display_limit, get_subserver_config
from btx_fix_mcp.subservers.base import BaseSubServer, SubServerResult
from btx_fix_mcp.subservers.common.files import categorize_files, find_files
from btx_fix_mcp.subservers.common.git import GitOperationError, GitOperations
from btx_fix_mcp.subservers.common.issues import ScopeMetrics
from btx_fix_mcp.subservers.common.logging import (
    LogContext,
    get_mcp_logger,
    log_dict,
    log_error_detailed,
    log_result,
    log_section,
    log_step,
    setup_logger,
)


class ScopeSubServer(BaseSubServer):
    """Determine scope of files to review.

    Identifies which files should be included in the code review based on:
    - Git status (uncommitted changes)
    - File types (code, tests, docs, config)
    - Exclusion patterns

    Args:
        name: Sub-server name (default: "scope")
        input_dir: Input directory for configuration
        output_dir: Output directory for results
        repo_path: Repository path (default: current directory)
        mode: "git" for uncommitted changes, "full" for all files

    Example:
        >>> from pathlib import Path
        >>> server = ScopeSubServer(
        ...     output_dir=Path("LLM-CONTEXT/btx_fix_mcp/review/scope"),
        ...     mode="git"
        ... )
        >>> result = server.run()
        >>> print(f"Files to review: {result.metrics['total_files']}")
    """

    def __init__(
        self,
        name: str = "scope",
        input_dir: Path | None = None,
        output_dir: Path | None = None,
        repo_path: Path | None = None,
        mode: str = "git",
        mcp_mode: bool = False,
        exclude_patterns: list[str] | None = None,
        include_patterns: list[str] | None = None,
    ):
        """Initialize scope sub-server.

        Args:
            name: Sub-server name
            input_dir: Input directory
            output_dir: Output directory
            repo_path: Repository path
            mode: "git" or "full"
            mcp_mode: If True, log to stderr only (MCP protocol compatible).
                      If False, log to stdout and optional log file (standalone mode).
            exclude_patterns: Patterns to exclude (overrides config)
            include_patterns: Patterns to include (overrides config, default: all files)
        """
        super().__init__(name=name, input_dir=input_dir, output_dir=output_dir)
        self.repo_path = repo_path or Path.cwd()
        self.mode = mode
        self.mcp_mode = mcp_mode

        # Load config
        config = get_subserver_config("scope")
        self.exclude_patterns = exclude_patterns or config.get("exclude_patterns", [])
        self.include_patterns = include_patterns or config.get("include_patterns", ["**/*"])

        # Setup logging based on mode
        if mcp_mode:
            # MCP mode: stderr only (MCP protocol uses stdout)
            self.logger = get_mcp_logger(f"btx_fix_mcp.{name}")
        else:
            # Standalone mode: stdout only (no file logging)
            self.logger = setup_logger(name, log_file=None, level=20)  # INFO

    def validate_inputs(self) -> tuple[bool, list[str]]:
        """Validate inputs for scope analysis.

        Returns:
            Tuple of (valid, missing_items)
        """
        missing = []

        # Check repository exists
        if not self.repo_path.exists():
            missing.append(f"Repository path does not exist: {self.repo_path}")

        # In git mode, check if it's a git repository
        if self.mode == "git":
            if not GitOperations.is_git_repo(self.repo_path):
                missing.append(f"Not a git repository: {self.repo_path}")

        # Validate mode
        if self.mode not in ("git", "full"):
            missing.append(f"Invalid mode '{self.mode}'. Must be 'git' or 'full'")

        return len(missing) == 0, missing

    def execute(self) -> SubServerResult:
        """Execute scope analysis.

        Returns:
            SubServerResult with file list and categorization
        """
        log_section(self.logger, "SCOPE ANALYSIS")

        try:
            # Step 1: Determine files to review
            log_step(self.logger, 1, f"Finding files to review (mode: {self.mode})")

            with LogContext(self.logger, "File discovery"):
                if self.mode == "git":
                    files = self._find_git_files()
                else:
                    files = self._find_all_files()

            log_result(self.logger, True, f"Found {len(files)} files")

            # Step 2: Categorize files
            log_step(self.logger, 2, "Categorizing files by type")

            with LogContext(self.logger, "File categorization"):
                categorized = categorize_files(files)

            # Log categorization
            category_counts = {cat: len(files) for cat, files in categorized.items()}
            log_dict(self.logger, category_counts, title="File Categories")

            # Step 3: Save results
            log_step(self.logger, 3, "Saving results")

            artifacts = self._save_results(files, categorized)

            # Step 4: Generate summary
            summary = self._generate_summary(files, categorized)

            log_result(self.logger, True, "Scope analysis completed successfully")

            metrics = ScopeMetrics(
                total_files=len(files),
                code_files=len(categorized.get("CODE", [])),
                test_files=len(categorized.get("TEST", [])),
                doc_files=len(categorized.get("DOCS", [])),
                config_files=len(categorized.get("CONFIG", [])),
                mode=self.mode,
            )

            return SubServerResult(
                status="SUCCESS",
                summary=summary,
                artifacts=artifacts,
                metrics=metrics.model_dump(),
            )

        except Exception as e:
            log_error_detailed(
                self.logger,
                e,
                context={"mode": self.mode, "repo_path": str(self.repo_path)},
                include_traceback=True,
            )
            return SubServerResult(
                status="FAILED",
                summary=f"# Scope Analysis Failed\n\n**Error**: {e}",
                artifacts={},
                errors=[str(e)],
            )

    def _find_git_files(self) -> list[Path]:
        """Find files from git uncommitted changes.

        Returns:
            List of file paths with uncommitted changes
        """
        try:
            uncommitted = GitOperations.get_uncommitted_files(self.repo_path)
            # Convert to Path objects
            paths = [self.repo_path / f for f in uncommitted]
            # Filter to existing files only (ignore deleted files)
            return [p for p in paths if p.exists() and p.is_file()]
        except GitOperationError as e:
            self.logger.warning(f"Git operation failed: {e}")
            # Fall back to full mode
            self.logger.info("Falling back to full mode")
            return self._find_all_files()

    def _find_all_files(self) -> list[Path]:
        """Find all files in repository.

        Returns:
            List of all file paths
        """
        all_files: list[Path] = []

        # Find files matching each include pattern
        for include_pattern in self.include_patterns:
            files = find_files(
                self.repo_path,
                pattern=include_pattern,
                exclude_patterns=self.exclude_patterns,
            )
            all_files.extend(files)

        # Remove duplicates and sort
        return sorted(set(all_files))

    def _save_results(self, files: list[Path], categorized: dict[str, list[Path]]) -> dict[str, Path]:
        """Save results to files.

        Args:
            files: List of all files
            categorized: Categorized files

        Returns:
            Dictionary of artifact paths
        """
        artifacts = {}

        # Save all files list
        all_files_path = self.output_dir / "files_to_review.txt"
        relative_files = [str(f.relative_to(self.repo_path)) for f in files]
        all_files_path.write_text("\n".join(sorted(relative_files)))
        artifacts["files_to_review"] = all_files_path

        # Save categorized files
        for category, cat_files in categorized.items():
            if cat_files:
                cat_path = self.output_dir / f"files_{category.lower()}.txt"
                relative_cat = [str(f.relative_to(self.repo_path)) for f in cat_files]
                cat_path.write_text("\n".join(sorted(relative_cat)))
                artifacts[f"files_{category.lower()}"] = cat_path

        return artifacts

    def _generate_summary(self, files: list[Path], categorized: dict[str, list[Path]]) -> str:
        """Generate markdown summary.

        Args:
            files: List of all files
            categorized: Categorized files

        Returns:
            Markdown summary string
        """
        # Get git info if available
        branch = "N/A"
        if GitOperations.is_git_repo(self.repo_path):
            try:
                branch = GitOperations.get_current_branch(self.repo_path) or "N/A"
            except GitOperationError:
                pass

        summary_lines = [
            "# Scope Analysis Report",
            "",
            "## Overview",
            "",
            f"**Mode**: {self.mode}",
            f"**Repository**: {self.repo_path}",
            f"**Branch**: {branch}",
            f"**Total Files**: {len(files)}",
            "",
            "## File Breakdown by Category",
            "",
        ]

        # Add category counts
        for category in ["CODE", "TEST", "DOCS", "CONFIG", "BUILD", "OTHER"]:
            count = len(categorized.get(category, []))
            if count > 0:
                summary_lines.append(f"- **{category}**: {count} files")

        # Add sample files
        if files:
            limit = get_display_limit("max_sample_files", 10, start_dir=str(self.repo_path))
            display_count = len(files) if limit is None else min(limit, len(files))

            header = "## Sample Files" if limit is None else f"## Sample Files (showing {display_count} of {len(files)})"
            summary_lines.extend(["", header, ""])

            for f in files[:limit]:
                rel_path = f.relative_to(self.repo_path)
                summary_lines.append(f"- `{rel_path}`")

            if limit is not None and len(files) > limit:
                summary_lines.append("")
                summary_lines.append(
                    f"*Note: {len(files) - limit} more files not shown. Set `output.display.max_sample_files = 0` in config for unlimited display.*"
                )

        summary_lines.extend(
            [
                "",
                "## Next Steps",
                "",
                "1. Review code files for quality issues",
                "2. Check test coverage",
                "3. Scan for security vulnerabilities",
                "4. Review documentation completeness",
            ]
        )

        return "\n".join(summary_lines)
