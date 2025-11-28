# Changelog

All notable changes to this project will be documented in this file following
the [Keep a Changelog](https://keepachangelog.com/) format.

## [1.1.1] - 2025-11-28

### Changed
- CLI QUICKSTART.md: Added quick reference table with all options and their default values

### Fixed
- Removed unused `shutil` import from `source_patcher.py`

## [1.1.0] - 2025-11-28

### Added
- Graceful fallback: `--mode git` automatically falls back to `--mode full` with a warning when not in a git repository
- Enhanced CLI documentation with Required/Default columns for all command options
- Context manager support for `SourcePatcher` class

### Changed
- Cache subserver no longer requires git - uses in-memory file backup instead of git branches
- `SourcePatcher` rewritten to use in-memory backup/restore for source modifications
- Emergency cleanup via `atexit` handler ensures files are restored even on crashes

### Fixed
- `btx_fix_mcp review all` now works on non-git directories (falls back to full mode)
- Code churn analysis gracefully skips when git is unavailable

## [1.0.0] - 2025-11-27

### Added
- Centralized configuration in `pyproject.toml`:
  - `[tool.clean]` section for clean patterns
  - `[tool.git]` section for default git remote
  - `[tool.scripts.test]` section for test runner settings (pytest-verbosity, coverage-report-file, src-path)
- Windows compatibility: All Unicode symbols replaced with ASCII equivalents
- Regex-based vulture output parsing to handle Windows paths with drive letters

### Changed
- **BREAKING**: Minimum Python version is now 3.13 (previously 3.9)
- Updated all dependencies to latest stable versions
- Modernized type hints to use Python 3.13+ syntax (`X | None` instead of `Optional[X]`)
- CI/CD now tests on Python 3.13, 3.14, and latest (3.x)
- Refactored `scripts/*.py` to reduce cyclomatic complexity (all functions now A/B grade)
- Moved `profile_application.py` to `src/btx_fix_mcp/scripts/` for proper packaging
- README badges now point to correct repository (btx_fix_mcp)

### Removed
- Dropped support for Python 3.9, 3.10, 3.11, and 3.12
- Removed `tomli` fallback (tomllib is built-in for Python 3.11+)
- Removed `typing.Optional` imports throughout codebase
- Removed all Unicode symbols (emojis, checkmarks, arrows) for Windows compatibility

### Fixed
- Windows encoding errors (`charmap` codec failures) by replacing Unicode with ASCII
- Windows path parsing in vulture dead code detection
- Windows `Path.home()` test failure when environment variables are cleared

## [0.1.0] - 2025-11-04
- Bootstrap `btx_fix_mcp`
