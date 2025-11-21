# Changelog

All notable changes to this project will be documented in this file following
the [Keep a Changelog](https://keepachangelog.com/) format.

## [Unreleased]

### Changed
- **BREAKING**: Minimum Python version is now 3.13 (previously 3.9)
- Updated all dependencies to latest stable versions
- Modernized type hints to use Python 3.13+ syntax (`X | None` instead of `Optional[X]`)
- CI/CD now tests on Python 3.13, 3.14, and latest (3.x)

### Removed
- Dropped support for Python 3.9, 3.10, 3.11, and 3.12
- Removed `tomli` fallback (tomllib is built-in for Python 3.11+)
- Removed `typing.Optional` imports throughout codebase

## [1.0.0] - 2025-11-04
- Bootstrap `btx_fix_mcp`
