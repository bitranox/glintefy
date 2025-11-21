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

from btx_fix_mcp.tools_venv import get_tool_path

from .base import BaseAnalyzer


class MetricsAnalyzer(BaseAnalyzer):
    """Halstead, raw metrics, and code churn analyzer."""

    def analyze(self, files: list[str]) -> dict[str, Any]:
        """Analyze metrics for all files.

        Returns:
            Dictionary with keys: halstead, raw_metrics, code_churn
        """
        return {
            "halstead": self._analyze_halstead(files),
            "raw_metrics": self._analyze_raw_metrics(files),
            "code_churn": self._analyze_code_churn(files),
        }

    def _analyze_halstead(self, files: list[str]) -> list[dict[str, Any]]:
        """Analyze Halstead metrics using radon."""
        results = []
        radon = str(get_tool_path("radon"))

        for file_path in files:
            if not Path(file_path).exists():
                continue
            try:
                result = subprocess.run(
                    [radon, "hal", "-j", file_path],
                    capture_output=True, text=True, timeout=30,
                )
                if result.returncode == 0 and result.stdout.strip():
                    data = json.loads(result.stdout)
                    for filepath, hal_data in data.items():
                        if hal_data.get("total"):
                            total = (
                                hal_data["total"][0]
                                if isinstance(hal_data["total"], list)
                                else hal_data["total"]
                            )
                            results.append({
                                "file": self._get_relative_path(filepath),
                                "h1": total.get("h1", 0),
                                "h2": total.get("h2", 0),
                                "N1": total.get("N1", 0),
                                "N2": total.get("N2", 0),
                                "vocabulary": total.get("vocabulary", 0),
                                "length": total.get("length", 0),
                                "volume": total.get("volume", 0),
                                "difficulty": total.get("difficulty", 0),
                                "effort": total.get("effort", 0),
                                "time": total.get("time", 0),
                                "bugs": total.get("bugs", 0),
                            })
            except subprocess.TimeoutExpired:
                self.logger.warning(f"Timeout analyzing Halstead in {file_path}")
            except json.JSONDecodeError:
                self.logger.warning(f"Invalid JSON from radon for {file_path}")
            except FileNotFoundError:
                self.logger.warning("radon not found")
                break
            except Exception as e:
                self.logger.warning(f"Error analyzing Halstead in {file_path}: {e}")

        return results

    def _analyze_raw_metrics(self, files: list[str]) -> list[dict[str, Any]]:
        """Analyze raw metrics (LOC, SLOC, comments) using radon."""
        results = []
        radon = str(get_tool_path("radon"))

        for file_path in files:
            if not Path(file_path).exists():
                continue
            try:
                result = subprocess.run(
                    [radon, "raw", "-j", file_path],
                    capture_output=True, text=True, timeout=30,
                )
                if result.returncode == 0 and result.stdout.strip():
                    data = json.loads(result.stdout)
                    for filepath, raw_data in data.items():
                        results.append({
                            "file": self._get_relative_path(filepath),
                            "loc": raw_data.get("loc", 0),
                            "lloc": raw_data.get("lloc", 0),
                            "sloc": raw_data.get("sloc", 0),
                            "comments": raw_data.get("comments", 0),
                            "multi": raw_data.get("multi", 0),
                            "blank": raw_data.get("blank", 0),
                            "single_comments": raw_data.get("single_comments", 0),
                        })
            except subprocess.TimeoutExpired:
                self.logger.warning(f"Timeout analyzing raw metrics in {file_path}")
            except json.JSONDecodeError:
                self.logger.warning(f"Invalid JSON from radon for {file_path}")
            except FileNotFoundError:
                self.logger.warning("radon not found")
                break
            except Exception as e:
                self.logger.warning(f"Error analyzing raw metrics in {file_path}: {e}")

        return results

    def _analyze_code_churn(self, files: list[str]) -> dict[str, Any]:
        """Analyze code churn using git history.

        Identifies frequently modified files which may indicate:
        - Unstable code needing refactoring
        - Hot spots with potential bugs
        - Technical debt areas
        """
        churn_threshold = self.config.get("churn_threshold", 20)
        results = {
            "files": [],
            "high_churn_files": [],
            "total_commits_analyzed": 0,
            "analysis_period_days": 90,
        }
        if not files:
            return results

        try:
            # Check if we're in a git repo
            git_check = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True, text=True, timeout=5, cwd=str(self.repo_path),
            )
            if git_check.returncode != 0:
                self.logger.info("Not a git repository, skipping churn analysis")
                return results

            # Convert absolute paths to relative paths for git
            relative_files = []
            for f in files:
                try:
                    relative_files.append(str(Path(f).relative_to(self.repo_path)))
                except ValueError:
                    # File not under repo_path, use as-is
                    relative_files.append(f)

            # Get git log with numstat for the past 90 days
            result = subprocess.run(
                [
                    "git", "log", "--numstat", "--format=%H|%ae|%at",
                    "--since=90 days ago", "--", *relative_files
                ],
                capture_output=True, text=True, timeout=60, cwd=str(self.repo_path),
            )

            if result.returncode != 0:
                return results

            # Parse git log output
            file_stats: dict[str, dict[str, Any]] = {}
            current_author = None
            commits_seen: set[str] = set()

            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                # Commit line format: hash|author_email|timestamp
                if "|" in line and line.count("|") == 2:
                    parts = line.split("|")
                    current_commit = parts[0]
                    current_author = parts[1]
                    commits_seen.add(current_commit)
                # Numstat line format: added\tdeleted\tfilename
                elif "\t" in line:
                    parts = line.split("\t")
                    if len(parts) >= 3:
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

            results["total_commits_analyzed"] = len(commits_seen)

            # Convert to list and sort by commits (descending)
            for filepath, stats in file_stats.items():
                file_info = {
                    "file": stats["file"],
                    "commits": stats["commits"],
                    "authors": len(stats["authors"]),
                    "lines_added": stats["lines_added"],
                    "lines_deleted": stats["lines_deleted"],
                    "total_changes": stats["total_changes"],
                    "churn_score": stats["commits"] * len(stats["authors"]),
                }
                results["files"].append(file_info)

                # Flag high churn files
                if stats["commits"] >= churn_threshold:
                    results["high_churn_files"].append(file_info)

            # Sort by churn score
            results["files"].sort(key=lambda x: x["churn_score"], reverse=True)
            results["high_churn_files"].sort(key=lambda x: x["churn_score"], reverse=True)

        except FileNotFoundError:
            self.logger.warning("git not found for churn analysis")
        except subprocess.TimeoutExpired:
            self.logger.warning("git log timed out")
        except Exception as e:
            self.logger.warning(f"churn analysis error: {e}")

        return results
