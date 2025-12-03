"""CLI stories: every invocation a single beat."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from click.testing import CliRunner, Result

from glintefy import cli as cli_mod
from glintefy import __init__conf__


@pytest.mark.os_agnostic
def test_when_cli_runs_without_arguments_help_is_printed(
    monkeypatch: pytest.MonkeyPatch,
    cli_runner: CliRunner,
) -> None:
    """When CLI runs without arguments, help should be displayed."""
    calls: list[str] = []

    def remember() -> None:
        calls.append("called")

    monkeypatch.setattr(cli_mod, "noop_main", remember)

    result = cli_runner.invoke(cli_mod.cli, [])

    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert calls == []


@pytest.mark.os_agnostic
def test_when_traceback_is_requested_without_command_the_domain_runs(
    monkeypatch: pytest.MonkeyPatch,
    cli_runner: CliRunner,
) -> None:
    """When --traceback is provided without command, noop_main should run."""
    calls: list[str] = []

    def remember() -> None:
        calls.append("called")

    monkeypatch.setattr(cli_mod, "noop_main", remember)

    result = cli_runner.invoke(cli_mod.cli, ["--traceback"])

    assert result.exit_code == 0
    assert calls == ["called"]
    assert "Usage:" not in result.output


@pytest.mark.os_agnostic
def test_default_shows_traceback(
    capsys: pytest.CaptureFixture[str],
    strip_ansi: Callable[[str], str],
) -> None:
    """By default (no flags), full traceback should appear on errors."""
    # Call main without any flags
    exit_code = cli_mod.main(["fail"])

    # Should return non-zero exit code
    assert exit_code != 0

    # Should show traceback in output (default behavior)
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert "Traceback" in output


@pytest.mark.os_agnostic
def test_no_traceback_flag_suppresses_traceback(
    capsys: pytest.CaptureFixture[str],
    strip_ansi: Callable[[str], str],
) -> None:
    """When --no-traceback is used, only simple error message should appear."""
    # Call main with --no-traceback flag
    exit_code = cli_mod.main(["--no-traceback", "fail"])

    # Should return non-zero exit code
    assert exit_code != 0

    # Should NOT show full traceback, just simple error
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert "Error: RuntimeError: I should fail" in output
    assert "Traceback" not in output or output.count("Traceback") == 0


@pytest.mark.os_agnostic
def test_when_hello_is_invoked_the_cli_smiles(cli_runner: CliRunner) -> None:
    """Hello command should output the canonical greeting."""
    result: Result = cli_runner.invoke(cli_mod.cli, ["hello"])

    assert result.exit_code == 0
    assert result.output == "Hello World\n"


@pytest.mark.os_agnostic
def test_when_fail_is_invoked_the_cli_raises(cli_runner: CliRunner) -> None:
    """Fail command should raise RuntimeError."""
    result: Result = cli_runner.invoke(cli_mod.cli, ["fail"])

    assert result.exit_code != 0
    assert isinstance(result.exception, RuntimeError)


@pytest.mark.os_agnostic
def test_when_info_is_invoked_the_metadata_is_displayed(cli_runner: CliRunner) -> None:
    """Info command should display package metadata."""
    result: Result = cli_runner.invoke(cli_mod.cli, ["info"])

    assert result.exit_code == 0
    assert f"Info for {__init__conf__.name}:" in result.output
    assert __init__conf__.version in result.output


@pytest.mark.os_agnostic
def test_when_an_unknown_command_is_used_a_helpful_error_appears(cli_runner: CliRunner) -> None:
    """Unknown commands should produce a helpful error message."""
    result: Result = cli_runner.invoke(cli_mod.cli, ["does-not-exist"])

    assert result.exit_code != 0
    assert "No such command" in result.output


@pytest.mark.os_agnostic
def test_main_returns_zero_on_success() -> None:
    """Main should return 0 for successful commands."""
    exit_code = cli_mod.main(["hello"])
    assert exit_code == 0


@pytest.mark.os_agnostic
def test_main_returns_nonzero_on_failure() -> None:
    """Main should return non-zero for failed commands."""
    exit_code = cli_mod.main(["fail"])
    assert exit_code != 0


@pytest.mark.os_agnostic
def test_version_option_displays_version(cli_runner: CliRunner) -> None:
    """--version should display the package version."""
    result = cli_runner.invoke(cli_mod.cli, ["--version"])

    assert result.exit_code == 0
    assert __init__conf__.version in result.output
    assert __init__conf__.shell_command in result.output


@pytest.mark.os_agnostic
def test_help_option_displays_help(cli_runner: CliRunner) -> None:
    """--help should display usage information."""
    result = cli_runner.invoke(cli_mod.cli, ["--help"])

    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "--traceback" in result.output


# =============================================================================
# Review Command Tests
# =============================================================================


class TestReviewCommands:
    """Tests for review CLI commands."""

    def test_review_group_help(self, cli_runner: CliRunner) -> None:
        """Review group should display available subcommands."""
        result = cli_runner.invoke(cli_mod.cli, ["review", "--help"])

        assert result.exit_code == 0
        assert "scope" in result.output
        assert "quality" in result.output
        assert "security" in result.output

    def test_review_scope_command(self, cli_runner: CliRunner, tmp_path) -> None:
        """Review scope command should execute without error."""
        from unittest.mock import patch

        mock_result = {"status": "SUCCESS", "summary": "# Scope Analysis\n\nTest summary."}

        with patch("glintefy.servers.review.ReviewMCPServer") as mock_server:
            mock_server.return_value.run_scope.return_value = mock_result

            result = cli_runner.invoke(
                cli_mod.cli,
                ["review", "--repo", str(tmp_path), "scope", "--mode", "full"],
            )

            assert result.exit_code == 0
            mock_server.return_value.run_scope.assert_called_once_with(mode="full")

    def test_review_quality_command(self, cli_runner: CliRunner, tmp_path) -> None:
        """Review quality command should pass options correctly."""
        from unittest.mock import patch

        mock_result = {"status": "SUCCESS", "summary": "# Quality Analysis\n\nTest summary."}

        with patch("glintefy.servers.review.ReviewMCPServer") as mock_server:
            mock_server.return_value.run_quality.return_value = mock_result

            result = cli_runner.invoke(
                cli_mod.cli,
                ["review", "--repo", str(tmp_path), "quality", "-c", "15", "-m", "25"],
            )

            assert result.exit_code == 0
            mock_server.return_value.run_quality.assert_called_once_with(
                complexity_threshold=15,
                maintainability_threshold=25,
            )

    def test_review_security_command(self, cli_runner: CliRunner, tmp_path) -> None:
        """Review security command should pass thresholds correctly."""
        from unittest.mock import patch

        mock_result = {"status": "SUCCESS", "summary": "# Security Analysis\n\nTest summary."}

        with patch("glintefy.servers.review.ReviewMCPServer") as mock_server:
            mock_server.return_value.run_security.return_value = mock_result

            result = cli_runner.invoke(
                cli_mod.cli,
                ["review", "--repo", str(tmp_path), "security", "-s", "high", "-c", "medium"],
            )

            assert result.exit_code == 0
            mock_server.return_value.run_security.assert_called_once_with(
                severity_threshold="high",
                confidence_threshold="medium",
            )

    def test_review_deps_command(self, cli_runner: CliRunner, tmp_path) -> None:
        """Review deps command should pass flags correctly."""
        from unittest.mock import patch

        mock_result = {"status": "SUCCESS", "summary": "# Deps Analysis\n\nTest summary."}

        with patch("glintefy.servers.review.ReviewMCPServer") as mock_server:
            mock_server.return_value.run_deps.return_value = mock_result

            result = cli_runner.invoke(
                cli_mod.cli,
                ["review", "--repo", str(tmp_path), "deps", "--no-vulnerabilities"],
            )

            assert result.exit_code == 0
            mock_server.return_value.run_deps.assert_called_once_with(
                scan_vulnerabilities=False,
                check_licenses=True,
                check_outdated=True,
            )

    def test_review_docs_command(self, cli_runner: CliRunner, tmp_path) -> None:
        """Review docs command should pass coverage option."""
        from unittest.mock import patch

        mock_result = {"status": "SUCCESS", "summary": "# Docs Analysis\n\nTest summary."}

        with patch("glintefy.servers.review.ReviewMCPServer") as mock_server:
            mock_server.return_value.run_docs.return_value = mock_result

            result = cli_runner.invoke(
                cli_mod.cli,
                ["review", "--repo", str(tmp_path), "docs", "--min-coverage", "90"],
            )

            assert result.exit_code == 0
            mock_server.return_value.run_docs.assert_called_once_with(min_coverage=90)

    def test_review_perf_command(self, cli_runner: CliRunner, tmp_path) -> None:
        """Review perf command should pass profiling flag."""
        from unittest.mock import patch

        mock_result = {"status": "SUCCESS", "summary": "# Perf Analysis\n\nTest summary."}

        with patch("glintefy.servers.review.ReviewMCPServer") as mock_server:
            mock_server.return_value.run_perf.return_value = mock_result

            result = cli_runner.invoke(
                cli_mod.cli,
                ["review", "--repo", str(tmp_path), "perf", "--no-profiling"],
            )

            assert result.exit_code == 0
            mock_server.return_value.run_perf.assert_called_once_with(run_profiling=False)

    def test_review_report_command(self, cli_runner: CliRunner, tmp_path) -> None:
        """Review report command should generate report."""
        from unittest.mock import patch

        mock_result = {"status": "SUCCESS", "summary": "# Report\n\nConsolidated report."}

        with patch("glintefy.servers.review.ReviewMCPServer") as mock_server:
            mock_server.return_value.run_report.return_value = mock_result

            result = cli_runner.invoke(
                cli_mod.cli,
                ["review", "--repo", str(tmp_path), "report"],
            )

            assert result.exit_code == 0
            mock_server.return_value.run_report.assert_called_once()

    def test_review_all_command(self, cli_runner: CliRunner, tmp_path) -> None:
        """Review all command should run all analyses."""
        from unittest.mock import patch

        mock_result = {"status": "SUCCESS", "summary": "# Full Analysis\n\nAll analyses complete."}

        with patch("glintefy.servers.review.ReviewMCPServer") as mock_server:
            mock_server.return_value.run_all.return_value = mock_result

            result = cli_runner.invoke(
                cli_mod.cli,
                ["review", "--repo", str(tmp_path), "all"],
            )

            assert result.exit_code == 0
            mock_server.return_value.run_all.assert_called_once()

    def test_review_clean_command_dry_run(self, cli_runner: CliRunner, tmp_path) -> None:
        """Review clean command should show what would be deleted in dry run."""
        # Create test directory structure
        review_dir = tmp_path / "LLM-CONTEXT" / "glintefy" / "review"
        scope_dir = review_dir / "scope"
        scope_dir.mkdir(parents=True)
        (scope_dir / "files_to_review.txt").write_text("test.py\n")

        result = cli_runner.invoke(
            cli_mod.cli,
            ["review", "--repo", str(tmp_path), "clean", "--dry-run"],
        )

        assert result.exit_code == 0
        assert "Would delete" in result.output
        # Directory should still exist after dry run
        assert scope_dir.exists()

    def test_review_clean_command_deletes_directory(self, cli_runner: CliRunner, tmp_path) -> None:
        """Review clean command should delete the review directory."""
        # Create test directory structure
        review_dir = tmp_path / "LLM-CONTEXT" / "glintefy" / "review"
        scope_dir = review_dir / "scope"
        scope_dir.mkdir(parents=True)
        (scope_dir / "files_to_review.txt").write_text("test.py\n")

        result = cli_runner.invoke(
            cli_mod.cli,
            ["review", "--repo", str(tmp_path), "clean"],
        )

        assert result.exit_code == 0
        assert "Deleted" in result.output
        # Directory should be deleted
        assert not review_dir.exists()

    def test_review_clean_command_specific_subserver(self, cli_runner: CliRunner, tmp_path) -> None:
        """Review clean command should delete only specific subserver directory."""
        # Create test directory structure
        review_dir = tmp_path / "LLM-CONTEXT" / "glintefy" / "review"
        scope_dir = review_dir / "scope"
        quality_dir = review_dir / "quality"
        scope_dir.mkdir(parents=True)
        quality_dir.mkdir(parents=True)
        (scope_dir / "files_to_review.txt").write_text("test.py\n")
        (quality_dir / "results.json").write_text("{}\n")

        result = cli_runner.invoke(
            cli_mod.cli,
            ["review", "--repo", str(tmp_path), "clean", "-s", "scope"],
        )

        assert result.exit_code == 0
        # Only scope should be deleted
        assert not scope_dir.exists()
        # Quality should still exist
        assert quality_dir.exists()

    def test_review_clean_command_profile_only(self, cli_runner: CliRunner, tmp_path) -> None:
        """Review clean command with -s profile should only delete profile file."""
        # Create test directory structure
        review_dir = tmp_path / "LLM-CONTEXT" / "glintefy" / "review"
        perf_dir = review_dir / "perf"
        perf_dir.mkdir(parents=True)
        profile_file = perf_dir / "test_profile.prof"
        profile_file.write_text("profile data")
        other_file = perf_dir / "other.json"
        other_file.write_text("{}")

        result = cli_runner.invoke(
            cli_mod.cli,
            ["review", "--repo", str(tmp_path), "clean", "-s", "profile"],
        )

        assert result.exit_code == 0
        # Profile should be deleted
        assert not profile_file.exists()
        # Other files should remain
        assert other_file.exists()
