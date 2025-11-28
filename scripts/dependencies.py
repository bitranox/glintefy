"""Check pyproject.toml dependencies against latest PyPI versions.

Purpose
-------
Scan all dependency specifications in ``pyproject.toml`` and compare them
against the latest available versions on PyPI. This helps keep dependencies
up-to-date and identifies potential upgrades.

Contents
--------
* ``DependencyInfo`` – captures a dependency's current constraint and latest version.
* ``check_dependencies`` – main entry point that checks all dependencies.
* ``print_report`` – renders a formatted report of dependency status.
* ``update_dependencies`` – updates outdated dependencies to latest versions.

System Role
-----------
Development automation helper that sits alongside other scripts. It queries
PyPI via its JSON API to retrieve latest package versions without requiring
additional dependencies.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ._utils import _load_pyproject  # pyright: ignore[reportPrivateUsage]

__all__ = ["DependencyInfo", "check_dependencies", "print_report", "update_dependencies"]


@dataclass
class DependencyInfo:
    """Information about a single dependency."""

    name: str
    source: str
    constraint: str
    current_min: str
    latest: str
    status: str  # "up-to-date", "outdated", "pinned", "unknown", "error"
    original_spec: str = ""  # Original dependency specification string
    upper_bound: str = ""  # Upper version bound if specified (e.g., "<9" means "9")


def _normalize_name(name: str) -> str:
    """Normalize package name for comparison (PEP 503)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _parse_version_constraint(spec: str) -> tuple[str, str, str, str]:
    """Parse a dependency spec into (name, constraint, minimum_version, upper_bound).

    Examples:
        "rich-click>=1.9.4" -> ("rich-click", ">=1.9.4", "1.9.4", "")
        "tomli>=2.0.0; python_version<'3.11'" -> ("tomli", ">=2.0.0", "2.0.0", "")
        "pytest>=8.4.2,<9" -> ("pytest", ">=8.4.2,<9", "8.4.2", "9")
        "hatchling>=1.27.0" -> ("hatchling", ">=1.27.0", "1.27.0", "")
    """
    spec = spec.strip()
    if not spec:
        return "", "", "", ""

    # Remove environment markers (e.g., "; python_version<'3.11'")
    marker_idx = spec.find(";")
    if marker_idx != -1:
        spec = spec[:marker_idx].strip()

    # Handle extras in brackets (e.g., "package[extra]>=1.0")
    bracket_idx = spec.find("[")
    if bracket_idx != -1:
        close_bracket = spec.find("]", bracket_idx)
        if close_bracket != -1:
            spec = spec[:bracket_idx] + spec[close_bracket + 1 :]

    # Extract version constraint
    # Patterns: >=, <=, ==, !=, ~=, >, <
    match = re.match(r"^([a-zA-Z0-9_.-]+)\s*((?:[><=!~]+\s*[\d.a-zA-Z*]+\s*,?\s*)+)?$", spec)
    if not match:
        # Fallback: just return the spec as name
        return spec, "", "", ""

    name = match.group(1).strip()
    constraint = match.group(2).strip() if match.group(2) else ""

    # Extract minimum version from constraint
    min_version = ""
    upper_bound = ""
    if constraint:
        # Look for >= or == patterns to find minimum version
        version_match = re.search(r"[>=~]=?\s*([\d.]+(?:a\d+|b\d+|rc\d+)?)", constraint)
        if version_match:
            min_version = version_match.group(1)

        # Look for < or <= patterns to find upper bound (but not !=)
        upper_match = re.search(r"<(?!=)\s*([\d.]+(?:a\d+|b\d+|rc\d+)?)", constraint)
        if upper_match:
            upper_bound = upper_match.group(1)

    return name, constraint, min_version, upper_bound


def _fetch_pypi_data(package_name: str) -> dict[str, Any] | None:
    """Fetch package data from PyPI."""
    normalized = _normalize_name(package_name)
    url = f"https://pypi.org/pypi/{normalized}/json"

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))  # type: ignore[no-any-return]
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        return None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def _fetch_latest_version(package_name: str) -> str | None:
    """Fetch the latest version of a package from PyPI."""
    data = _fetch_pypi_data(package_name)
    if data is None:
        return None
    return str(data.get("info", {}).get("version", ""))


def _fetch_latest_version_below(package_name: str, upper_bound: str) -> str | None:
    """Fetch the latest version of a package that is below the upper bound.

    Args:
        package_name: Name of the package
        upper_bound: Upper version bound (exclusive), e.g., "9" for "<9"

    Returns:
        Latest version string below the bound, or None if not found
    """
    data = _fetch_pypi_data(package_name)
    if data is None:
        return None

    releases = data.get("releases", {})
    if not releases:
        return None

    # Get all version strings and filter to those below upper_bound
    valid_versions: list[tuple[tuple[int, ...], str]] = []
    for version_str in releases.keys():
        # Skip pre-release versions (containing a, b, rc, dev, etc.)
        if re.search(r"(a|b|rc|dev|alpha|beta)", version_str, re.IGNORECASE):
            continue

        version_tuple = _parse_version_tuple(version_str)
        if not version_tuple:
            continue

        # Check if version is below upper_bound
        if not _version_gte(version_str, upper_bound):
            valid_versions.append((version_tuple, version_str))

    if not valid_versions:
        return None

    # Sort by version tuple (descending) and return the highest
    valid_versions.sort(reverse=True, key=lambda x: x[0])
    return valid_versions[0][1]


def _parse_version_tuple(v: str) -> tuple[int, ...]:
    """Parse version string into a tuple of integers for comparison."""
    match = re.match(r"^([\d.]+)", v)
    if not match:
        return ()
    numeric = match.group(1)
    return tuple(int(p) for p in numeric.split(".") if p.isdigit())


def _version_gte(version_a: str, version_b: str) -> bool:
    """Check if version_a >= version_b."""
    a_parts = _parse_version_tuple(version_a)
    b_parts = _parse_version_tuple(version_b)

    # Pad to same length
    max_len = max(len(a_parts), len(b_parts))
    a_padded = a_parts + (0,) * (max_len - len(a_parts))
    b_padded = b_parts + (0,) * (max_len - len(b_parts))

    return a_padded >= b_padded


def _compare_versions(current: str, latest: str) -> str:
    """Compare two version strings and return status."""
    if not current or not latest:
        return "unknown"

    current_parts = _parse_version_tuple(current)
    latest_parts = _parse_version_tuple(latest)

    # Pad to same length for comparison
    max_len = max(len(current_parts), len(latest_parts))
    current_padded = current_parts + (0,) * (max_len - len(current_parts))
    latest_padded = latest_parts + (0,) * (max_len - len(latest_parts))

    if current_padded >= latest_padded:
        return "up-to-date"
    return "outdated"


def _extract_dependencies_from_list(
    deps: list[Any],
    source: str,
) -> list[DependencyInfo]:
    """Extract dependency info from a list of requirement strings."""
    results: list[DependencyInfo] = []

    for dep in deps:
        if not isinstance(dep, str):
            continue

        original_spec = dep.strip()
        name, constraint, min_version, upper_bound = _parse_version_constraint(dep)
        if not name:
            continue

        # Fetch latest version (respecting upper bound if present)
        latest_absolute = _fetch_latest_version(name)
        if latest_absolute is None:
            status = "error"
            latest_str = "not found"
            latest_in_range = None
        elif not min_version:
            status = "unknown"
            latest_str = latest_absolute
            latest_in_range = None
        elif upper_bound and _version_gte(latest_absolute, upper_bound):
            # Latest version exceeds our upper bound - check for updates within range
            latest_in_range = _fetch_latest_version_below(name, upper_bound)
            if latest_in_range is None:
                status = "pinned"
                latest_str = f"{latest_absolute} (pinned <{upper_bound})"
            elif _version_gte(min_version, latest_in_range):
                # We're at the latest version within the allowed range
                status = "pinned"
                latest_str = f"{latest_absolute} (pinned <{upper_bound})"
            else:
                # There's a newer version within the allowed range
                status = "outdated"
                latest_str = f"{latest_in_range} (max <{upper_bound}, absolute: {latest_absolute})"
        else:
            # No upper bound constraint or latest is within range
            status = _compare_versions(min_version, latest_absolute)
            latest_str = latest_absolute
            latest_in_range = None

        results.append(
            DependencyInfo(
                name=name,
                source=source,
                constraint=constraint,
                current_min=min_version,
                latest=latest_str,
                status=status,
                original_spec=original_spec,
                upper_bound=upper_bound,
            )
        )

    return results


def _extract_all_dependencies(data: dict[str, Any]) -> list[DependencyInfo]:
    """Extract all dependencies from pyproject.toml data."""
    all_deps: list[DependencyInfo] = []

    # 1. [project].dependencies
    project = data.get("project", {})
    if isinstance(project, dict):
        deps = project.get("dependencies", [])
        if isinstance(deps, list):
            all_deps.extend(_extract_dependencies_from_list(deps, "[project].dependencies"))

        # 2. [project.optional-dependencies]
        optional = project.get("optional-dependencies", {})
        if isinstance(optional, dict):
            for group_name, group_deps in optional.items():
                if isinstance(group_deps, list):
                    source = f"[project.optional-dependencies].{group_name}"
                    all_deps.extend(_extract_dependencies_from_list(group_deps, source))

    # 3. [build-system].requires
    build_system = data.get("build-system", {})
    if isinstance(build_system, dict):
        requires = build_system.get("requires", [])
        if isinstance(requires, list):
            all_deps.extend(_extract_dependencies_from_list(requires, "[build-system].requires"))

    # 4. [dependency-groups] (PEP 735 - newer spec)
    dep_groups = data.get("dependency-groups", {})
    if isinstance(dep_groups, dict):
        for group_name, group_deps in dep_groups.items():
            if isinstance(group_deps, list):
                source = f"[dependency-groups].{group_name}"
                all_deps.extend(_extract_dependencies_from_list(group_deps, source))

    # 5. Check for tool-specific dependency sections
    tool = data.get("tool", {})
    if isinstance(tool, dict):
        # [tool.pdm.dev-dependencies] (PDM)
        pdm = tool.get("pdm", {})
        if isinstance(pdm, dict):
            pdm_dev = pdm.get("dev-dependencies", {})
            if isinstance(pdm_dev, dict):
                for group_name, group_deps in pdm_dev.items():
                    if isinstance(group_deps, list):
                        source = f"[tool.pdm.dev-dependencies].{group_name}"
                        all_deps.extend(_extract_dependencies_from_list(group_deps, source))

        # [tool.poetry.dependencies] and [tool.poetry.dev-dependencies] (Poetry)
        poetry = tool.get("poetry", {})
        if isinstance(poetry, dict):
            poetry_deps = poetry.get("dependencies", {})
            if isinstance(poetry_deps, dict):
                poetry_dep_list = _poetry_deps_to_list(poetry_deps)
                all_deps.extend(_extract_dependencies_from_list(poetry_dep_list, "[tool.poetry.dependencies]"))

            poetry_dev = poetry.get("dev-dependencies", {})
            if isinstance(poetry_dev, dict):
                poetry_dev_list = _poetry_deps_to_list(poetry_dev)
                all_deps.extend(_extract_dependencies_from_list(poetry_dev_list, "[tool.poetry.dev-dependencies]"))

            # Poetry group dependencies
            poetry_groups = poetry.get("group", {})
            if isinstance(poetry_groups, dict):
                for group_name, group_data in poetry_groups.items():
                    if isinstance(group_data, dict):
                        group_deps = group_data.get("dependencies", {})
                        if isinstance(group_deps, dict):
                            source = f"[tool.poetry.group.{group_name}.dependencies]"
                            all_deps.extend(_extract_dependencies_from_list(_poetry_deps_to_list(group_deps), source))

        # [tool.uv.dev-dependencies] (uv)
        uv = tool.get("uv", {})
        if isinstance(uv, dict):
            uv_dev = uv.get("dev-dependencies", [])
            if isinstance(uv_dev, list):
                all_deps.extend(_extract_dependencies_from_list(uv_dev, "[tool.uv.dev-dependencies]"))

    return all_deps


def _poetry_deps_to_list(deps: dict[str, Any]) -> list[str]:
    """Convert Poetry-style dependency dict to requirement strings."""
    result: list[str] = []
    for name, spec in deps.items():
        if name.lower() == "python":
            continue
        if isinstance(spec, str):
            # Simple version constraint
            if spec == "*":
                result.append(name)
            elif spec.startswith("^"):
                # Poetry caret constraint -> approximate >=
                result.append(f"{name}>={spec[1:]}")
            elif spec.startswith("~"):
                # Poetry tilde constraint -> approximate >=
                result.append(f"{name}>={spec[1:]}")
            else:
                result.append(f"{name}{spec}")
        elif isinstance(spec, dict):
            version = spec.get("version", "")
            if isinstance(version, str) and version:
                if version == "*":
                    result.append(name)
                elif version.startswith("^"):
                    result.append(f"{name}>={version[1:]}")
                elif version.startswith("~"):
                    result.append(f"{name}>={version[1:]}")
                else:
                    result.append(f"{name}{version}")
            else:
                result.append(name)
        else:
            result.append(name)
    return result


def check_dependencies(pyproject: Path = Path("pyproject.toml")) -> list[DependencyInfo]:
    """Check all dependencies in pyproject.toml against PyPI.

    Args:
        pyproject: Path to pyproject.toml file

    Returns:
        List of DependencyInfo objects for all found dependencies.
    """
    data = _load_pyproject(pyproject)
    return _extract_all_dependencies(data)


def print_report(deps: list[DependencyInfo], *, verbose: bool = False) -> int:
    """Print a formatted dependency status report.

    Args:
        deps: List of dependency info objects
        verbose: If True, show all dependencies; if False, show only outdated

    Returns:
        Exit code (0 if all up-to-date, 1 if any outdated)
    """
    if not deps:
        print("No dependencies found in pyproject.toml")
        return 0

    # Group by source
    by_source: dict[str, list[DependencyInfo]] = {}
    for dep in deps:
        by_source.setdefault(dep.source, []).append(dep)

    outdated_count = 0
    error_count = 0

    for source, source_deps in sorted(by_source.items()):
        # Filter if not verbose
        display_deps = source_deps if verbose else [d for d in source_deps if d.status != "up-to-date"]

        if not display_deps:
            continue

        print(f"\n{source}:")
        print("-" * len(source) + "-")

        # Calculate column widths
        name_width = max(len(d.name) for d in display_deps)
        constraint_width = max(len(d.constraint) for d in display_deps) if display_deps else 0
        latest_width = max(len(d.latest) for d in display_deps)

        for dep in sorted(display_deps, key=lambda d: d.name.lower()):
            status_icon = _get_status_icon(dep.status)
            constraint_display = dep.constraint if dep.constraint else "(any)"

            print(f"  {status_icon} {dep.name:<{name_width}}  {constraint_display:<{constraint_width}}  -> {dep.latest:<{latest_width}}  [{dep.status}]")

            if dep.status == "outdated":
                outdated_count += 1
            elif dep.status == "error":
                error_count += 1

    # Summary
    total = len(deps)
    up_to_date = sum(1 for d in deps if d.status == "up-to-date")
    pinned = sum(1 for d in deps if d.status == "pinned")
    unknown = sum(1 for d in deps if d.status == "unknown")

    print(f"\nSummary: {total} dependencies checked")
    print(f"  Up-to-date: {up_to_date}")
    print(f"  Pinned:     {pinned}")
    print(f"  Outdated:   {outdated_count}")
    print(f"  Unknown:    {unknown}")
    print(f"  Errors:     {error_count}")

    if outdated_count > 0:
        print("\nRun with --verbose to see all dependencies")
        return 1
    return 0


def _get_status_icon(status: str) -> str:
    """Get a status icon character (ASCII-safe for Windows compatibility)."""
    icons = {
        "up-to-date": "[ok]",
        "outdated": "[!!]",
        "pinned": "[==]",
        "unknown": "[??]",
        "error": "[XX]",
    }
    return icons.get(status, "[??]")


def _build_updated_spec(dep: DependencyInfo) -> str:
    """Build an updated dependency specification with the latest version.

    Preserves the original format (>=, ==, etc.) and any environment markers.
    """
    original = dep.original_spec
    latest = dep.latest

    if not original or not latest or latest == "not found":
        return original

    # Check for environment markers
    marker = ""
    marker_idx = original.find(";")
    if marker_idx != -1:
        marker = original[marker_idx:]
        original = original[:marker_idx].strip()

    # Check for extras
    extras = ""
    bracket_idx = original.find("[")
    if bracket_idx != -1:
        close_bracket = original.find("]", bracket_idx)
        if close_bracket != -1:
            extras = original[bracket_idx : close_bracket + 1]

    # Find the version constraint pattern and replace the version
    # Common patterns: >=X.Y.Z, ==X.Y.Z, ~=X.Y.Z, >X.Y.Z
    pattern = r"([><=!~]+)\s*([\d.]+(?:a\d+|b\d+|rc\d+)?)"

    def replace_version(match: re.Match[str]) -> str:
        operator = match.group(1)
        return f"{operator}{latest}"

    # Replace all version constraints with latest
    updated = re.sub(pattern, replace_version, original)

    # If no version constraint was found, add >=latest
    if updated == original and not re.search(r"[><=!~]", original):
        # Extract just the package name
        name_match = re.match(r"^([a-zA-Z0-9_.-]+)", original)
        if name_match:
            pkg_name = name_match.group(1)
            updated = f"{pkg_name}{extras}>={latest}"
        else:
            updated = f"{original}>={latest}"
    elif extras and extras not in updated:
        # Re-add extras if they were stripped
        name_match = re.match(r"^([a-zA-Z0-9_.-]+)", updated)
        if name_match:
            pkg_name = name_match.group(1)
            rest = updated[len(pkg_name) :]
            updated = f"{pkg_name}{extras}{rest}"

    # Re-add environment marker
    if marker:
        updated = f"{updated}{marker}"

    return updated


def update_dependencies(
    deps: list[DependencyInfo],
    pyproject: Path = Path("pyproject.toml"),
    *,
    dry_run: bool = False,
) -> int:
    """Update outdated dependencies in pyproject.toml to latest versions.

    Args:
        deps: List of dependency info objects from check_dependencies
        pyproject: Path to pyproject.toml file
        dry_run: If True, only show what would be changed without modifying

    Returns:
        Number of dependencies updated
    """
    outdated = [d for d in deps if d.status == "outdated"]
    if not outdated:
        print("All dependencies are up-to-date!")
        return 0

    # Read the file content
    content = pyproject.read_text(encoding="utf-8")
    updated_count = 0

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Updating {len(outdated)} dependencies:\n")

    for dep in outdated:
        if not dep.original_spec:
            continue

        new_spec = _build_updated_spec(dep)
        if new_spec == dep.original_spec:
            continue

        # Escape special regex characters in the original spec
        escaped_original = re.escape(dep.original_spec)

        # Try to find and replace the dependency in the file
        # We need to be careful to match the exact string in quotes
        patterns = [
            # Double-quoted string
            rf'"{escaped_original}"',
            # Single-quoted string
            rf"'{escaped_original}'",
        ]

        replaced = False
        for pattern in patterns:
            if re.search(pattern, content):
                quote = pattern[0]
                replacement = f"{quote}{new_spec}{quote}"
                content = re.sub(pattern, replacement, content, count=1)
                replaced = True
                break

        if replaced:
            print(f"  {dep.name}: {dep.original_spec} -> {new_spec}")
            updated_count += 1
        else:
            print(f"  {dep.name}: Could not locate in file (manual update needed)")

    if updated_count > 0:
        if dry_run:
            print(f"\n[DRY RUN] Would update {updated_count} dependencies")
        else:
            pyproject.write_text(content, encoding="utf-8")
            print(f"\nUpdated {updated_count} dependencies in {pyproject}")

            # Clear the pyproject cache since we modified the file
            from ._utils import _PYPROJECT_DATA_CACHE  # pyright: ignore[reportPrivateUsage]

            _PYPROJECT_DATA_CACHE.pop(pyproject.resolve(), None)
    else:
        print("\nNo dependencies were updated")

    return updated_count


def main(
    verbose: bool = False,
    update: bool = False,
    dry_run: bool = False,
    pyproject: Path = Path("pyproject.toml"),
) -> int:
    """Main entry point for dependency checking.

    Args:
        verbose: Show all dependencies, not just outdated ones
        update: Update outdated dependencies to latest versions
        dry_run: Show what would be updated without making changes
        pyproject: Path to pyproject.toml

    Returns:
        Exit code (0 if all up-to-date or update successful, 1 if any outdated)
    """
    print(f"Checking dependencies in {pyproject}...")
    deps = check_dependencies(pyproject)
    exit_code = print_report(deps, verbose=verbose)

    if update:
        updated = update_dependencies(deps, pyproject, dry_run=dry_run)
        if updated > 0 and not dry_run:
            return 0  # Successfully updated
    return exit_code


if __name__ == "__main__":  # pragma: no cover
    verbose_flag = "--verbose" in sys.argv or "-v" in sys.argv
    update_flag = "--update" in sys.argv or "-u" in sys.argv
    dry_run_flag = "--dry-run" in sys.argv
    sys.exit(main(verbose=verbose_flag, update=update_flag, dry_run=dry_run_flag))
