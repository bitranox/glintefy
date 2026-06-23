"""Base sub-server class for MCP agents."""

import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

# Valid status values for sub-server results
StatusType = Literal["SUCCESS", "FAILED", "PARTIAL"]
VALID_STATUSES: frozenset[str] = frozenset({"SUCCESS", "FAILED", "PARTIAL"})


@dataclass(slots=True)
class SubServerResult:
    """Standard result format for sub-servers.

    All sub-servers return this structured result containing:
    - Status (SUCCESS, FAILED, or PARTIAL)
    - Human-readable summary
    - Artifacts (file paths)
    - Metrics (quantifiable data)
    - Errors (if any)

    Attributes:
        status: "SUCCESS", "FAILED", or "PARTIAL"
        summary: Human-readable markdown summary
        artifacts: Dict mapping artifact names to file paths
        metrics: Quantifiable metrics dictionary
        errors: List of error messages
        timestamp: ISO format timestamp of result creation
    """

    status: StatusType
    summary: str
    artifacts: dict[str, Path]
    metrics: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self) -> None:
        """Validate status after initialization."""
        if self.status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {self.status}. Must be SUCCESS, FAILED, or PARTIAL")

    def to_dict(self) -> dict:
        """Convert result to dictionary with Path objects as strings.

        Uses POSIX-style paths (forward slashes) for cross-platform consistency.
        """
        result = asdict(self)
        result["artifacts"] = {k: v.as_posix() for k, v in self.artifacts.items()}
        return result


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

    def __init__(self, name: str, input_dir: Path | None, output_dir: Path | None):
        """Initialize sub-server.

        Args:
            name: Sub-server name (e.g., 'scope', 'quality', 'security')
            input_dir: Input directory (contains required inputs), or None
            output_dir: Output directory (for results), or None
        """
        self.name = name
        self.input_dir = Path(input_dir) if input_dir else None
        self.output_dir = Path(output_dir) if output_dir else None
        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def validate_inputs(self) -> tuple[bool, list[str]]:
        """Validate required inputs exist.

        Returns:
            Tuple of (valid, missing_files)
            - valid: True if all required inputs exist
            - missing_files: List of missing file paths (empty if valid)
        """

    @abstractmethod
    def execute(self) -> SubServerResult:
        """Execute sub-server logic.

        Returns:
            SubServerResult with status, summary, artifacts, and metrics
        """

    def save_status(self, status: str) -> None:
        """Save status.txt per integration protocol.

        Args:
            status: "SUCCESS", "FAILED", or "IN_PROGRESS"
        """
        if status not in ("SUCCESS", "FAILED", "IN_PROGRESS", "PARTIAL"):
            raise ValueError(f"Invalid status: {status}")

        if self.output_dir:
            status_file = self.output_dir / "status.txt"
            status_file.write_text(status)

    def save_summary(self, content: str) -> None:
        """Save summary report.

        Args:
            content: Markdown-formatted summary
        """
        if self.output_dir:
            summary_file = self.output_dir / f"{self.name}_summary.md"
            summary_file.write_text(content)

    def save_json(self, filename: str, data: dict) -> None:
        """Save JSON data.

        Args:
            filename: Output filename (e.g., 'results.json')
            data: Dictionary to save
        """
        if self.output_dir:
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
            error_msg = f"Execution failed: {e!s}"
            self.save_status("FAILED")
            self.save_summary(f"# {self.name} - FAILED\n\n{error_msg}\n\n```\n{e}\n```")
            return SubServerResult(
                status="FAILED",
                summary=error_msg,
                artifacts={},
                errors=[error_msg],
            )
