"""Base class for quality analyzers.

All quality analyzers inherit from this base class and implement the analyze() method.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseAnalyzer(ABC):
    """Base class for quality analyzers.

    Each analyzer focuses on a specific aspect of code quality
    (complexity, types, architecture, etc.).

    Args:
        repo_path: Path to the repository being analyzed
        logger: Logger instance for output
        config: Configuration dictionary
    """

    def __init__(
        self,
        repo_path: Path,
        logger: logging.Logger,
        config: dict[str, Any],
    ):
        """Initialize analyzer with repository path, logger, and configuration."""
        self.repo_path = repo_path
        self.logger = logger
        self.config = config

    @abstractmethod
    def analyze(self, files: list[str]) -> dict[str, Any]:
        """Analyze the given files.

        Args:
            files: List of absolute file paths to analyze

        Returns:
            Dictionary containing analysis results
        """

    def _get_relative_path(self, file_path: str) -> str:
        """Get relative path from repo root."""
        try:
            return str(Path(file_path).relative_to(self.repo_path))
        except ValueError:
            return file_path
