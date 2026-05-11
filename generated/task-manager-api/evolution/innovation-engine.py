#!/usr/bin/env python3
"""
Innovation Engine: Discover unmet needs and propose innovations.

After all acceptance criteria are met, this engine analyzes the product
state against domain advancement patterns to propose new features.

This is the "推陈出新" (innovation) component of the self-evolving harness.

Usage:
    python evolution/innovation-engine.py [--project-root <dir>] [--dry-run]
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import yaml

DOMAIN_ADVANCEMENT_MAP = {
    "web-app": "domain-advancements.yaml",
    "api-service": "domain-advancements-api.yaml",
    "automation": "domain-advancements.yaml",
    "data-pipeline": "domain-advancements.yaml",
    "content-system": "domain-advancements.yaml",
}


def load_product_state(project_root: Path) -> dict:
    analyzer = project_root / "evolution" / "product-analyzer.py"
    if analyzer.exists():
        import subprocess
        proc = subprocess.run(
            [sys.executable, str(analyzer), "--project-root", str(project_root)],
            capture_output=True, text=True,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return yaml.safe_load(proc.stdout) or {}
    return {"all_criteria_met": False, "criteria_progress": {"completion_rate": 0}}


def load_domain_advancements(project_root: Path, template_name: str) -> dict:
    adv_file = project_root / "evolution" / DOMAIN_ADVANCEMENT_MAP.get(template_name, "domain-advancements.yaml")
    if not adv_file.exists():
        return {"stages": []}
    with open(adv_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {"stages": []}


def detect_template(project_root: Path) -> str:
    task_file = project_root / "task.yaml"
    if task_file.exists():
        with open(task_file, "r", encoding="utf-8") as f:
            task = yaml.safe_load(f) or {}
        domain = task.get("domain", "").lower()
        domain_map = {
            "web_app": "web-app", "api_service": "api-service",
            "automation": "automation", "data_pipeline": "data-pipeline",
            "content_system": "content-system",
        }
        return domain_map.get(domain, "web-app")
    return "web-app"


def determine_current_stage(product_state: dict, advancements: dict) -> str:
    completion_rate = product_state.get("criteria_progress", {}).get("completion_rate", 0)
    all_met = product_state.get("all_criteria_met", False)

    if not all_met:
        return "Basic"

    structure = product_state.get("structure", {})
    files_with_content = structure.get("files_with_content", 0)
    has_tests = product_state.get("tests", {}).get("has_tests", False)
    total_tests = product_state.get("tests", {}).get("total_tests", 0)

    if files_with_content > 5 and has_tests and total_tests > 5:
        return "Solid"
    elif files_with_content > 10 and total_tests > 10:
        return "Advanced"
    else:
        return "Solid"


def propose_innovations(product_state: dict, advancements: dict, current_stage: str) -> list:
    proposals = []
    stage_names = [s.get("name", "") for s in advancements.get("stages", [])]
    current_idx = stage_names.index(current_stage) if current_stage in stage_names else 0

    next_stage_idx = current_idx + 1
    if next_stage_idx >= len(advancements.get("stages", [])):
        return proposals

    next_stage = advancements["stages"][next_stage_idx]
    next_stage_name = next_stage.get("name", "Unknown")

    innovations = next_stage.get("innovations", [])
    for innovation in innovations:
        trigger = innovation.get("trigger", "")
        category = innovation.get("category", "general")
        effort = innovation.get("effort", "medium")
        impact = innovation.get("impact", "medium")

        proposals.append({
            "id": innovation.get("id", "UNKNOWN"),
            "name": innovation.get("name", "Unknown"),
            "description": innovation.get("description", ""),
            "category": category,
            "effort": effort,
            "impact": impact,
            "trigger_condition": trigger,
            "target_stage": next_stage_name,
            "type": "product_innovation",
            "requires_approval": effort == "high" or category == "security",
            "proposed_at": datetime.now().isoformat(),
        })

    return proposals


def prioritize_innovations(proposals: list) -> list:
    impact_weight = {"high": 3, "medium": 2, "low": 1}
    effort_weight = {"low": 3, "medium": 2, "high": 1}

    def score(p):
        return impact_weight.get(p.get("impact", "medium"), 2) * 2 + effort_weight.get(p.get("effort", "medium"), 2)

    return sorted(proposals, key=score, reverse=True)


def run_innovation_cycle(project_root: Path, dry_run: bool = False) -> dict:
    print(f"\n{'='*60}")
    print("INNOVATION ENGINE — 推陈出新")
    print(f"{'='*60}")

    product_state = load_product_state(project_root)
    all_met = product_state.get("all_criteria_met", False)
    completion_rate = product_state.get("criteria_progress", {}).get("completion_rate", 0)

    print(f"\nProduct state: {completion_rate*100:.0f}% criteria met")
    print(f"All criteria met: {all_met}")

    if not all_met:
        print("\n⚠️  Not all acceptance criteria are met yet.")
        print("   Complete the current requirements first, then innovation can begin.")
        return {"status": "requirements_not_met", "proposals": []}

    template_name = detect_template(project_root)
    advancements = load_domain_advancements(project_root, template_name)
    current_stage = determine_current_stage(product_state, advancements)

    print(f"Current stage: {current_stage}")
    print(f"Domain template: {template_name}")

    proposals = propose_innovations(product_state, advancements, current_stage)
    proposals = prioritize_innovations(proposals)

    if not proposals:
        print("\n✅ Product is at the highest advancement stage. No further innovations proposed.")
        return {"status": "max_stage_reached", "proposals": []}

    next_stage = proposals[0].get("target_stage", "Unknown") if proposals else "Unknown"
    print(f"\nNext stage: {next_stage}")
    print(f"Innovation proposals: {len(proposals)}")

    for i, p in enumerate(proposals, 1):
        approval_tag = "🔒 NEEDS APPROVAL" if p.get("requires_approval") else "🟢 AUTO-APPROVED"
        print(f"\n  {i}. [{p['id']}] {p['name']} {approval_tag}")
        print(f"     Category: {p['category']} | Effort: {p['effort']} | Impact: {p['impact']}")
        print(f"     Description: {p['description']}")
        print(f"     Trigger: {p['trigger_condition']}")

    if not dry_run:
        innovation_log = project_root / "evolution" / "innovation-log.yaml"
        existing = []
        if innovation_log.exists():
            with open(innovation_log, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                existing = data.get("proposals", [])

        for p in proposals:
            p["status"] = "proposed"
            existing.append(p)

        with open(innovation_log, "w", encoding="utf-8") as f:
            yaml.dump({"version": 1, "proposals": existing}, f, default_flow_style=False, allow_unicode=True)

        print(f"\n📝 Proposals saved to evolution/innovation-log.yaml")

        genome_file = project_root / "evolution" / "genome.yaml"
        if genome_file.exists():
            with open(genome_file, "r", encoding="utf-8") as f:
                genome = yaml.safe_load(f) or {}
            genome.setdefault("harness_genome", {}).setdefault("skills", [])
            for p in proposals:
                if not any(s.get("name") == p["name"] for s in genome["harness_genome"]["skills"]):
                    genome["harness_genome"]["skills"].append({
                        "id": p["id"],
                        "name": p["name"],
                        "source": f"innovation engine: {p['trigger_condition']}",
                        "status": "proposed",
                    })
            with open(genome_file, "w", encoding="utf-8") as f:
                yaml.dump(genome, f, default_flow_style=False, allow_unicode=True)

    return {"status": "innovations_proposed", "proposals": proposals, "current_stage": current_stage, "next_stage": next_stage}


def main():
    parser = argparse.ArgumentParser(description="Innovation Engine — 推陈出新")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--dry-run", action="store_true", help="Propose without saving")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    run_innovation_cycle(project_root, args.dry_run)


if __name__ == "__main__":
    main()
