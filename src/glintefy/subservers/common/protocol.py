"""Integration protocol validation for sub-servers."""

from pathlib import Path


class ProtocolViolation(Exception):
    """Raised when a sub-server violates the integration protocol."""


class IntegrationProtocol:
    """Validates sub-server integration protocol compliance.

    The integration protocol requires:
    1. status.txt - Must contain "SUCCESS", "FAILED", "IN_PROGRESS", or "PARTIAL"
    2. {subagent_name}_summary.md - Must exist and contain markdown
    3. result.json - Optional but recommended

    All sub-servers MUST create these files in their output directory.
    """

    VALID_STATUSES = {"SUCCESS", "FAILED", "IN_PROGRESS", "PARTIAL"}

    @staticmethod
    def _validate_status_file(status_file: Path, violations: list[str]) -> None:
        """Validate status.txt file exists and has valid status."""
        if not status_file.exists():
            violations.append("Missing required file: status.txt")
            return

        try:
            status = status_file.read_text().strip()
            if status not in IntegrationProtocol.VALID_STATUSES:
                violations.append(f"Invalid status '{status}'. Must be one of: {', '.join(IntegrationProtocol.VALID_STATUSES)}")
        except Exception as e:
            violations.append(f"Cannot read status.txt: {e}")

    @staticmethod
    def _validate_summary_file(summary_file: Path, subagent_name: str, violations: list[str]) -> None:
        """Validate summary.md file exists and is valid markdown."""
        if not summary_file.exists():
            violations.append(f"Missing required file: {subagent_name}_summary.md")
            return

        try:
            content = summary_file.read_text().strip()
            if not content:
                violations.append(f"{subagent_name}_summary.md is empty")
            elif not content.startswith("#"):
                violations.append(f"{subagent_name}_summary.md should start with markdown heading (#)")
        except Exception as e:
            violations.append(f"Cannot read {subagent_name}_summary.md: {e}")

    @staticmethod
    def _validate_result_file(result_file: Path, require_result_json: bool, violations: list[str]) -> None:
        """Validate result.json file exists if required."""
        if require_result_json and not result_file.exists():
            violations.append("Missing required file: result.json")

    @staticmethod
    def validate_outputs(
        output_dir: Path,
        subagent_name: str,
        require_result_json: bool = False,
    ) -> tuple[bool, list[str]]:
        """Validate that all required protocol files exist.

        Args:
            output_dir: Sub-server output directory
            subagent_name: Name of the sub-server
            require_result_json: Whether to require result.json

        Returns:
            Tuple of (valid, violations)
            - valid: True if all requirements met
            - violations: List of violation messages (empty if valid)

        Example:
            >>> from pathlib import Path
            >>> valid, violations = IntegrationProtocol.validate_outputs(
            ...     Path("LLM-CONTEXT/glintefy/review/scope"),
            ...     "scope"
            ... )
            >>> if not valid:
            ...     print("Violations:", violations)
        """
        violations = []

        IntegrationProtocol._validate_status_file(output_dir / "status.txt", violations)
        IntegrationProtocol._validate_summary_file(output_dir / f"{subagent_name}_summary.md", subagent_name, violations)
        IntegrationProtocol._validate_result_file(output_dir / "result.json", require_result_json, violations)

        return len(violations) == 0, violations

    @staticmethod
    def validate_status_file(status_file: Path) -> tuple[bool, str | None]:
        """Validate status.txt file.

        Args:
            status_file: Path to status.txt

        Returns:
            Tuple of (valid, error_message)
            - valid: True if status is valid
            - error_message: Error description (None if valid)

        Example:
            >>> from pathlib import Path
            >>> valid, error = IntegrationProtocol.validate_status_file(
            ...     Path("LLM-CONTEXT/glintefy/review/scope/status.txt")
            ... )
        """
        if not status_file.exists():
            return False, "status.txt does not exist"

        try:
            status = status_file.read_text().strip()
            if not status:
                return False, "status.txt is empty"

            if status not in IntegrationProtocol.VALID_STATUSES:
                return False, f"Invalid status '{status}'. Must be one of: {', '.join(IntegrationProtocol.VALID_STATUSES)}"

            return True, None

        except Exception as e:
            return False, f"Cannot read status.txt: {e}"

    @staticmethod
    def validate_summary_file(summary_file: Path) -> tuple[bool, str | None]:
        """Validate summary markdown file.

        Args:
            summary_file: Path to {name}_summary.md

        Returns:
            Tuple of (valid, error_message)
            - valid: True if summary is valid
            - error_message: Error description (None if valid)

        Example:
            >>> from pathlib import Path
            >>> valid, error = IntegrationProtocol.validate_summary_file(
            ...     Path("LLM-CONTEXT/glintefy/review/scope/scope_summary.md")
            ... )
        """
        if not summary_file.exists():
            return False, f"{summary_file.name} does not exist"

        try:
            content = summary_file.read_text().strip()

            if not content:
                return False, f"{summary_file.name} is empty"

            if not content.startswith("#"):
                return False, f"{summary_file.name} should start with markdown heading (#)"

            return True, None

        except Exception as e:
            return False, f"Cannot read {summary_file.name}: {e}"

    @staticmethod
    def create_status_file(output_dir: Path, status: str) -> None:
        """Create status.txt with validation.

        Args:
            output_dir: Output directory
            status: Status value

        Raises:
            ValueError: If status is invalid
            IOError: If file cannot be written

        Example:
            >>> from pathlib import Path
            >>> IntegrationProtocol.create_status_file(
            ...     Path("output"),
            ...     "SUCCESS"
            ... )
        """
        if status not in IntegrationProtocol.VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of: {', '.join(IntegrationProtocol.VALID_STATUSES)}")

        output_dir.mkdir(parents=True, exist_ok=True)
        status_file = output_dir / "status.txt"

        try:
            status_file.write_text(status)
        except Exception as e:
            raise OSError(f"Failed to write status.txt: {e}") from e

    @staticmethod
    def create_summary_file(
        output_dir: Path,
        subagent_name: str,
        content: str,
    ) -> None:
        """Create summary markdown file with validation.

        Args:
            output_dir: Output directory
            subagent_name: Name of the sub-server
            content: Markdown content

        Raises:
            ValueError: If content is empty or not markdown
            IOError: If file cannot be written

        Example:
            >>> from pathlib import Path
            >>> IntegrationProtocol.create_summary_file(
            ...     Path("output"),
            ...     "scope",
            ...     "# Scope Analysis\\n\\nComplete!"
            ... )
        """
        if not content or not content.strip():
            raise ValueError("Summary content cannot be empty")

        if not content.strip().startswith("#"):
            raise ValueError("Summary must start with markdown heading (#)")

        output_dir.mkdir(parents=True, exist_ok=True)
        summary_file = output_dir / f"{subagent_name}_summary.md"

        try:
            summary_file.write_text(content)
        except Exception as e:
            raise OSError(f"Failed to write {subagent_name}_summary.md: {e}") from e

    @staticmethod
    def get_status(output_dir: Path) -> str | None:
        """Read status from status.txt.

        Args:
            output_dir: Sub-server output directory

        Returns:
            Status string, or None if file doesn't exist or is invalid

        Example:
            >>> from pathlib import Path
            >>> status = IntegrationProtocol.get_status(
            ...     Path("LLM-CONTEXT/glintefy/review/scope")
            ... )
            >>> print(status)
            SUCCESS
        """
        status_file = output_dir / "status.txt"
        if not status_file.exists():
            return None

        try:
            status = status_file.read_text().strip()
            if status in IntegrationProtocol.VALID_STATUSES:
                return status
            return None
        except Exception:
            return None

    @staticmethod
    def check_all_subservers(
        workspace: Path,
        subserver_names: list[str],
    ) -> dict[str, dict[str, bool | list[str]]]:
        """Check protocol compliance for multiple sub-servers.

        Args:
            workspace: Workspace directory (e.g., LLM-CONTEXT/glintefy/review/)
            subserver_names: List of sub-server names to check

        Returns:
            Dictionary mapping sub-server name to validation results:
            {
                "scope": {
                    "valid": True,
                    "violations": [],
                    "status": "SUCCESS"
                },
                ...
            }

        Example:
            >>> from pathlib import Path
            >>> results = IntegrationProtocol.check_all_subservers(
            ...     Path("LLM-CONTEXT/glintefy/review"),
            ...     ["scope", "quality", "security"]
            ... )
            >>> for name, result in results.items():
            ...     print(f"{name}: {'[OK]' if result['valid'] else '[FAIL]'}")
        """
        results = {}

        for name in subserver_names:
            output_dir = workspace / name
            valid, violations = IntegrationProtocol.validate_outputs(output_dir, name)
            status = IntegrationProtocol.get_status(output_dir)

            results[name] = {
                "valid": valid,
                "violations": violations,
                "status": status,
            }

        return results

    @staticmethod
    def wait_for_completion(
        output_dir: Path,
        timeout_seconds: int = 300,
        poll_interval: float = 1.0,
    ) -> tuple[bool, str | None]:
        """Wait for sub-server to complete (status != IN_PROGRESS).

        Args:
            output_dir: Sub-server output directory
            timeout_seconds: Maximum time to wait (default: 5 minutes)
            poll_interval: Seconds between status checks

        Returns:
            Tuple of (completed, final_status)
            - completed: True if sub-server finished before timeout
            - final_status: Final status value (or None if timeout)

        Example:
            >>> from pathlib import Path
            >>> completed, status = IntegrationProtocol.wait_for_completion(
            ...     Path("LLM-CONTEXT/glintefy/review/scope"),
            ...     timeout_seconds=60
            ... )
            >>> if completed:
            ...     print(f"Completed with status: {status}")
            ... else:
            ...     print("Timed out")
        """
        import time

        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            status = IntegrationProtocol.get_status(output_dir)

            if status and status != "IN_PROGRESS":
                return True, status

            time.sleep(poll_interval)

        # Timeout
        status = IntegrationProtocol.get_status(output_dir)
        return False, status
