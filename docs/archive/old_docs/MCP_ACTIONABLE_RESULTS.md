# MCP Actionable Results Guide

## Can the Server Tell the Caller What to Do?

**Short Answer**: Yes! The MCP server returns **structured recommendations** that Claude Desktop interprets and presents to the user.

## How It Works

### Architecture

```
User ↔ Claude Desktop ↔ MCP Server
         ↓
   Interprets results
   Suggests actions
   Offers to help
```

The MCP server returns **data**, Claude Desktop provides the **conversational wrapper**.

## Result Structure

### Basic Structure

```python
{
    # Status
    "status": "SUCCESS" | "PARTIAL" | "FAILED",

    # Human-readable summary (Claude reads this)
    "summary": "Found 15 issues across 8 files...",

    # Detailed findings
    "issues": [...],

    # What to do about it
    "recommendations": [
        "Fix critical issue in foo.py:42 first",
        "Consider adding type hints"
    ],

    # Actionable next steps
    "next_steps": [
        "Run: glintefy fix --auto",
        "Review test coverage"
    ],

    # Commands user can run
    "suggested_commands": [
        "glintefy fix --file foo.py",
        "glintefy review quality --recheck"
    ],

    # Metrics
    "metrics": {...}
}
```

### Example: Quality Review Result

```python
def run_quality(...) -> dict:
    """Run quality analysis and return actionable results."""

    # Analyze code
    issues = analyze_code()

    # Build recommendations based on findings
    recommendations = []
    next_steps = []
    commands = []

    if critical_issues:
        recommendations.append(
            f"⚠️ Fix {len(critical_issues)} critical issues first"
        )
        next_steps.append(
            "Review functions with complexity >15"
        )
        commands.append(
            "glintefy fix --severity critical --auto"
        )

    if missing_types:
        recommendations.append(
            "Add type hints to improve maintainability"
        )
        commands.append(
            "glintefy fix --add-types"
        )

    if high_duplication:
        recommendations.append(
            "Refactor duplicated code blocks"
        )
        next_steps.append(
            "Extract common logic into shared functions"
        )

    return {
        "status": "PARTIAL",
        "summary": f"Found {len(issues)} issues requiring attention",
        "issues": issues,
        "recommendations": recommendations,
        "next_steps": next_steps,
        "suggested_commands": commands,
        "metrics": {...}
    }
```

## Real-World Example

### User Interaction

```
User: "Review my code quality"

Claude Desktop:
  [Calls review_quality MCP tool]

  I've completed a code quality review. Here's what I found:

  📊 Summary:
  - 15 issues detected across 8 files
  - 3 critical complexity issues
  - 5 functions missing type hints
  - 2 code duplication blocks

  🎯 Recommendations:
  1. Fix high complexity in process() function (foo.py:42) first
  2. Add type hints to validate(), parse(), and format()
  3. Extract duplicate validation logic into shared helper

  📋 Next Steps:
  - Review the 3 critical issues immediately
  - Run automated fixes for safe changes
  - Re-run quality check after fixes

  💻 Commands:
  Run these to fix automatically:
  ```bash
  glintefy fix --severity critical --auto
  glintefy fix --add-types
  ```

  Would you like me to help fix these issues?
```

## Advanced: Conditional Recommendations

```python
def build_recommendations(issues: list[dict]) -> dict:
    """Build context-aware recommendations."""

    recommendations = []
    next_steps = []

    # Analyze issue patterns
    complexity_issues = [i for i in issues if i['type'] == 'complexity']
    type_issues = [i for i in issues if i['type'] == 'missing_types']
    security_issues = [i for i in issues if i['type'] == 'security']

    # Priority 1: Security
    if security_issues:
        recommendations.append({
            "priority": "CRITICAL",
            "action": "Fix security vulnerabilities immediately",
            "rationale": f"{len(security_issues)} security issues detected",
            "command": "glintefy fix --security --verify"
        })

    # Priority 2: Complexity
    if len(complexity_issues) > 5:
        recommendations.append({
            "priority": "HIGH",
            "action": "Refactor high-complexity functions",
            "rationale": "Code maintainability at risk",
            "files": [i['file'] for i in complexity_issues],
            "command": "glintefy fix --complexity --interactive"
        })

    # Priority 3: Types
    if len(type_issues) > 10:
        recommendations.append({
            "priority": "MEDIUM",
            "action": "Add type hints",
            "rationale": "Improves IDE support and catches errors early",
            "benefit": "Prevents runtime type errors",
            "command": "glintefy fix --add-types --safe"
        })

    # Build execution plan
    next_steps = [
        "1. Backup code or commit current state",
        "2. Fix security issues first",
        "3. Refactor complex functions",
        "4. Add type hints",
        "5. Re-run quality check",
        "6. Run test suite to verify"
    ]

    return {
        "recommendations": recommendations,
        "next_steps": next_steps,
        "estimated_time": "30-45 minutes",
        "difficulty": "medium"
    }
```

## Guided Workflow Example

```python
def create_fix_workflow(issues: list[dict]) -> dict:
    """Create step-by-step workflow for fixing issues."""

    workflow = {
        "title": "Code Quality Fix Workflow",
        "steps": []
    }

    # Step 1: Preparation
    workflow["steps"].append({
        "step": 1,
        "title": "Prepare",
        "actions": [
            "Commit current changes: git add . && git commit -m 'pre-fix snapshot'",
            "Create fix branch: git checkout -b fix/quality-issues"
        ],
        "duration": "2 minutes"
    })

    # Step 2: Critical fixes
    if critical := [i for i in issues if i['severity'] == 'critical']:
        workflow["steps"].append({
            "step": 2,
            "title": "Fix Critical Issues",
            "description": f"Fix {len(critical)} critical issues",
            "actions": [
                f"Review {i['file']}:{i['line']}" for i in critical[:3]
            ],
            "command": "glintefy fix --severity critical --interactive",
            "duration": "15-20 minutes"
        })

    # Step 3: Automated fixes
    workflow["steps"].append({
        "step": 3,
        "title": "Apply Automated Fixes",
        "description": "Safe, automated fixes",
        "actions": [
            "Add type hints",
            "Format code",
            "Fix linting issues"
        ],
        "command": "glintefy fix --auto --safe",
        "duration": "5 minutes"
    })

    # Step 4: Verification
    workflow["steps"].append({
        "step": 4,
        "title": "Verify Fixes",
        "actions": [
            "Run tests: pytest",
            "Check types: mypy src/",
            "Re-review: glintefy review quality"
        ],
        "duration": "5 minutes"
    })

    # Step 5: Commit
    workflow["steps"].append({
        "step": 5,
        "title": "Commit Changes",
        "actions": [
            "Review diff: git diff",
            "Commit fixes: git commit -m 'fix: address quality issues'",
            "Merge: git checkout main && git merge fix/quality-issues"
        ],
        "duration": "3 minutes"
    })

    return workflow
```

## Interactive Guidance

### Server Can Provide Context

```python
{
    "status": "PARTIAL",
    "issues": [...],

    # Explain what the issues mean
    "explanations": {
        "high_complexity": {
            "what": "Functions with cyclomatic complexity >10",
            "why_bad": "Harder to test, understand, and maintain",
            "how_to_fix": "Extract helper methods, simplify logic",
            "example": "Break 100-line function into 5 smaller ones"
        }
    },

    # Suggest fixes with rationale
    "fix_suggestions": [
        {
            "issue_id": "complexity_001",
            "suggested_fix": "Extract validation logic into validate_input()",
            "benefit": "Reduces complexity from 15 to 8",
            "risk": "Low - pure function",
            "test_impact": "Minimal - add 1 new test"
        }
    ],

    # Provide learning resources
    "learn_more": {
        "complexity": "https://docs.python.org/3/faq/programming.html#how-can-i-tell-if-a-function-is-too-complex",
        "refactoring": "https://refactoring.guru/extract-method"
    }
}
```

## What Claude Desktop Does

When it receives these results, Claude Desktop:

1. **Interprets the data**
   - Reads summary, recommendations, next_steps
   - Understands the context

2. **Presents conversationally**
   - Explains findings in natural language
   - Highlights priorities
   - Suggests actions

3. **Offers to help**
   - "Would you like me to help fix these?"
   - "Shall I generate the fixes?"
   - "Want me to explain this issue?"

4. **Can take action** (if user agrees)
   - Call more MCP tools
   - Generate code fixes
   - Verify results

## Example: Full Conversation

```
User: "Review my code"

Claude: [Calls review_quality]
"I found 15 issues. The most critical is high complexity in process().

Recommendations:
1. Refactor process() to reduce complexity
2. Add type hints (5 functions missing)
3. Extract duplicate validation logic

Would you like me to:
- Explain the complexity issue?
- Generate a refactoring plan?
- Fix these automatically?"

User: "Explain the complexity issue"

Claude: "The process() function has complexity of 18 (threshold is 10).
This means it has too many decision points (if/else, loops, etc.).

High complexity makes code:
- Harder to test (need 18+ test cases)
- Harder to understand
- More prone to bugs

I suggest extracting these into helpers:
- validation logic → validate_input()
- processing logic → process_data()
- error handling → handle_errors()

This would reduce complexity to ~6 per function.

Shall I generate the refactored code?"

User: "Yes, do it"

Claude: [Calls fix_complexity tool]
"Done! I've refactored the code. Here's what changed:
- Extracted 3 helper functions
- Reduced complexity from 18 to 6
- Added type hints
- Preserved all functionality

Changes in: foo.py
Tests: All 15 tests still passing

Next: Review the changes and commit if satisfied."
```

## Best Practices for Actionable Results

### 1. Be Specific

❌ Bad:
```python
"recommendations": ["Fix the issues"]
```

✅ Good:
```python
"recommendations": [
    "Refactor process() in foo.py:42 to reduce complexity from 18 to <10",
    "Add type hints to parse(), validate(), and format() functions",
    "Extract duplicate validation into shared validate_input() helper"
]
```

### 2. Provide Context

```python
{
    "issue": "High complexity in process()",
    "why_it_matters": "Functions with complexity >10 are 3x more likely to contain bugs",
    "impact_if_ignored": "Technical debt accumulates, harder to maintain",
    "benefit_if_fixed": "Easier testing, better maintainability, fewer bugs"
}
```

### 3. Give Options

```python
"fix_options": [
    {
        "approach": "automatic",
        "description": "Safe automated fixes",
        "time": "5 minutes",
        "risk": "low",
        "command": "glintefy fix --auto"
    },
    {
        "approach": "interactive",
        "description": "Review each fix",
        "time": "20 minutes",
        "risk": "none",
        "command": "glintefy fix --interactive"
    },
    {
        "approach": "manual",
        "description": "Fix manually with guidance",
        "time": "45 minutes",
        "risk": "none",
        "guidance": "See recommendations above"
    }
]
```

### 4. Make It Actionable

```python
"next_steps": [
    {
        "step": 1,
        "action": "Create backup",
        "command": "git commit -am 'pre-fix snapshot'",
        "required": True
    },
    {
        "step": 2,
        "action": "Run automated fixes",
        "command": "glintefy fix --auto --safe",
        "optional_flags": ["--dry-run", "--interactive"]
    },
    {
        "step": 3,
        "action": "Verify fixes",
        "command": "pytest && glintefy review quality",
        "expected": "All tests pass, <5 issues remaining"
    }
]
```

## Summary

**Can the server tell the caller what to do?**

**YES! In multiple ways:**

1. ✅ **Recommendations** - What to fix and why
2. ✅ **Next Steps** - Step-by-step action plan
3. ✅ **Commands** - Exact commands to run
4. ✅ **Context** - Why it matters, what happens if ignored
5. ✅ **Options** - Different approaches (auto, interactive, manual)
6. ✅ **Workflows** - Complete guided fix process
7. ✅ **Learning** - Links to resources, explanations

**The MCP server returns structured data, Claude Desktop makes it conversational.**

**Example Flow:**
```
Server: "Here's what's wrong and how to fix it"
    ↓
Claude: "I found issues. Here's my suggestion. Want me to fix it?"
    ↓
User: "Yes"
    ↓
Claude: [Calls fix tool] "Done! Here's what I changed."
```

**The server provides the intelligence, Claude provides the conversation.**
