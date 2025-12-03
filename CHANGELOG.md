# Changelog

All notable changes to this project will be documented in this file following
the [Keep a Changelog](https://keepachangelog.com/) format.

## [3.0.0] - 2025-12-03

### Changed
- **BREAKING**: Renamed project from `btx_fix_mcp` to `glintefy`
  - Package name: `btx_fix_mcp` → `glintefy`
  - CLI command: `btx_fix_mcp` → `glintefy`
  - Import: `from btx_fix_mcp` → `from glintefy`
  - Config file: `.btx-review.yaml` → `.glintefy.yaml`
  - Environment variables: `BTX_FIX_MCP___*` → `GLINTEFY___*`
  - Cache directory: `~/.cache/btx-fix-mcp/` → `~/.cache/glintefy/`
  - Config directory: `~/.config/btx-fix-mcp/` → `~/.config/glintefy/`

### Fixed
- Updated `mcp` dependency to `>=1.23.0` to fix CVE-2025-66416

## [2.0.1] - 2025-11-29

### Fixed
- Normalized paths to POSIX form before applying scope exclusion patterns, so Windows runs now correctly skip `.git`, `node_modules`, `__pycache__`, and `*.pyc` files when discovering review scope.

## [2.0.0] - 2025-11-29

### Changed
- Doubled all timeout values in `defaultconfig.toml` for reliability on slower systems
- Quality JSON outputs now sorted for prioritization:
  - `complexity.json`: descending by complexity (most complex first)
  - `cognitive.json`: descending by complexity (most complex first)
  - `maintainability.json`: ascending by MI (hardest to maintain first)
  - `halstead.json`: descending by effort (most difficult first)
  - `function_issues.json`: descending by value (worst first)

### Fixed
- RuffDiagnostic JSON serialization error - Pydantic models now properly converted via `model_dump()`
- Beartype check timeout increased to 120s with dedicated `beartype_check` config setting
- Deps scanner false positives - outdated packages now filtered to only project dependencies from `pyproject.toml`
- Scope exclusions now work for nested paths (e.g., `.mypy_cache/` files)
  - Added fallback directory-name matching when `Path.match()` glob patterns fail
  - Updated patterns from `**/.dir/*` to `**/.dir/**/*` format for recursive matching

### Added
- New exclusion patterns for IDE/CI directories:
  - `.claude/`, `.devcontainer/`, `.idea/`, `.vscode/`
  - `.github/`, `.qlty/`
  - `*.example`, `codecov.yml`, `.snyk`
- New timeout settings: `git_diff`, `beartype_check`

## [1.2.0] - 2025-11-28

### Changed
- Cache batch_screener now derives exclude patterns from `[review.scope].exclude_patterns` config instead of hardcoded list

### Fixed
- Nested iteration issues now sorted by nesting depth (descending) in JSON output - added `value` field to `PerformanceIssue`
- Report verdict now clearly distinguishes failed vs skipped subservers with specific reasons for each
- Removed unnecessary f-string prefix in `cli.py` (`config-path` command)

## [1.1.1] - 2025-11-28

### Added
- CLI `config-deploy` command: Deploy default configuration to app/host/user directories using lib_layered_config
- CLI `config-show` command: Display current effective configuration (merged from all sources)
- CLI `config-path` command: Show all configuration file locations and their status
- New `config_deploy.py` module wrapping lib_layered_config's deploy_config API
- Clear skip reasons in reports when subservers are not run (e.g., "Not in configured subservers", "Git not available")
- Code churn analysis now reports detailed skip reasons (e.g., "Not a git repository", "Git executable not found")

### Changed
- CLI QUICKSTART.md: Added quick reference table with all options and their default values
- CLI REFERENCE.md: Added "Permitted Values" column to all parameter tables
- CLI REFERENCE.md: Added detailed subserver values table for `review clean` command
- MCP TOOLS.md: Added complete parameter documentation with Type/Required/Default/Permitted columns

### Fixed
- Removed unused `shutil` import from `source_patcher.py`
- Removed emoji from scope.py git fallback notice (Windows `charmap` codec compatibility)
- Fixed environment variable format documentation (GLINTEFY___SECTION__KEY, not GLINTEFY_KEY)
- Added missing `venv/` to default exclude patterns (was only excluding `.venv/`)
- Added common cache/build directories to exclude: `.tox/`, `.nox/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `*.egg-info/`
- Cache batch_screener now excludes virtual environments and cache directories when scanning for function calls
- Synchronized fallback exclude patterns in `files.py` with `defaultconfig.toml`

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
- `glintefy review all` now works on non-git directories (falls back to full mode)
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
- Moved `profile_application.py` to `src/glintefy/scripts/` for proper packaging
- README badges now point to correct repository (glintefy)

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
- Bootstrap `glintefy`
