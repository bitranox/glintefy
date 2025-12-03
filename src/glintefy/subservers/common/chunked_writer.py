"""Chunked issue file writer for review sub-servers.

Handles writing issues to chunked JSON files organized by type and severity.
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

SEVERITY_ORDER = {"critical": 0, "error": 1, "warning": 2, "info": 3}
CHUNK_SIZE = 50


def _get_severity_rank(severity: str) -> int:
    """Get numeric rank for severity (lower is more severe)."""
    return SEVERITY_ORDER.get(severity.lower(), 999)


def _get_sort_key(issue: dict[str, Any]) -> tuple[str, int, Any, str, int]:
    """Generate sort key for an issue.

    Sorts by:
    1. Type (alphabetically)
    2. Severity (critical > error > warning > info)
    3. Value (high to low, if present)
    4. File path (alphabetically)
    5. Line number (numerically)
    """
    issue_type = issue.get("type", "unknown")
    severity_rank = _get_severity_rank(issue.get("severity", "info"))
    value = issue.get("value", 0)

    # Negate value for descending order (high to low)
    sort_value = -value if isinstance(value, (int, float)) else 0

    file_path = issue.get("file", "")
    line = issue.get("line", 0)

    return (issue_type, severity_rank, sort_value, file_path, line)


def sort_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort issues by type, severity, value, file, and line."""
    return sorted(issues, key=_get_sort_key)


def group_by_type_and_severity(issues: list[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    """Group sorted issues by (type, severity)."""
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    for issue in issues:
        issue_type = issue.get("type", "unknown")
        severity = issue.get("severity", "info")
        groups[(issue_type, severity)].append(issue)

    return groups


def write_chunked_issues(
    issues: list[dict[str, Any]],
    output_dir: Path,
    prefix: str = "issues",
) -> list[Path]:
    """Write issues to chunked JSON files.

    Args:
        issues: List of issue dictionaries
        output_dir: Directory to write files to
        prefix: Filename prefix (default: "issues")

    Returns:
        List of written file paths

    Files are named: {prefix}_{type}_{severity}_{chunk:04d}.json
    Each file contains up to CHUNK_SIZE issues.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    written_files: list[Path] = []

    # Sort all issues first
    sorted_issues = sort_issues(issues)

    # Group by type and severity
    groups = group_by_type_and_severity(sorted_issues)

    # Write each group in chunks
    for (issue_type, severity), group_issues in groups.items():
        # Split into chunks of CHUNK_SIZE
        for chunk_idx, start_idx in enumerate(range(0, len(group_issues), CHUNK_SIZE)):
            chunk = group_issues[start_idx : start_idx + CHUNK_SIZE]
            chunk_num = chunk_idx + 1

            filename = f"{prefix}_{issue_type}_{severity}_{chunk_num:04d}.json"
            filepath = output_dir / filename

            filepath.write_text(json.dumps(chunk, indent=2))
            written_files.append(filepath)

    return written_files


def cleanup_chunked_issues(
    output_dir: Path,
    issue_types: list[str],
    prefix: str = "issues",
) -> int:
    """Delete old chunked issue files for specific issue types.

    Args:
        output_dir: Directory containing chunked files
        issue_types: List of issue types to clean up (e.g., ["god_object", "high_complexity"])
        prefix: Filename prefix to match (default: "issues")

    Returns:
        Number of files deleted
    """
    if not output_dir.exists():
        return 0

    deleted = 0
    for issue_type in issue_types:
        # Match pattern: {prefix}_{issue_type}_*_*.json
        pattern = f"{prefix}_{issue_type}_*.json"
        for filepath in output_dir.glob(pattern):
            filepath.unlink()
            deleted += 1

    return deleted


def write_chunked_all_issues(
    all_issues: list[dict[str, Any]],
    output_dir: Path,
) -> list[Path]:
    """Write all_issues.json in chunked format, organized by severity only.

    Args:
        all_issues: Combined list of all issues from all sub-servers
        output_dir: Directory to write files to

    Returns:
        List of written file paths

    Files are named: all_issues_{severity}_{chunk:04d}.json
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    written_files: list[Path] = []

    # Sort all issues
    sorted_issues = sort_issues(all_issues)

    # Group by severity only
    severity_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for issue in sorted_issues:
        severity = issue.get("severity", "info")
        severity_groups[severity].append(issue)

    # Write each severity group in chunks
    for severity, group_issues in severity_groups.items():
        for chunk_idx, start_idx in enumerate(range(0, len(group_issues), CHUNK_SIZE)):
            chunk = group_issues[start_idx : start_idx + CHUNK_SIZE]
            chunk_num = chunk_idx + 1

            filename = f"all_issues_{severity}_{chunk_num:04d}.json"
            filepath = output_dir / filename

            filepath.write_text(json.dumps(chunk, indent=2))
            written_files.append(filepath)

    return written_files


def cleanup_all_issues(output_dir: Path) -> int:
    """Delete old all_issues_*.json files.

    Args:
        output_dir: Directory containing all_issues files

    Returns:
        Number of files deleted
    """
    if not output_dir.exists():
        return 0

    deleted = 0
    for filepath in output_dir.glob("all_issues_*.json"):
        filepath.unlink()
        deleted += 1

    return deleted
