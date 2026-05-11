#!/usr/bin/env python3
"""
Context Loader: Assembles relevant context per task.

Reads a task card, matches it against the knowledge index,
and loads the relevant constraints, workflows, and skills.

Usage:
    python context/loader.py --task <task-card.yaml>
"""

import argparse
import sys
from pathlib import Path

import yaml


def load_knowledge_index(project_root: Path) -> dict:
    index_file = project_root / "context" / "knowledge-index.yaml"
    if not index_file.exists():
        return {}
    with open(index_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_constraints(project_root: Path) -> list:
    rules_file = project_root / "constraints" / "architecture-rules.yaml"
    if not rules_file.exists():
        return []
    with open(rules_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("rules", [])


def load_workflows(project_root: Path) -> list:
    flow_file = project_root / "planning" / "flow-control.yaml"
    if not flow_file.exists():
        return []
    with open(flow_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("workflows", [])


def load_skills(project_root: Path) -> list:
    dispatch_file = project_root / "planning" / "sub-agent-dispatch.yaml"
    if not dispatch_file.exists():
        return []
    with open(dispatch_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("roles", [])


def match_context(task: dict, knowledge_index: dict) -> list:
    matched = []
    task_keywords = set()
    for field in ["name", "domain", "real_need", "goal"]:
        val = task.get(field, "")
        if val:
            task_keywords.update(str(val).lower().split())

    for path, domain in knowledge_index.items():
        domain_words = set(str(domain).lower().split())
        if task_keywords & domain_words:
            matched.append({"path": path, "domain": domain})

    return matched


def assemble_context(task: dict, project_root: Path) -> dict:
    knowledge_index = load_knowledge_index(project_root)
    constraints = load_constraints(project_root)
    workflows = load_workflows(project_root)
    skills = load_skills(project_root)
    matched_paths = match_context(task, knowledge_index)

    return {
        "task_name": task.get("name", "unknown"),
        "matched_knowledge": matched_paths,
        "active_constraints": constraints,
        "active_workflows": workflows,
        "available_roles": skills,
        "project_root": str(project_root),
    }


def main():
    parser = argparse.ArgumentParser(description="Context Loader")
    parser.add_argument("--task", required=True, help="Path to task card YAML")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    args = parser.parse_args()

    task_file = Path(args.task)
    if not task_file.exists():
        print(f"ERROR: Task file not found: {task_file}")
        sys.exit(1)

    with open(task_file, "r", encoding="utf-8") as f:
        task = yaml.safe_load(f) or {}

    project_root = Path(args.project_root).resolve()
    context = assemble_context(task, project_root)

    print(yaml.dump(context, default_flow_style=False, allow_unicode=True))


if __name__ == "__main__":
    main()
