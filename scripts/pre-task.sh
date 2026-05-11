#!/usr/bin/env bash
set -euo pipefail

TASK_FILE="${1:-}"
ERRORS=()

if [ -n "$TASK_FILE" ] && [ -f "$TASK_FILE" ]; then
    CONTENT=$(cat "$TASK_FILE")
    if ! echo "$CONTENT" | grep -q "Acceptance Criteria"; then
        ERRORS+=("FAIL: Task card missing 'Acceptance Criteria' section")
    fi
    if ! echo "$CONTENT" | grep -q "Scope"; then
        ERRORS+=("FAIL: Task card missing 'Scope' section")
    fi
    if ! echo "$CONTENT" | grep -q "Verification Method"; then
        ERRORS+=("FAIL: Task card missing 'Verification Method' section")
    fi
elif [ -n "$TASK_FILE" ]; then
    ERRORS+=("FAIL: Task file not found: $TASK_FILE")
fi

if git status --porcelain 2>/dev/null | grep -q .; then
    ERRORS+=("FAIL: Working tree has uncommitted changes. Commit or stash before starting.")
fi

if [ -f "memory/meta-mistakes.md" ]; then
    if grep -q "BLOCKER:" "memory/meta-mistakes.md"; then
        ERRORS+=("FAIL: Unresolved blockers in memory/meta-mistakes.md. Resolve before proceeding.")
    fi
fi

if [ ${#ERRORS[@]} -eq 0 ]; then
    echo -e "\e[32mPASS: All pre-task checks passed\e[0m"
    exit 0
else
    echo -e "\e[31mFAIL: Pre-task checks failed:\e[0m"
    for err in "${ERRORS[@]}"; do
        echo -e "  \e[31m$err\e[0m"
    done
    exit 1
fi
