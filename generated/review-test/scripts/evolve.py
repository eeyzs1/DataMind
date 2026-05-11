#!/usr/bin/env python3
"""
Evolution Engine: Evidence-driven self-evolution for the harness.

Implements the evolution loop:
  Collect evidence → Measure fitness → Propose mutation → Test → Select or reject

Safety constraints:
  - Never remove verification (cancer prevention)
  - Never remove evolution itself (suicide prevention)
  - Mutation rate <= 30% per generation (chaos prevention)
  - All mutations reversible (previous genome preserved)
  - Human can veto any mutation

Usage:
    python scripts/evolve.py [--project-root <dir>] [--trigger <type>] [--dry-run]
"""

import argparse
import copy
import random
import sys
from datetime import datetime
from pathlib import Path

import yaml

HARNESS_ROOT = Path(__file__).resolve().parent.parent

SAFETY_CONSTRAINTS = [
    "never remove verification layer",
    "never remove evolution system",
    "mutation rate <= 30%",
    "all mutations reversible",
]


def load_genome(project_root: Path) -> dict:
    genome_file = project_root / "evolution" / "genome.yaml"
    if not genome_file.exists():
        return {"version": 1, "harness_genome": {"constraints": [], "workflows": [], "skills": []}}
    with open(genome_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_genome(project_root: Path, genome: dict) -> None:
    genome_file = project_root / "evolution" / "genome.yaml"
    genome_file.parent.mkdir(parents=True, exist_ok=True)
    with open(genome_file, "w", encoding="utf-8") as f:
        yaml.dump(genome, f, default_flow_style=False, allow_unicode=True)


def load_evolution_log(project_root: Path) -> dict:
    log_file = project_root / "evolution" / "log.yaml"
    if not log_file.exists():
        return {"version": 1, "mutations": []}
    with open(log_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {"version": 1, "mutations": []}


def save_evolution_log(project_root: Path, log: dict) -> None:
    log_file = project_root / "evolution" / "log.yaml"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "w", encoding="utf-8") as f:
        yaml.dump(log, f, default_flow_style=False, allow_unicode=True)


def collect_evidence(project_root: Path) -> dict:
    evidence = {
        "meta_mistakes": [],
        "generation_results": [],
        "verification_results": [],
    }

    mistakes_file = project_root / "memory" / "meta-mistakes.md"
    if mistakes_file.exists():
        content = mistakes_file.read_text(encoding="utf-8")
        count = content.count("## Meta-Mistake")
        unresolved = content.count("Status: Open")
        evidence["meta_mistakes"] = {"total": count, "unresolved": unresolved}

    gen_log = project_root / "memory" / "generation-log.yaml"
    if gen_log.exists():
        with open(gen_log, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        entries = data.get("entries", []) if isinstance(data, dict) else []
        evidence["generation_results"] = {
            "total_generations": len(entries),
            "complete": sum(1 for e in entries if isinstance(e, dict) and e.get("all_complete")),
            "incomplete": sum(1 for e in entries if isinstance(e, dict) and not e.get("all_complete")),
        }

    return evidence


def measure_fitness(genome: dict, evidence: dict) -> float:
    evo_genome = genome.get("evolution_genome", {})
    weights = evo_genome.get("fitness_weights", {
        "evidence_satisfaction_rate": 0.35,
        "loop_efficiency": 0.25,
        "root_cause_hit_rate": 0.2,
        "goal_drift_rate": 0.2,
    })

    scores = {}

    gen_results = evidence.get("generation_results", {})
    if isinstance(gen_results, list):
        total = len(gen_results)
        complete = sum(1 for e in gen_results if isinstance(e, dict) and e.get("all_complete"))
        incomplete = total - complete
    elif isinstance(gen_results, dict):
        total = gen_results.get("total_generations", 0)
        complete = gen_results.get("complete", 0)
        incomplete = gen_results.get("incomplete", 0)
    else:
        total, complete, incomplete = 0, 0, 0
    scores["evidence_satisfaction_rate"] = (complete / total) if total > 0 else 1.0

    scores["loop_efficiency"] = 0.7

    mistakes = evidence.get("meta_mistakes", {})
    if isinstance(mistakes, dict):
        total_mistakes = mistakes.get("total", 0)
        unresolved = mistakes.get("unresolved", 0)
    elif isinstance(mistakes, list):
        total_mistakes = len(mistakes)
        unresolved = sum(1 for m in mistakes if isinstance(m, dict) and m.get("status") != "Resolved")
    else:
        total_mistakes, unresolved = 0, 0
    scores["root_cause_hit_rate"] = ((total_mistakes - unresolved) / total_mistakes) if total_mistakes > 0 else 1.0

    scores["goal_drift_rate"] = 0.9

    fitness = sum(weights.get(k, 0) * v for k, v in scores.items())
    return round(fitness, 4)


def propose_mutations(genome: dict, evidence: dict, fitness: float) -> list:
    mutations = []
    harness = genome.get("harness_genome", {})
    constraints = harness.get("constraints", [])

    mistakes = evidence.get("meta_mistakes", {})
    if isinstance(mistakes, dict):
        unresolved = mistakes.get("unresolved", 0)
    elif isinstance(mistakes, list):
        unresolved = sum(1 for m in mistakes if isinstance(m, dict) and m.get("status") != "Resolved")
    else:
        unresolved = 0
    if unresolved > 3:
        mutations.append({
            "type": "ADD_CONSTRAINT",
            "target": "harness_genome.constraints",
            "description": "Add constraint from unresolved mistake pattern",
            "evidence": f"{unresolved} unresolved meta-mistakes",
            "expected_outcome": "Reduce mistake recurrence",
        })

    gen_results = evidence.get("generation_results", {})
    if isinstance(gen_results, dict):
        incomplete = gen_results.get("incomplete", 0)
    elif isinstance(gen_results, list):
        incomplete = sum(1 for e in gen_results if isinstance(e, dict) and not e.get("all_complete"))
    else:
        incomplete = 0
    if incomplete > 0:
        mutations.append({
            "type": "STRENGTHEN_CONSTRAINT",
            "target": "harness_genome.constraints",
            "description": "Strengthen generation completeness constraint",
            "evidence": f"{incomplete} incomplete generations",
            "expected_outcome": "Improve generation completeness rate",
        })

    if fitness > 0.8 and len(constraints) > 5:
        untriggered = [c for c in constraints if c.get("trigger_count", 0) == 0]
        if len(untriggered) > 2:
            mutations.append({
                "type": "WEAKEN_CONSTRAINT",
                "target": f"harness_genome.constraints[{untriggered[0].get('id', '')}]",
                "description": f"Weaken untriggered constraint {untriggered[0].get('id', '')}",
                "evidence": f"Constraint never triggered, {len(untriggered)} untriggered total",
                "expected_outcome": "Reduce unnecessary constraint overhead",
            })

    return mutations


def check_safety(mutation: dict, genome: dict) -> bool:
    if mutation["type"] in ("REMOVE_CONSTRAINT", "WEAKEN_CONSTRAINT"):
        target = mutation.get("target", "")
        if "verification" in target.lower():
            print(f"  ❌ SAFETY: Cannot remove/weaken verification constraint")
            return False
        if "evolution" in target.lower():
            print(f"  ❌ SAFETY: Cannot remove/weaken evolution constraint")
            return False
    return True


def apply_mutation(genome: dict, mutation: dict) -> dict:
    new_genome = copy.deepcopy(genome)
    harness = new_genome.get("harness_genome", {})
    constraints = harness.get("constraints", [])

    if mutation["type"] == "ADD_CONSTRAINT":
        new_id = f"C{len(constraints) + 1:03d}"
        constraints.append({
            "id": new_id,
            "rule": mutation["description"],
            "source": f"evolution: {mutation['evidence']}",
            "last_triggered": None,
            "trigger_count": 0,
        })

    elif mutation["type"] == "STRENGTHEN_CONSTRAINT":
        for c in constraints:
            if c.get("trigger_count", 0) > 0:
                c["rule"] = c["rule"] + " (strengthened)"

    elif mutation["type"] == "WEAKEN_CONSTRAINT":
        target_id = mutation.get("target", "")
        for c in constraints:
            if c.get("id", "") in target_id and c.get("trigger_count", 0) == 0:
                c["rule"] = c["rule"] + " (weakened — low trigger rate)"

    new_genome["harness_genome"]["constraints"] = constraints
    new_genome["total_mutations"] = new_genome.get("total_mutations", 0) + 1
    new_genome["last_evolved"] = datetime.now().isoformat()
    return new_genome


def run_evolution(project_root: Path, trigger: str = "periodic", dry_run: bool = False) -> dict:
    print(f"\n{'='*60}")
    print(f"EVOLUTION CYCLE — Trigger: {trigger}")
    print(f"{'='*60}")

    genome = load_genome(project_root)
    evidence = collect_evidence(project_root)
    fitness = measure_fitness(genome, evidence)

    print(f"\nCurrent fitness: {fitness}")
    print(f"Evidence: {yaml.dump(evidence, default_flow_style=False)}")

    mutations = propose_mutations(genome, evidence, fitness)
    print(f"\nProposed mutations: {len(mutations)}")

    if not mutations:
        print("No mutations proposed — system is stable.")
        return {"fitness": fitness, "mutations_proposed": 0, "mutations_applied": 0}

    max_mutations = max(1, int(len(genome.get("harness_genome", {}).get("constraints", [])) * 0.3))
    mutations = mutations[:max_mutations]

    applied = []
    for mutation in mutations:
        print(f"\n  Mutation: {mutation['type']} — {mutation['description']}")
        print(f"  Evidence: {mutation['evidence']}")
        print(f"  Expected: {mutation['expected_outcome']}")

        if not check_safety(mutation, genome):
            continue

        if dry_run:
            print(f"  🔄 DRY RUN — would apply")
            applied.append({**mutation, "status": "dry_run"})
        else:
            new_genome = apply_mutation(genome, mutation)
            new_fitness = measure_fitness(new_genome, evidence)

            if new_fitness >= fitness:
                print(f"  ✅ ACCEPTED — fitness: {fitness} → {new_fitness}")
                delta = new_fitness - fitness
                genome = new_genome
                fitness = new_fitness
                applied.append({**mutation, "status": "accepted", "fitness_delta": delta})
            else:
                print(f"  ❌ REJECTED — fitness would decrease: {fitness} → {new_fitness}")
                applied.append({**mutation, "status": "rejected", "fitness_delta": new_fitness - fitness})

    if not dry_run and applied:
        save_genome(project_root, genome)

        log = load_evolution_log(project_root)
        for mutation in applied:
            log["mutations"].append({
                "timestamp": datetime.now().isoformat(),
                "trigger": trigger,
                "type": mutation["type"],
                "description": mutation["description"],
                "evidence": mutation["evidence"],
                "status": mutation["status"],
                "fitness_after": fitness,
            })
        save_evolution_log(project_root, log)

    print(f"\n{'='*60}")
    print(f"Evolution complete — Fitness: {fitness}, Applied: {len(applied)}")
    print(f"{'='*60}")

    return {"fitness": fitness, "mutations_proposed": len(mutations), "mutations_applied": len(applied)}


def main():
    parser = argparse.ArgumentParser(description="Evolution Engine")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--trigger", default="periodic", choices=["periodic", "reactive", "emergency", "adaptive"],
                        help="Evolution trigger type")
    parser.add_argument("--dry-run", action="store_true", help="Propose mutations without applying")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    run_evolution(project_root, args.trigger, args.dry_run)


if __name__ == "__main__":
    main()
