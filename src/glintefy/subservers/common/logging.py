"""Logging utilities for sub-servers."""

import logging
import sys
import traceback
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def get_configured_log_level(start_dir: str | None = None) -> int:
    """Get the configured log level from config.

    Imports config lazily to avoid circular imports.

    Returns:
        int: Log level (10=DEBUG, 20=INFO, 30=WARNING, 40=ERROR, 50=CRITICAL)
    """
    try:
        from glintefy.config import get_log_level

        return get_log_level(start_dir)
    except ImportError:
        return logging.INFO


def setup_logger(
    name: str,
    log_file: Path | None = None,
    level: int = logging.INFO,
    console: bool = True,
) -> logging.Logger:
    """Set up a logger for a sub-server.

    Args:
        name: Logger name (usually sub-server name)
        log_file: Optional log file path
        level: Logging level (default: INFO)
        console: Whether to log to console (default: True)

    Returns:
        Configured logger instance

    Example:
        >>> from pathlib import Path
        >>> logger = setup_logger(
        ...     "scope",
        ...     log_file=Path("LLM-CONTEXT/glintefy/review/logs/scope.log")
        ... )
        >>> logger.info("Starting scope analysis")
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    logger.handlers = []

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def log_section(logger: logging.Logger, title: str, level: int = logging.INFO) -> None:
    """Log a section header for better readability.

    Args:
        logger: Logger instance
        title: Section title
        level: Logging level (default: INFO)

    Example:
        >>> logger = setup_logger("test")
        >>> log_section(logger, "STEP 1: Initialize")
        2025-11-21 10:00:00 - test - INFO - ===================================
        2025-11-21 10:00:00 - test - INFO - STEP 1: Initialize
        2025-11-21 10:00:00 - test - INFO - ===================================
    """
    separator = "=" * 60
    logger.log(level, separator)
    logger.log(level, title)
    logger.log(level, separator)


def log_dict(
    logger: logging.Logger,
    data: dict,
    title: str | None = None,
    level: int = logging.INFO,
) -> None:
    """Log a dictionary in a readable format.

    Args:
        logger: Logger instance
        data: Dictionary to log
        title: Optional title
        level: Logging level (default: INFO)

    Example:
        >>> logger = setup_logger("test")
        >>> log_dict(logger, {"files": 10, "errors": 0}, title="Results")
        2025-11-21 10:00:00 - test - INFO - Results:
        2025-11-21 10:00:00 - test - INFO -   files: 10
        2025-11-21 10:00:00 - test - INFO -   errors: 0
    """
    if title:
        logger.log(level, f"{title}:")

    for key, value in data.items():
        logger.log(level, f"  {key}: {value}")


def log_file_list(
    logger: logging.Logger,
    files: list[str],
    title: str = "Files",
    max_display: int = 10,
    level: int = logging.INFO,
) -> None:
    """Log a list of files with truncation for long lists.

    Args:
        logger: Logger instance
        files: List of file paths
        title: Section title (default: "Files")
        max_display: Maximum files to display before truncating
        level: Logging level (default: INFO)

    Example:
        >>> logger = setup_logger("test")
        >>> log_file_list(logger, ["file1.py", "file2.py"], title="Changed Files")
        2025-11-21 10:00:00 - test - INFO - Changed Files (2):
        2025-11-21 10:00:00 - test - INFO -   - file1.py
        2025-11-21 10:00:00 - test - INFO -   - file2.py
    """
    logger.log(level, f"{title} ({len(files)}):")

    for i, file in enumerate(files):
        if i >= max_display:
            remaining = len(files) - max_display
            logger.log(level, f"  ... and {remaining} more")
            break
        logger.log(level, f"  - {file}")


def log_error(
    logger: logging.Logger,
    error: Exception,
    context: str | None = None,
) -> None:
    """Log an error with context.

    Args:
        logger: Logger instance
        error: Exception to log
        context: Optional context description

    Example:
        >>> logger = setup_logger("test")
        >>> try:
        ...     raise ValueError("Invalid input")
        ... except ValueError as e:
        ...     log_error(logger, e, context="Validating inputs")
    """
    if context:
        logger.error(f"Error in {context}: {type(error).__name__}: {error}")
    else:
        logger.error(f"{type(error).__name__}: {error}")

    # Log exception traceback at DEBUG level
    logger.debug("Exception details:", exc_info=True)


def log_step(
    logger: logging.Logger,
    step_num: int,
    description: str,
    level: int = logging.INFO,
) -> None:
    """Log a numbered step.

    Args:
        logger: Logger instance
        step_num: Step number
        description: Step description
        level: Logging level (default: INFO)

    Example:
        >>> logger = setup_logger("test")
        >>> log_step(logger, 1, "Load configuration")
        2025-11-21 10:00:00 - test - INFO - [Step 1] Load configuration
    """
    logger.log(level, f"[Step {step_num}] {description}")


def log_result(
    logger: logging.Logger,
    success: bool,
    message: str,
    level: int | None = None,
) -> None:
    """Log a result with success/failure indicator.

    Args:
        logger: Logger instance
        success: Whether operation was successful
        message: Result message
        level: Optional logging level (defaults based on success)

    Example:
        >>> logger = setup_logger("test")
        >>> log_result(logger, True, "All tests passed")
        2025-11-21 10:00:00 - test - INFO - [OK] All tests passed
        >>> log_result(logger, False, "2 tests failed")
        2025-11-21 10:00:00 - test - ERROR - [FAIL] 2 tests failed
    """
    if level is None:
        level = logging.INFO if success else logging.ERROR

    symbol = "[OK]" if success else "[FAIL]"
    logger.log(level, f"{symbol} {message}")


def log_metric(
    logger: logging.Logger,
    name: str,
    value: float | str,
    unit: str | None = None,
    level: int = logging.INFO,
) -> None:
    """Log a metric value.

    Args:
        logger: Logger instance
        name: Metric name
        value: Metric value
        unit: Optional unit (e.g., "ms", "MB", "files")
        level: Logging level (default: INFO)

    Example:
        >>> logger = setup_logger("test")
        >>> log_metric(logger, "Files processed", 100, unit="files")
        2025-11-21 10:00:00 - test - INFO - Files processed: 100 files
    """
    if unit:
        logger.log(level, f"{name}: {value} {unit}")
    else:
        logger.log(level, f"{name}: {value}")


def log_timing(
    logger: logging.Logger,
    operation: str,
    seconds: float,
    level: int = logging.INFO,
) -> None:
    """Log operation timing.

    Args:
        logger: Logger instance
        operation: Operation description
        seconds: Duration in seconds
        level: Logging level (default: INFO)

    Example:
        >>> import time
        >>> logger = setup_logger("test")
        >>> start = time.time()
        >>> time.sleep(0.1)
        >>> log_timing(logger, "Data processing", time.time() - start)
        2025-11-21 10:00:00 - test - INFO - Data processing took 0.10s
    """
    logger.log(level, f"{operation} took {seconds:.2f}s")


def create_execution_log(
    output_dir: Path,
    subagent_name: str,
) -> Path:
    """Create a timestamped execution log file.

    Args:
        output_dir: Output directory
        subagent_name: Name of the sub-server

    Returns:
        Path to the created log file

    Example:
        >>> from pathlib import Path
        >>> log_file = create_execution_log(
        ...     Path("LLM-CONTEXT/glintefy/review/logs"),
        ...     "scope"
        ... )
        >>> print(log_file)
        LLM-CONTEXT/glintefy/review/logs/scope_20251121_100000.log
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = output_dir / f"{subagent_name}_{timestamp}.log"
    return log_file


class LogContext:
    """Context manager for logging a section with timing.

    Example:
        >>> logger = setup_logger("test")
        >>> with LogContext(logger, "Processing files"):
        ...     # Do work
        ...     pass
        2025-11-21 10:00:00 - test - INFO - Starting: Processing files
        2025-11-21 10:00:00 - test - INFO - Completed: Processing files (0.01s)
    """

    def __init__(
        self,
        logger: logging.Logger,
        operation: str,
        level: int = logging.INFO,
    ):
        """Initialize log context.

        Args:
            logger: Logger instance
            operation: Operation description
            level: Logging level
        """
        self.logger = logger
        self.operation = operation
        self.level = level
        self.start_time: float | None = None

    def __enter__(self):
        """Enter context."""
        import time

        self.start_time = time.time()
        self.logger.log(self.level, f"Starting: {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, _exc_tb):
        """Exit context."""
        import time

        if self.start_time is not None:
            duration = time.time() - self.start_time
            if exc_type is None:
                self.logger.log(
                    self.level,
                    f"Completed: {self.operation} ({duration:.2f}s)",
                )
            else:
                self.logger.error(f"Failed: {self.operation} ({duration:.2f}s) - {exc_type.__name__}: {exc_val}")
        return False  # Don't suppress exceptions


# =============================================================================
# MCP Server Logging Utilities (stderr only, no log files)
# =============================================================================


def get_mcp_logger(name: str = "glintefy") -> logging.Logger:
    """Get a logger configured for MCP server debugging.

    Logs to stderr only (no files) for MCP protocol compatibility.
    MCP uses stdout for protocol messages, so logs go to stderr.

    Args:
        name: Logger name (default: "glintefy")

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    return logger


def log_debug(
    logger: logging.Logger,
    message: str,
    context: dict[str, Any] | None = None,
    **extra: Any,
) -> None:
    """Log a debug message with optional context.

    Args:
        logger: Logger instance
        message: Debug message
        context: Optional context dictionary
        **extra: Additional key-value pairs to include
    """
    all_context = {**(context or {}), **extra}
    if all_context:
        context_str = " | ".join(f"{k}={v}" for k, v in all_context.items())
        logger.debug(f"{message} | {context_str}")
    else:
        logger.debug(message)


def log_error_detailed(
    logger: logging.Logger,
    error: Exception,
    context: dict[str, Any] | None = None,
    include_traceback: bool = True,
    **extra: Any,
) -> None:
    """Log an error with full details for debugging.

    Args:
        logger: Logger instance
        error: Exception to log
        context: Optional context dictionary
        include_traceback: Whether to include traceback (default: True)
        **extra: Additional key-value pairs to include
    """
    all_context = {**(context or {}), **extra}
    context_str = ""
    if all_context:
        context_str = " | " + " | ".join(f"{k}={v}" for k, v in all_context.items())

    logger.error(f"{type(error).__name__}: {error}{context_str}")

    if include_traceback:
        tb = traceback.format_exc()
        if tb and tb.strip() != "NoneType: None":
            for line in tb.strip().split("\n"):
                logger.error(f"  {line}")


def log_function_call(
    logger: logging.Logger,
    func_name: str,
    args: tuple[Any, ...] | None = None,
    kwargs: dict[str, Any] | None = None,
) -> None:
    """Log a function call with arguments.

    Args:
        logger: Logger instance
        func_name: Function name
        args: Positional arguments (truncated for display)
        kwargs: Keyword arguments (truncated for display)
    """
    args_str = ""
    if args:
        args_str = ", ".join(repr(a)[:50] for a in args[:5])
    if kwargs:
        kw_str = ", ".join(f"{k}={repr(v)[:30]}" for k, v in list(kwargs.items())[:5])
        args_str = f"{args_str}, {kw_str}" if args_str else kw_str
    logger.debug(f"CALL {func_name}({args_str})")


def log_function_result(
    logger: logging.Logger,
    func_name: str,
    result: Any,
    duration_ms: float | None = None,
) -> None:
    """Log a function result.

    Args:
        logger: Logger instance
        func_name: Function name
        result: Return value (truncated for display)
        duration_ms: Optional execution time in milliseconds
    """
    result_str = repr(result)[:100]
    timing = f" ({duration_ms:.1f}ms)" if duration_ms is not None else ""
    logger.debug(f"RETURN {func_name} -> {result_str}{timing}")


def debug_log(logger: logging.Logger) -> Callable[[F], F]:
    """Decorator to log function entry, exit, and errors.

    Args:
        logger: Logger to use for logging

    Returns:
        Decorator function
    """

    def decorator(func: F) -> F:
        """Wrap function with debug logging."""

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            """Execute function with logging."""
            import time

            start = time.perf_counter()
            log_function_call(logger, func.__name__, args, kwargs)
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start) * 1000
                log_function_result(logger, func.__name__, result, duration_ms)
                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start) * 1000
                log_error_detailed(
                    logger,
                    e,
                    context={"function": func.__name__, "duration_ms": f"{duration_ms:.1f}"},
                )
                raise

        return wrapper  # type: ignore[return-value]

    return decorator


def log_config_loaded(
    logger: logging.Logger,
    config: dict[str, Any],
    source: str = "config",
) -> None:
    """Log configuration values that were loaded (redacts secrets).

    Args:
        logger: Logger instance
        config: Configuration dictionary
        source: Source name for the config
    """
    sensitive_keys = {"password", "secret", "token", "key", "api_key", "auth"}

    def redact_value(key: str, value: Any) -> Any:
        """Redact sensitive values based on key name."""
        key_lower = key.lower()
        if any(s in key_lower for s in sensitive_keys):
            return "***REDACTED***"
        return value

    logger.debug(f"Configuration loaded from {source}:")
    for key, value in config.items():
        redacted = redact_value(key, value)
        logger.debug(f"  {key}={redacted}")


def log_subprocess_call(
    logger: logging.Logger,
    cmd: list[str] | str,
    cwd: str | Path | None = None,
    timeout: int | None = None,
) -> None:
    """Log a subprocess call before execution.

    Args:
        logger: Logger instance
        cmd: Command to execute
        cwd: Working directory
        timeout: Timeout in seconds
    """
    cmd_str = cmd if isinstance(cmd, str) else " ".join(cmd)
    extras = []
    if cwd:
        extras.append(f"cwd={cwd}")
    if timeout:
        extras.append(f"timeout={timeout}s")
    extra_str = f" | {' | '.join(extras)}" if extras else ""
    logger.debug(f"EXEC: {cmd_str}{extra_str}")


def log_subprocess_result(
    logger: logging.Logger,
    cmd: list[str] | str,
    returncode: int,
    stdout: str | None = None,
    stderr: str | None = None,
    duration_ms: float | None = None,
) -> None:
    """Log subprocess result after execution.

    Args:
        logger: Logger instance
        cmd: Command that was executed
        returncode: Exit code
        stdout: Standard output (truncated for display)
        stderr: Standard error (truncated for display)
        duration_ms: Execution time in milliseconds
    """
    cmd_name = cmd if isinstance(cmd, str) else cmd[0] if cmd else "unknown"
    timing = f" ({duration_ms:.1f}ms)" if duration_ms is not None else ""
    status = "OK" if returncode == 0 else f"FAILED(rc={returncode})"
    logger.debug(f"EXEC {cmd_name} {status}{timing}")

    if returncode != 0:
        if stdout:
            for line in stdout[:500].split("\n")[:5]:
                logger.debug(f"  stdout: {line}")
        if stderr:
            for line in stderr[:500].split("\n")[:5]:
                logger.debug(f"  stderr: {line}")


def log_tool_execution(
    logger: logging.Logger,
    tool_name: str,
    files_count: int,
    status: str,
    issues_found: int = 0,
    duration_ms: float | None = None,
) -> None:
    """Log analysis tool execution summary.

    Args:
        logger: Logger instance
        tool_name: Name of the analysis tool
        files_count: Number of files analyzed
        status: Execution status (e.g., "SUCCESS", "PARTIAL", "FAILED")
        issues_found: Number of issues found
        duration_ms: Execution time in milliseconds
    """
    timing = f" in {duration_ms:.1f}ms" if duration_ms is not None else ""
    logger.info(f"TOOL {tool_name}: {status} | files={files_count} | issues={issues_found}{timing}")
