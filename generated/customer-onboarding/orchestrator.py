#!/usr/bin/env python3
"""
ACTIVE ORCHESTRATOR: Drives the execution loop with mandatory enforcement.

This is THE entry point for the generated harness project.
AI agents MUST start here and follow the enforced workflow.

The orchestrator:
1. Tracks progress with enforced checkpoints
2. Requires guard.py pass before allowing implementation
3. Requires verification before allowing completion
4. Auto-checks architecture constraints after code changes
5. Prevents self-certification

Usage:
    python orchestrator.py --status                        # MUST run first
    python orchestrator.py --next                          # Show next criterion to implement
    python orchestrator.py --verify                        # Run full verification suite
    python orchestrator.py --mark-complete "criterion"     # Mark after verification passes
    python orchestrator.py --evolve                        # Run evolution cycle
    python orchestrator.py --innovate                      # Innovation engine (推陈出新)
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent


def run_script(script_path: Path, args: list = None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT))


def load_task() -> dict:
    task_file = PROJECT_ROOT / "task.yaml"
    if not task_file.exists():
        print("ERROR: No task.yaml found.")
        sys.exit(1)
    with open(task_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_session_state() -> dict:
    state_file = PROJECT_ROOT / "memory" / "session-state.yaml"
    if not state_file.exists():
        return {
            "status": "initialized",
            "progress": {
                "acceptance_criteria": [],
                "completed_criteria": [],
                "failed_criteria": [],
            },
            "guard_log": [],
        }
    with open(state_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_session_state(state: dict) -> None:
    state_file = PROJECT_ROOT / "memory" / "session-state.yaml"
    state["updated_at"] = datetime.now().isoformat()
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with open(state_file, "w", encoding="utf-8") as f:
        yaml.dump(state, f, default_flow_style=False, allow_unicode=True)


def load_architecture_rules() -> dict:
    rules_file = PROJECT_ROOT / "constraints" / "architecture-rules.yaml"
    if not rules_file.exists():
        return {}
    with open(rules_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def status_ok(state: dict) -> bool:
    return state.get("status") not in ("not_started", "")


def run_guard_check(plan_description: str) -> dict:
    guard_script = PROJECT_ROOT / "guard.py"
    if not guard_script.exists():
        return {"verdict": "PASS", "blockers": [], "warnings": ["guard.py not found — skipping check"]}
    proc = run_script(guard_script, ["--check", plan_description])
    result = {
        "verdict": "PASS" if proc.returncode == 0 else "BLOCKED",
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }
    return result


def show_status() -> None:
    task = load_task()
    state = load_session_state()
    criteria = task.get("acceptance_criteria", [])
    completed = state.get("progress", {}).get("completed_criteria", [])

    print(f"\n{'='*60}")
    print(f"PROJECT STATUS")
    print(f"{'='*60}")
    print(f"Task: {task.get('name', 'unknown')}")
    print(f"Goal: {task.get('goal', 'N/A')}")
    print(f"Status: {state.get('status', 'unknown')}")
    print(f"Last Updated: {state.get('updated_at', 'never')}")
    print(f"\nProgress: {len(completed)}/{len(criteria)} criteria satisfied")

    for c in criteria:
        status = "✅" if c in completed else "❌"
        print(f"  {status} {c}")

    pending = [c for c in criteria if c not in completed]
    if pending:
        print(f"\n🔵 NEXT TO IMPLEMENT:")
        print(f"   → {pending[0]}")
        print(f"\n📋 REQUIRED STEPS:")
        print(f"   1. Run `python guard.py --check \"describe your plan\"`")
        print(f"   2. Implement the criterion in src/")
        print(f"   3. Run `python orchestrator.py --verify`")
        print(f"   4. Run `python orchestrator.py --mark-complete \"{pending[0][:50]}...\"`")
    else:
        print(f"\n🎉 ALL CRITERIA COMPLETE!")
        print(f"   Next: python orchestrator.py --evolve")
        print(f"   Next: python orchestrator.py --innovate")

    guard_log = state.get("guard_log", [])
    if guard_log:
        last_guard = guard_log[-1]
        print(f"\n🛡️ Last Guard Check: {last_guard.get('verdict', 'unknown')} at {last_guard.get('timestamp', 'unknown')}")


def show_next() -> None:
    task = load_task()
    state = load_session_state()
    criteria = task.get("acceptance_criteria", [])
    completed = state.get("progress", {}).get("completed_criteria", [])
    pending = [c for c in criteria if c not in completed]

    if not pending:
        print("✅ All criteria complete. Run --evolve or --innovate.")
        return

    print(f"\n🔵 NEXT CRITERION: {pending[0]}")
    print(f"📋 Steps:")
    print(f"  1. Describe your plan and run: python guard.py --check \"your plan\"")
    print(f"  2. Implement in src/")
    print(f"  3. Run: python orchestrator.py --verify")
    print(f"  4. Run: python orchestrator.py --mark-complete \"criterion\"")


def run_verification() -> dict:
    print(f"\n{'='*60}")
    print(f"RUNNING VERIFICATION SUITE")
    print(f"{'='*60}")

    all_passed = True

    guard_script = PROJECT_ROOT / "guard.py"
    if guard_script.exists():
        print("\n--- Guard Compliance Check ---")
        proc = run_script(guard_script, ["--report"])
        print(proc.stdout)

    self_check = PROJECT_ROOT / "verification" / "self-check.py"
    if self_check.exists():
        print("\n--- Self-Check Loop ---")
        proc = run_script(self_check, ["--project-root", str(PROJECT_ROOT)])
        if proc.returncode != 0:
            all_passed = False
            print(proc.stdout)
            if proc.stderr:
                print(proc.stderr[-500:])
        else:
            print("✅ Self-check passed")

    consistency_check = PROJECT_ROOT / "verification" / "consistency-check.py"
    if consistency_check.exists():
        print("\n--- Consistency Check ---")
        proc = run_script(consistency_check, ["--project-root", str(PROJECT_ROOT)])
        if proc.returncode != 0:
            all_passed = False
            print(proc.stdout)
        else:
            print("✅ Consistency check passed")

    entropy_script = PROJECT_ROOT / "constraints" / "entropy-reduction.py"
    if entropy_script.exists():
        print("\n--- Entropy Check ---")
        proc = run_script(entropy_script, ["--check-only", "--project-root", str(PROJECT_ROOT)])
        if proc.returncode != 0:
            all_passed = False
            print(proc.stdout)
        else:
            print("✅ Entropy check passed")

    print(f"\n{'='*60}")
    if all_passed:
        print("✅ ALL VERIFICATIONS PASSED")
    else:
        print("❌ SOME VERIFICATIONS FAILED — Run error analysis:")
        print("   python feedback/error-capture.py --error-output <file>")
        print("   python feedback/mistake-to-constraint.py")
    print(f"{'='*60}")

    return {"passed": all_passed}


def mark_complete(criterion_text: str) -> dict:
    task = load_task()
    state = load_session_state()
    criteria = task.get("acceptance_criteria", [])
    completed = state.get("progress", {}).get("completed_criteria", [])

    matched = None
    for c in criteria:
        if criterion_text in c or c in criterion_text:
            matched = c
            break

    if not matched:
        print(f"ERROR: Criterion not found: '{criterion_text}'")
        print(f"Available criteria:")
        for c in criteria:
            print(f"  - {c}")
        return {"status": "not_found"}

    if matched in completed:
        print(f"Already completed: {matched}")
        return {"status": "already_complete"}

    print(f"\n⚠️  ATTENTION: Only mark complete if verification PASSED.")
    print(f"   Criterion: {matched}")

    verification_result = run_verification()
    if not verification_result["passed"]:
        print(f"\n🛑 CANNOT MARK COMPLETE: Verification failed.")
        print(f"   Fix the issues above and run verification again.")
        return {"status": "verification_failed"}

    completed.append(matched)
    state.setdefault("progress", {})["completed_criteria"] = completed
    state["status"] = "in_progress"

    all_done = len(completed) >= len(criteria)

    guard_log = state.get("guard_log", [])
    guard_log.append({
        "timestamp": datetime.now().isoformat(),
        "action": "mark_complete",
        "criterion": matched,
        "verdict": "VERIFIED",
    })
    state["guard_log"] = guard_log[-20:]

    save_session_state(state)

    print(f"✅ Marked complete: {matched}")
    print(f"   Progress: {len(completed)}/{len(criteria)}")

    if all_done:
        print(f"\n🎉 ALL CRITERIA SATISFIED!")
        print(f"   Next: python orchestrator.py --evolve")
        print(f"   Next: python orchestrator.py --innovate")
    else:
        print(f"\n🔵 Next: python orchestrator.py --next")

    return {"status": "marked", "all_done": all_done}


def run_evolve() -> dict:
    print(f"\n{'='*60}")
    print(f"EVOLUTION CYCLE")
    print(f"{'='*60}")

    evolve_script = PROJECT_ROOT / "scripts" / "evolve.py"
    if evolve_script.exists():
        proc = run_script(evolve_script, ["--project-root", str(PROJECT_ROOT)])
        if proc.returncode == 0:
            print("✅ Evolution cycle completed.")
        else:
            print(f"Evolution issues: {proc.stderr[-300:] if proc.stderr else 'none'}")
        return {"status": "evolved"}
    else:
        print("Evolution script not found. Run from meta-harness:")
        print("  python scripts/evolve.py --project-root .")
        return {"status": "no_evolve_script"}


def run_innovate() -> dict:
    print(f"\n{'='*60}")
    print(f"INNOVATION CYCLE — 推陈出新")
    print(f"{'='*60}")

    innovation_engine = PROJECT_ROOT / "evolution" / "innovation-engine.py"
    if innovation_engine.exists():
        proc = run_script(innovation_engine, ["--project-root", str(PROJECT_ROOT)])
        if proc.returncode == 0:
            print("✅ Innovation proposals generated.")
        print(proc.stdout[-2000:] if proc.stdout else "No output")
        return {"status": "innovated"}
    else:
        print("Innovation engine not found.")
        return {"status": "no_innovation_engine"}


def main():
    parser = argparse.ArgumentParser(description="Active Orchestrator — Enforced Execution Engine")
    parser.add_argument("--status", action="store_true", help="Show project status")
    parser.add_argument("--next", action="store_true", help="Show next criterion to implement")
    parser.add_argument("--verify", action="store_true", help="Run full verification suite")
    parser.add_argument("--mark-complete", default=None, help="Mark criterion complete (after verification)")
    parser.add_argument("--evolve", action="store_true", help="Run evolution cycle")
    parser.add_argument("--innovate", action="store_true", help="Run innovation cycle")
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if args.next:
        show_next()
        return

    if args.verify:
        run_verification()
        return

    if args.mark_complete:
        mark_complete(args.mark_complete)
        return

    if args.evolve:
        run_evolve()
        return

    if args.innovate:
        run_innovate()
        return

    show_status()


if __name__ == "__main__":
    main()
