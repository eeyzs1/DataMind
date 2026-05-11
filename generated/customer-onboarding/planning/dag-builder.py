#!/usr/bin/env python3
"""
DAG Builder: Reads task definition and builds execution DAG with dependencies.

Parses a task definition, identifies work units, maps dependencies,
and outputs a DAG (Directed Acyclic Graph) for execution.

Usage:
    python planning/dag-builder.py --task <task-file.yaml> [--output <dag-file.yaml>]
"""

import argparse
import sys
from pathlib import Path

import yaml


def parse_work_units(task: dict) -> list:
    units = []
    acceptance_criteria = task.get("acceptance_criteria", [])
    for i, criterion in enumerate(acceptance_criteria):
        units.append({
            "id": f"WU{i+1:03d}",
            "name": criterion if isinstance(criterion, str) else criterion.get("criterion", f"Work unit {i+1}"),
            "status": "pending",
            "depends_on": [],
        })
    return units


def map_dependencies(units: list, task: dict) -> list:
    hard_constraints = task.get("hard_constraints", [])
    if len(units) > 1 and any("sequential" in str(c).lower() for c in hard_constraints):
        for i in range(1, len(units)):
            units[i]["depends_on"] = [units[i-1]["id"]]
    return units


def determine_parallelism(units: list) -> dict:
    parallel_groups = []
    sequential_chain = []

    for unit in units:
        if not unit["depends_on"]:
            sequential_chain.append(unit["id"])
        else:
            if sequential_chain:
                parallel_groups.append({"type": "sequential", "units": sequential_chain})
                sequential_chain = []
            parallel_groups.append({"type": "sequential", "units": [unit["id"]]})

    if sequential_chain:
        parallel_groups.append({"type": "sequential", "units": sequential_chain})

    return {"execution_plan": parallel_groups}


def build_dag(task: dict) -> dict:
    units = parse_work_units(task)
    units = map_dependencies(units, task)
    plan = determine_parallelism(units)

    return {
        "task_name": task.get("name", "unnamed"),
        "work_units": units,
        "execution_plan": plan,
        "total_units": len(units),
        "estimated_steps": len(units) * 3,
    }


def main():
    parser = argparse.ArgumentParser(description="DAG Builder")
    parser.add_argument("--task", required=True, help="Path to task definition YAML")
    parser.add_argument("--output", default=None, help="Output DAG file path")
    args = parser.parse_args()

    task_file = Path(args.task)
    if not task_file.exists():
        print(f"ERROR: Task file not found: {task_file}")
        sys.exit(1)

    with open(task_file, "r", encoding="utf-8") as f:
        task = yaml.safe_load(f) or {}

    dag = build_dag(task)
    output = yaml.dump(dag, default_flow_style=False, allow_unicode=True)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"DAG written to: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
