"""Example: How MCP Server Provides Actionable Results.

This demonstrates how the server tells the caller what to do with results.
"""


def example_basic_result():
    """Basic result with recommendations."""
    return {
        "status": "PARTIAL",
        "summary": "Found 15 code quality issues requiring attention",
        # What was found
        "issues": [
            {
                "file": "src/main.py",
                "line": 42,
                "severity": "high",
                "type": "high_complexity",
                "description": "Function complexity of 18 exceeds threshold of 10",
            },
            # ... more issues
        ],
        # What to do about it (server's recommendations)
        "recommendations": [
            "⚠️ Fix high complexity in process() function (main.py:42) first",
            "Add type hints to 5 functions for better type safety",
            "Extract duplicate validation logic into shared helper",
        ],
        # Step-by-step guidance
        "next_steps": ["Review critical issues in main.py and utils.py", "Run automated fixes for safe changes", "Re-run quality check after fixes"],
        # Exact commands to run
        "suggested_commands": ["glintefy fix --severity high --interactive", "glintefy fix --add-types --auto", "glintefy review quality --recheck"],
        "metrics": {"total_issues": 15, "critical": 3, "high": 5, "medium": 7},
    }


def example_with_workflow():
    """Result with complete fix workflow."""
    return {
        "status": "PARTIAL",
        "summary": "Found security and quality issues",
        # Guided workflow (server tells caller the process)
        "workflow": {
            "title": "Fix Critical Issues",
            "estimated_time": "30 minutes",
            "steps": [
                {
                    "number": 1,
                    "title": "Backup Code",
                    "description": "Create snapshot before making changes",
                    "command": "git commit -am 'pre-fix snapshot'",
                    "required": True,
                },
                {
                    "number": 2,
                    "title": "Fix Security Issues",
                    "description": "Address 2 SQL injection vulnerabilities",
                    "priority": "CRITICAL",
                    "command": "glintefy fix --security --verify",
                    "expected_outcome": "All security issues resolved",
                },
                {
                    "number": 3,
                    "title": "Refactor Complex Functions",
                    "description": "Reduce complexity in 3 functions",
                    "command": "glintefy fix --complexity --interactive",
                    "review_required": True,
                },
                {
                    "number": 4,
                    "title": "Verify Changes",
                    "description": "Run tests and re-check quality",
                    "command": "pytest && glintefy review quality",
                    "success_criteria": "All tests pass, <5 issues remain",
                },
            ],
        },
        # Priority matrix (helps caller decide what to do first)
        "priority_matrix": {
            "immediate": ["Fix SQL injection in query() function", "Fix hardcoded credentials in config.py"],
            "this_week": ["Refactor process() to reduce complexity", "Add type hints to public API"],
            "nice_to_have": ["Extract duplicate code", "Improve docstring coverage"],
        },
    }


def example_with_explanations():
    """Result with detailed explanations for learning."""
    return {
        "status": "PARTIAL",
        "issues": [...],
        # Explain issues to help user understand
        "explanations": {
            "high_complexity": {
                "what": "Functions with cyclomatic complexity >10",
                "why_it_matters": "Complex functions are harder to test and maintain",
                "consequences": ["3x more likely to contain bugs", "Harder for new developers to understand", "Difficult to write comprehensive tests"],
                "how_to_fix": "Extract helper methods, simplify conditionals",
                "example": "Break 100-line function into 5 smaller functions of 20 lines each",
            },
            "missing_type_hints": {
                "what": "Functions without type annotations",
                "why_it_matters": "Type hints catch errors before runtime",
                "benefits": ["IDE autocomplete and type checking", "Prevents common type-related bugs", "Self-documenting code"],
                "how_to_fix": "Add type annotations to function signatures",
                "example": "def process(data: list[str]) -> dict[str, int]:",
            },
        },
        # Provide learning resources
        "learn_more": {
            "complexity": "https://docs.python.org/3/faq/programming.html",
            "type_hints": "https://mypy.readthedocs.io/en/stable/",
            "refactoring": "https://refactoring.guru/extract-method",
        },
    }


def example_with_fix_preview():
    """Result that shows what fixes would look like."""
    return {
        "status": "PARTIAL",
        "issues": [...],
        # Show preview of fixes (helps caller decide)
        "fix_previews": [
            {
                "issue_id": "complexity_001",
                "file": "main.py",
                "line": 42,
                "current_code": """
def process(items):
    for item in items:
        if item.valid:
            if item.active:
                # ... 50 more lines
""",
                "suggested_fix": """
def process(items):
    for item in items:
        if should_process(item):
            process_item(item)

def should_process(item):
    return item.valid and item.active

def process_item(item):
    # ... processing logic
""",
                "benefit": "Reduces complexity from 18 to 6",
                "risk": "Low - pure refactoring",
                "tests_affected": 1,
                "auto_fixable": False,
                "review_required": True,
            }
        ],
        # Options for applying fixes
        "fix_options": [
            {
                "approach": "automatic",
                "description": "Apply safe fixes automatically",
                "fixes_count": 8,
                "time": "5 minutes",
                "risk": "low",
                "command": "glintefy fix --auto --safe",
            },
            {
                "approach": "interactive",
                "description": "Review and approve each fix",
                "fixes_count": 15,
                "time": "20 minutes",
                "risk": "none",
                "command": "glintefy fix --interactive",
            },
            {
                "approach": "manual",
                "description": "Fix manually with AI guidance",
                "fixes_count": 15,
                "time": "45 minutes",
                "risk": "none",
                "provides": "Step-by-step instructions",
            },
        ],
    }


def example_conversation_flow():
    """Example of how Claude Desktop uses these results."""

    # Step 1: User asks for review
    user_message = "Review my code quality"

    # Step 2: Claude calls MCP tool
    mcp_result = {
        "status": "PARTIAL",
        "summary": "Found 15 issues: 3 critical, 5 high, 7 medium",
        "recommendations": ["Fix high complexity in process() first", "Add type hints to public API", "Extract duplicate validation logic"],
        "next_steps": ["Review critical issues in main.py", "Run automated fixes", "Re-check quality"],
        "suggested_commands": ["glintefy fix --severity high --interactive", "glintefy fix --add-types"],
    }

    # Step 3: Claude interprets and presents to user
    claude_response = f"""
I've completed a code quality review. Here's what I found:

📊 **Summary**: {mcp_result["summary"]}

🎯 **Recommendations**:
{chr(10).join(f"{i + 1}. {rec}" for i, rec in enumerate(mcp_result["recommendations"]))}

📋 **Next Steps**:
{chr(10).join(f"- {step}" for step in mcp_result["next_steps"])}

💻 **Commands to Fix**:
```bash
{chr(10).join(mcp_result["suggested_commands"])}
```

Would you like me to:
- Explain any of these issues in detail?
- Generate a fix plan?
- Apply automated fixes?
- Create a step-by-step guide?
"""

    return {"user_message": user_message, "mcp_result": mcp_result, "claude_response": claude_response}


def example_full_interaction():
    """Complete interaction showing actionable guidance."""

    interaction = {
        "user": "Review my code",
        "claude_calls_mcp": "review_quality",
        "mcp_returns": {
            "status": "PARTIAL",
            "issues_summary": "15 issues found",
            "critical_issues": [
                {
                    "file": "main.py",
                    "line": 42,
                    "issue": "High complexity (18)",
                    "fix": "Extract 3 helper methods",
                    "command": "glintefy fix main.py:42 --refactor",
                }
            ],
            "recommendations": [
                "Fix process() complexity first - biggest impact",
                "Then add type hints - prevents future issues",
                "Finally refactor duplicates - improves maintainability",
            ],
            "workflow": {
                "1": "Backup: git commit -am 'pre-fix'",
                "2": "Fix critical: glintefy fix --critical",
                "3": "Verify: pytest",
                "4": "Re-check: glintefy review",
            },
        },
        "claude_presents": """
I found 15 code quality issues. Here's my analysis:

🚨 **Most Critical**: High complexity in process() (main.py:42)
   - Current complexity: 18 (threshold: 10)
   - Impact: Hard to test, prone to bugs
   - Fix: Extract 3 helper methods
   - Benefit: Reduces complexity to 6

📈 **Priority Order**:
1. Fix process() complexity → Biggest maintainability win
2. Add type hints (5 functions) → Prevents future bugs
3. Refactor duplicates → DRY principle

🔧 **Recommended Workflow**:
```bash
# 1. Backup
git commit -am 'pre-fix snapshot'

# 2. Fix critical
glintefy fix --critical --interactive

# 3. Verify
pytest && glintefy review quality
```

**Estimated time**: 30 minutes
**Risk level**: Low (with tests)

Would you like me to:
A) Explain the complexity issue in detail
B) Generate the refactored code
C) Walk you through fixing it manually
D) Just do it automatically
""",
        "user_chooses": "B - Generate the refactored code",
        "claude_calls_mcp_again": "fix_complexity",
        "mcp_generates_fix": {
            "status": "SUCCESS",
            "changes": "Refactored process() into 4 functions",
            "new_complexity": 6,
            "tests_status": "All 15 tests passing",
            "next": "Review changes and commit if satisfied",
        },
        "claude_shows_result": """
✅ Done! I've refactored the code.

**Changes Made**:
- Split process() into 4 focused functions
- Reduced complexity: 18 → 6
- Added type hints
- All 15 tests still passing

**Files Changed**:
- main.py: +30 lines, -45 lines (net: -15 lines)

**New Functions**:
1. `validate_input(data: list[str]) -> bool`
2. `transform_data(data: list[str]) -> dict`
3. `process_item(item: dict) -> Result`
4. `process(items: list[str]) -> list[Result]` (simplified)

**Next Steps**:
```bash
# Review the changes
git diff main.py

# If satisfied, commit
git add main.py
git commit -m "refactor: reduce process() complexity to 6"

# Re-check quality
glintefy review quality
```

The code is now much cleaner! Want me to explain any of the changes?
""",
    }

    return interaction


if __name__ == "__main__":
    # Demo: What the server can tell the caller

    print("=" * 70)
    print("EXAMPLE: MCP Server Actionable Results")
    print("=" * 70)

    print("\n1. BASIC RESULT (with recommendations)")
    print("-" * 70)
    result = example_basic_result()
    print(f"Status: {result['status']}")
    print(f"Summary: {result['summary']}")
    print("\nRecommendations:")
    for rec in result["recommendations"]:
        print(f"  • {rec}")
    print("\nSuggested Commands:")
    for cmd in result["suggested_commands"]:
        print(f"  $ {cmd}")

    print("\n\n2. WORKFLOW RESULT (step-by-step)")
    print("-" * 70)
    result = example_with_workflow()
    workflow = result["workflow"]
    print(f"Workflow: {workflow['title']}")
    print(f"Estimated Time: {workflow['estimated_time']}")
    print("\nSteps:")
    for step in workflow["steps"]:
        print(f"\n  Step {step['number']}: {step['title']}")
        print(f"    Description: {step['description']}")
        print(f"    Command: {step['command']}")

    print("\n\n3. CONVERSATION FLOW")
    print("-" * 70)
    flow = example_conversation_flow()
    print(f"User: {flow['user_message']}")
    print("\nClaude Desktop presents:")
    print(flow["claude_response"])

    print("\n\n" + "=" * 70)
    print("KEY TAKEAWAY:")
    print("=" * 70)
    print("""
The MCP server provides:
✓ What's wrong (issues)
✓ What to do (recommendations)
✓ How to do it (commands, workflows)
✓ Why it matters (explanations)
✓ What happens next (next_steps)

Claude Desktop makes it conversational and actionable!
""")
