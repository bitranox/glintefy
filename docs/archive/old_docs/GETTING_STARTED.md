# Getting Started: Implementation Checklist

## Quick Start - First Steps

### Prerequisites
- [ ] Python 3.13+ installed
- [ ] Git installed and configured
- [ ] Development environment ready (VS Code, PyCharm, etc.)
- [ ] Familiarity with MCP protocol basics

---

## Phase 1: Week 1 - Project Setup (Days 1-5)

### Day 1: Project Structure ✓

```bash
# 1. Create directory structure
mkdir -p src/glintefy/{servers,subservers/{review,fix,common},tools}
mkdir -p tests/{servers,subservers,integration}
mkdir -p docs/{api,guides,examples}

# 2. Create __init__.py files
touch src/glintefy/__init__.py
touch src/glintefy/servers/__init__.py
touch src/glintefy/subservers/__init__.py
touch src/glintefy/subservers/common/__init__.py
touch src/glintefy/subservers/review/__init__.py
touch src/glintefy/subservers/fix/__init__.py
touch src/glintefy/tools/__init__.py
touch tests/__init__.py

# 3. Create base files
touch src/glintefy/servers/base.py
touch src/glintefy/servers/review.py
touch src/glintefy/servers/fix.py
touch src/glintefy/subservers/base.py
touch src/glintefy/subservers/common/files.py
touch src/glintefy/subservers/common/git.py
touch src/glintefy/subservers/common/logging.py
touch src/glintefy/subservers/common/protocol.py
```

**Tasks**:
- [ ] Create directory structure
- [ ] Initialize all __init__.py files
- [ ] Create placeholder files for base classes

### Day 2: Dependencies Setup

```bash
# Update pyproject.toml
```

**Edit pyproject.toml**:
```toml
[project]
name = "glintefy"
version = "0.1.0"
description = "MCP servers for code review and fixing"
requires-python = ">=3.13"
dependencies = [
    "mcp>=1.0.0",
    "bandit>=1.7.0",
    "radon>=6.0.0",
    "pytest>=8.0.0",
    "pytest-cov>=5.0.0",
    "gitpython>=3.1.0",
    "pyyaml>=6.0",
    "jinja2>=3.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest-asyncio>=0.23.0",
    "pytest-mock>=3.12.0",
    "black>=24.0.0",
    "ruff>=0.1.0",
    "mypy>=1.8.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --cov=src/glintefy --cov-report=term-missing"

[tool.black]
line-length = 100
target-version = ['py313']

[tool.ruff]
line-length = 100
target-version = "py313"
```

**Tasks**:
- [ ] Update pyproject.toml with dependencies
- [ ] Run `make dev` or `pip install -e ".[dev]"`
- [ ] Verify all packages install correctly

### Day 3: Base Orchestrator Class

**File**: `src/glintefy/servers/base.py`

```python
"""Base orchestrator class for MCP servers."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import logging

# Note: Replace with actual MCP SDK imports
# from mcp import Server


class BaseOrchestrator(ABC):
    """Base class for MCP orchestrator servers."""

    def __init__(self, name: str, version: str, workspace: Optional[Path] = None):
        """Initialize orchestrator.

        Args:
            name: Server name (e.g., 'glintefy-review')
            version: Server version (e.g., '1.0.0')
            workspace: Workspace directory (default: LLM-CONTEXT/)
        """
        self.name = name
        self.version = version
        self.workspace = workspace or Path("LLM-CONTEXT")
        self.logger = self._setup_logger()

        # Will be initialized with actual MCP SDK
        # self.server = Server(name)

    def _setup_logger(self) -> logging.Logger:
        """Set up logging for orchestrator."""
        logger = logging.getLogger(self.name)
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    @abstractmethod
    def register_tools(self):
        """Register MCP tools. Implemented by subclasses."""
        pass

    @abstractmethod
    def register_resources(self):
        """Register MCP resources. Implemented by subclasses."""
        pass

    def initialize_workspace(self):
        """Create workspace directories."""
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Workspace initialized: {self.workspace}")

    async def run(self):
        """Start MCP server."""
        self.initialize_workspace()
        self.register_tools()
        self.register_resources()
        self.logger.info(f"{self.name} v{self.version} started")

        # Will be replaced with actual MCP SDK run
        # await self.server.run()
```

**Tasks**:
- [ ] Implement BaseOrchestrator class
- [ ] Add docstrings
- [ ] Create basic test in `tests/servers/test_base.py`

### Day 4: Base Sub-Server Class

**File**: `src/glintefy/subservers/base.py`

```python
"""Base sub-server class."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import json
from datetime import datetime


class SubServerResult:
    """Standard result format for sub-servers."""

    def __init__(
        self,
        status: str,
        summary: str,
        artifacts: dict[str, Path],
        metrics: Optional[dict] = None,
        errors: Optional[list[str]] = None
    ):
        """Initialize result.

        Args:
            status: "SUCCESS", "FAILED", or "PARTIAL"
            summary: Human-readable summary
            artifacts: Dict mapping artifact names to file paths
            metrics: Optional metrics dictionary
            errors: Optional list of error messages
        """
        self.status = status
        self.summary = summary
        self.artifacts = artifacts
        self.metrics = metrics or {}
        self.errors = errors or []
        self.timestamp = datetime.now().isoformat()


class BaseSubServer(ABC):
    """Base class for sub-servers."""

    def __init__(self, name: str, input_dir: Path, output_dir: Path):
        """Initialize sub-server.

        Args:
            name: Sub-server name (e.g., 'scope', 'quality')
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
        """
        pass

    @abstractmethod
    def execute(self) -> SubServerResult:
        """Execute sub-server logic.

        Returns:
            SubServerResult with status, summary, and artifacts
        """
        pass

    def save_status(self, status: str):
        """Save status.txt per integration protocol.

        Args:
            status: "SUCCESS", "FAILED", or "IN_PROGRESS"
        """
        status_file = self.output_dir / "status.txt"
        status_file.write_text(status)

    def save_summary(self, content: str):
        """Save summary report.

        Args:
            content: Markdown-formatted summary
        """
        summary_file = self.output_dir / f"{self.name}_summary.md"
        summary_file.write_text(content)

    def save_json(self, filename: str, data: dict):
        """Save JSON data.

        Args:
            filename: Output filename
            data: Dictionary to save
        """
        output_file = self.output_dir / filename
        output_file.write_text(json.dumps(data, indent=2))

    def run(self) -> SubServerResult:
        """Main entry point. Handles validation and execution.

        Returns:
            SubServerResult
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
                errors=[error_msg]
            )

        # Execute
        try:
            result = self.execute()
            self.save_status(result.status)
            self.save_summary(result.summary)
            return result
        except Exception as e:
            error_msg = f"Execution failed: {str(e)}"
            self.save_status("FAILED")
            self.save_summary(f"# {self.name} - FAILED\n\n{error_msg}")
            return SubServerResult(
                status="FAILED",
                summary=error_msg,
                artifacts={},
                errors=[error_msg]
            )
```

**Tasks**:
- [ ] Implement BaseSubServer class
- [ ] Implement SubServerResult class
- [ ] Add docstrings
- [ ] Create test in `tests/subservers/test_base.py`

### Day 5: File & Logging Utilities

**File**: `src/glintefy/subservers/common/files.py`

```python
"""File I/O utilities."""

from pathlib import Path
from typing import Optional


def read_file(path: Path) -> str:
    """Read file with error handling.

    Args:
        path: File path

    Returns:
        File contents as string

    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file cannot be read
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    try:
        return path.read_text()
    except Exception as e:
        raise IOError(f"Failed to read {path}: {e}")


def write_file(path: Path, content: str):
    """Write file with error handling.

    Args:
        path: File path
        content: Content to write

    Raises:
        IOError: If file cannot be written
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    except Exception as e:
        raise IOError(f"Failed to write {path}: {e}")


def ensure_dir(path: Path):
    """Ensure directory exists.

    Args:
        path: Directory path
    """
    path.mkdir(parents=True, exist_ok=True)


def find_files(
    root: Path,
    pattern: str = "*",
    exclude_patterns: Optional[list[str]] = None
) -> list[Path]:
    """Find files matching pattern.

    Args:
        root: Root directory to search
        pattern: Glob pattern (e.g., "*.py")
        exclude_patterns: Patterns to exclude

    Returns:
        List of matching file paths
    """
    exclude_patterns = exclude_patterns or [
        "*/node_modules/*",
        "*/.venv/*",
        "*/__pycache__/*",
        "*/dist/*",
        "*/build/*",
        "*/.git/*",
        "*/LLM-CONTEXT/*"
    ]

    files = []
    for file_path in root.rglob(pattern):
        if file_path.is_file():
            # Check exclusions
            excluded = any(
                file_path.match(excl) for excl in exclude_patterns
            )
            if not excluded:
                files.append(file_path)

    return sorted(files)
```

**Tasks**:
- [ ] Implement file utilities
- [ ] Add docstrings
- [ ] Create tests in `tests/subservers/common/test_files.py`

---

## After Week 1 Checklist

✓ **Structure Created**
- [ ] All directories exist
- [ ] All __init__.py files created
- [ ] pyproject.toml updated

✓ **Base Classes Implemented**
- [ ] BaseOrchestrator working
- [ ] BaseSubServer working
- [ ] SubServerResult working

✓ **Utilities Implemented**
- [ ] File I/O utilities working
- [ ] Logging utilities working
- [ ] Tests passing (>80% coverage)

✓ **Development Environment**
- [ ] Dependencies installed
- [ ] Tests can run (`make test`)
- [ ] Linting works (`ruff check`)
- [ ] Formatting works (`black .`)

---

## Next Steps

Once Week 1 is complete:

1. **Week 2**: Git operations & protocol validation
2. **Week 3**: First sub-servers (scope, deps, quality)
3. **Week 4**: Security sub-server & review orchestrator
4. Continue following the implementation plan...

---

## Development Commands

```bash
# Install dependencies
make dev

# Run tests
make test

# Run linting
ruff check src/

# Run formatting
black src/ tests/

# Type checking
mypy src/

# Run specific test
pytest tests/servers/test_base.py -v

# Check coverage
pytest --cov=src/glintefy --cov-report=html
```

---

## Questions & Support

- **Architecture**: See `docs/MCP_ARCHITECTURE.md`
- **Full Plan**: See `docs/IMPLEMENTATION_PLAN.md`
- **Issues**: Create GitHub issue
- **Discussions**: GitHub Discussions

---

**Ready to start?** Begin with Day 1 tasks above!
