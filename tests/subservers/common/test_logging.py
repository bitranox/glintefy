"""Tests for logging utilities."""

import logging
import time

import pytest

from glintefy.subservers.common.logging import (
    LogContext,
    create_execution_log,
    debug_log,
    get_mcp_logger,
    log_config_loaded,
    log_debug,
    log_dict,
    log_error,
    log_error_detailed,
    log_file_list,
    log_function_call,
    log_function_result,
    log_metric,
    log_result,
    log_section,
    log_step,
    log_subprocess_call,
    log_subprocess_result,
    log_timing,
    log_tool_execution,
    setup_logger,
)


class TestSetupLogger:
    """Tests for setup_logger function."""

    def test_setup_basic_logger(self):
        """Test setting up basic logger."""
        logger = setup_logger("test_basic")

        assert logger.name == "test_basic"
        assert logger.level == logging.INFO
        assert len(logger.handlers) > 0

    def test_setup_logger_with_file(self, tmp_path):
        """Test setting up logger with file output."""
        log_file = tmp_path / "test.log"
        logger = setup_logger("test_file", log_file=log_file)

        logger.info("Test message")

        assert log_file.exists()
        content = log_file.read_text()
        assert "Test message" in content

    def test_setup_logger_custom_level(self):
        """Test setting up logger with custom level."""
        logger = setup_logger("test_level", level=logging.DEBUG)

        assert logger.level == logging.DEBUG

    def test_setup_logger_no_console(self, tmp_path):
        """Test setting up logger without console output."""
        log_file = tmp_path / "test.log"
        logger = setup_logger("test_no_console", log_file=log_file, console=False)

        # Only file handler should exist
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.FileHandler)

    def test_logger_removes_duplicate_handlers(self):
        """Test that setting up same logger twice doesn't duplicate handlers."""
        logger1 = setup_logger("test_duplicate")
        handler_count1 = len(logger1.handlers)

        logger2 = setup_logger("test_duplicate")
        handler_count2 = len(logger2.handlers)

        assert handler_count1 == handler_count2


class TestLogSection:
    """Tests for log_section function."""

    def test_log_section(self, caplog):
        """Test logging a section."""
        logger = setup_logger("test_section")

        with caplog.at_level(logging.INFO):
            log_section(logger, "TEST SECTION")

        # Should log separator and title
        assert "TEST SECTION" in caplog.text
        assert "=" in caplog.text

    def test_log_section_custom_level(self, caplog):
        """Test logging section with custom level."""
        logger = setup_logger("test_section_level")

        with caplog.at_level(logging.WARNING):
            log_section(logger, "WARNING SECTION", level=logging.WARNING)

        assert "WARNING SECTION" in caplog.text


class TestLogDict:
    """Tests for log_dict function."""

    def test_log_dict_with_title(self, caplog):
        """Test logging dictionary with title."""
        logger = setup_logger("test_dict")
        data = {"key1": "value1", "key2": "value2"}

        with caplog.at_level(logging.INFO):
            log_dict(logger, data, title="Test Data")

        assert "Test Data:" in caplog.text
        assert "key1: value1" in caplog.text
        assert "key2: value2" in caplog.text

    def test_log_dict_without_title(self, caplog):
        """Test logging dictionary without title."""
        logger = setup_logger("test_dict_no_title")
        data = {"count": 42}

        with caplog.at_level(logging.INFO):
            log_dict(logger, data)

        assert "count: 42" in caplog.text


class TestLogFileList:
    """Tests for log_file_list function."""

    def test_log_file_list_short(self, caplog):
        """Test logging short file list."""
        logger = setup_logger("test_files")
        files = ["file1.py", "file2.py", "file3.py"]

        with caplog.at_level(logging.INFO):
            log_file_list(logger, files, title="Modified Files")

        assert "Modified Files (3):" in caplog.text
        assert "file1.py" in caplog.text
        assert "file2.py" in caplog.text
        assert "file3.py" in caplog.text

    def test_log_file_list_truncated(self, caplog):
        """Test logging long file list with truncation."""
        logger = setup_logger("test_files_truncate")
        files = [f"file{i}.py" for i in range(15)]

        with caplog.at_level(logging.INFO):
            log_file_list(logger, files, title="Files", max_display=5)

        assert "Files (15):" in caplog.text
        assert "file0.py" in caplog.text
        assert "file4.py" in caplog.text
        assert "and 10 more" in caplog.text
        # Should not show all files
        assert "file14.py" not in caplog.text


class TestLogError:
    """Tests for log_error function."""

    def test_log_error_with_context(self, caplog):
        """Test logging error with context."""
        logger = setup_logger("test_error")
        error = ValueError("Invalid input")

        with caplog.at_level(logging.ERROR):
            log_error(logger, error, context="Validating inputs")

        assert "Error in Validating inputs" in caplog.text
        assert "ValueError" in caplog.text
        assert "Invalid input" in caplog.text

    def test_log_error_without_context(self, caplog):
        """Test logging error without context."""
        logger = setup_logger("test_error_no_context")
        error = RuntimeError("Something went wrong")

        with caplog.at_level(logging.ERROR):
            log_error(logger, error)

        assert "RuntimeError" in caplog.text
        assert "Something went wrong" in caplog.text


class TestLogStep:
    """Tests for log_step function."""

    def test_log_step(self, caplog):
        """Test logging numbered step."""
        logger = setup_logger("test_step")

        with caplog.at_level(logging.INFO):
            log_step(logger, 1, "Initialize configuration")

        assert "[Step 1]" in caplog.text
        assert "Initialize configuration" in caplog.text


class TestLogResult:
    """Tests for log_result function."""

    def test_log_result_success(self, caplog):
        """Test logging success result."""
        logger = setup_logger("test_result_success")

        with caplog.at_level(logging.INFO):
            log_result(logger, True, "All tests passed")

        assert "[OK]" in caplog.text
        assert "All tests passed" in caplog.text

    def test_log_result_failure(self, caplog):
        """Test logging failure result."""
        logger = setup_logger("test_result_failure")

        with caplog.at_level(logging.ERROR):
            log_result(logger, False, "2 tests failed")

        assert "[FAIL]" in caplog.text
        assert "2 tests failed" in caplog.text

    def test_log_result_custom_level(self, caplog):
        """Test logging result with custom level."""
        logger = setup_logger("test_result_custom")

        with caplog.at_level(logging.WARNING):
            log_result(logger, True, "Warning message", level=logging.WARNING)

        assert "[OK]" in caplog.text
        assert "Warning message" in caplog.text


class TestLogMetric:
    """Tests for log_metric function."""

    def test_log_metric_with_unit(self, caplog):
        """Test logging metric with unit."""
        logger = setup_logger("test_metric")

        with caplog.at_level(logging.INFO):
            log_metric(logger, "Files processed", 100, unit="files")

        assert "Files processed: 100 files" in caplog.text

    def test_log_metric_without_unit(self, caplog):
        """Test logging metric without unit."""
        logger = setup_logger("test_metric_no_unit")

        with caplog.at_level(logging.INFO):
            log_metric(logger, "Score", 95)

        assert "Score: 95" in caplog.text


class TestLogTiming:
    """Tests for log_timing function."""

    def test_log_timing(self, caplog):
        """Test logging operation timing."""
        logger = setup_logger("test_timing")

        with caplog.at_level(logging.INFO):
            log_timing(logger, "Data processing", 1.234)

        assert "Data processing took 1.23s" in caplog.text


class TestCreateExecutionLog:
    """Tests for create_execution_log function."""

    def test_create_execution_log(self, tmp_path):
        """Test creating timestamped execution log."""
        log_file = create_execution_log(tmp_path, "scope")

        assert log_file.parent == tmp_path
        assert log_file.name.startswith("scope_")
        assert log_file.name.endswith(".log")
        # Format: scope_YYYYMMDD_HHMMSS.log
        assert len(log_file.stem) == len("scope_20251121_100000")

    def test_create_execution_log_creates_directory(self, tmp_path):
        """Test that create_execution_log creates output directory."""
        nested_dir = tmp_path / "logs" / "subdir"
        log_file = create_execution_log(nested_dir, "test")

        assert nested_dir.exists()
        assert log_file.parent == nested_dir


class TestLogContext:
    """Tests for LogContext context manager."""

    def test_log_context_success(self, caplog):
        """Test LogContext for successful operation."""
        logger = setup_logger("test_context")

        with caplog.at_level(logging.INFO):
            with LogContext(logger, "Processing files"):
                time.sleep(0.01)

        assert "Starting: Processing files" in caplog.text
        assert "Completed: Processing files" in caplog.text
        # Should include timing
        assert "s)" in caplog.text

    def test_log_context_failure(self, caplog):
        """Test LogContext for failed operation."""
        logger = setup_logger("test_context_fail")

        with caplog.at_level(logging.INFO):
            try:
                with LogContext(logger, "Risky operation"):
                    raise ValueError("Something broke")
            except ValueError:
                pass

        assert "Starting: Risky operation" in caplog.text
        assert "Failed: Risky operation" in caplog.text
        assert "ValueError" in caplog.text
        assert "Something broke" in caplog.text

    def test_log_context_custom_level(self, caplog):
        """Test LogContext with custom log level."""
        logger = setup_logger("test_context_level", level=logging.DEBUG)

        with caplog.at_level(logging.DEBUG):
            with LogContext(logger, "Debug operation", level=logging.DEBUG):
                pass

        assert "Starting: Debug operation" in caplog.text
        assert "Completed: Debug operation" in caplog.text


class TestLoggerIntegration:
    """Integration tests for logging utilities."""

    def test_full_logging_workflow(self, tmp_path):
        """Test complete logging workflow."""
        log_file = tmp_path / "workflow.log"
        logger = setup_logger("workflow", log_file=log_file)

        # Use various logging functions
        log_section(logger, "WORKFLOW TEST")
        log_step(logger, 1, "Initialize")
        log_dict(logger, {"files": 10, "errors": 0}, title="Summary")
        log_file_list(logger, ["file1.py", "file2.py"], title="Files")
        log_metric(logger, "Duration", 1.5, unit="seconds")
        log_result(logger, True, "Workflow completed")

        # Verify log file contains all output
        content = log_file.read_text()
        assert "WORKFLOW TEST" in content
        assert "[Step 1]" in content
        assert "Summary:" in content
        assert "file1.py" in content
        assert "Duration: 1.5 seconds" in content
        assert "[OK] Workflow completed" in content


# =============================================================================
# MCP Server Debug Logging Tests
# =============================================================================


class TestGetMcpLogger:
    """Tests for get_mcp_logger function."""

    def test_get_mcp_logger_returns_logger(self):
        """Test that get_mcp_logger returns a logger."""
        logger = get_mcp_logger("test_mcp")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_mcp"

    def test_get_mcp_logger_default_name(self):
        """Test default logger name."""
        logger = get_mcp_logger()
        assert logger.name == "glintefy"

    def test_get_mcp_logger_debug_level(self):
        """Test that logger is set to DEBUG level."""
        logger = get_mcp_logger("test_mcp_debug")
        assert logger.level == logging.DEBUG

    def test_get_mcp_logger_has_handler(self):
        """Test that logger has a handler."""
        logger = get_mcp_logger("test_mcp_handler")
        assert len(logger.handlers) > 0

    def test_get_mcp_logger_no_duplicate_handlers(self):
        """Test that calling get_mcp_logger twice doesn't add duplicate handlers."""
        logger1 = get_mcp_logger("test_mcp_dup")
        handler_count = len(logger1.handlers)
        logger2 = get_mcp_logger("test_mcp_dup")
        assert len(logger2.handlers) == handler_count


class TestLogDebug:
    """Tests for log_debug function."""

    def test_log_debug_simple_message(self, capsys):
        """Test logging simple debug message."""
        logger = get_mcp_logger("test_debug_simple2")

        log_debug(logger, "Simple debug message")

        captured = capsys.readouterr()
        assert "Simple debug message" in captured.err

    def test_log_debug_with_context(self, capsys):
        """Test logging debug message with context."""
        logger = get_mcp_logger("test_debug_ctx2")

        log_debug(logger, "Processing file", path="/foo/bar.py", size=1024)

        captured = capsys.readouterr()
        assert "Processing file" in captured.err
        assert "path=" in captured.err
        assert "/foo/bar.py" in captured.err


class TestLogErrorDetailed:
    """Tests for log_error_detailed function."""

    def test_log_error_detailed_basic(self, capsys):
        """Test basic detailed error logging."""
        logger = get_mcp_logger("test_err_detail2")

        try:
            raise ValueError("Test error")
        except ValueError as e:
            log_error_detailed(logger, e)

        captured = capsys.readouterr()
        assert "ValueError" in captured.err
        assert "Test error" in captured.err

    def test_log_error_detailed_with_context(self, capsys):
        """Test detailed error logging with context."""
        logger = get_mcp_logger("test_err_ctx2")

        try:
            raise RuntimeError("Failed operation")
        except RuntimeError as e:
            log_error_detailed(logger, e, context={"operation": "file processing"}, file="test.py")

        captured = capsys.readouterr()
        assert "RuntimeError" in captured.err
        assert "Failed operation" in captured.err
        assert "operation=" in captured.err or "file processing" in captured.err

    def test_log_error_detailed_with_traceback(self, capsys):
        """Test that traceback is included by default."""
        logger = get_mcp_logger("test_err_tb2")

        try:
            raise KeyError("missing_key")
        except KeyError as e:
            log_error_detailed(logger, e, include_traceback=True)

        captured = capsys.readouterr()
        assert "KeyError" in captured.err


class TestLogFunctionCall:
    """Tests for log_function_call function."""

    def test_log_function_call_no_args(self, capsys):
        """Test logging function call without arguments."""
        logger = get_mcp_logger("test_func_call2")

        log_function_call(logger, "my_function")

        captured = capsys.readouterr()
        assert "CALL my_function()" in captured.err

    def test_log_function_call_with_args(self, capsys):
        """Test logging function call with arguments."""
        logger = get_mcp_logger("test_func_args2")

        log_function_call(logger, "process", args=("file.py",), kwargs={"verbose": True})

        captured = capsys.readouterr()
        assert "CALL process(" in captured.err
        assert "file.py" in captured.err

    def test_log_function_call_truncates_long_args(self, capsys):
        """Test that long arguments are truncated."""
        logger = get_mcp_logger("test_func_trunc2")

        long_string = "x" * 200

        log_function_call(logger, "process", args=(long_string,))

        captured = capsys.readouterr()
        # Long args get truncated to 50 chars
        assert len(captured.err) > 0
        assert "CALL process(" in captured.err


class TestLogFunctionResult:
    """Tests for log_function_result function."""

    def test_log_function_result(self, capsys):
        """Test logging function result."""
        logger = get_mcp_logger("test_func_result2")

        log_function_result(logger, "my_function", {"status": "ok"})

        captured = capsys.readouterr()
        assert "RETURN my_function" in captured.err

    def test_log_function_result_with_timing(self, capsys):
        """Test logging function result with timing."""
        logger = get_mcp_logger("test_func_timing2")

        log_function_result(logger, "fast_func", 42, duration_ms=1.5)

        captured = capsys.readouterr()
        assert "RETURN fast_func" in captured.err
        assert "1.5" in captured.err or "1.50" in captured.err


class TestDebugLogDecorator:
    """Tests for debug_log decorator."""

    def test_debug_log_decorator_logs_call(self, capsys):
        """Test that decorator logs function call."""
        logger = get_mcp_logger("test_decorator2")

        @debug_log(logger)
        def add(a, b):
            return a + b

        result = add(1, 2)

        assert result == 3
        captured = capsys.readouterr()
        assert "CALL" in captured.err
        assert "RETURN" in captured.err

    def test_debug_log_decorator_logs_error(self, capsys):
        """Test that decorator logs errors."""
        logger = get_mcp_logger("test_decorator_err2")

        @debug_log(logger)
        def failing_func():
            raise ValueError("Intentional error")

        with pytest.raises(ValueError):
            failing_func()

        captured = capsys.readouterr()
        assert "ERROR" in captured.err
        assert "ValueError" in captured.err


class TestLogConfigLoaded:
    """Tests for log_config_loaded function."""

    def test_log_config_loaded(self, capsys):
        """Test logging loaded configuration."""
        logger = get_mcp_logger("test_config2")

        log_config_loaded(logger, {"threshold": 10, "enabled": True}, source="test.toml")

        captured = capsys.readouterr()
        assert "Configuration loaded" in captured.err
        assert "test.toml" in captured.err

    def test_log_config_loaded_redacts_secrets(self, capsys):
        """Test that sensitive values are redacted."""
        logger = get_mcp_logger("test_config_secret2")

        log_config_loaded(logger, {"api_key": "secret123", "password": "hunter2"})

        captured = capsys.readouterr()
        assert "REDACTED" in captured.err
        assert "secret123" not in captured.err
        assert "hunter2" not in captured.err


class TestLogSubprocessCall:
    """Tests for log_subprocess_call function."""

    def test_log_subprocess_call(self, capsys):
        """Test logging subprocess call."""
        logger = get_mcp_logger("test_subprocess2")

        log_subprocess_call(logger, ["ruff", "check", "src/"], cwd="/project", timeout=60)

        captured = capsys.readouterr()
        assert "EXEC" in captured.err
        assert "ruff" in captured.err


class TestLogSubprocessResult:
    """Tests for log_subprocess_result function."""

    def test_log_subprocess_result_success(self, capsys):
        """Test logging successful subprocess result."""
        logger = get_mcp_logger("test_subprocess_ok2")

        log_subprocess_result(logger, ["ruff", "check"], 0, stdout="OK", duration_ms=100)

        captured = capsys.readouterr()
        assert "EXEC" in captured.err
        assert "OK" in captured.err

    def test_log_subprocess_result_failure(self, capsys):
        """Test logging failed subprocess result."""
        logger = get_mcp_logger("test_subprocess_fail2")

        log_subprocess_result(logger, ["ruff", "check"], 1, stderr="Error occurred")

        captured = capsys.readouterr()
        assert "FAILED" in captured.err


class TestLogToolExecution:
    """Tests for log_tool_execution function."""

    def test_log_tool_execution(self, capsys):
        """Test logging tool execution summary."""
        logger = get_mcp_logger("test_tool2")

        log_tool_execution(logger, "ruff", files_count=10, status="success", issues_found=3, duration_ms=150)

        captured = capsys.readouterr()
        assert "TOOL ruff" in captured.err
        assert "files=10" in captured.err
