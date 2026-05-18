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
import sys
from pathlib import Path

import yaml

DOMAIN_KEYWORDS = {
    "web-app": [
        "web app", "website", "frontend", "ui", "dashboard",
        "portal", "landing page", "spa", "react", "vue", "angular", "svelte",
    ],
    "api-service": ["api", "rest", "graphql", "backend", "microservice", "endpoint", "server", "grpc", "webhook"],
    "automation": [
        "automate", "schedule", "cron", "workflow", "trigger",
        "monitor", "alert", "bot", "ci/cd", "pipeline",
    ],
    "data-pipeline": [
        "data pipeline", "etl", "ingest", "transform", "analytics",
        "warehouse", "batch", "stream", "lakehouse",
    ],
    "content-system": ["content", "blog", "cms", "publish", "article", "document", "newsletter", "media", "editorial"],
}

SCALE_KEYWORDS = {
    "personal": ["personal", "my", "i need", "simple", "just me", "myself"],
    "team": ["team", "our", "we need", "group", "department", "squad"],
    "organization": ["company", "organization", "enterprise", "everyone", "all employees", "org-wide"],
    "public": ["public", "users", "customers", "saas", "marketplace", "external"],
}

QUALITY_KEYWORDS = {
    "reliability": ["reliable", "stable", "uptime", "fault-tolerant", "resilient", "robust"],
    "performance": ["fast", "performant", "scalable", "low-latency", "high-throughput", "responsive"],
    "security": ["secure", "auth", "encryption", "compliance", "privacy", "gdpr", "hipaa"],
    "usability": ["easy", "intuitive", "accessible", "user-friendly", "a11y"],
    "maintainability": ["maintainable", "clean", "modular", "testable", "documented"],
}


def classify_domain(intent: str) -> str:
    intent_lower = intent.lower()
    scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw in intent_lower:
                score += len(kw.split())
        scores[domain] = score
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "web-app"


def classify_scale(intent: str) -> str:
    intent_lower = intent.lower()
    for scale, keywords in SCALE_KEYWORDS.items():
        if any(kw in intent_lower for kw in keywords):
            return scale
    return "team"


def extract_quality_attributes(intent: str) -> list:
    intent_lower = intent.lower()
    attributes = []
    for attr, keywords in QUALITY_KEYWORDS.items():
        if any(kw in intent_lower for kw in keywords):
            attributes.append(attr)
    if not attributes:
        attributes = ["reliability", "maintainability", "usability"]
    return attributes[:3]


def extract_goal(intent: str) -> str:
    goal = intent.strip()
    prefixes = ["i need ", "i want ", "build ", "create ", "make ", "help me "]
    for prefix in prefixes:
        if goal.lower().startswith(prefix):
            goal = goal[len(prefix):].strip()
    return goal[0].upper() + goal[1:] if goal else "Complete the task"


def extract_hard_constraints(intent: str, domain: str) -> list:
    constraints = []
    intent_lower = intent.lower()
    constraint_indicators = ["must", "require", "mandatory", "no ", "never", "cannot", "should not", "forbidden"]
    for indicator in constraint_indicators:
        if indicator in intent_lower:
            idx = intent_lower.index(indicator)
            fragment = intent[idx:idx + 80].strip().rstrip(".,;")
            if fragment and fragment not in constraints:
                constraints.append(fragment)
    if domain == "api-service" and "authentication" not in intent_lower:
        constraints.append("API must have authentication")
    return constraints


def generate_acceptance_criteria(intent: str, domain: str) -> list:
    criteria = []
    if domain == "api-service":
        criteria = [
            "API endpoints respond with correct status codes for valid and invalid requests",
            "Input validation rejects malformed requests with descriptive error messages",
            "Error responses follow a consistent JSON format across all endpoints",
            "API documentation is auto-generated from code annotations",
        ]
    elif domain == "web-app":
        criteria = [
            "Users can complete the primary workflow end-to-end without errors",
            "UI is responsive on mobile (375px) and desktop (1440px) viewports",
            "Authentication and authorization work correctly for all user roles",
            "Build succeeds with no errors and no console warnings",
        ]
    elif domain == "automation":
        criteria = [
            "Automation triggers correctly on configured events",
            "Actions produce expected results with idempotent behavior",
            "Error handling works: simulate failures and verify recovery",
            "Manual override is available for all automated actions",
        ]
    elif domain == "data-pipeline":
        criteria = [
            "Data is ingested without loss (row count matches source)",
            "Transformations produce correct output (validated with sample data)",
            "Error records are quarantined, not silently dropped",
            "Pipeline completes within the configured time budget",
        ]
    elif domain == "content-system":
        criteria = [
            "Content follows the defined style guide rules",
            "Review step catches quality issues before publication",
            "Metadata is complete and validated before publication",
            "Version history is maintained for all content changes",
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
        "quality_attributes": extract_quality_attributes(intent),
        "hard_constraints": extract_hard_constraints(intent, domain),
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
