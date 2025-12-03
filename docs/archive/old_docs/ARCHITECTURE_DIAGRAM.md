# Architecture Diagrams

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Claude Code                              │
│                    (MCP Client / LLM Host)                       │
│                                                                   │
│  User: "Review my code for security issues"                     │
└───────────┬─────────────────────────────────────┬───────────────┘
            │                                     │
            │ MCP Protocol                        │ MCP Protocol
            │ (JSON-RPC)                          │ (JSON-RPC)
            │                                     │
┌───────────▼──────────────┐          ┌──────────▼──────────────┐
│  glintefy-review Server        │          │  glintefy Server         │
│  Port: Unix Socket        │          │  Port: Unix Socket      │
│  ┌─────────────────────┐ │          │  ┌───────────────────┐ │
│  │ MCP Tools:          │ │          │  │ MCP Tools:        │ │
│  │  review_codebase    │ │          │  │  fix_issues       │ │
│  │  review_changes     │ │          │  │  fix_critical     │ │
│  │  review_files       │ │          │  │  fix_quality      │ │
│  │                     │ │          │  │  fix_docs         │ │
│  │ MCP Resources:      │ │          │  │                   │ │
│  │  review://report    │ │          │  │ MCP Resources:    │ │
│  │  review://findings  │ │          │  │  fix://report     │ │
│  │  review://metrics   │ │          │  │  fix://evidence   │ │
│  └─────────────────────┘ │          │  │  fix://changes    │ │
└──────┬───────────────────┘          │  └───────────────────┘ │
       │                              └──────┬──────────────────┘
       │ Spawns Sub-processes                │ Spawns Sub-processes
       │ (Parallel Execution)                │ (Sequential w/ Evidence)
       │                                     │
       ├─────────┬─────────┬─────────┐     ├─────────┬─────────┐
       │         │         │         │     │         │         │
┌──────▼───┐ ┌──▼───┐ ┌───▼──┐ ┌───▼──┐ ┌─▼────┐ ┌─▼────┐ ┌──▼────┐
│ scope    │ │quality│ │security│ │ perf │ │ plan │ │critical│ │quality│
│ sub-srv  │ │sub-srv│ │sub-srv│ │sub-srv│ │sub-srv│ │sub-srv│ │sub-srv│
└──────────┘ └───────┘ └────────┘ └──────┘ └──────┘ └───────┘ └───────┘
```

## MCP Protocol Flow

### Review Workflow

```
┌──────────┐
│  User    │
└────┬─────┘
     │ "Review my code"
     ▼
┌─────────────┐
│ Claude Code │
│ (MCP Client)│
└────┬────────┘
     │ 1. MCP Tool Call
     │    tool: "review_codebase"
     │    args: {priority: "all", parallel: true}
     ▼
┌──────────────────┐
│  glintefy-review      │
│  Orchestrator    │
└────┬─────────────┘
     │
     │ 2. Initialize Workspace (LLM-CONTEXT/review-anal/)
     ▼
     │ 3. Spawn Sub-servers (Parallel)
     ├──────────┬──────────┬──────────┬──────────┐
     ▼          ▼          ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌─────────┐ ┌────────┐ ┌──────┐
│ scope  │ │ quality│ │ security│ │  perf  │ │ docs │
└───┬────┘ └───┬────┘ └────┬────┘ └───┬────┘ └───┬──┘
    │          │           │           │          │
    │ 4. Each sub-server creates:
    │    - status.txt
    │    - {name}_summary.md
    │    - artifacts/
    │          │           │           │          │
    ▼          ▼           ▼           ▼          ▼
┌──────────────────────────────────────────────────┐
│           LLM-CONTEXT/review-anal/                │
│  ├── scope/                                       │
│  │   ├── status.txt                              │
│  │   ├── scope_summary.md                        │
│  │   └── files_to_review.txt                     │
│  ├── quality/                                     │
│  │   ├── status.txt                              │
│  │   ├── quality_summary.md                      │
│  │   └── complexity_report.json                  │
│  └── security/                                    │
│      ├── status.txt                               │
│      ├── security_summary.md                      │
│      └── bandit_report.json                       │
└──────────────────────────────────────────────────┘
    │
    │ 5. Wait for all sub-servers
    ▼
┌──────────────────┐
│  Compile Report  │
└────┬─────────────┘
     │
     │ 6. MCP Response
     ▼
┌─────────────┐
│ Claude Code │ ◄── {
│             │       "status": "success",
└─────────────┘       "data": {
                        "files_reviewed": 347,
                        "findings": {...}
                      }
                    }
```

### Fix Workflow (Evidence-Based)

```
┌──────────┐
│  User    │
└────┬─────┘
     │ "Fix critical issues"
     ▼
┌─────────────┐
│ Claude Code │
└────┬────────┘
     │ 1. MCP Tool Call
     │    tool: "fix_critical"
     │    args: {verify: true, auto_commit: true}
     ▼
┌──────────────────┐
│  glintefy         │
│  Orchestrator    │
└────┬─────────────┘
     │
     │ 2. Create Fix Plan
     ▼
┌────────────┐
│ plan       │  ◄── Read review report
│ sub-server │       Generate strategies
└────┬───────┘
     │
     │ 3. For Each Critical Issue:
     ▼
┌─────────────────────────────────────────────┐
│         EVIDENCE-BASED FIX PROTOCOL         │
│                                             │
│  ┌─────────────────────────────────┐       │
│  │ STEP 1: MEASURE BEFORE          │       │
│  │  - Run tests 3x                 │       │
│  │  - Security scan                │       │
│  │  - Capture metrics              │       │
│  └──────────┬──────────────────────┘       │
│             ▼                               │
│  ┌─────────────────────────────────┐       │
│  │ STEP 2: APPLY FIX               │       │
│  │  - Backup file                  │       │
│  │  - Modify code (AST/regex)      │       │
│  └──────────┬──────────────────────┘       │
│             ▼                               │
│  ┌─────────────────────────────────┐       │
│  │ STEP 3: MEASURE AFTER           │       │
│  │  - Run tests 3x                 │       │
│  │  - Security scan                │       │
│  │  - Compare metrics              │       │
│  └──────────┬──────────────────────┘       │
│             ▼                               │
│  ┌─────────────────────────────────┐       │
│  │ STEP 4: DECIDE                  │       │
│  │  ✓ Tests pass 3x → git commit   │       │
│  │  ✗ Tests fail → git revert      │       │
│  └──────────┬──────────────────────┘       │
│             ▼                               │
│  ┌─────────────────────────────────┐       │
│  │ STEP 5: DOCUMENT                │       │
│  │  - Save evidence files          │       │
│  │  - Log decision + reasoning     │       │
│  └─────────────────────────────────┘       │
└─────────────────────────────────────────────┘
     │
     │ 4. Comprehensive Verification
     ▼
┌────────────┐
│ verify     │  ◄── Run full test suite 3x
│ sub-server │      Check no regressions
└────┬───────┘
     │
     │ 5. Generate Report
     ▼
┌────────────┐
│ report     │  ◄── Compile evidence
│ sub-server │      Git commits list
└────┬───────┘      Reverted fixes list
     │
     │ 6. MCP Response
     ▼
┌─────────────┐
│ Claude Code │ ◄── {
│             │       "status": "success",
└─────────────┘       "data": {
                        "issues_fixed": 7,
                        "git_commits": 7,
                        "tests_passing": true
                      }
                    }
```

## Sub-Server Architecture

```
┌─────────────────────────────────────────────┐
│            BaseSubServer                     │
│                                              │
│  + name: str                                 │
│  + input_dir: Path                           │
│  + output_dir: Path                          │
│                                              │
│  + validate_inputs() → (bool, list[str])    │
│  + execute() → SubServerResult              │
│  + save_status(status: str)                 │
│  + save_summary(content: str)               │
│  + run() → SubServerResult                  │
└──────┬──────────────────────────────────────┘
       │ Inherited by all sub-servers
       │
       ├────────────┬────────────┬────────────┐
       ▼            ▼            ▼            ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ Scope    │ │ Quality  │ │ Security │ │ Critical │
│          │ │          │ │          │ │          │
│ validate │ │ validate │ │ validate │ │ validate │
│ execute  │ │ execute  │ │ execute  │ │ execute  │
└──────────┘ └──────────┘ └──────────┘ └──────────┘
```

## Directory Structure Flow

```
Project Root
│
├── LLM-CONTEXT/                  ← Workspace (created by orchestrators)
│   │
│   ├── review-anal/              ← glintefy-review workspace
│   │   ├── python_path.txt       ← Python interpreter path
│   │   ├── files_to_review.txt   ← Master file list
│   │   │
│   │   ├── scope/                ← Each sub-server has own dir
│   │   │   ├── status.txt        ← SUCCESS/FAILED/IN_PROGRESS
│   │   │   ├── scope_summary.md  ← Human-readable summary
│   │   │   └── artifacts...      ← Analysis results
│   │   │
│   │   ├── quality/
│   │   │   ├── status.txt
│   │   │   ├── quality_summary.md
│   │   │   ├── complexity.json
│   │   │   └── duplication.txt
│   │   │
│   │   ├── security/
│   │   │   ├── status.txt
│   │   │   ├── security_summary.md
│   │   │   ├── bandit_report.json
│   │   │   └── secrets_scan.txt
│   │   │
│   │   ├── report/               ← Final compiled report
│   │   │   └── review_report.md
│   │   │
│   │   └── logs/                 ← All logs
│   │       └── review.log
│   │
│   └── fix-anal/                 ← glintefy workspace
│       ├── python_path.txt
│       ├── metrics/              ← Baseline metrics (BEFORE)
│       │
│       ├── plan/                 ← Fix plan
│       │   ├── issues.json       ← All issues categorized
│       │   └── strategies.json   ← Fix strategies
│       │
│       ├── critical/             ← Critical fixes
│       │   ├── status.txt
│       │   ├── critical_summary.md
│       │   ├── security_fixes.log
│       │   └── test_fixes.log
│       │
│       ├── evidence/             ← Evidence trail
│       │   ├── before/           ← Measurements BEFORE fixes
│       │   │   ├── SEC_001_test_run_1.txt
│       │   │   ├── SEC_001_test_run_2.txt
│       │   │   ├── SEC_001_test_run_3.txt
│       │   │   └── SEC_001_scan.txt
│       │   │
│       │   └── after/            ← Measurements AFTER fixes
│       │       ├── SEC_001_test_run_1.txt
│       │       ├── SEC_001_test_run_2.txt
│       │       ├── SEC_001_test_run_3.txt
│       │       └── SEC_001_scan.txt
│       │
│       ├── verification/         ← Post-fix verification
│       │   └── verify_summary.md
│       │
│       ├── report/               ← Final fix report
│       │   ├── fix_report.md
│       │   └── after_fixes.diff
│       │
│       └── logs/
│           └── fix.log
│
└── src/glintefy/              ← Source code
    ├── servers/                   ← Orchestrators
    │   ├── base.py
    │   ├── review.py
    │   └── fix.py
    │
    └── subservers/                ← Sub-servers
        ├── review/
        │   ├── scope.py
        │   ├── quality.py
        │   └── security.py
        │
        └── fix/
            ├── plan.py
            ├── critical.py
            └── verify.py
```

## Evidence-Based Fixing Detail

```
┌─────────────────────────────────────────────────────────────┐
│                    CRITICAL FIX PROTOCOL                     │
│                                                               │
│  Issue: SQL Injection in src/auth.py:45                     │
│  File: cursor.execute(f"SELECT * FROM users WHERE id={uid}")│
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: MEASURE BEFORE                                       │
├─────────────────────────────────────────────────────────────┤
│  Run 1: pytest → 98 passed, 0 failed                        │
│  Run 2: pytest → 98 passed, 0 failed                        │
│  Run 3: pytest → 98 passed, 0 failed                        │
│  ✓ No flaky tests                                           │
│                                                               │
│  Security Scan: bandit → 5 vulnerabilities found            │
│  Evidence saved: evidence/before/SEC_001_*                   │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: APPLY FIX                                            │
├─────────────────────────────────────────────────────────────┤
│  Backup: src/auth.py → src/auth.py.backup                   │
│                                                               │
│  AST Parse: Identify cursor.execute with f-string           │
│  Transform:                                                  │
│    OLD: cursor.execute(f"SELECT * FROM users WHERE id={uid}")│
│    NEW: cursor.execute("SELECT * FROM users WHERE id=?", (uid,))│
│                                                               │
│  Write: src/auth.py (modified)                               │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: MEASURE AFTER                                        │
├─────────────────────────────────────────────────────────────┤
│  Run 1: pytest → 98 passed, 0 failed ✓                      │
│  Run 2: pytest → 98 passed, 0 failed ✓                      │
│  Run 3: pytest → 98 passed, 0 failed ✓                      │
│  ✓ Tests still pass, no flaky tests                         │
│                                                               │
│  Security Scan: bandit → 4 vulnerabilities found            │
│  ✓ Reduced by 1 (the SQL injection we fixed)                │
│  Evidence saved: evidence/after/SEC_001_*                    │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: DECIDE                                               │
├─────────────────────────────────────────────────────────────┤
│  Decision Matrix:                                            │
│    Tests 3/3 pass:     ✓ YES                                │
│    No flaky tests:     ✓ YES                                │
│    Security improved:  ✓ YES (5 → 4 vulnerabilities)        │
│    No regressions:     ✓ YES                                │
│                                                               │
│  DECISION: KEEP FIX → git commit                             │
│                                                               │
│  Git: Add src/auth.py                                        │
│  Git: Commit "fix: SQL injection in auth.py:45"              │
│  Commit SHA: a1b2c3d4                                        │
│                                                               │
│  Delete backup: src/auth.py.backup                           │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: DOCUMENT                                             │
├─────────────────────────────────────────────────────────────┤
│  Log: critical_fixes.log                                     │
│    [SEC_001] SQL Injection - FIXED ✓                         │
│    Before: 5 vulnerabilities, tests 3/3 pass                │
│    After:  4 vulnerabilities, tests 3/3 pass                │
│    Committed: a1b2c3d4                                       │
│    Evidence: evidence/before/* + evidence/after/*           │
└─────────────────────────────────────────────────────────────┘
```

## Parallel vs Sequential Execution

### Review (Parallel)

```
Time →
0s     ├── scope     ─────────────┤ (10s)
0s     ├── quality   ─────────────────────┤ (15s)
0s     ├── security  ──────────────────┤ (13s)
0s     ├── perf      ────────────────────────┤ (18s)
       └───────────────────────────────────────┘
                                          18s total
```

### Fix (Sequential with Evidence)

```
Time →
0s     ├── plan      ─────┤ (5s)
5s          ├── critical (Issue 1) ───────┤ (7s, tests 3x)
12s              ├── critical (Issue 2) ───────┤ (7s, tests 3x)
19s                   ├── verify ──────────┤ (6s, tests 3x)
       └──────────────────────────────────────────┘
                                            25s total

Why sequential? Evidence-based protocol requires:
- Measure before each fix
- Apply one fix at a time
- Verify after each fix
- Avoid interference between fixes
```

## Legend

```
┌────────┐
│ Box    │  Component or process
└────────┘

    │
    ▼       Flow direction

◄───────    Data flow / Return value

├─────┐
      ▼     Branch / Multiple outputs

┌──────────────────────┐
│                      │
│  ✓ Success           │  Status indicators
│  ✗ Failure           │
│  ⚠ Warning           │
└──────────────────────┘
```

---

**Use these diagrams** to understand the system architecture and explain it to team members.
