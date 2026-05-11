# Verification Specifications (Platform-Agnostic)

## Design Principle
These specs declare WHAT to verify, not HOW.
The agent reading this translates each check into the correct command
for the current platform (Windows/Linux/macOS).

## Pre-Task Checks

### Check: Task Card Completeness
- File: [task-file-path] (provided as argument)
- Assert: file contains "Acceptance Criteria" section
- Assert: file contains "Scope" section
- Assert: file contains "Verification Method" section
- On fail: "Task card missing required section"

### Check: Clean Working Tree
- Command: git status --porcelain
- Assert: output is empty
- On fail: "Working tree has uncommitted changes. Commit or stash before starting."

### Check: No Blocking Mistakes
- File: memory/meta-mistakes.md
- Assert: content does not contain "BLOCKER:"
- On fail: "Unresolved blockers in memory/meta-mistakes.md. Resolve before proceeding."

## Post-Change Verification

### Check: Lint (Node.js projects)
- Condition: package.json exists
- Command: npx eslint . --format compact
- Assert: exit code 0
- On fail: "ESLint errors found"

### Check: Lint (Python projects)
- Condition: requirements.txt or pyproject.toml exists
- Command: ruff check .
- Assert: exit code 0
- On fail: "Ruff lint check failed"

### Check: Type Check (TypeScript)
- Condition: tsconfig.json exists
- Command: npx tsc --noEmit
- Assert: exit code 0
- On fail: "TypeScript type check failed"

### Check: Type Check (Python)
- Condition: pyproject.toml or mypy.ini exists
- Command: mypy .
- Assert: exit code 0
- On fail: "MyPy type check failed"

### Check: Tests (Node.js)
- Condition: package.json exists AND has scripts.test
- Command: npm test
- Assert: exit code 0
- On fail: "Tests failed"

### Check: Tests (Python)
- Condition: pytest.ini or pyproject.toml exists
- Command: pytest
- Assert: exit code 0
- On fail: "Pytest tests failed"

### Check: Build
- Condition: package.json exists
- Command: npm run build
- Assert: exit code 0
- On fail: "Build failed"

### Check: No Secrets Leaked
- Scan: all files matching *.py, *.ts, *.js, *.yaml, *.yml, *.json, *.env
- Exclude: node_modules, .git, venv, __pycache__
- Patterns: password\s*=, api_key\s*=, secret\s*=, token\s*=, PRIVATE KEY
- Assert: no file content matches any pattern
- On fail: "Potential secret found in [filename] matching pattern: [pattern]"

## Quality Score Metrics

### Metric: Mistake Recurrence Rate
- Source: memory/mistakes.md
- Calculate: (total mistakes - resolved mistakes) / total mistakes * 100
- Threshold: > 20% triggers warning

### Metric: Constraint Coverage
- Source: .agents/constraints/ file count
- Threshold: < 3 triggers warning

### Metric: Workflow Coverage
- Source: .agents/workflows/ file count

### Metric: Skill Coverage
- Source: .agents/skills/ file count

## How Agents Should Use This
1. Read this file to know WHAT to check
2. Detect the current platform (Windows/Linux/macOS)
3. Translate each check into the appropriate platform command
4. Execute checks in order
5. Report PASS/FAIL for each check
6. If ANY check fails, the overall result is FAIL
