#!/usr/bin/env python3
"""
Interpreter: Intent → Structured Task Definition (First Principles)

Parses a raw intent string and produces a structured task definition
following the interpreter.md specification. This is the first step
of the compilation pipeline.

Usage:
    python scripts/interpret.py --intent "I need a customer onboarding system"
    python scripts/interpret.py --intent-file intent.txt
"""

import argparse
import json
import sys
from pathlib import Path

import yaml

DOMAIN_KEYWORDS = {
    "web-app": ["web app", "website", "frontend", "ui", "dashboard", "portal", "landing page", "spa"],
    "api-service": ["api", "rest", "graphql", "backend", "microservice", "endpoint", "server"],
    "automation": ["automate", "schedule", "cron", "workflow", "trigger", "monitor", "alert", "bot"],
    "data-pipeline": ["data pipeline", "etl", "ingest", "transform", "analytics", "warehouse", "batch"],
    "content-system": ["content", "blog", "cms", "publish", "article", "document", "newsletter"],
}

SCALE_KEYWORDS = {
    "personal": ["personal", "my", "i need", "simple", "just me"],
    "team": ["team", "our", "we need", "group", "department"],
    "organization": ["company", "organization", "enterprise", "everyone", "all employees"],
    "public": ["public", "users", "customers", "saas", "marketplace"],
}


def classify_domain(intent: str) -> str:
    intent_lower = intent.lower()
    scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        scores[domain] = sum(1 for kw in keywords if kw in intent_lower)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "web-app"


def classify_scale(intent: str) -> str:
    intent_lower = intent.lower()
    for scale, keywords in SCALE_KEYWORDS.items():
        if any(kw in intent_lower for kw in keywords):
            return scale
    return "team"


def extract_goal(intent: str) -> str:
    goal = intent.strip()
    prefixes = ["i need ", "i want ", "build ", "create ", "make ", "help me "]
    for prefix in prefixes:
        if goal.lower().startswith(prefix):
            goal = goal[len(prefix):].strip()
    return goal[0].upper() + goal[1:] if goal else "Complete the task"


def generate_acceptance_criteria(intent: str, domain: str) -> list:
    criteria = []
    if domain == "api-service":
        criteria = [
            "API endpoints respond with correct status codes",
            "Input validation rejects invalid requests",
            "Error responses follow consistent format",
            "API documentation is auto-generated",
        ]
    elif domain == "web-app":
        criteria = [
            "Users can complete the primary workflow end-to-end",
            "UI is responsive on mobile and desktop",
            "Authentication works correctly",
            "Build succeeds with no errors",
        ]
    elif domain == "automation":
        criteria = [
            "Automation triggers correctly on events",
            "Actions produce expected results",
            "Error handling works (simulate failures)",
            "Manual override is available",
        ]
    elif domain == "data-pipeline":
        criteria = [
            "Data is ingested without loss",
            "Transformations produce correct output",
            "Error records are quarantined, not dropped",
            "Pipeline completes within time budget",
        ]
    elif domain == "content-system":
        criteria = [
            "Content follows style guide",
            "Review step catches quality issues",
            "Metadata is complete before publication",
            "Version history is maintained",
        ]
    return criteria


def interpret_intent(intent: str) -> dict:
    domain = classify_domain(intent)
    scale = classify_scale(intent)
    goal = extract_goal(intent)

    task = {
        "name": goal[:80],
        "domain": domain.replace("-", "_"),
        "real_need": intent.strip(),
        "goal": goal,
        "scale": scale,
        "quality_attributes": [],
        "hard_constraints": [],
        "soft_constraints": [],
        "acceptance_criteria": generate_acceptance_criteria(intent, domain),
        "unknowns": [
            "Exact technical stack preference",
            "Authentication method",
            "Deployment target",
        ],
        "assumptions": [
            f"Domain classified as {domain} based on intent keywords",
            f"Scale classified as {scale} based on intent keywords",
            "Acceptance criteria are initial suggestions — user should refine",
        ],
    }
    return task


def main():
    parser = argparse.ArgumentParser(description="Meta-Harness Interpreter")
    parser.add_argument("--intent", default=None, help="Raw intent string")
    parser.add_argument("--intent-file", default=None, help="File containing raw intent")
    parser.add_argument("--output", default=None, help="Output task definition file (YAML)")
    args = parser.parse_args()

    if args.intent:
        intent = args.intent
    elif args.intent_file:
        intent_file = Path(args.intent_file)
        if not intent_file.exists():
            print(f"ERROR: Intent file not found: {intent_file}")
            sys.exit(1)
        intent = intent_file.read_text(encoding="utf-8").strip()
    else:
        print("ERROR: Provide --intent or --intent-file")
        sys.exit(1)

    task = interpret_intent(intent)

    output = yaml.dump(task, default_flow_style=False, allow_unicode=True)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Task definition written to: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
