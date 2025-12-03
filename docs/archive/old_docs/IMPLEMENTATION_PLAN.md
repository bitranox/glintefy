# Implementation Plan: glintefy and glintefy-review MCP Servers

## Overview

This plan outlines the step-by-step implementation of the MCP server architecture for glintefy and glintefy-review, transforming the existing bash command system into a maintainable, testable Python-based MCP server ecosystem.

**Total Timeline**: 10 weeks (50 working days)
**Team Size**: 1-2 developers
**Risk Level**: Medium (new protocol, complex migration)

---

## Phase 1: Foundation & Infrastructure (Weeks 1-2)

### Week 1: Project Setup & MCP Framework

#### Day 1-2: Project Structure
- [ ] Set up Python package structure
  ```
  src/glintefy/
  ├── __init__.py
  ├── servers/
  │   ├── __init__.py
  │   ├── review.py          # glintefy-review orchestrator
  │   ├── fix.py             # glintefy orchestrator
  │   └── base.py            # Base orchestrator class
  ├── subservers/
  │   ├── __init__.py
  │   ├── base.py            # Base sub-server class
  │   └── common/            # Shared utilities
  │       ├── __init__.py
  │       ├── files.py       # File I/O utilities
  │       ├── git.py         # Git operations
  │       ├── logging.py     # Logging utilities
  │       └── protocol.py    # Integration protocol
  └── tools/
      ├── __init__.py
      └── analysis.py        # Analysis tools (AST, regex, etc.)
  ```

- [ ] Update `pyproject.toml` with dependencies:
  ```toml
  [project]
  dependencies = [
      "mcp>=1.0.0",           # MCP SDK
      "bandit>=1.7.0",        # Security scanning
      "radon>=6.0.0",         # Complexity metrics
      "pytest>=8.0.0",        # Testing
      "pytest-cov>=5.0.0",    # Coverage
      "gitpython>=3.1.0",     # Git operations
      "pyyaml>=6.0",          # YAML parsing
      "jinja2>=3.1.0",        # Template rendering
  ]
  ```

- [ ] Set up development environment
  ```bash
  make dev  # Install with dev extras
  ```

**Deliverables**:
- ✓ Package structure created
- ✓ Dependencies installed
- ✓ Dev environment working

#### Day 3-4: MCP Base Classes

- [ ] Implement `BaseOrchestrator` class
  ```python
  # src/glintefy/servers/base.py
  class BaseOrchestrator:
      """Base class for MCP orchestrator servers."""

      def __init__(self, name: str, version: str):
          self.name = name
          self.version = version
          self.server = Server(name)

      async def run(self):
          """Start MCP server."""
          pass

      def register_tools(self):
          """Register MCP tools."""
          pass

      def register_resources(self):
          """Register MCP resources."""
          pass
  ```

- [ ] Implement `BaseSubServer` class
  ```python
  # src/glintefy/subservers/base.py
  class BaseSubServer:
      """Base class for sub-servers."""

      def __init__(self, name: str, input_dir: str, output_dir: str):
          self.name = name
          self.input_dir = Path(input_dir)
          self.output_dir = Path(output_dir)

      def execute(self) -> dict:
          """Execute sub-server logic."""
          pass

      def validate_inputs(self) -> bool:
          """Validate required inputs exist."""
          pass

      def save_status(self, status: str):
          """Save status.txt per integration protocol."""
          pass

      def save_summary(self, content: str):
          """Save summary report."""
          pass
  ```

**Deliverables**:
- ✓ BaseOrchestrator implemented
- ✓ BaseSubServer implemented
- ✓ Basic tests passing

#### Day 5: File I/O & Utilities

- [ ] Implement file utilities (`src/glintefy/subservers/common/files.py`)
  - Directory creation/validation
  - File reading/writing with error handling
  - Glob pattern matching
  - File filtering (exclude build artifacts, etc.)

- [ ] Implement logging utilities (`src/glintefy/subservers/common/logging.py`)
  - Structured logging
  - Log file management
  - Timestamp formatting

- [ ] Write unit tests for utilities

**Deliverables**:
- ✓ File utilities tested
- ✓ Logging utilities tested
- ✓ 90%+ code coverage

### Week 2: Integration Protocol & Git Operations

#### Day 6-7: Integration Protocol Implementation

- [ ] Implement protocol validation (`src/glintefy/subservers/common/protocol.py`)
  ```python
  class IntegrationProtocol:
      """Validates subagent integration protocol compliance."""

      @staticmethod
      def validate_outputs(output_dir: Path, subagent_name: str) -> dict:
          """Check all required files exist."""
          required = [
              "status.txt",
              f"{subagent_name}_summary.md"
          ]
          # Check existence, validate status format
          pass

      @staticmethod
      def create_status_file(output_dir: Path, status: str):
          """Create status.txt with validation."""
          pass
  ```

- [ ] Add protocol tests
- [ ] Document protocol requirements

**Deliverables**:
- ✓ Protocol validator implemented
- ✓ Protocol tests passing
- ✓ Documentation updated

#### Day 8-9: Git Operations

- [ ] Implement git utilities (`src/glintefy/subservers/common/git.py`)
  ```python
  class GitOperations:
      """Git operations for fix workflow."""

      @staticmethod
      def is_git_repo() -> bool:
          """Check if in git repository."""
          pass

      @staticmethod
      def create_commit(files: list[str], message: str) -> str:
          """Create git commit, return hash."""
          pass

      @staticmethod
      def revert_changes(files: list[str]):
          """Revert file changes."""
          pass

      @staticmethod
      def get_diff(commit_range: str = "HEAD") -> str:
          """Get git diff."""
          pass
  ```

- [ ] Add git operation tests (mock git repo)
- [ ] Handle edge cases (not in repo, detached HEAD, etc.)

**Deliverables**:
- ✓ Git utilities implemented
- ✓ Tests with mock git repo
- ✓ Error handling complete

#### Day 10: Testing & Documentation

- [ ] Write integration tests for base classes
- [ ] Document base class APIs
- [ ] Create developer guide for adding new sub-servers
- [ ] Phase 1 review and cleanup

**Deliverables**:
- ✓ Phase 1 complete
- ✓ All tests passing
- ✓ Documentation complete
- ✓ Ready for Phase 2

---

## Phase 2: Review Server Implementation (Weeks 3-4)

### Week 3: Core Review Sub-servers

#### Day 11-12: Scope Sub-server

- [ ] Port `bx_review_anal_sub_scope.md` to Python
  ```python
  # src/glintefy/subservers/review/scope.py
  class ScopeSubServer(BaseSubServer):
      def execute(self) -> dict:
          # 1. Detect git repo
          # 2. Parse user intent
          # 3. Generate file list
          # 4. Categorize files
          # 5. Optional: Priority scoring (>500 files)
          pass
  ```

- [ ] Implement priority scoring algorithm
- [ ] Add tests for different scope scenarios
- [ ] Test with real repositories

**Deliverables**:
- ✓ Scope sub-server functional
- ✓ Priority scoring working
- ✓ Tests passing

#### Day 13-14: Dependencies Sub-server

- [ ] Port `bx_review_anal_sub_deps.md` to Python
  ```python
  # src/glintefy/subservers/review/deps.py
  class DepsSubServer(BaseSubServer):
      def execute(self) -> dict:
          # 1. Detect project type (Python, Node, Ruby, etc.)
          # 2. List outdated packages
          # 3. Update to latest stable
          # 4. Run tests
          # 5. Report results
          pass
  ```

- [ ] Support multiple package managers (pip, npm, cargo, go)
- [ ] Add dependency update tests
- [ ] Handle breaking changes gracefully

**Deliverables**:
- ✓ Deps sub-server functional
- ✓ Multi-language support
- ✓ Tests passing

#### Day 15: Quality Sub-server

- [ ] Port `bx_review_anal_sub_quality.md` to Python
  ```python
  # src/glintefy/subservers/review/quality.py
  class QualitySubServer(BaseSubServer):
      def execute(self) -> dict:
          # 1. Run radon complexity analysis
          # 2. Detect long functions (>50 lines)
          # 3. Find code duplication
          # 4. Check style issues
          # 5. Generate recommendations
          pass
  ```

- [ ] Integrate radon for complexity metrics
- [ ] Implement duplication detector
- [ ] Add quality tests

**Deliverables**:
- ✓ Quality sub-server functional
- ✓ Metrics accurate
- ✓ Tests passing

### Week 4: Security & Performance Sub-servers

#### Day 16-17: Security Sub-server

- [ ] Port `bx_review_anal_sub_security.md` to Python
  ```python
  # src/glintefy/subservers/review/security.py
  class SecuritySubServer(BaseSubServer):
      def execute(self) -> dict:
          # 1. Run bandit for Python
          # 2. Run npm audit for Node
          # 3. Check for hardcoded secrets
          # 4. Scan for common vulnerabilities
          # 5. Generate security report
          pass
  ```

- [ ] Integrate bandit security scanner
- [ ] Implement secret detection (regex patterns)
- [ ] Add vulnerability tests

**Deliverables**:
- ✓ Security sub-server functional
- ✓ Bandit integration working
- ✓ Secret detection working
- ✓ Tests passing

#### Day 18-19: glintefy-review Orchestrator

- [ ] Implement glintefy-review orchestrator
  ```python
  # src/glintefy/servers/review.py
  class ReviewOrchestrator(BaseOrchestrator):
      def register_tools(self):
          @self.server.call_tool()
          async def review_codebase(priority: str, parallel: bool):
              # 1. Initialize environment
              # 2. Run scope analysis
              # 3. Launch sub-servers (parallel if requested)
              # 4. Wait for completion
              # 5. Compile report
              # 6. Return results
              pass

          @self.server.call_tool()
          async def review_changes(scope: str, custom_spec: str):
              pass

          @self.server.call_tool()
          async def review_files(files: list, patterns: list):
              pass
  ```

- [ ] Implement parallel sub-server execution
- [ ] Add orchestrator tests
- [ ] Test end-to-end review workflow

**Deliverables**:
- ✓ glintefy-review orchestrator functional
- ✓ Parallel execution working
- ✓ End-to-end tests passing

#### Day 20: Review Server Testing & Polish

- [ ] Integration tests for full review workflow
- [ ] Performance testing (large codebases)
- [ ] Error handling and edge cases
- [ ] Documentation updates
- [ ] Phase 2 review and cleanup

**Deliverables**:
- ✓ Phase 2 complete
- ✓ glintefy-review server production-ready
- ✓ All tests passing
- ✓ Documentation complete

---

## Phase 3: Fix Server Implementation (Weeks 5-6)

### Week 5: Plan & Critical Fix Sub-servers

#### Day 21-22: Plan Sub-server

- [ ] Port `bx_fix_anal_sub_plan.md` to Python
  ```python
  # src/glintefy/subservers/fix/plan.py
  class PlanSubServer(BaseSubServer):
      def execute(self) -> dict:
          # 1. Read review report
          # 2. Extract and categorize issues
          # 3. Create fixing order
          # 4. Define fix strategies for each issue
          # 5. Estimate effort
          # 6. Generate comprehensive plan
          pass

      def add_fix_strategies(self, issues: list) -> list:
          """Add actionable fix strategies to issues."""
          # For each issue:
          # - fix_strategy: Specific steps
          # - evidence_before: What to measure
          # - evidence_after: What to verify
          # - success_criteria: Quantifiable metrics
          # - rollback_trigger: When to revert
          pass
  ```

- [ ] Implement fix strategy generator
- [ ] Add plan generation tests
- [ ] Test with real review reports

**Deliverables**:
- ✓ Plan sub-server functional
- ✓ Fix strategies actionable
- ✓ Tests passing

#### Day 23-25: Critical Fix Sub-server (Evidence-Based)

- [ ] Port `bx_fix_anal_sub_critical.md` to Python
  ```python
  # src/glintefy/subservers/fix/critical.py
  class CriticalSubServer(BaseSubServer):
      def execute(self) -> dict:
          # 1. Load critical issues from plan
          # 2. For each issue:
          #    a. MEASURE BEFORE (tests 3x, security scan)
          #    b. APPLY FIX (using AST/regex)
          #    c. MEASURE AFTER (tests 3x, rescan)
          #    d. COMPARE METRICS
          #    e. KEEP or REVERT (evidence-based)
          # 3. Generate summary with evidence
          pass

      def fix_sql_injection(self, file_path: str, content: str):
          """Fix SQL injection using AST."""
          # Parse with ast.parse()
          # Find cursor.execute with f-strings
          # Replace with parameterized queries
          pass

      def fix_command_injection(self, file_path: str, content: str):
          """Fix command injection."""
          # Replace os.system() with subprocess.run(shell=False)
          pass

      def run_tests_3x(self, issue_id: str, before: bool):
          """Run tests 3 times, detect flaky tests."""
          pass
  ```

- [ ] Implement AST-based security fixes
- [ ] Implement 3x test verification
- [ ] Implement git commit/revert logic
- [ ] Add evidence capture
- [ ] Test with real vulnerabilities

**Deliverables**:
- ✓ Critical sub-server functional
- ✓ Security fixes working (AST-based)
- ✓ Evidence-based verification working
- ✓ Git commit/revert working
- ✓ Tests passing

### Week 6: Quality Fix & Verification

#### Day 26-27: Quality Fix Sub-server

- [ ] Port `bx_fix_anal_sub_quality.md` to Python
  ```python
  # src/glintefy/subservers/fix/quality.py
  class QualitySubServer(BaseSubServer):
      def execute(self) -> dict:
          # 1. Load quality issues from plan
          # 2. For each issue:
          #    a. MEASURE BEFORE (complexity, lines, tests 3x)
          #    b. APPLY REFACTORING (extract functions, simplify)
          #    c. MEASURE AFTER (verify improvement)
          #    d. KEEP or REVERT
          # 3. Generate summary with evidence
          pass

      def refactor_long_function(self, file_path: str, func_name: str):
          """Refactor function >50 lines."""
          # Use AST to extract logical sections
          # Create helper functions
          # Update original function to call helpers
          pass

      def reduce_complexity(self, file_path: str, func_name: str):
          """Reduce cyclomatic complexity."""
          # Flatten nesting
          # Extract conditions
          # Use guard clauses
          pass
  ```

- [ ] Implement AST-based refactoring
- [ ] Add complexity reduction algorithms
- [ ] Test with real long functions

**Deliverables**:
- ✓ Quality sub-server functional
- ✓ Refactoring working
- ✓ Tests passing

#### Day 28-29: Verification Sub-server

- [ ] Port `bx_fix_anal_sub_verify.md` to Python
  ```python
  # src/glintefy/subservers/fix/verify.py
  class VerifySubServer(BaseSubServer):
      def execute(self) -> dict:
          # 1. Run full test suite 3x
          # 2. Compare with baseline metrics
          # 3. Detect flaky tests
          # 4. Run security scan
          # 5. Check coverage
          # 6. Verify no regressions
          # 7. Generate verification report
          pass

      def detect_flaky_tests(self, runs: list) -> list:
          """Identify tests with inconsistent results."""
          pass
  ```

- [ ] Implement 3x test verification
- [ ] Implement flaky test detection
- [ ] Add metrics comparison
- [ ] Test verification logic

**Deliverables**:
- ✓ Verify sub-server functional
- ✓ Flaky test detection working
- ✓ Tests passing

#### Day 30: glintefy Orchestrator & Testing

- [ ] Implement glintefy orchestrator
  ```python
  # src/glintefy/servers/fix.py
  class FixOrchestrator(BaseOrchestrator):
      def register_tools(self):
          @self.server.call_tool()
          async def fix_issues(scope: str, verify: bool, auto_commit: bool):
              # 1. Capture baseline metrics
              # 2. Create fix plan
              # 3. Get user approval
              # 4. Execute fixes based on scope
              # 5. Run verification
              # 6. Generate report
              pass

          @self.server.call_tool()
          async def fix_critical(verify: bool, auto_commit: bool):
              pass

          @self.server.call_tool()
          async def fix_quality(verify: bool, auto_commit: bool):
              pass

          @self.server.call_tool()
          async def fix_docs(verify: bool, auto_commit: bool):
              pass
  ```

- [ ] Integration tests for fix workflow
- [ ] Test evidence-based verification
- [ ] Test git operations
- [ ] Phase 3 review and cleanup

**Deliverables**:
- ✓ Phase 3 complete
- ✓ glintefy server production-ready
- ✓ Evidence-based fixing working
- ✓ All tests passing

---

## Phase 4: Remaining Sub-servers (Weeks 7-8)

### Week 7: Performance, Cache, Docs

#### Day 31-32: Performance Sub-server

- [ ] Port `bx_review_anal_sub_perf.md` to Python
- [ ] Implement profiling integration
- [ ] Add performance tests
- [ ] Deliverable: Performance sub-server complete

#### Day 33: Cache Sub-server

- [ ] Port `bx_review_anal_sub_cache.md` to Python
- [ ] Implement cache candidate detection
- [ ] Implement cache application with verification
- [ ] Add cache tests
- [ ] Deliverable: Cache sub-server complete

#### Day 34: Docs Sub-server

- [ ] Port `bx_review_anal_sub_docs.md` to Python
- [ ] Port `bx_fix_anal_sub_docs.md` to Python
- [ ] Implement docstring generation
- [ ] Add documentation tests
- [ ] Deliverable: Docs sub-servers complete

#### Day 35: CI/CD Sub-server

- [ ] Port `bx_review_anal_sub_cicd.md` to Python
- [ ] Implement CI/CD config analysis
- [ ] Add CI/CD tests
- [ ] Deliverable: CI/CD sub-server complete

### Week 8: Test Refactoring, Report, Log Analysis

#### Day 36-37: Test Refactoring Sub-server

- [ ] Port `bx_fix_anal_sub_refactor_tests.md` to Python
- [ ] Implement test naming improvements
- [ ] Implement OS marker addition
- [ ] Add test refactoring tests
- [ ] Deliverable: Test refactoring sub-server complete

#### Day 38: Report Sub-servers

- [ ] Port `bx_review_anal_sub_report.md` to Python
- [ ] Port `bx_fix_anal_sub_report.md` to Python
- [ ] Implement report compilation
- [ ] Add template rendering
- [ ] Add report tests
- [ ] Deliverable: Report sub-servers complete

#### Day 39: Log Analysis Sub-server

- [ ] Port `bx_review_anal_sub_analyze_command_logs.md` to Python
- [ ] Port `bx_fix_anal_sub_analyze_command_logs.md` to Python
- [ ] Implement log parsing and error detection
- [ ] Add log analysis tests
- [ ] Deliverable: Log analysis sub-servers complete

#### Day 40: Phase 4 Review

- [ ] Integration tests for all new sub-servers
- [ ] Performance testing
- [ ] Documentation updates
- [ ] Phase 4 cleanup
- [ ] Deliverable: Phase 4 complete

---

## Phase 5: Testing, Documentation, Deployment (Weeks 9-10)

### Week 9: Testing & Quality

#### Day 41-42: Integration Testing

- [ ] End-to-end tests for review workflow
- [ ] End-to-end tests for fix workflow
- [ ] Test with real repositories (small, medium, large)
- [ ] Test error handling and edge cases
- [ ] Deliverable: Comprehensive test suite

#### Day 43-44: Performance & Load Testing

- [ ] Benchmark against old bash system
- [ ] Test with large codebases (1000+ files)
- [ ] Optimize slow operations
- [ ] Test parallel execution performance
- [ ] Deliverable: Performance benchmarks

#### Day 45: Code Quality & Coverage

- [ ] Code review and refactoring
- [ ] Ensure 90%+ test coverage
- [ ] Run static analysis tools
- [ ] Fix any linting issues
- [ ] Deliverable: High-quality codebase

### Week 10: Documentation & Deployment

#### Day 46-47: Documentation

- [ ] API documentation (tools, resources)
- [ ] User guides
  - Getting started
  - Configuration
  - Usage examples
  - Troubleshooting
- [ ] Developer guides
  - Architecture overview
  - Adding new sub-servers
  - Testing guidelines
  - Contributing guide
- [ ] Deliverable: Complete documentation

#### Day 48: Deployment Preparation

- [ ] Create release checklist
- [ ] Set up versioning (semantic versioning)
- [ ] Create installation scripts
- [ ] Create MCP configuration examples
- [ ] Test installation on fresh environments
- [ ] Deliverable: Deployment ready

#### Day 49: Initial Deployment

- [ ] Release v1.0.0-beta
- [ ] Deploy to test environment
- [ ] Test with real users (if available)
- [ ] Gather feedback
- [ ] Deliverable: Beta release deployed

#### Day 50: Final Review & Planning

- [ ] Address beta feedback
- [ ] Plan v1.0.0 final release
- [ ] Document lessons learned
- [ ] Plan future enhancements
- [ ] Deliverable: Project complete

---

## Risk Management

### High Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| MCP SDK changes | High | Pin SDK version, monitor changelog |
| AST parsing failures | High | Extensive testing, fallback to regex |
| Git conflicts | Medium | Comprehensive git tests, clear docs |
| Test framework compatibility | High | Support multiple frameworks, graceful fallback |

### Medium Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Performance regression | Medium | Benchmark early, optimize continuously |
| Complex refactoring failures | Medium | Conservative approach, manual fallback |
| Dependency conflicts | Low | Pin versions, test matrix |

---

## Success Criteria

### Must Have (v1.0)
- ✓ glintefy-review server fully functional
- ✓ glintefy server fully functional
- ✓ All core sub-servers working
- ✓ Evidence-based fixing protocol working
- ✓ Git commit/revert working
- ✓ 90%+ test coverage
- ✓ Complete documentation

### Should Have (v1.1)
- ✓ Performance optimization
- ✓ Additional language support
- ✓ CI/CD integration guides
- ✓ Web UI for reports

### Nice to Have (v2.0)
- ✓ Real-time progress updates
- ✓ Incremental review/fix
- ✓ Machine learning for fix suggestions
- ✓ Integration with code review platforms

---

## Development Guidelines

### Code Standards
- Follow PEP 8 style guide
- Type hints for all functions
- Comprehensive docstrings
- Maximum function length: 50 lines
- Maximum cyclomatic complexity: 10

### Testing Standards
- Unit tests for all functions
- Integration tests for workflows
- 90%+ code coverage required
- Mock external dependencies
- Test both success and failure paths

### Git Workflow
- Feature branches for all changes
- Descriptive commit messages
- Squash commits before merge
- Code review required
- CI must pass before merge

### Documentation Standards
- API docs generated from docstrings
- User guides with examples
- Architecture diagrams
- Troubleshooting guides
- Keep docs up-to-date with code

---

## Maintenance Plan

### Post-Launch Support
- Bug fixes within 48 hours
- Feature requests reviewed weekly
- Security patches within 24 hours
- Documentation updates continuous

### Version Strategy
- Semantic versioning (MAJOR.MINOR.PATCH)
- Beta releases for major features
- LTS support for stable versions
- Deprecation warnings 2 versions ahead

---

## Team & Resources

### Required Skills
- Python 3.13+ expertise
- MCP protocol knowledge
- Git operations
- AST parsing
- Testing frameworks
- DevOps/CI/CD

### Tools Needed
- Python 3.13+
- Git
- VS Code or PyCharm
- pytest
- GitHub Actions (or similar CI)

---

## Appendix

### Quick Start Commands

```bash
# Development setup
git clone <repo>
cd glintefy
make dev

# Run tests
make test

# Run specific sub-server
python -m glintefy.subservers.review.scope

# Run orchestrator
python -m glintefy.servers.review

# Build package
make build

# Install locally
pip install -e .
```

### Configuration Example

```json
{
  "mcpServers": {
    "glintefy-review": {
      "command": "python",
      "args": ["-m", "glintefy.servers.review"],
      "env": {
        "LOG_LEVEL": "INFO",
        "PYTHON_VERSION": "3.13"
      }
    },
    "glintefy": {
      "command": "python",
      "args": ["-m", "glintefy.servers.fix"],
      "env": {
        "LOG_LEVEL": "INFO",
        "PYTHON_VERSION": "3.13",
        "AUTO_COMMIT": "true",
        "VERIFY_3X": "true"
      }
    }
  }
}
```

---

**Status**: Ready to implement
**Next Action**: Phase 1, Day 1 - Project structure setup
**Owner**: Development team
**Last Updated**: 2025-11-21
