import re
import sys
from pathlib import Path

FORBIDDEN_IMPORTS = [
    (r"\bimport duckdb\b", "duckdb"),
    (r"\bimport boto3\b", "boto3"),
    (r"\bfrom pyspark", "pyspark"),
    (r"\bimport minio\b", "minio"),
    (r"\bfrom kafka", "kafka"),
    (r"\bimport psycopg2\b", "psycopg2"),
    (r"\bfrom elasticsearch", "elasticsearch"),
]

EXCLUDED_DIRS = {"backends", "tests", "__pycache__", ".git"}

PROJECT_ROOT = Path(__file__).parent.parent


def check_file(filepath: Path) -> list[tuple[int, str, str]]:
    violations = []
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        for line_num, line in enumerate(f, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for pattern, lib_name in FORBIDDEN_IMPORTS:
                if re.search(pattern, line):
                    violations.append((line_num, lib_name, line.strip()))
    return violations


def main():
    all_violations = []
    for py_file in PROJECT_ROOT.rglob("*.py"):
        parts = py_file.relative_to(PROJECT_ROOT).parts
        if any(part in EXCLUDED_DIRS for part in parts):
            continue

        violations = check_file(py_file)
        for line_num, lib_name, line_content in violations:
            rel_path = py_file.relative_to(PROJECT_ROOT)
            all_violations.append(f"  {rel_path}:{line_num} → {lib_name} ({line_content})")

    if all_violations:
        print("❌ Interface leak detected! Business code directly imports backend libraries:\n")
        for v in all_violations:
            print(v)
        print(f"\nTotal violations: {len(all_violations)}")
        print("Fix: Use factory.get_*() instead of direct imports.")
        sys.exit(1)
    else:
        print("✅ No interface leaks found. All business code uses factory pattern.")
        sys.exit(0)


if __name__ == "__main__":
    main()
