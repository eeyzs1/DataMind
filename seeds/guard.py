#!/usr/bin/env python3
"""
PRE-ACTION GUARD: Validates planned actions against project constraints.

This script is THE enforcement mechanism. Before writing ANY code, the AI agent
MUST run this guard. It checks the planned action against architecture rules,
domain constraints, and workflow requirements.

The guard BLOCKS actions that violate constraints and explains exactly why.
No guard pass = NO code changes allowed.

Usage:
    python guard.py --check "I plan to add a new API endpoint for user login"
    python guard.py --check "I plan to modify the database schema directly from frontend"
    python guard.py --status           Check if guard system is active
    python guard.py --report           Generate compliance report
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent

VIOLATION_PATTERNS = {
    "frontend_db_access": {
        "patterns": [
            r"(?:import|from).*(?:sql|database|db|prisma|sequelize|typeorm|mongoose|pymongo|sqlite)",
            r"(?:connect|query|execute|cursor).*(?:database|db|sql)",
        ],
        "frontend_dirs": ["components", "views", "pages", "frontend", "ui", "client"],
        "message": "Direct database access from frontend/presentation layer is FORBIDDEN. Use the API layer.",
        "severity": "BLOCKED",
    },
    "business_logic_in_routes": {
        "patterns": [
            r"(?:def|function|class).*(?:calculate|process_payment|business_logic|validate_business|transform_data)",
        ],
        "target_dirs": ["routes", "controllers", "handlers"],
        "message": "Business logic in route handlers is FORBIDDEN. Move logic to services/ layer.",
        "severity": "BLOCKED",
    },
    "missing_validation": {
        "patterns": [],
        "check_hint": "If creating an API endpoint, input validation is REQUIRED.",
        "message": "API endpoints without input validation are FORBIDDEN. Add validation before processing.",
        "severity": "WARNING",
    },
    "circular_dependency": {
        "patterns": [],
        "check_hint": "Import graph must be a DAG. Check for A→B and B→A patterns.",
        "message": "Circular dependencies between modules are FORBIDDEN. Restructure your imports.",
        "severity": "BLOCKED",
    },
    "multiple_criteria_at_once": {
        "patterns": [],
        "check_hint": "Are you implementing more than one acceptance criterion?",
        "message": "Implementing multiple criteria at once is FORBIDDEN. Focus on ONE criterion at a time.",
        "severity": "BLOCKED",
    },
    "self_certification": {
        "patterns": [],
        "check_hint": "Are you trying to mark a criterion as complete without running verification?",
        "message": "Self-certification is FORBIDDEN. Only orchestrator.py --verify + --mark-complete can certify.",
        "severity": "BLOCKED",
    },
}


def load_architecture_rules() -> dict:
    rules_file = PROJECT_ROOT / "constraints" / "architecture-rules.yaml"
    if not rules_file.exists():
        return {}
    with open(rules_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_domain_constraints() -> list:
    agents_file = PROJECT_ROOT / "AGENTS.md"
    if not agents_file.exists():
        return []
    content = agents_file.read_text(encoding="utf-8")
    constraints = []
    in_section = False
    for line in content.split("\n"):
        if "Domain Constraints" in line:
            in_section = True
            continue
        if in_section:
            if line.strip().startswith("- "):
                constraints.append(line.strip()[2:])
            elif line.strip().startswith("###") or line.strip().startswith("##"):
                break
    return constraints


def load_session_state() -> dict:
    state_file = PROJECT_ROOT / "memory" / "session-state.yaml"
    if not state_file.exists():
        return {"status": "not_started"}
    with open(state_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def check_orchestrator_ran() -> tuple:
    state = load_session_state()
    if state.get("status") == "not_started":
        return False, "You have NOT run `python orchestrator.py --status` yet. Run it FIRST."
    if not state.get("progress", {}).get("acceptance_criteria"):
        return False, "No acceptance criteria loaded. Run `python orchestrator.py --status` FIRST."
    return True, "Orchestrator status loaded."


def analyze_plan(plan_description: str) -> list:
    violations = []
    plan_lower = plan_description.lower()
    arch_rules = load_architecture_rules()

    has_frontend_indicator = any(
        kw in plan_lower
        for kw in ["frontend", "component", "page", "view", "ui", "client", "browser", "react", "vue", "angular"]
    )
    has_db_indicator = any(
        kw in plan_lower
        for kw in ["database", "db", "sql", "query", "table", "schema", "migrate", "prisma", "orm", "mongoose", "model"]
    )
    has_route_indicator = any(
        kw in plan_lower
        for kw in ["route", "endpoint", "api", "controller", "handler", "rest"]
    )
    has_business_indicator = any(
        kw in plan_lower
        for kw in ["business logic", "process", "calculate", "transform", "workflow logic"]
    )
    has_multiple_indicator = len(re.findall(r"(?:and also|additionally|furthermore|second,|third,|also)", plan_lower)) > 0

    if has_frontend_indicator and has_db_indicator:
        violations.append({
            "rule": "NO_DIRECT_DB_FROM_FRONTEND",
            "severity": "BLOCKED",
            "message": "Your plan mentions both frontend and database. Direct database access from frontend is FORBIDDEN. All data access MUST go through the API layer: frontend → API → service → repository → database.",
        })

    if has_route_indicator and has_business_indicator:
        violations.append({
            "rule": "NO_BUSINESS_LOGIC_IN_ROUTES",
            "severity": "BLOCKED",
            "message": "Your plan suggests business logic in route/endpoint handlers. Business logic belongs in the service layer. Routes should ONLY handle request/response formatting.",
        })

    if has_multiple_indicator:
        violations.append({
            "rule": "ONE_CRITERION_AT_A_TIME",
            "severity": "WARNING",
            "message": "Your plan seems to cover multiple concerns. Implement ONE acceptance criterion at a time. Break your plan into smaller, sequential steps.",
        })

    if has_route_indicator and "validation" not in plan_lower and "validate" not in plan_lower:
        violations.append({
            "rule": "INPUT_VALIDATION_REQUIRED",
            "severity": "WARNING",
            "message": "You're creating an API endpoint but your plan doesn't mention input validation. Every API endpoint MUST have input validation.",
        })

    domain_constraints = load_domain_constraints()
    for dc in domain_constraints:
        dc_lower = dc.lower()
        for keyword in ["no ", "never ", "must not", "forbidden", "cannot", "should not"]:
            if keyword in dc_lower:
                constraint_subject = dc_lower.replace(keyword, "").strip()
                if constraint_subject and constraint_subject in plan_lower:
                    violations.append({
                        "rule": "DOMAIN_CONSTRAINT_VIOLATION",
                        "severity": "BLOCKED",
                        "message": f"Your plan violates the domain constraint: '{dc}'",
                    })
                    break

    if arch_rules:
        dep_direction = arch_rules.get("dependency_direction", {})
        forbidden = dep_direction.get("forbidden", [])
        for fb in forbidden:
            parts = fb.replace(" ", "").split("→")
            if len(parts) == 2:
                source, target = parts
                source_in_plan = source.lower() in plan_lower
                target_in_plan = target.lower() in plan_lower
                if source_in_plan and target_in_plan:
                    violations.append({
                        "rule": "DEPENDENCY_DIRECTION_VIOLATION",
                        "severity": "BLOCKED",
                        "message": f"Forbidden dependency direction: {fb}. Architecture rules require: {', '.join(dep_direction.get('allowed', []))}",
                    })

    return violations


def run_guard(plan_description: str) -> dict:
    result = {
        "timestamp": datetime.now().isoformat(),
        "plan": plan_description,
        "checks": [],
        "verdict": "PASS",
        "blockers": [],
        "warnings": [],
    }

    orch_ok, orch_msg = check_orchestrator_ran()
    result["checks"].append({"check": "orchestrator_status", "passed": orch_ok, "message": orch_msg})
    if not orch_ok:
        result["verdict"] = "BLOCKED"
        result["blockers"].append(orch_msg)

    violations = analyze_plan(plan_description)
    for v in violations:
        check_result = {"check": v["rule"], "passed": v["severity"] != "BLOCKED", "message": v["message"]}
        result["checks"].append(check_result)
        if v["severity"] == "BLOCKED":
            result["verdict"] = "BLOCKED"
            result["blockers"].append(v["message"])
        else:
            result["warnings"].append(v["message"])

    return result


def print_guard_result(result: dict) -> None:
    print("\n" + "=" * 70)
    print("GUARD CHECK RESULT")
    print("=" * 70)
    print(f"Plan: {result['plan'][:100]}...")
    print(f"Verdict: {result['verdict']}")
    print(f"Timestamp: {result['timestamp']}")

    print(f"\n--- Checks ({len(result['checks'])}) ---")
    for check in result["checks"]:
        status = "✅" if check["passed"] else "❌"
        print(f"  {status} {check['check']}: {check['message']}")

    if result["warnings"]:
        print(f"\n--- Warnings ({len(result['warnings'])}) ---")
        for w in result["warnings"]:
            print(f"  ⚠️  {w}")

    if result["blockers"]:
        print(f"\n--- BLOCKERS ({len(result['blockers'])}) ---")
        for b in result["blockers"]:
            print(f"  🛑 {b}")

    print("\n" + "=" * 70)
    if result["verdict"] == "PASS":
        print("✅ GUARD PASSED — You may proceed with implementation.")
        print("   Remember: Run `python orchestrator.py --verify` after coding.")
    else:
        print("🛑 GUARD BLOCKED — Fix the blockers above before writing any code.")
        print("   Rethink your approach and run guard.py again.")
    print("=" * 70)


def compliance_report() -> None:
    state = load_session_state()
    arch_rules = load_architecture_rules()
    domain_constraints = load_domain_constraints()

    print("\n" + "=" * 70)
    print("COMPLIANCE REPORT")
    print("=" * 70)
    print(f"Project Status: {state.get('status', 'unknown')}")
    print(f"Completed Criteria: {len(state.get('progress', {}).get('completed_criteria', []))}")
    print(f"Total Criteria: {len(state.get('progress', {}).get('acceptance_criteria', []))}")
    print(f"Architecture Rules: {len(arch_rules.get('rules', []))} defined")
    print(f"Domain Constraints: {len(domain_constraints)} active")
    print(f"Allowed Dependencies: {len(arch_rules.get('dependency_direction', {}).get('allowed', []))}")
    print(f"Forbidden Dependencies: {len(arch_rules.get('dependency_direction', {}).get('forbidden', []))}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Pre-Action Guard — Validates AI actions against constraints")
    parser.add_argument("--check", default=None, help="Description of what you plan to do")
    parser.add_argument("--status", action="store_true", help="Check if guard system is active")
    parser.add_argument("--report", action="store_true", help="Generate compliance report")
    args = parser.parse_args()

    if args.report:
        compliance_report()
        return

    if args.status:
        state = load_session_state()
        arch_rules = load_architecture_rules()
        print(f"Guard system: ACTIVE")
        print(f"Project status: {state.get('status', 'unknown')}")
        print(f"Architecture rules: {len(arch_rules.get('rules', []))} defined")
        return

    if not args.check:
        print("ERROR: Must provide --check with a description of your planned action.")
        print("Example: python guard.py --check \"I plan to add a new API endpoint for login\"")
        sys.exit(1)

    result = run_guard(args.check)
    print_guard_result(result)

    if result["verdict"] == "BLOCKED":
        sys.exit(1)


if __name__ == "__main__":
    main()
