"""Metrics analysis module.

Analyzes code metrics using:
- Halstead metrics (radon hal)
- Raw metrics (radon raw - LOC, SLOC, comments)
- Code churn analysis (git history)
"""

import json
import subprocess
from pathlib import Path
from typing import Any

from glintefy.config import get_timeout
from glintefy.tools_venv import get_tool_path

from .analyzer_results import (
    CodeChurnResults,
    FileChurnInfo,
    HalsteadItem,
    MetricsResults,
    RawMetricsItem,
)
from .base import BaseAnalyzer


class MetricsAnalyzer(BaseAnalyzer[MetricsResults]):
    """Halstead, raw metrics, and code churn analyzer."""

    def analyze(self, files: list[str]) -> MetricsResults:
        """Analyze metrics for all files.

        Returns:
            MetricsResults dataclass with halstead, raw_metrics, code_churn
        """
        return MetricsResults(
            halstead=self._analyze_halstead(files),
            raw_metrics=self._analyze_raw_metrics(files),
            code_churn=self._analyze_code_churn(files),
        )

    def _analyze_halstead(self, files: list[str]) -> list[HalsteadItem]:
        """Analyze Halstead metrics using radon."""
        results: list[HalsteadItem] = []
        radon = str(get_tool_path("radon"))

        for file_path in files:
            if not Path(file_path).exists():
                continue

            try:
                self._analyze_file_halstead(file_path, radon, results)
            except FileNotFoundError:
                # radon not found - stop processing remaining files
                break

        return results

    def _analyze_file_halstead(self, file_path: str, radon: str, results: list[HalsteadItem]) -> None:
        """Analyze Halstead metrics for a single file."""
        try:
            radon_hal_timeout = get_timeout("tool_quick", 60)
            result = subprocess.run(
                [radon, "hal", "-j", file_path],
                check=False,
                capture_output=True,
                text=True,
                timeout=radon_hal_timeout,
            )

            if result.returncode != 0 or not result.stdout.strip():
                return

            self._parse_halstead_output(result.stdout, results)

        except subprocess.TimeoutExpired:
            self.logger.warning(f"Timeout analyzing Halstead in {file_path}")
        except json.JSONDecodeError:
            self.logger.warning(f"Invalid JSON from radon for {file_path}")
        except FileNotFoundError:
            self.logger.warning("radon not found")
            raise  # Re-raise to stop processing
        except Exception as e:
            self.logger.warning(f"Error analyzing Halstead in {file_path}: {e}")

    def _parse_halstead_output(self, stdout: str, results: list[HalsteadItem]) -> None:
        """Parse radon Halstead metrics JSON output."""
        data = json.loads(stdout)

        for filepath, hal_data in data.items():
            if not hal_data.get("total"):
                continue

            total = hal_data["total"][0] if isinstance(hal_data["total"], list) else hal_data["total"]
            results.append(
                HalsteadItem(
                    file=self._get_relative_path(filepath),
                    h1=total.get("h1", 0),
                    h2=total.get("h2", 0),
                    N1=total.get("N1", 0),
                    N2=total.get("N2", 0),
                    vocabulary=total.get("vocabulary", 0),
                    length=total.get("length", 0),
                    volume=total.get("volume", 0),
                    difficulty=total.get("difficulty", 0),
                    effort=total.get("effort", 0),
                    time=total.get("time", 0),
                    bugs=total.get("bugs", 0),
                )
            )

    def _analyze_raw_metrics(self, files: list[str]) -> list[RawMetricsItem]:
        """Analyze raw metrics (LOC, SLOC, comments) using radon."""
        results: list[RawMetricsItem] = []
        radon = str(get_tool_path("radon"))

        for file_path in files:
            if not Path(file_path).exists():
                continue

            try:
                self._analyze_file_raw_metrics(file_path, radon, results)
            except FileNotFoundError:
                # radon not found - stop processing remaining files
                break

        return results

    def _analyze_file_raw_metrics(self, file_path: str, radon: str, results: list[RawMetricsItem]) -> None:
        """Analyze raw metrics for a single file."""
        try:
            radon_raw_timeout = get_timeout("tool_quick", 60)
            result = subprocess.run(
                [radon, "raw", "-j", file_path],
                check=False,
                capture_output=True,
                text=True,
                timeout=radon_raw_timeout,
            )

            if result.returncode != 0 or not result.stdout.strip():
                return

            self._parse_raw_metrics_output(result.stdout, results)

        except subprocess.TimeoutExpired:
            self.logger.warning(f"Timeout analyzing raw metrics in {file_path}")
        except json.JSONDecodeError:
            self.logger.warning(f"Invalid JSON from radon for {file_path}")
        except FileNotFoundError:
            self.logger.warning("radon not found")
            raise  # Re-raise to stop processing
        except Exception as e:
            self.logger.warning(f"Error analyzing raw metrics in {file_path}: {e}")

    def _parse_raw_metrics_output(self, stdout: str, results: list[RawMetricsItem]) -> None:
        """Parse radon raw metrics JSON output."""
        data = json.loads(stdout)

        for filepath, raw_data in data.items():
            results.append(
                RawMetricsItem(
                    file=self._get_relative_path(filepath),
                    loc=raw_data.get("loc", 0),
                    lloc=raw_data.get("lloc", 0),
                    sloc=raw_data.get("sloc", 0),
                    comments=raw_data.get("comments", 0),
                    multi=raw_data.get("multi", 0),
                    blank=raw_data.get("blank", 0),
                    single_comments=raw_data.get("single_comments", 0),
                )
            )

    def _analyze_code_churn(self, files: list[str]) -> CodeChurnResults:
        """Analyze code churn using git history.

        Identifies frequently modified files which may indicate:
        - Unstable code needing refactoring
        - Hot spots with potential bugs
        - Technical debt areas
        """
        churn_threshold = self.config.get("churn_threshold", 20)

        if not files:
            return CodeChurnResults(skip_reason="No files provided for churn analysis")

        is_git_repo, skip_reason = self._is_git_repository()
        if not is_git_repo:
            return CodeChurnResults(skip_reason=skip_reason)

        results = CodeChurnResults()

        try:
            relative_files = self._convert_to_relative_paths(files)
            git_output = self._run_git_log(relative_files)

            if git_output is None:
                results.skip_reason = "Git log returned no output"
                return results

            file_stats, commits_seen = self._parse_git_log(git_output)
            results.total_commits_analyzed = len(commits_seen)

            self._compile_churn_results(file_stats, churn_threshold, results)

        except FileNotFoundError:
            self.logger.warning("git not found for churn analysis")
            results.skip_reason = "Git executable not found"
        except subprocess.TimeoutExpired:
            self.logger.warning("git log timed out")
            results.skip_reason = "Git log command timed out"
        except Exception as e:
            self.logger.warning(f"churn analysis error: {e}")
            results.skip_reason = f"Error during churn analysis: {e}"

        return results

    def _is_git_repository(self) -> tuple[bool, str | None]:
        """Check if current directory is a git repository.

        Returns:
            Tuple of (is_git_repo, skip_reason). skip_reason is None if is_git_repo is True.
        """
        try:
            git_check_timeout = get_timeout("git_log", 20)
            git_check = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                check=False,
                capture_output=True,
                text=True,
                timeout=git_check_timeout,
                cwd=str(self.repo_path),
            )
            if git_check.returncode != 0:
                reason = f"Not a git repository ({self.repo_path}). Code churn analysis requires git to track file modification history."
                self.logger.info(reason)
                return False, reason
            return True, None
        except FileNotFoundError:
            reason = "Git executable not found. Install git to enable code churn analysis."
            self.logger.info(reason)
            return False, reason
        except subprocess.TimeoutExpired:
            reason = "Git check timed out. Code churn analysis skipped."
            self.logger.info(reason)
            return False, reason

    def _convert_to_relative_paths(self, files: list[str]) -> list[str]:
        """Convert absolute paths to relative paths for git."""
        relative_files = []
        for f in files:
            try:
                relative_files.append(str(Path(f).relative_to(self.repo_path)))
            except ValueError:
                # File not under repo_path, use as-is
                relative_files.append(f)
        return relative_files

    def _run_git_log(self, relative_files: list[str]) -> str | None:
        """Run git log command to get file change history."""
        git_log_timeout = get_timeout("tool_analysis", 120)
        churn_period_days = self.config.get("churn_period_days", 90)

        result = subprocess.run(
            [
                "git",
                "log",
                "--numstat",
                "--format=%H|%ae|%at",
                f"--since={churn_period_days} days ago",
                "--",
                *relative_files,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=git_log_timeout,
            cwd=str(self.repo_path),
        )

        if result.returncode != 0:
            return None
        return result.stdout

    def _parse_git_log(self, git_output: str) -> tuple[dict[str, dict[str, Any]], set[str]]:
        """Parse git log output to extract file statistics."""
        file_stats: dict[str, dict[str, Any]] = {}
        current_author = None
        commits_seen: set[str] = set()

        for line in git_output.strip().split("\n"):
            if not line:
                continue

            # Commit line format: hash|author_email|timestamp
            if "|" in line and line.count("|") == 2:
                parts = line.split("|")
                commits_seen.add(parts[0])
                current_author = parts[1]
            # Numstat line format: added\tdeleted\tfilename
            elif "\t" in line:
                self._process_numstat_line(line, current_author, file_stats)

        return file_stats, commits_seen

    def _process_numstat_line(self, line: str, current_author: str | None, file_stats: dict[str, dict[str, Any]]) -> None:
        """Process a single numstat line from git log."""
        parts = line.split("\t")
        if len(parts) < 3:
            return

        added = int(parts[0]) if parts[0] != "-" else 0
        deleted = int(parts[1]) if parts[1] != "-" else 0
        filepath = parts[2]

        if filepath not in file_stats:
            file_stats[filepath] = {
                "file": filepath,
                "commits": 0,
                "authors": set(),
                "lines_added": 0,
                "lines_deleted": 0,
                "total_changes": 0,
            }

        file_stats[filepath]["commits"] += 1
        if current_author:
            file_stats[filepath]["authors"].add(current_author)
        file_stats[filepath]["lines_added"] += added
        file_stats[filepath]["lines_deleted"] += deleted
        file_stats[filepath]["total_changes"] += added + deleted

    def _compile_churn_results(self, file_stats: dict[str, dict[str, Any]], churn_threshold: int, results: CodeChurnResults) -> None:
        """Compile file statistics into churn results."""
        for filepath, stats in file_stats.items():
            file_info = FileChurnInfo(
                file=stats["file"],
                commits=stats["commits"],
                authors=len(stats["authors"]),
                lines_added=stats["lines_added"],
                lines_deleted=stats["lines_deleted"],
                total_changes=stats["total_changes"],
                churn_score=stats["commits"] * len(stats["authors"]),
            )
            results.files.append(file_info)

            if stats["commits"] >= churn_threshold:
                results.high_churn_files.append(file_info)

        # Sort by churn score
        results.files.sort(key=lambda x: x.churn_score, reverse=True)
        results.high_churn_files.sort(key=lambda x: x.churn_score, reverse=True)
