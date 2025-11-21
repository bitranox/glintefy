"""Base sub-server class for MCP agents."""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional
import json


class SubServerResult:
    """Standard result format for sub-servers.

    All sub-servers return this structured result containing:
    - Status (SUCCESS, FAILED, or PARTIAL)
    - Human-readable summary
    - Artifacts (file paths)
    - Metrics (quantifiable data)
    - Errors (if any)
    """

    def __init__(
        self,
        status: str,
        summary: str,
        artifacts: dict[str, Path],
        metrics: dict | None = None,
        errors: Optional[list[str]] = None,
    ):
        """Initialize result.

        Args:
            status: "SUCCESS", "FAILED", or "PARTIAL"
            summary: Human-readable markdown summary
            artifacts: Dict mapping artifact names to file paths
            metrics: Optional metrics dictionary
            errors: Optional list of error messages
        """
        if status not in ("SUCCESS", "FAILED", "PARTIAL"):
            raise ValueError(f"Invalid status: {status}. Must be SUCCESS, FAILED, or PARTIAL")

        self.status = status
        self.summary = summary
        self.artifacts = artifacts
        self.metrics = metrics or {}
        self.errors = errors or []
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        """Convert result to dictionary."""
        return {
            "status": self.status,
            "summary": self.summary,
            "artifacts": {k: str(v) for k, v in self.artifacts.items()},
            "metrics": self.metrics,
            "errors": self.errors,
            "timestamp": self.timestamp,
        }


class BaseSubServer(ABC):
    """Base class for sub-servers.

    All sub-servers inherit from this class and implement:
    - validate_inputs() - Check required inputs exist
    - execute() - Main execution logic

    The base class handles:
    - Directory management
    - Status tracking (status.txt)
    - Summary reports ({name}_summary.md)
    - JSON output
    - Error handling
    """

    def __init__(self, name: str, input_dir: Path, output_dir: Path):
        """Initialize sub-server.

        Args:
            name: Sub-server name (e.g., 'scope', 'quality', 'security')
            input_dir: Input directory (contains required inputs)
            output_dir: Output directory (for results)
        """
        self.name = name
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def validate_inputs(self) -> tuple[bool, list[str]]:
        """Validate required inputs exist.

        Returns:
            Tuple of (valid, missing_files)
            - valid: True if all required inputs exist
            - missing_files: List of missing file paths (empty if valid)
        """
        pass

    @abstractmethod
    def execute(self) -> SubServerResult:
        """Execute sub-server logic.

        Returns:
            SubServerResult with status, summary, artifacts, and metrics
        """
        pass

    def save_status(self, status: str) -> None:
        """Save status.txt per integration protocol.

        Args:
            status: "SUCCESS", "FAILED", or "IN_PROGRESS"
        """
        if status not in ("SUCCESS", "FAILED", "IN_PROGRESS", "PARTIAL"):
            raise ValueError(f"Invalid status: {status}")

        status_file = self.output_dir / "status.txt"
        status_file.write_text(status)

    def save_summary(self, content: str) -> None:
        """Save summary report.

        Args:
            content: Markdown-formatted summary
        """
        summary_file = self.output_dir / f"{self.name}_summary.md"
        summary_file.write_text(content)

    def save_json(self, filename: str, data: dict) -> None:
        """Save JSON data.

        Args:
            filename: Output filename (e.g., 'results.json')
            data: Dictionary to save
        """
        output_file = self.output_dir / filename
        output_file.write_text(json.dumps(data, indent=2))

    def run(self) -> SubServerResult:
        """Main entry point. Handles validation and execution.

        This method:
        1. Marks status as IN_PROGRESS
        2. Validates inputs
        3. Executes sub-server logic
        4. Saves status, summary, and artifacts
        5. Returns result

        Returns:
            SubServerResult with execution results
        """
        # Mark as in progress
        self.save_status("IN_PROGRESS")

        # Validate inputs
        valid, missing = self.validate_inputs()
        if not valid:
            error_msg = f"Missing inputs: {', '.join(missing)}"
            self.save_status("FAILED")
            self.save_summary(f"# {self.name} - FAILED\n\n{error_msg}")
            return SubServerResult(
                status="FAILED",
                summary=error_msg,
                artifacts={},
                errors=[error_msg],
            )

        # Execute
        try:
            result = self.execute()
            self.save_status(result.status)
            self.save_summary(result.summary)

            # Save result as JSON
            self.save_json("result.json", result.to_dict())

            return result
        except Exception as e:
            error_msg = f"Execution failed: {str(e)}"
            self.save_status("FAILED")
            self.save_summary(f"# {self.name} - FAILED\n\n{error_msg}\n\n```\n{e}\n```")
            return SubServerResult(
                status="FAILED",
                summary=error_msg,
                artifacts={},
                errors=[error_msg],
            )
