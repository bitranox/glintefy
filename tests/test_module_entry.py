"""Module entry stories ensuring `python -m` mirrors the CLI."""

from __future__ import annotations

from collections.abc import Callable
import runpy
import sys

import pytest

from glintefy import cli as cli_mod


@pytest.mark.os_agnostic
def test_when_module_entry_returns_zero_the_story_matches_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    """Module entry should successfully execute hello command."""
    monkeypatch.setattr(sys, "argv", ["glintefy", "hello"], raising=False)

    with pytest.raises(SystemExit) as exc:
        runpy.run_module("glintefy.__main__", run_name="__main__")

    assert exc.value.code == 0


@pytest.mark.os_agnostic
def test_when_module_entry_raises_the_exit_helpers_format_the_song(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Module entry should handle exceptions and return non-zero exit code."""
    monkeypatch.setattr(sys, "argv", ["glintefy", "fail"], raising=False)

    with pytest.raises(SystemExit) as exc:
        runpy.run_module("glintefy.__main__", run_name="__main__")

    assert exc.value.code != 0
    assert exc.value.code is not None


@pytest.mark.os_agnostic
def test_when_traceback_flag_is_used_via_module_entry_the_full_poem_is_printed(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    strip_ansi: Callable[[str], str],
) -> None:
    """Module entry with --traceback should show full traceback."""
    monkeypatch.setattr(sys, "argv", ["glintefy", "--traceback", "fail"])

    with pytest.raises(SystemExit) as exc:
        runpy.run_module("glintefy.__main__", run_name="__main__")

    captured = capsys.readouterr()
    plain_out = strip_ansi(captured.out)
    plain_err = strip_ansi(captured.err)
    combined = plain_out + plain_err

    assert exc.value.code != 0
    # With rich traceback we should see error information
    assert "RuntimeError" in combined or "I should fail" in combined


@pytest.mark.os_agnostic
def test_when_module_entry_imports_cli_the_alias_stays_intact() -> None:
    """CLI name should be accessible."""
    assert hasattr(cli_mod.cli, "name")
