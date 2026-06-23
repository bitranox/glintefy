# MCP Server Architecture for glintefy and glintefy-review

## Executive Summary

This document outlines the architectural design for converting the existing Claude command system into MCP (Model Context Protocol) servers. The system will consist of:

1. **2 Orchestration Servers**: `glintefy` and `glintefy-review`
2. **Multiple Sub-servers**: Specialized agents for specific tasks
3. **MCP Tools**: Expose functionality through MCP tool interface
4. **MCP Resources**: Provide access to analysis results and artifacts

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Claude Code                              │
│                    (MCP Client / LLM Host)                       │
└───────────┬─────────────────────────────────────┬───────────────┘
            │                                     │
            │ MCP Protocol                        │ MCP Protocol
            │                                     │
┌───────────▼──────────────┐          ┌──────────▼──────────────┐
│  glintefy-review Server        │          │  glintefy Server         │
│  (Orchestrator)           │          │  (Orchestrator)         │
│  ┌─────────────────────┐ │          │  ┌───────────────────┐ │
│  │ Tools:              │ │          │  │ Tools:            │ │
│  │ - review_codebase   │ │          │  │ - fix_issues      │ │
│  │ - review_changes    │ │          │  │ - fix_critical    │ │
│  │ - review_files      │ │          │  │ - fix_quality     │ │
│  │                     │ │          │  │ - fix_docs        │ │
│  │ Resources:          │ │          │  │                   │ │
│  │ - review_report     │ │          │  │ Resources:        │ │
│  │ - findings          │ │          │  │ - fix_report      │ │
│  │ - metrics           │ │          │  │ - changes         │ │
│  └─────────────────────┘ │          │  │ - evidence        │ │
└──────┬───────────────────┘          │  └───────────────────┘ │
       │                              └──────┬──────────────────┘
       │ Delegates to                        │ Delegates to
       │                                     │
       └────────┬────────────────────────────┴─────────┐
                │                                      │
    ┌───────────▼────────┐                ┌───────────▼────────┐
    │  Sub-servers       │                │  Sub-servers       │
    │                    │                │                    │
    │  - scope           │                │  - plan            │
    │  - deps            │                │  - critical        │
    │  - quality         │                │  - quality         │
    │  - security        │                │  - refactor-tests  │
    │  - performance     │                │  - cache           │
    │  - cache           │                │  - docs            │
    │  - docs            │                │  - verify          │
    │  - cicd            │                │  - report          │
    │  - refactor-tests  │                │  - log-analyzer    │
    │  - report          │                │                    │
    │  - log-analyzer    │                │                    │
    └────────────────────┘                └────────────────────┘
```

## Server Architecture

### 1. Orchestration Servers

#### glintefy-review Server (Review Orchestrator)

**Purpose**: Orchestrates comprehensive code review

**MCP Tools**:

```typescript
{
  "review_codebase": {
    description: "Review entire codebase for quality, security, and best practices",
    parameters: {
      priority: "critical|high|medium|low|all",  // Priority level
      parallel: boolean                          // Run analyses in parallel
    }
  },

  "review_changes": {
    description: "Review specific changes (uncommitted, time-based, or commit range)",
    parameters: {
      scope: "uncommitted|1h|8h|24h|7d|custom",
      custom_spec: string  // Custom commit range or file patterns
    }
  },

  "review_files": {
    description: "Review specific files or patterns",
    parameters: {
      files: string[],       // File paths
      patterns: string[]     // Glob patterns
    }
  }
}
```

**MCP Resources**:

```typescript
{
  "review://report": "Final comprehensive review report",
  "review://findings/security": "Security analysis results",
  "review://findings/quality": "Code quality analysis",
  "review://findings/performance": "Performance analysis",
  "review://findings/docs": "Documentation analysis",
  "review://metrics/coverage": "Code coverage metrics",
  "review://metrics/complexity": "Complexity metrics",
  "review://artifacts/{subagent}": "All subagent artifacts"
}
```

**Sub-servers Managed**:
- `scope` - Determine review scope
- `deps` - Update and verify dependencies
- `quality` - Code quality analysis
- `security` - Security scanning
- `performance` - Performance profiling
- `cache` - Caching opportunity analysis
- `docs` - Documentation review
- `cicd` - CI/CD analysis
- `refactor-tests` - Test quality review
- `report` - Report compilation
- `log-analyzer` - Error analysis

#### glintefy Server (Fix Orchestrator)

**Purpose**: Actually fixes code issues with evidence-based verification

**MCP Tools**:

```typescript
{
  "fix_issues": {
    description: "Fix all issues from review report with evidence-based verification",
    parameters: {
      scope: "all|critical|quality|docs",  // What to fix
      verify: boolean,                     // Run 3x test verification (default: true)
      auto_commit: boolean                 // Auto-commit successful fixes (default: true)
    }
  },

  "fix_critical": {
    description: "Fix only critical blocking issues (security, test failures)",
    parameters: {
      verify: boolean,
      auto_commit: boolean
    }
  },

  "fix_quality": {
    description: "Fix code quality issues (refactoring, complexity)",
    parameters: {
      verify: boolean,
      auto_commit: boolean
    }
  },

  "fix_docs": {
    description: "Fix documentation issues",
    parameters: {
      verify: boolean,
      auto_commit: boolean
    }
  }
}
```

**MCP Resources**:

```typescript
{
  "fix://report": "Final fix report with evidence",
  "fix://plan": "Detailed fix plan with strategies",
  "fix://evidence/before": "Baseline metrics before fixes",
  "fix://evidence/after": "Metrics after fixes",
  "fix://changes": "Git diff of all changes",
  "fix://commits": "List of git commits created",
  "fix://reverted": "List of fixes that were reverted and why",
  "fix://artifacts/{subagent}": "All subagent artifacts"
}
```

**Sub-servers Managed**:
- `plan` - Create actionable fix plan
- `critical` - Fix security and test issues
- `quality` - Fix code quality issues
- `refactor-tests` - Refactor test suite
- `cache` - Apply cache optimizations
- `docs` - Fix documentation
- `verify` - Comprehensive verification
- `report` - Fix report generation
- `log-analyzer` - Error analysis

### 2. Sub-server Architecture

Each sub-server is a standalone MCP server that can be invoked by orchestrators.

**Standard Interface**:

```typescript
interface SubServer {
  // MCP Tools
  tools: {
    execute: {
      description: string,
      parameters: {
        input_dir: string,      // Input directory (LLM-CONTEXT/*)
        output_dir: string,     // Output directory for results
        config?: object         // Subagent-specific config
      }
    }
  },

  // MCP Resources
  resources: {
    "output://status": "SUCCESS|FAILED|IN_PROGRESS",
    "output://summary": "Human-readable summary",
    "output://artifacts": "All output files",
    "output://logs": "Execution logs"
  }
}
```

**Integration Protocol**:

Every sub-server MUST:
1. Create `status.txt` with final status
2. Create `{subagent}_summary.md` with results
3. Save all artifacts to designated directory
4. Return structured output via MCP response
5. Exit with proper status code

## Key Design Principles

### 1. Evidence-Based Fixing

The fix system operates on the principle: **"Don't trust anything, verify everything"**

```
FOR EACH FIX:
1. MEASURE BEFORE: Capture baseline (run tests 3x, security scan, metrics)
2. APPLY FIX: Actually modify code
3. MEASURE AFTER: Re-run tests 3x, rescan, compare metrics
4. DECIDE:
   - If evidence shows improvement → git commit
   - If evidence shows regression → git revert
5. DOCUMENT: Save all evidence files
```

### 2. Parallel Execution

The review orchestrator runs analyses in parallel for efficiency:

```
Single MCP Request → Launches Multiple Sub-servers in Parallel:
- quality + security + performance + cache + docs + cicd + tests

Wait for all → Compile results → Return unified report
```

### 3. Stateless Sub-servers

Each sub-server is stateless and communicates only through:
- Input files in `LLM-CONTEXT/`
- Output files in designated directories
- MCP tool responses

No shared memory, no inter-process communication.

### 4. Progressive Enhancement

- **Phase 1**: Full codebase review/fix
- **Phase 2**: Priority-based review (critical → high → medium → low)
- **Phase 3**: Incremental review/fix for CI/CD integration

## Directory Structure

```
LLM-CONTEXT/
├── review-anal/           # Review orchestrator workspace
│   ├── scope/             # Scope analysis results
│   ├── deps/              # Dependency updates
│   ├── quality/           # Quality analysis
│   ├── security/          # Security analysis
│   ├── perf/              # Performance analysis
│   ├── cache/             # Cache analysis
│   ├── docs/              # Documentation analysis
│   ├── cicd/              # CI/CD analysis
│   ├── refactor-tests/    # Test quality analysis
│   ├── report/            # Final report
│   └── logs/              # All logs
│
├── fix-anal/              # Fix orchestrator workspace
│   ├── plan/              # Fix plan with strategies
│   ├── metrics/           # Baseline metrics (BEFORE fix)
│   ├── critical/          # Critical fixes
│   ├── quality/           # Quality fixes
│   ├── refactor-tests/    # Test refactoring
│   ├── cache/             # Cache optimization
│   ├── docs/              # Documentation fixes
│   ├── verification/      # After-fix verification
│   ├── evidence/          # All evidence files
│   │   ├── before/        # Evidence before fixes
│   │   └── after/         # Evidence after fixes
│   ├── report/            # Final report
│   └── logs/              # All logs
│
└── venv/                  # Python virtual environment
    └── python-3.13/       # Python 3.13 venv for analysis tools
```

## MCP Protocol Examples

### Example 1: Full Codebase Review

**Client Request**:
```json
{
  "tool": "review_codebase",
  "arguments": {
    "priority": "all",
    "parallel": true
  }
}
```

**Server Response**:
```json
{
  "status": "success",
  "data": {
    "files_reviewed": 347,
    "findings": {
      "critical": 2,
      "high": 8,
      "medium": 23,
      "low": 45
    },
    "approval_status": "APPROVED_WITH_COMMENTS",
    "report": "review://report"
  }
}
```

### Example 2: Fix Critical Issues

**Client Request**:
```json
{
  "tool": "fix_critical",
  "arguments": {
    "verify": true,
    "auto_commit": true
  }
}
```

**Server Response**:
```json
{
  "status": "success",
  "data": {
    "issues_fixed": 7,
    "issues_reverted": 3,
    "git_commits": 7,
    "tests_passing": true,
    "evidence": "fix://evidence/after",
    "report": "fix://report"
  }
}
```

## Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1-2)
- [ ] Set up MCP server framework (Python + MCP SDK)
- [ ] Implement base orchestrator class
- [ ] Implement base sub-server class
- [ ] Create directory structure and file I/O utilities
- [ ] Implement integration protocol validation

### Phase 2: Review Server (Week 3-4)
- [ ] Implement glintefy-review orchestrator
- [ ] Port scope sub-server
- [ ] Port deps sub-server
- [ ] Port quality sub-server
- [ ] Port security sub-server
- [ ] Implement parallel execution
- [ ] Test end-to-end review workflow

### Phase 3: Fix Server (Week 5-6)
- [ ] Implement glintefy orchestrator
- [ ] Port plan sub-server
- [ ] Port critical sub-server (with evidence-based fixing)
- [ ] Port quality fix sub-server
- [ ] Implement 3x test verification
- [ ] Implement git commit/revert logic
- [ ] Test end-to-end fix workflow

### Phase 4: Remaining Sub-servers (Week 7-8)
- [ ] Port performance sub-server
- [ ] Port cache sub-server
- [ ] Port docs sub-server
- [ ] Port cicd sub-server
- [ ] Port refactor-tests sub-server
- [ ] Port report sub-server
- [ ] Port log-analyzer sub-server

### Phase 5: Testing & Documentation (Week 9-10)
- [ ] Integration tests for all workflows
- [ ] Performance testing
- [ ] Documentation
- [ ] Example usage guides
- [ ] Deployment guides

## Technical Stack

- **Language**: Python 3.13+
- **MCP SDK**: Official Anthropic MCP Python SDK
- **Analysis Tools**:
  - `bandit` (security scanning)
  - `radon` (complexity metrics)
  - `pytest` (testing framework)
  - `coverage` (code coverage)
  - Python AST (code parsing and manipulation)
- **Version Control**: Git (for commit/revert operations)

## Configuration

MCP servers will be configured via Claude Code's MCP configuration:

```json
{
  "mcpServers": {
    "glintefy-review": {
      "command": "python",
      "args": ["-m", "glintefy.servers.review"],
      "env": {
        "PYTHON_VERSION": "3.13"
      }
    },
    "glintefy": {
      "command": "python",
      "args": ["-m", "glintefy.servers.fix"],
      "env": {
        "PYTHON_VERSION": "3.13"
      }
    }
  }
}
```

## Benefits of MCP Architecture

### vs. Old Command System

**OLD**:
- ❌ Commands hardcoded in Claude Code
- ❌ Bash scripts difficult to maintain
- ❌ No standardized interface
- ❌ Hard to version and deploy
- ❌ Limited error handling

**NEW (MCP)**:
- ✅ Standardized protocol
- ✅ Language-agnostic (Python backend)
- ✅ Versioned and deployable as package
- ✅ Rich error handling and logging
- ✅ Can be used by any MCP client
- ✅ Better testing and maintenance
- ✅ Progressive enhancement possible

## Compatibility

The MCP servers will maintain compatibility with the existing workflow:
- Same directory structure (`LLM-CONTEXT/`)
- Same file formats and naming conventions
- Same evidence-based fixing protocol
- Same integration protocol for sub-agents

Existing bash scripts can be gradually ported to Python sub-servers.

## Conclusion

This MCP architecture provides:
1. **Standardization**: Clear protocol and interfaces
2. **Modularity**: Independent orchestrators and sub-servers
3. **Maintainability**: Python codebase easier to maintain than bash
4. **Extensibility**: Easy to add new sub-servers
5. **Evidence-Based**: All fixes verified with tests
6. **Safety**: Automatic revert on failures
7. **Auditability**: Complete evidence trail

The system transforms the existing command architecture into a robust, maintainable MCP server ecosystem while preserving the evidence-based fixing philosophy that makes it effective.
