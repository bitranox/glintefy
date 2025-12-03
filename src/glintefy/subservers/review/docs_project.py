"""Project documentation checking.

Checks for presence and quality of project documentation files
(README, CHANGELOG, LICENSE, CONTRIBUTING).
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

from glintefy.subservers.common.issues import ProjectDocIssue


@dataclass
class ProjectDocsConfig:
    """Configuration for project docs checking."""

    require_readme: bool = True
    require_changelog: bool = False
    required_readme_sections: list[str] = field(default_factory=list)


@dataclass
class ProjectDocsResult:
    """Result of project documentation check."""

    readme: bool = False
    readme_path: str | None = None
    changelog: bool = False
    contributing: bool = False
    license: bool = False
    issues: list[ProjectDocIssue] = field(default_factory=list)


REQUIRED_PROJECT_DOCS = ["README.md", "README.rst", "README.txt"]


def find_readme_file(repo_path: Path) -> tuple[bool, Path | None]:
    """Find README file in project root.

    Args:
        repo_path: Path to repository root

    Returns:
        Tuple of (found, path)
    """
    for readme in REQUIRED_PROJECT_DOCS:
        readme_path = repo_path / readme
        if readme_path.exists():
            return True, readme_path
    return False, None


def check_readme_file(
    repo_path: Path,
    require_readme: bool,
    issues: list[ProjectDocIssue],
) -> tuple[bool, Path | None]:
    """Check for README file and add issues if missing.

    Args:
        repo_path: Path to repository root
        require_readme: Whether README is required
        issues: List to append issues to

    Returns:
        Tuple of (found, path)
    """
    readme_found, readme_path = find_readme_file(repo_path)

    if not readme_found:
        severity = "critical" if require_readme else "warning"
        issues.append(
            ProjectDocIssue(
                type="missing_readme",
                severity=severity,
                message="No README file found (README.md, README.rst, or README.txt)",
                doc_file="README",
                required=require_readme,
            )
        )

    return readme_found, readme_path


def check_readme_sections(
    readme_path: Path,
    required_sections: list[str],
    logger: logging.Logger | None = None,
) -> list[str]:
    """Check if README contains required sections.

    Args:
        readme_path: Path to README file
        required_sections: List of required section names
        logger: Optional logger for warnings

    Returns:
        List of missing section names
    """
    try:
        content = readme_path.read_text().lower()
        missing = []

        for section in required_sections:
            section_lower = section.lower()
            if f"# {section_lower}" not in content and f"#{section_lower}" not in content:
                missing.append(section)

        return missing

    except Exception as e:
        if logger:
            logger.warning(f"Error checking README sections: {e}")
        return []


def check_readme_sections_if_required(
    readme_path: Path | None,
    required_sections: list[str],
    issues: list[ProjectDocIssue],
    logger: logging.Logger | None = None,
) -> None:
    """Check README sections if file exists and sections are required.

    Args:
        readme_path: Path to README file or None
        required_sections: List of required section names
        issues: List to append issues to
        logger: Optional logger for warnings
    """
    if not readme_path or not required_sections:
        return

    missing_sections = check_readme_sections(readme_path, required_sections, logger)
    for section in missing_sections:
        issues.append(
            ProjectDocIssue(
                type="missing_readme_section",
                severity="warning",
                message=f"README is missing required section: {section}",
                doc_file="README",
                required=True,
            )
        )


def check_changelog_file(
    repo_path: Path,
    require_changelog: bool,
    issues: list[ProjectDocIssue],
) -> bool:
    """Check for CHANGELOG file.

    Args:
        repo_path: Path to repository root
        require_changelog: Whether changelog is required
        issues: List to append issues to

    Returns:
        True if changelog exists
    """
    if (repo_path / "CHANGELOG.md").exists():
        return True

    if require_changelog:
        issues.append(
            ProjectDocIssue(
                type="missing_changelog",
                severity="warning",
                message="No CHANGELOG.md file found",
                doc_file="CHANGELOG",
                required=True,
            )
        )
    return False


def check_license_file(repo_path: Path, issues: list[ProjectDocIssue]) -> bool:
    """Check for LICENSE file.

    Args:
        repo_path: Path to repository root
        issues: List to append issues to

    Returns:
        True if license exists
    """
    if (repo_path / "LICENSE").exists() or (repo_path / "LICENSE.md").exists():
        return True

    issues.append(
        ProjectDocIssue(
            type="missing_license",
            severity="warning",
            message="No LICENSE file found",
            doc_file="LICENSE",
            required=False,
        )
    )
    return False


def check_project_docs(
    repo_path: Path,
    config: ProjectDocsConfig,
    logger: logging.Logger | None = None,
) -> ProjectDocsResult:
    """Check project documentation files.

    Args:
        repo_path: Path to repository root
        config: Configuration for checking
        logger: Optional logger for warnings

    Returns:
        ProjectDocsResult with findings
    """
    issues: list[ProjectDocIssue] = []

    # Check README
    readme_found, readme_path = check_readme_file(repo_path, config.require_readme, issues)
    check_readme_sections_if_required(readme_path, config.required_readme_sections, issues, logger)

    # Check other project docs
    changelog_found = check_changelog_file(repo_path, config.require_changelog, issues)
    contributing_found = (repo_path / "CONTRIBUTING.md").exists()
    license_found = check_license_file(repo_path, issues)

    return ProjectDocsResult(
        readme=readme_found,
        readme_path=str(readme_path) if readme_path else None,
        changelog=changelog_found,
        contributing=contributing_found,
        license=license_found,
        issues=issues,
    )
