#!/usr/bin/env bash
set -euo pipefail

ERRORS=()

if [ -f "package.json" ]; then
    if npx eslint . --format compact 2>/dev/null; [ $? -ne 0 ]; then
        ERRORS+=("FAIL: ESLint errors found")
    fi

    if [ -f "tsconfig.json" ]; then
        if npx tsc --noEmit 2>/dev/null; [ $? -ne 0 ]; then
            ERRORS+=("FAIL: TypeScript type check failed")
        fi
    fi

    if grep -q '"test"' package.json 2>/dev/null; then
        if npm test 2>/dev/null; [ $? -ne 0 ]; then
            ERRORS+=("FAIL: Tests failed")
        fi
    fi

    if npm run build 2>/dev/null; [ $? -ne 0 ]; then
        ERRORS+=("FAIL: Build failed")
    fi
fi

if [ -f "requirements.txt" ] || [ -f "pyproject.toml" ]; then
    if command -v ruff &>/dev/null; then
        if ! ruff check . 2>/dev/null; then
            ERRORS+=("FAIL: Ruff lint check failed")
        fi
    fi

    if [ -f "pyproject.toml" ] || [ -f "mypy.ini" ]; then
        if command -v mypy &>/dev/null; then
            if ! mypy . 2>/dev/null; then
                ERRORS+=("FAIL: MyPy type check failed")
            fi
        fi
    fi

    if [ -f "pytest.ini" ] || [ -f "pyproject.toml" ]; then
        if command -v pytest &>/dev/null; then
            if ! pytest 2>/dev/null; then
                ERRORS+=("FAIL: Pytest tests failed")
            fi
        fi
    fi
fi

SECRET_PATTERNS=("password\s*=" "api_key\s*=" "secret\s*=" "token\s*=" "PRIVATE KEY")
while IFS= read -r -d '' file; do
    for pattern in "${SECRET_PATTERNS[@]}"; do
        if grep -qE "$pattern" "$file" 2>/dev/null; then
            ERRORS+=("FAIL: Potential secret found in $(basename "$file") matching pattern: $pattern")
        fi
    done
done < <(find . -type f \( -name "*.py" -o -name "*.ts" -o -name "*.js" -o -name "*.yaml" -o -name "*.yml" -o -name "*.json" -o -name "*.env" \) \
    ! -path "*/node_modules/*" ! -path "*/.git/*" ! -path "*/venv/*" ! -path "*/__pycache__/*" -print0 2>/dev/null)

if [ ${#ERRORS[@]} -eq 0 ]; then
    echo -e "\e[32mPASS: All verification checks passed\e[0m"
    exit 0
else
    echo -e "\e[31mFAIL: Verification failed:\e[0m"
    for err in "${ERRORS[@]}"; do
        echo -e "  \e[31m$err\e[0m"
    done
    exit 1
fi
