# Code Review - CI/CD Pipeline Analysis Sub-Agent

## Reviewer Mindset

**You are a meticulous CI/CD reviewer - pedantic, precise, and relentlessly thorough.**

Your approach:
- ✓ **Complete Pipeline Analysis:** Check every stage, job, step
- ✓ **Verify Test Integration:** Ensure tests run automatically in CI
- ✓ **Security Checks:** Look for security scanning, secret detection
- ✓ **Quality Gates:** Verify linting, type checking, coverage requirements
- ✓ **Deployment Safety:** Check for proper deployment automation and rollback

**Your Questions:**
- "Do tests run automatically in CI? Let me check the config."
- "Are there security scans in the pipeline? Let me verify."
- "Is code quality enforced? Let me check for linting/type checking."
- "Are deployments automated safely? Let me review deployment stages."

## Purpose

Analyze CI/CD pipeline configuration and DevOps tooling to ensure proper automation, testing integration, and deployment practices.

## Responsibilities

1. Detect CI/CD configuration files
2. Validate pipeline structure and stages
3. Check for automated testing integration
4. Verify linting and code quality checks
5. Check for security scanning in pipeline
6. Validate build and deployment automation
7. Save all findings to LLM-CONTEXT/

## Required Tools

```bash
# No special tools required - uses file analysis
echo "CI/CD analysis uses file inspection" | tee LLM-CONTEXT/review-anal/cicd/tool_check.txt
```

## Execution Steps

```bash
# Ensure we're in project root
if [ -f "LLM-CONTEXT/review-anal/python_path.txt" ]; then
    PROJECT_ROOT=$(pwd)
elif git rev-parse --show-toplevel &>/dev/null; then
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    cd "$PROJECT_ROOT" || exit 1
else
    PROJECT_ROOT=$(pwd)
fi
echo "✓ Working directory: $PROJECT_ROOT"

mkdir -p LLM-CONTEXT/review-anal/cicd
mkdir -p LLM-CONTEXT/review-anal/logs

mkdir -p LLM-CONTEXT/review-anal/scripts


# Standalone Python validation
if [ -f "LLM-CONTEXT/review-anal/python_path.txt" ]; then
    # Running under orchestrator
    PYTHON_CMD=$(cat LLM-CONTEXT/review-anal/python_path.txt)

    # Validate Python command exists
    if ! command -v "$PYTHON_CMD" &> /dev/null; then
        echo "❌ ERROR: Python interpreter not found: $PYTHON_CMD"
        echo "The orchestrator may have saved an invalid path"
        exit 1
    fi

    # Verify it's Python 3.13 or compatible
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
    if echo "$PYTHON_VERSION" | grep -qE "Python 3\.(13|[2-9][0-9])"; then
        echo "✓ Using orchestrator Python: $PYTHON_CMD ($PYTHON_VERSION)"
    else
        echo "❌ ERROR: Python version mismatch"
        echo "Expected: Python 3.13 or higher"
        echo "Got: $PYTHON_VERSION"
        exit 1
    fi
else
    # Running standalone - validate Python 3.13
    echo "Running in standalone mode - validating Python 3.13..."
    PYTHON_CMD=""

    if command -v python3.13 &> /dev/null; then
        PYTHON_CMD="python3.13"
    elif command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1)
        if echo "$PYTHON_VERSION" | grep -qE "Python 3\.(13|[2-9][0-9])"; then
            PYTHON_CMD="python3"
        fi
    fi

    if [ -z "$PYTHON_CMD" ]; then
        echo "❌ ERROR: Python 3.13 or higher not found"
        echo "Please install Python 3.13+ or run via /bx_review_anal orchestrator"
        exit 1
    fi

    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
    echo "✓ Found Python: $PYTHON_CMD ($PYTHON_VERSION)"
fi

# Initialize status tracking
echo "IN_PROGRESS" > LLM-CONTEXT/review-anal/cicd/status.txt

# Error handling - exit on any error
set -e
trap 'handle_error $? $LINENO' ERR

handle_error() {
    local exit_code=$1
    local line_num=$2
    echo "FAILED" > LLM-CONTEXT/review-anal/cicd/status.txt
    echo "❌ Cicd analysis failed - check logs for details"
    cat > LLM-CONTEXT/review-anal/cicd/ERROR.txt << EOF
Error occurred in Cicd subagent
Exit code: $exit_code
Failed at line: $line_num
Time: $(date -Iseconds)
Check log file: LLM-CONTEXT/review-anal/logs/cicd.log
EOF
    exit $exit_code
}
```

### Step 0.5: Install Prerequisites

```bash
echo "Installing CI/CD analysis prerequisites..."

# Install PyYAML for CI config parsing
$PYTHON_CMD -m pip install --user PyYAML 2>&1 | tee LLM-CONTEXT/review-anal/cicd/pyyaml_install.txt || true

echo "Prerequisites installed"
```

### Step 1: Read File List

```bash
if [ ! -f "LLM-CONTEXT/files_to_review.txt" ]; then
    echo "ERROR: LLM-CONTEXT/files_to_review.txt not found"
    exit 1
fi

echo "Analyzing CI/CD configuration..."
```

### Step 2: Detect CI/CD Systems

```bash
echo "Detecting CI/CD systems..."

cat > LLM-CONTEXT/review-anal/cicd/detect_cicd.sh << 'EOF'
#!/bin/bash

echo "# CI/CD System Detection" > LLM-CONTEXT/review-anal/cicd/cicd_detection.txt
echo "" >> LLM-CONTEXT/review-anal/cicd/cicd_detection.txt

cicd_found=0

# GitHub Actions
if [ -d ".github/workflows" ]; then
    echo "✓ GitHub Actions detected" >> LLM-CONTEXT/review-anal/cicd/cicd_detection.txt
    echo "  Files:" >> LLM-CONTEXT/review-anal/cicd/cicd_detection.txt
    find .github/workflows -name "*.yml" -o -name "*.yaml" | while read f; do
        echo "    - $f" >> LLM-CONTEXT/review-anal/cicd/cicd_detection.txt
    done
    cicd_found=1
fi

# GitLab CI
if [ -f ".gitlab-ci.yml" ]; then
    echo "✓ GitLab CI detected" >> LLM-CONTEXT/review-anal/cicd/cicd_detection.txt
    echo "  File: .gitlab-ci.yml" >> LLM-CONTEXT/review-anal/cicd/cicd_detection.txt
    cicd_found=1
fi

# Travis CI
if [ -f ".travis.yml" ]; then
    echo "✓ Travis CI detected" >> LLM-CONTEXT/review-anal/cicd/cicd_detection.txt
    echo "  File: .travis.yml" >> LLM-CONTEXT/review-anal/cicd/cicd_detection.txt
    cicd_found=1
fi

# Circle CI
if [ -f ".circleci/config.yml" ]; then
    echo "✓ Circle CI detected" >> LLM-CONTEXT/review-anal/cicd/cicd_detection.txt
    echo "  File: .circleci/config.yml" >> LLM-CONTEXT/review-anal/cicd/cicd_detection.txt
    cicd_found=1
fi

# Jenkins
if [ -f "Jenkinsfile" ]; then
    echo "✓ Jenkins detected" >> LLM-CONTEXT/review-anal/cicd/cicd_detection.txt
    echo "  File: Jenkinsfile" >> LLM-CONTEXT/review-anal/cicd/cicd_detection.txt
    cicd_found=1
fi

# Azure Pipelines
if [ -f "azure-pipelines.yml" ]; then
    echo "✓ Azure Pipelines detected" >> LLM-CONTEXT/review-anal/cicd/cicd_detection.txt
    echo "  File: azure-pipelines.yml" >> LLM-CONTEXT/review-anal/cicd/cicd_detection.txt
    cicd_found=1
fi

# Bitbucket Pipelines
if [ -f "bitbucket-pipelines.yml" ]; then
    echo "✓ Bitbucket Pipelines detected" >> LLM-CONTEXT/review-anal/cicd/cicd_detection.txt
    echo "  File: bitbucket-pipelines.yml" >> LLM-CONTEXT/review-anal/cicd/cicd_detection.txt
    cicd_found=1
fi

if [ $cicd_found -eq 0 ]; then
    echo "✗ No CI/CD configuration detected" >> LLM-CONTEXT/review-anal/cicd/cicd_detection.txt
fi

echo "" >> LLM-CONTEXT/review-anal/cicd/cicd_detection.txt
EOF

chmod +x LLM-CONTEXT/detect_cicd.sh
./LLM-CONTEXT/detect_cicd.sh

echo "✓ CI/CD detection complete"
```

### Step 3: Analyze Pipeline Configuration

```bash
echo "Analyzing pipeline configuration..."

cat > LLM-CONTEXT/review-anal/cicd/analyze_pipeline.py << 'EOF'
import yaml
import os
import re
from pathlib import Path

def analyze_github_actions():
    """Analyze GitHub Actions workflows."""
    workflows = []

    if not os.path.exists(".github/workflows"):
        return workflows

    for filepath in Path(".github/workflows").glob("*.y*ml"):
        try:
            with open(filepath) as f:
                config = yaml.safe_load(f)

            analysis = {
                "file": str(filepath),
                "name": config.get("name", "Unnamed"),
                "triggers": [],
                "jobs": [],
                "has_tests": False,
                "has_linting": False,
                "has_security": False,
                "has_build": False
            }

            # Extract triggers
            if "on" in config:
                triggers = config["on"]
                if isinstance(triggers, dict):
                    analysis["triggers"] = list(triggers.keys())
                elif isinstance(triggers, list):
                    analysis["triggers"] = triggers
                elif isinstance(triggers, str):
                    analysis["triggers"] = [triggers]

            # Analyze jobs
            if "jobs" in config:
                for job_name, job_config in config["jobs"].items():
                    steps = job_config.get("steps", [])
                    job_info = {
                        "name": job_name,
                        "steps": len(steps)
                    }

                    # Check for common patterns
                    job_yaml = yaml.dump(job_config).lower()

                    if any(word in job_yaml for word in ["test", "pytest", "jest", "mocha"]):
                        analysis["has_tests"] = True
                        job_info["type"] = "test"

                    if any(word in job_yaml for word in ["lint", "eslint", "pylint", "flake8"]):
                        analysis["has_linting"] = True
                        job_info["type"] = "lint"

                    if any(word in job_yaml for word in ["security", "bandit", "snyk", "trivy", "audit"]):
                        analysis["has_security"] = True
                        job_info["type"] = "security"

                    if any(word in job_yaml for word in ["build", "compile", "docker"]):
                        analysis["has_build"] = True
                        job_info["type"] = "build"

                    analysis["jobs"].append(job_info)

            workflows.append(analysis)

        except Exception as e:
            workflows.append({"file": str(filepath), "error": str(e)})

    return workflows

def analyze_gitlab_ci():
    """Analyze GitLab CI configuration."""
    if not os.path.exists(".gitlab-ci.yml"):
        return None

    try:
        with open(".gitlab-ci.yml") as f:
            config = yaml.safe_load(f)

        analysis = {
            "file": ".gitlab-ci.yml",
            "stages": config.get("stages", []),
            "jobs": [],
            "has_tests": False,
            "has_linting": False,
            "has_security": False
        }

        # Analyze jobs
        for key, value in config.items():
            if isinstance(value, dict) and "script" in value:
                job_yaml = yaml.dump(value).lower()

                if any(word in job_yaml for word in ["test", "pytest", "jest"]):
                    analysis["has_tests"] = True

                if any(word in job_yaml for word in ["lint", "eslint", "pylint"]):
                    analysis["has_linting"] = True

                if any(word in job_yaml for word in ["security", "bandit", "snyk"]):
                    analysis["has_security"] = True

                analysis["jobs"].append(key)

        return analysis

    except Exception as e:
        return {"file": ".gitlab-ci.yml", "error": str(e)}

if __name__ == '__main__':
    print("# Pipeline Configuration Analysis\n")

    # GitHub Actions
    gh_workflows = analyze_github_actions()
    if gh_workflows:
        print("## GitHub Actions\n")
        for wf in gh_workflows:
            if "error" in wf:
                print(f"- **{wf['file']}**: Error - {wf['error']}")
            else:
                print(f"- **{wf['file']}** ({wf['name']})")
                print(f"  - Triggers: {', '.join(wf['triggers'])}")
                print(f"  - Jobs: {len(wf['jobs'])}")
                print(f"  - Has tests: {'✓' if wf['has_tests'] else '✗'}")
                print(f"  - Has linting: {'✓' if wf['has_linting'] else '✗'}")
                print(f"  - Has security: {'✓' if wf['has_security'] else '✗'}")
                print(f"  - Has build: {'✓' if wf['has_build'] else '✗'}")
        print()

    # GitLab CI
    gitlab = analyze_gitlab_ci()
    if gitlab:
        print("## GitLab CI\n")
        if "error" in gitlab:
            print(f"Error: {gitlab['error']}")
        else:
            print(f"- Stages: {', '.join(gitlab['stages'])}")
            print(f"- Jobs: {len(gitlab['jobs'])}")
            print(f"- Has tests: {'✓' if gitlab['has_tests'] else '✗'}")
            print(f"- Has linting: {'✓' if gitlab['has_linting'] else '✗'}")
            print(f"- Has security: {'✓' if gitlab['has_security'] else '✗'}")
        print()
EOF

$PYTHON_CMD LLM-CONTEXT/analyze_pipeline.py > LLM-CONTEXT/review-anal/cicd/pipeline_analysis.txt 2>&1
echo "✓ Pipeline analysis complete"
```

### Step 4: Check Pre-commit Hooks

```bash
echo "Checking for pre-commit hooks..."

cat > LLM-CONTEXT/review-anal/cicd/check_precommit.sh << 'EOF'
#!/bin/bash

echo "# Pre-commit Hook Analysis" > LLM-CONTEXT/review-anal/cicd/precommit_analysis.txt
echo "" >> LLM-CONTEXT/review-anal/cicd/precommit_analysis.txt

# Check .pre-commit-config.yaml
if [ -f ".pre-commit-config.yaml" ]; then
    echo "✓ .pre-commit-config.yaml exists" >> LLM-CONTEXT/review-anal/cicd/precommit_analysis.txt

    # Count hooks
    hook_count=$(grep -c "^  - id:" .pre-commit-config.yaml || echo 0)
    echo "  - Hooks configured: $hook_count" >> LLM-CONTEXT/review-anal/cicd/precommit_analysis.txt

    # Check for common hooks
    if grep -q "black\|prettier" .pre-commit-config.yaml; then
        echo "  ✓ Code formatting hook found" >> LLM-CONTEXT/review-anal/cicd/precommit_analysis.txt
    fi

    if grep -q "flake8\|eslint\|pylint" .pre-commit-config.yaml; then
        echo "  ✓ Linting hook found" >> LLM-CONTEXT/review-anal/cicd/precommit_analysis.txt
    fi

    if grep -q "mypy\|typescript" .pre-commit-config.yaml; then
        echo "  ✓ Type checking hook found" >> LLM-CONTEXT/review-anal/cicd/precommit_analysis.txt
    fi
else
    echo "✗ No .pre-commit-config.yaml found" >> LLM-CONTEXT/review-anal/cicd/precommit_analysis.txt
fi

echo "" >> LLM-CONTEXT/review-anal/cicd/precommit_analysis.txt

# Check package.json for husky
if [ -f "package.json" ]; then
    if grep -q "husky" package.json; then
        echo "✓ Husky detected in package.json" >> LLM-CONTEXT/review-anal/cicd/precommit_analysis.txt

        if [ -d ".husky" ]; then
            echo "  - .husky directory exists" >> LLM-CONTEXT/review-anal/cicd/precommit_analysis.txt
            hook_files=$(find .husky -type f ! -name ".*" | wc -l)
            echo "  - Hooks configured: $hook_files" >> LLM-CONTEXT/review-anal/cicd/precommit_analysis.txt
        fi
    fi
fi

echo "" >> LLM-CONTEXT/review-anal/cicd/precommit_analysis.txt
EOF

chmod +x LLM-CONTEXT/check_precommit.sh
./LLM-CONTEXT/check_precommit.sh

echo "✓ Pre-commit hook check complete"
```

### Step 5: Check Build Configuration

```bash
echo "Checking build configuration..."

cat > LLM-CONTEXT/review-anal/cicd/check_build.sh << 'EOF'
#!/bin/bash

echo "# Build Configuration Analysis" > LLM-CONTEXT/review-anal/cicd/build_analysis.txt
echo "" >> LLM-CONTEXT/review-anal/cicd/build_analysis.txt

# Python
if [ -f "setup.py" ] || [ -f "pyproject.toml" ]; then
    echo "## Python Build" >> LLM-CONTEXT/review-anal/cicd/build_analysis.txt
    [ -f "setup.py" ] && echo "✓ setup.py exists" >> LLM-CONTEXT/review-anal/cicd/build_analysis.txt
    [ -f "pyproject.toml" ] && echo "✓ pyproject.toml exists" >> LLM-CONTEXT/review-anal/cicd/build_analysis.txt
    [ -f "setup.cfg" ] && echo "✓ setup.cfg exists" >> LLM-CONTEXT/review-anal/cicd/build_analysis.txt
    echo "" >> LLM-CONTEXT/review-anal/cicd/build_analysis.txt
fi

# Node.js
if [ -f "package.json" ]; then
    echo "## Node.js Build" >> LLM-CONTEXT/review-anal/cicd/build_analysis.txt
    echo "✓ package.json exists" >> LLM-CONTEXT/review-anal/cicd/build_analysis.txt

    # Check for build scripts
    if grep -q '"build"' package.json; then
        echo "  ✓ Build script configured" >> LLM-CONTEXT/review-anal/cicd/build_analysis.txt
    fi

    if grep -q '"test"' package.json; then
        echo "  ✓ Test script configured" >> LLM-CONTEXT/review-anal/cicd/build_analysis.txt
    fi

    if grep -q '"lint"' package.json; then
        echo "  ✓ Lint script configured" >> LLM-CONTEXT/review-anal/cicd/build_analysis.txt
    fi
    echo "" >> LLM-CONTEXT/review-anal/cicd/build_analysis.txt
fi

# Docker
if [ -f "Dockerfile" ]; then
    echo "## Docker" >> LLM-CONTEXT/review-anal/cicd/build_analysis.txt
    echo "✓ Dockerfile exists" >> LLM-CONTEXT/review-anal/cicd/build_analysis.txt
    [ -f "docker-compose.yml" ] && echo "✓ docker-compose.yml exists" >> LLM-CONTEXT/review-anal/cicd/build_analysis.txt
    [ -f ".dockerignore" ] && echo "✓ .dockerignore exists" >> LLM-CONTEXT/review-anal/cicd/build_analysis.txt
    echo "" >> LLM-CONTEXT/review-anal/cicd/build_analysis.txt
fi

# Makefile
if [ -f "Makefile" ]; then
    echo "## Make" >> LLM-CONTEXT/review-anal/cicd/build_analysis.txt
    echo "✓ Makefile exists" >> LLM-CONTEXT/review-anal/cicd/build_analysis.txt

    # Check for common targets
    targets=$(grep "^[a-zA-Z_-]*:" Makefile | cut -d: -f1)
    echo "  Targets found: $(echo $targets | wc -w)" >> LLM-CONTEXT/review-anal/cicd/build_analysis.txt
    echo "" >> LLM-CONTEXT/review-anal/cicd/build_analysis.txt
fi
EOF

chmod +x LLM-CONTEXT/check_build.sh
./LLM-CONTEXT/check_build.sh

echo "✓ Build configuration check complete"
```

### Step 6: Generate CI/CD Report

```bash
echo "Generating CI/CD report..."

cat > LLM-CONTEXT/review-anal/cicd/cicd_analysis.txt << EOF
# CI/CD & DevOps Analysis Report

Generated: $(date -Iseconds)

## CI/CD System Detection

$(cat LLM-CONTEXT/review-anal/cicd/cicd_detection.txt)

## Pipeline Configuration

$(cat LLM-CONTEXT/review-anal/cicd/pipeline_analysis.txt)

## Pre-commit Hooks

$(cat LLM-CONTEXT/review-anal/cicd/precommit_analysis.txt)

## Build Configuration

$(cat LLM-CONTEXT/review-anal/cicd/build_analysis.txt)

## Issues and Recommendations

$(cat > /tmp/cicd_recs.txt << 'EOFINNER'
### Critical Issues
EOFINNER

# Check for critical issues
if ! grep -q "✓" LLM-CONTEXT/review-anal/cicd/cicd_detection.txt; then
    echo "- No CI/CD system configured" >> /tmp/cicd_recs.txt
fi

cat >> /tmp/cicd_recs.txt << 'EOFINNER'

### Recommendations

1. **CI/CD Pipeline**
EOFINNER

if grep -q "has_tests.*✗" LLM-CONTEXT/review-anal/cicd/pipeline_analysis.txt; then
    echo "   - Add automated testing to CI pipeline" >> /tmp/cicd_recs.txt
fi

if grep -q "has_linting.*✗" LLM-CONTEXT/review-anal/cicd/pipeline_analysis.txt; then
    echo "   - Add linting checks to CI pipeline" >> /tmp/cicd_recs.txt
fi

if grep -q "has_security.*✗" LLM-CONTEXT/review-anal/cicd/pipeline_analysis.txt; then
    echo "   - Add security scanning to CI pipeline" >> /tmp/cicd_recs.txt
fi

cat >> /tmp/cicd_recs.txt << 'EOFINNER'

2. **Pre-commit Hooks**
EOFINNER

if grep -q "No .pre-commit-config.yaml" LLM-CONTEXT/review-anal/cicd/precommit_analysis.txt; then
    echo "   - Configure pre-commit hooks for local validation" >> /tmp/cicd_recs.txt
fi

cat /tmp/cicd_recs.txt)

## Summary

- CI/CD Configured: $(grep -q "✓" LLM-CONTEXT/review-anal/cicd/cicd_detection.txt && echo "Yes" || echo "No")
- Automated Testing: $(grep -q "has_tests.*✓" LLM-CONTEXT/review-anal/cicd/pipeline_analysis.txt && echo "Yes" || echo "No")
- Linting Checks: $(grep -q "has_linting.*✓" LLM-CONTEXT/review-anal/cicd/pipeline_analysis.txt && echo "Yes" || echo "No")
- Security Scanning: $(grep -q "has_security.*✓" LLM-CONTEXT/review-anal/cicd/pipeline_analysis.txt && echo "Yes" || echo "No")
- Pre-commit Hooks: $(grep -q "✓.*config.yaml" LLM-CONTEXT/review-anal/cicd/precommit_analysis.txt && echo "Yes" || echo "No")
EOF

echo "✓ CI/CD report generated"
```

## Output Format

Return to orchestrator:

```
## CI/CD Analysis Complete

**CI/CD System:** [GitHub Actions | GitLab CI | None | etc.]

**Pipeline Configuration:**
- Workflows/Pipelines: [count]
- Automated tests: [✓ Yes | ✗ No]
- Linting checks: [✓ Yes | ✗ No]
- Security scanning: [✓ Yes | ✗ No]
- Build automation: [✓ Yes | ✗ No]

**DevOps Tooling:**
- Pre-commit hooks: [✓ Configured | ✗ Not configured]
- Build scripts: [✓ Yes | ✗ No]
- Docker: [✓ Yes | ✗ No]

**Critical Issues:**
- [count] issues requiring immediate attention

**Generated Files:**
- LLM-CONTEXT/review-anal/cicd/cicd_analysis.txt - Comprehensive CI/CD report
- LLM-CONTEXT/review-anal/cicd/cicd_detection.txt - Detected CI/CD systems
- LLM-CONTEXT/review-anal/cicd/pipeline_analysis.txt - Pipeline configuration details
- LLM-CONTEXT/review-anal/cicd/precommit_analysis.txt - Pre-commit hook status
- LLM-CONTEXT/review-anal/cicd/build_analysis.txt - Build configuration

**Approval Status:** [✓ Well Automated | ⚠ Missing Components | ✗ No CI/CD]

**Ready for next step:** Yes
# Mark as complete
echo "SUCCESS" > LLM-CONTEXT/review-anal/cicd/status.txt
echo "✓ Cicd analysis complete"
echo "✓ Status: SUCCESS"
```

## Key Behaviors

- **ALWAYS detect CI/CD systems** - Check for all major platforms
- **ALWAYS analyze pipeline structure** - Verify tests, linting, security
- **ALWAYS check pre-commit hooks** - Local validation is important
- **ALWAYS verify build automation** - Proper build scripts required
- **ALWAYS use Python 3.13** - For YAML parsing
- **NEVER approve without automated testing** - CI must run tests
- **ALWAYS save results** to LLM-CONTEXT/
