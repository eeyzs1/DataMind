#!/usr/bin/env python3
"""
Self-Check Loop: Execute → Check → Reflect → Fix.

Runs verification, uses error-capture for structured analysis,
applies retry strategy from retry-config, and re-runs.
Maximum 3 iterations to prevent infinite loops.

Usage:
    python verification/self-check.py [--project-root <dir>] [--max-iterations 3]
"""

import argparse
import subprocess
import sys
from pathlib import Path

import yaml


def load_retry_config(project_root: Path) -> dict:
    retry_file = project_root / "feedback" / "retry-config.yaml"
    if not retry_file.exists():
        return {}
    with open(retry_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def run_error_capture(project_root: Path, error_output: str, source: str) -> list:
    error_capture = project_root / "feedback" / "error-capture.py"
    if not error_capture.exists():
        return []
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as tmp:
        tmp.write(error_output)
        tmp_path = tmp.name
    try:
        proc = subprocess.run(
            [sys.executable, str(error_capture), "--error-output", tmp_path, "--source", source],
            capture_output=True, text=True,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            data = yaml.safe_load(proc.stdout) or {}
            return data.get("errors", [])
    except Exception:
        pass
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    return []


def run_verification(project_root: Path) -> dict:
    result = {"passed": True, "errors": []}

    consistency_script = project_root / "verification" / "consistency-check.py"
    if consistency_script.exists():
        proc = subprocess.run(
            [sys.executable, str(consistency_script), "--project-root", str(project_root)],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            result["passed"] = False
            combined = proc.stdout + proc.stderr
            result["errors"].append({"source": "consistency-check", "output": combined})
            captured = run_error_capture(project_root, combined, "consistency-check")
            if captured:
                result["errors"][-1]["parsed_errors"] = captured

    lint_result = subprocess.run(
        ["python", "-m", "ruff", "check", str(project_root / "src")],
        capture_output=True, text=True, cwd=str(project_root),
    )
    if lint_result.returncode != 0:
        result["passed"] = False
        result["errors"].append({"source": "lint", "output": lint_result.stdout})
        captured = run_error_capture(project_root, lint_result.stdout, "lint")
        if captured:
            result["errors"][-1]["parsed_errors"] = captured

    return result


def reflect_on_errors(errors: list, retry_config: dict) -> list:
    fixes = []
    for error in errors:
        source = error.get("source", "unknown")
        output = error.get("output", "")
        parsed = error.get("parsed_errors", [])

        if parsed:
            for pe in parsed:
                error_type = pe.get("type", "unknown")
                fix_hint = pe.get("fix_hint", "")
                strategy = _get_retry_strategy(error_type, retry_config)
                fixes.append({"type": strategy, "action": fix_hint, "source": source, "error_type": error_type})
        elif "unused import" in output:
            fixes.append({"type": "auto_fix", "action": "remove_unused_imports", "source": source})
        elif "undefined name" in output:
            fixes.append({"type": "manual_fix", "action": "add_missing_import_or_definition", "source": source})
        else:
            fixes.append({"type": "manual_fix", "action": "investigate_and_fix", "source": source, "detail": output[:200]})

    return fixes


def _get_retry_strategy(error_type: str, retry_config: dict) -> str:
    strategies = retry_config.get("strategies", {})
    for strategy_name, strategy_data in strategies.items():
        if error_type in strategy_data.get("error_types", []):
            return strategy_data.get("strategy", "manual_fix")
    return "manual_fix"


def self_check_loop(project_root: Path, max_iterations: int) -> dict:
    history = []
    retry_config = load_retry_config(project_root)

    for iteration in range(1, max_iterations + 1):
        print(f"\n--- Self-Check Iteration {iteration}/{max_iterations} ---")
        result = run_verification(project_root)
        history.append({"iteration": iteration, "result": result})

        if result["passed"]:
            print(f"✅ All checks passed at iteration {iteration}")
            return {"passed": True, "iterations": iteration, "history": history}

        print(f"❌ Checks failed. Errors: {len(result['errors'])}")
        fixes = reflect_on_errors(result["errors"], retry_config)
        print(f"   Proposed fixes: {len(fixes)}")
        for fix in fixes:
            print(f"   - [{fix['type']}] {fix['action']}")

    print(f"\n⚠️  Self-check loop exhausted ({max_iterations} iterations)")
    return {"passed": False, "iterations": max_iterations, "history": history}


def main():
    parser = argparse.ArgumentParser(description="Self-Check Loop")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--max-iterations", type=int, default=3, help="Maximum check iterations")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    result = self_check_loop(project_root, args.max_iterations)

    if not result["passed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
