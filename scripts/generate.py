#!/usr/bin/env python3
"""
Meta-Harness Generator: Task → Complete Executable Harness Project

Reads a task definition (from interpreter output) and generates a complete
7-layer + 2 cross-cutting + evolution harness project with executable artifacts
in every layer. Output is customized per domain template.

Usage:
    python scripts/generate.py --task <task-file.yaml> [--template <domain>] [--output <dir>]
    python scripts/generate.py --task task.yaml --template api-service --output generated/my-project
"""

import argparse
import json
import os
import re
import shutil
import sys
import yaml
from datetime import datetime
from pathlib import Path

META_DIR = Path(__file__).resolve().parent.parent / "meta"
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
SEEDS_DIR = Path(__file__).resolve().parent.parent / "seeds"
HARNESS_ROOT = Path(__file__).resolve().parent.parent

TASK_SCHEMA = {
    "type": "object",
    "required": ["name", "domain", "goal"],
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "domain": {"type": "string", "minLength": 1},
        "real_need": {"type": "string"},
        "goal": {"type": "string", "minLength": 1},
        "scale": {"type": "string"},
        "quality_attributes": {"type": "array"},
        "hard_constraints": {"type": "array"},
        "soft_constraints": {"type": "array"},
        "acceptance_criteria": {"type": "array"},
        "unknowns": {"type": "array"},
        "assumptions": {"type": "array"},
    },
}

LAYER_DIRS = {
    "context": "Layer 1: Context Engineering",
    "tools": "Layer 2: Tool Integration",
    "memory": "Layer 3: Memory & State",
    "planning": "Layer 4: Planning & Orchestration",
    "verification": "Layer 5: Verification & Guardrails",
    "feedback": "Layer 6: Feedback & Self-Healing",
    "constraints": "Layer 7: Constraints & Entropy",
    "security": "Cross-Cutting: Security & Isolation",
    "observability": "Cross-Cutting: Observability & Governance",
    "evolution": "Self-Evolution",
}

LAYER_ARTIFACTS = {
    "context": ["loader.py", "knowledge-index.yaml"],
    "tools": ["schemas.yaml", "sandbox.yaml", "permissions.yaml", "mcp-config.json"],
    "memory": ["session-state.yaml", "compression-rules.yaml", "snapshot.py"],
    "planning": ["dag-builder.py", "flow-control.yaml", "sub-agent-dispatch.yaml", "budget.yaml"],
    "verification": ["consistency-check.py", "security-guardrails.yaml", "self-check.py"],
    "feedback": ["error-capture.py", "retry-config.yaml", "mistake-to-constraint.py", "human-interface.yaml"],
    "constraints": ["architecture-rules.yaml", "linter-config.yaml", "entropy-reduction.py", "cost-budget.yaml"],
    "security": ["sandbox-config.yaml", "encryption-rules.yaml", "audit-log.yaml"],
    "observability": ["tracing.yaml", "metrics-dashboard.yaml", "session-replay.yaml", "versioning.yaml"],
    "evolution": ["framework.md", "genome.yaml", "log.yaml"],
}


def _get_src_dirs(template_name: str) -> list:
    src_layouts = {
        "web-app": ["src/api", "src/components", "src/services", "src/repositories", "src/models", "src/utils", "tests"],
        "api-service": ["src/routes", "src/services", "src/repositories", "src/models", "src/utils", "schemas", "tests"],
        "automation": ["src/triggers", "src/actions", "src/conditions", "src/monitors", "src/utils", "tests"],
        "data-pipeline": ["src/ingest", "src/transforms", "src/validate", "src/output", "src/utils", "schemas", "tests"],
        "content-system": ["src/research", "src/drafts", "src/reviews", "src/templates", "src/utils", "tests"],
    }
    return src_layouts.get(template_name, ["src", "tests"])


def validate_task(task: dict) -> list:
    errors = []
    for field in TASK_SCHEMA.get("required", []):
        if field not in task or not task[field]:
            errors.append(f"Missing required field: {field}")
    props = TASK_SCHEMA.get("properties", {})
    for key, value in task.items():
        if key in props:
            expected_type = props[key].get("type")
            if expected_type == "string" and not isinstance(value, str):
                errors.append(f"Field '{key}' must be a string")
            elif expected_type == "array" and not isinstance(value, list):
                errors.append(f"Field '{key}' must be an array")
    if "acceptance_criteria" in task and isinstance(task["acceptance_criteria"], list):
        if len(task["acceptance_criteria"]) == 0:
            errors.append("acceptance_criteria should not be empty (tasks need measurable outcomes)")
    return errors


def load_task(task_file: Path) -> dict:
    if not task_file.exists():
        print(f"ERROR: Task file not found: {task_file}")
        sys.exit(1)
    with open(task_file, "r", encoding="utf-8") as f:
        if task_file.suffix in (".yaml", ".yml"):
            task = yaml.safe_load(f)
        elif task_file.suffix == ".json":
            task = json.load(f)
        else:
            print(f"ERROR: Unsupported task file format: {task_file.suffix}")
            sys.exit(1)

    if not task or not isinstance(task, dict):
        print("ERROR: Task file is empty or not a valid object")
        sys.exit(1)

    errors = validate_task(task)
    if errors:
        print("ERROR: Task definition validation failed:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    return task


def detect_template(task: dict) -> str:
    domain = task.get("domain", "").lower()
    domain_map = {
        "software_development": "web-app",
        "web_app": "web-app",
        "web_application": "web-app",
        "api_service": "api-service",
        "api": "api-service",
        "automation": "automation",
        "data_processing": "data-pipeline",
        "data_pipeline": "data-pipeline",
        "etl": "data-pipeline",
        "content_generation": "content-system",
        "content_system": "content-system",
    }
    return domain_map.get(domain, "web-app")


def parse_template(template_file: Path) -> dict:
    if not template_file.exists():
        return {"constraints": [], "workflows": [], "agent_topology": [], "verification_checklist": [], "quality_attributes": []}
    content = template_file.read_text(encoding="utf-8")
    result = {"constraints": [], "workflows": [], "agent_topology": [], "verification_checklist": [], "quality_attributes": []}

    sections = re.split(r"^### ", content, flags=re.MULTILINE)
    for section in sections:
        if section.startswith("Constraints (seed"):
            items = re.findall(r"^- (.+)$", section, re.MULTILINE)
            result["constraints"] = [item.strip() for item in items]
        elif section.startswith("Workflows (seed"):
            blocks = re.split(r"^- ", section)
            for block in blocks:
                if ":" in block:
                    name = block.split(":")[0].strip()
                    steps_match = re.search(r"→\s*(.+)$", block, re.MULTILINE)
                    steps = steps_match.group(1).split(" → ") if steps_match else []
                    result["workflows"].append({"name": name, "steps": [s.strip() for s in steps]})
        elif section.startswith("Agent Topology (seed"):
            lines = section.strip().split("\n")
            current_pattern = None
            for line in lines:
                line = line.strip()
                if "pattern:" in line.lower() or "Three-Agent" in line or "Planner-Executor" in line or "Pipeline" in line:
                    current_pattern = line.rstrip(":")
                elif line.startswith("- ") and current_pattern:
                    result["agent_topology"].append({"role": line[2:].strip(), "pattern": current_pattern})
        elif section.startswith("Verification Checklist (seed"):
            items = re.findall(r"^- (.+)$", section, re.MULTILINE)
            result["verification_checklist"] = [item.strip() for item in items]
        elif section.startswith("Quality Attributes Priority"):
            items = re.findall(r"^\d+\.\s+(\w+)", section, re.MULTILINE)
            result["quality_attributes"] = items

    return result


def load_template(template_name: str) -> dict:
    template_file = TEMPLATES_DIR / template_name / "template.md"
    if not template_file.exists():
        print(f"WARNING: Template not found: {template_file}, using web-app")
        template_file = TEMPLATES_DIR / "web-app" / "template.md"
    parsed = parse_template(template_file)
    return {"path": template_file, "name": template_name, "parsed": parsed}


def copy_seed_artifacts(output_dir: Path, layer: str) -> list:
    seed_dir = SEEDS_DIR / layer
    layer_dir = output_dir / layer
    layer_dir.mkdir(parents=True, exist_ok=True)
    copied = []

    if seed_dir.exists():
        for item in seed_dir.iterdir():
            dest = layer_dir / item.name
            if item.is_file():
                shutil.copy2(item, dest)
                copied.append(dest.relative_to(output_dir))
            elif item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
                for f in dest.rglob("*"):
                    if f.is_file():
                        copied.append(f.relative_to(output_dir))
    return copied


def customize_knowledge_index(output_dir: Path, template: dict) -> None:
    ki_file = output_dir / "context" / "knowledge-index.yaml"
    if not ki_file.exists():
        return
    with open(ki_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    template_name = template.get("name", "web-app")
    domain_mappings = {
        "web-app": {"src/api/": "API endpoints and contracts", "src/components/": "UI components", "src/services/": "Business logic", "src/repositories/": "Data access"},
        "api-service": {"src/routes/": "API route handlers", "src/services/": "Business logic layer", "src/repositories/": "Data access layer", "src/models/": "Data models and types", "schemas/": "API schema definitions"},
        "automation": {"triggers/": "Event trigger definitions", "actions/": "Automation action handlers", "monitors/": "Health check monitors", "workflows/": "Automation workflow configs"},
        "data-pipeline": {"schemas/": "Data schema definitions", "transforms/": "Data transformation logic", "quality/": "Data validation rules", "pipelines/": "Pipeline configurations"},
        "content-system": {"templates/": "Content structure templates", "style-guide/": "Writing rules and style", "topics/": "Subject matter knowledge", "reviews/": "Content review records"},
    }
    if template_name in domain_mappings:
        data["mappings"] = domain_mappings[template_name]

    with open(ki_file, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def customize_architecture_rules(output_dir: Path, template: dict) -> None:
    rules_file = output_dir / "constraints" / "architecture-rules.yaml"
    if not rules_file.exists():
        return
    with open(rules_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    parsed = template.get("parsed", {})
    domain_constraints = parsed.get("constraints", [])
    if domain_constraints:
        existing_ids = {r.get("id", "") for r in data.get("rules", [])}
        next_id = len(data.get("rules", [])) + 1
        for constraint in domain_constraints:
            rule_id = f"DC{next_id:03d}"
            if rule_id not in existing_ids:
                data.setdefault("rules", []).append({
                    "id": rule_id,
                    "description": constraint,
                    "pattern": "",
                    "severity": "warning",
                    "source": f"domain template: {template.get('name', 'unknown')}",
                })
                next_id += 1

    template_name = template.get("name", "web-app")
    dep_directions = {
        "web-app": {"allowed": ["frontend → api", "api → service", "service → repo", "repo → DB"], "forbidden": ["DB → repo", "repo → service", "service → api", "frontend → DB"]},
        "api-service": {"allowed": ["route → service", "service → repository", "repository → database"], "forbidden": ["database → repository", "repository → service", "service → route"]},
        "automation": {"allowed": ["trigger → condition → action", "action → verify → log"], "forbidden": ["action → trigger", "log → action"]},
        "data-pipeline": {"allowed": ["ingest → validate → transform → output", "output → audit"], "forbidden": ["output → ingest", "transform → ingest"]},
        "content-system": {"allowed": ["research → draft → review → publish"], "forbidden": ["publish → draft", "review → research"]},
    }
    if template_name in dep_directions:
        data["dependency_direction"] = dep_directions[template_name]

    with open(rules_file, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def customize_flow_control(output_dir: Path, template: dict) -> None:
    flow_file = output_dir / "planning" / "flow-control.yaml"
    if not flow_file.exists():
        return
    with open(flow_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    parsed = template.get("parsed", {})
    domain_workflows = parsed.get("workflows", [])
    if domain_workflows:
        for wf in domain_workflows:
            wf_name = wf.get("name", "custom").lower().replace(" ", "_")
            steps = wf.get("steps", [])
            if steps:
                flow_steps = []
                for i, step in enumerate(steps):
                    flow_step = {"name": step.lower().replace(" ", "_"), "next": []}
                    if i < len(steps) - 1:
                        flow_step["next"] = [steps[i + 1].lower().replace(" ", "_")]
                    flow_steps.append(flow_step)
                data["workflows"][wf_name] = {"type": "sequential", "steps": flow_steps}

    with open(flow_file, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def customize_sub_agent_dispatch(output_dir: Path, template: dict) -> None:
    dispatch_file = output_dir / "planning" / "sub-agent-dispatch.yaml"
    if not dispatch_file.exists():
        return
    with open(dispatch_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    parsed = template.get("parsed", {})
    agent_topology = parsed.get("agent_topology", [])
    if agent_topology:
        data["roles"] = []
        for agent in agent_topology:
            role_name = agent.get("role", "unknown").lower().split(":")[0].strip()
            data["roles"].append({
                "name": role_name,
                "responsibilities": [agent.get("role", "")],
                "receives": [],
                "produces": [],
            })

    with open(dispatch_file, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def customize_cost_budget(output_dir: Path, template: dict) -> None:
    budget_file = output_dir / "constraints" / "cost-budget.yaml"
    if not budget_file.exists():
        return

    template_name = template.get("name", "web-app")
    domain_budgets = {
        "web-app": {"api": {"max_response_time_seconds": 2}, "build": {"max_bundle_size_kb": 500}, "cost": {"max_monthly_infra_cost_usd": 50}},
        "api-service": {"api": {"max_response_time_seconds": 0.5}, "database": {"max_query_time_seconds": 0.1}, "cost": {"max_monthly_infra_cost_usd": 30}},
        "automation": {"runtime": {"max_automation_runtime_seconds": 1800}, "cost": {"max_monthly_compute_cost_usd": 20}},
        "data-pipeline": {"runtime": {"max_pipeline_runtime_seconds": 3600}, "storage": {"max_data_storage_gb": 10}, "cost": {"max_monthly_compute_cost_usd": 40}},
        "content-system": {"content": {"max_content_pieces_per_day": 20}, "cost": {"max_monthly_api_cost_usd": 15}},
    }

    with open(budget_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if template_name in domain_budgets:
        for category, limits in domain_budgets[template_name].items():
            if category in data.get("limits", {}):
                data["limits"][category].update(limits)
            else:
                data.setdefault("limits", {})[category] = limits

    with open(budget_file, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def generate_agents_md(output_dir: Path, task: dict, template: dict) -> None:
    name = task.get("name", "Generated Project")
    real_need = task.get("real_need", "See task definition")
    goal = task.get("goal", "Complete the task successfully")
    template_name = template.get("name", "web-app")
    parsed = template.get("parsed", {})

    constraints_section = ""
    domain_constraints = parsed.get("constraints", [])
    if domain_constraints:
        constraints_lines = [f"- {c}" for c in domain_constraints]
        constraints_section = "\n### Domain Constraints (YOU MUST FOLLOW)\n" + "\n".join(constraints_lines)

    workflows_section = ""
    domain_workflows = parsed.get("workflows", [])
    if domain_workflows:
        workflow_lines = []
        for wf in domain_workflows:
            steps = " → ".join(wf.get("steps", []))
            workflow_lines.append(f"- **{wf.get('name', 'custom')}**: {steps}")
        workflows_section = "\n### Domain Workflows\n" + "\n".join(workflow_lines)

    topology_section = ""
    agent_topology = parsed.get("agent_topology", [])
    if agent_topology:
        topology_lines = []
        for agent in agent_topology:
            topology_lines.append(f"- {agent.get('role', 'unknown')}")
        topology_section = "\n### Agent Topology (Your Role Assignment)\n" + "\n".join(topology_lines)

    checklist_section = ""
    verification_checklist = parsed.get("verification_checklist", [])
    if verification_checklist:
        checklist_section = "\n### Mandatory Verification Checklist\n" + "\n".join(f"- [ ] {c}" for c in verification_checklist)

    acceptance_section = ""
    criteria = task.get("acceptance_criteria", [])
    if criteria:
        acceptance_section = "\n### Acceptance Criteria (Implement One At A Time)\n" + "\n".join(f"- [ ] {c}" for c in criteria)

    content = f"""# {name} — EXECUTION PROTOCOL

## ⚠️ THIS FILE IS YOUR OPERATING SYSTEM. YOU CANNOT DEVIATE FROM IT.

This project is governed by an automated harness. You are an AI agent operating
within this harness. The harness dictates WHAT you do, HOW you do it, and HOW
your work is verified. You DO NOT have freedom to choose your own approach.

---

## 🔴 CRITICAL: Mandatory Startup Sequence

**The FIRST thing you MUST do when this project is opened:**

1. Run `python orchestrator.py --status` and READ the output
2. Identify the NEXT pending criterion
3. Follow the EXACT workflow below

**YOU MUST NEVER skip the orchestrator. Every action goes through it.**

---

## 🔵 Execution Loop (This Is Your ONLY Workflow)

You MUST follow this loop for EVERY criterion. No exceptions.

```
STEP 1: PLAN    → Read constraints in constraints/architecture-rules.yaml
                  Read workflow in planning/flow-control.yaml
                  Plan your implementation BEFORE writing code

STEP 2: GUARD   → Run python guard.py --check "describe what you plan to do"
                  (You MUST describe your plan; guard will block violations)

STEP 3: IMPLEMENT → Write code following:
                  - The domain constraints listed below
                  - The architecture rules in constraints/
                  - The workflow sequence in planning/

STEP 4: VERIFY  → Run python orchestrator.py --verify
                  (You MUST run this; do not skip)

STEP 5: FIX     → If verification fails:
                  Run python feedback/error-capture.py to analyze errors
                  Fix the root cause (not symptoms)
                  Go back to STEP 4

STEP 6: MARK    → Run python orchestrator.py --mark-complete "criterion text"
                  (Only when verification passes)

STEP 7: REPEAT  → Go to STEP 1 for the next pending criterion
```

---

## 🟡 BEFORE You Write ANY Code — Mandatory Pre-Checks

You MUST complete ALL of these before creating or modifying any file:

1. ✅ Run `python guard.py --check "describe your plan"` and get a PASS
2. ✅ Read `constraints/architecture-rules.yaml` and confirm understanding
3. ✅ Identify which domain constraints apply to your current task
4. ✅ Confirm the dependency direction (allowed/forbidden in arch rules)

**If guard.py returns BLOCKED, you CANNOT proceed. Fix your plan first.**

---

## 🟢 After ALL Criteria Are Satisfied

```
python orchestrator.py --evolve     # System self-improvement
python orchestrator.py --innovate  # Innovation engine (推陈出新)
```

---

## 📋 Project Definition

### Real Need
{real_need}

### Goal
{goal}

### Domain Template
{template_name}

### Architecture (Reference)
7 layers + 2 cross-cutting + self-evolution:
- Layer 1: Context Engineering → context/
- Layer 2: Tool Integration → tools/
- Layer 3: Memory & State → memory/
- Layer 4: Planning & Orchestration → planning/
- Layer 5: Verification & Guardrails → verification/
- Layer 6: Feedback & Self-Healing → feedback/
- Layer 7: Constraints & Entropy → constraints/
- Cross-cutting A: Security & Isolation → security/
- Cross-cutting B: Observability & Governance → observability/
- Self-Evolution → evolution/
{constraints_section}
{workflows_section}
{topology_section}
{checklist_section}
{acceptance_section}

---

## 🔴 ABSOLUTE RULES — CANNOT BE OVERRIDDEN

1. NO code without first running `python guard.py --check`
2. NO completion without running `python orchestrator.py --verify`
3. NO constraint violation — guard.py will block you
4. NO skipping steps in the execution loop
5. NO implementing multiple criteria at once — ONE at a time
6. NO self-certification — only orchestrator marks criteria complete
7. NO symptom patching — chase root causes
8. NO deviation from domain constraints listed above
9. Evolution never removes verification or itself
10. All mutations reversible

---

## 🛠️ Quick Reference Commands

```bash
python orchestrator.py --status                              # MUST run first
python guard.py --check "your plan description"              # MUST run before code
python orchestrator.py --verify                              # MUST run after code
python orchestrator.py --mark-complete "criterion text"      # Mark as done
python orchestrator.py --evolve                              # Self-improvement
python orchestrator.py --innovate                            # Innovation suggestions
python feedback/error-capture.py --error-output <file>      # Analyze errors
python constraints/entropy-reduction.py                      # Clean up code
```
"""
    (output_dir / "AGENTS.md").write_text(content, encoding="utf-8")
    (output_dir / "CLAUDE.md").write_text(content, encoding="utf-8")
    (output_dir / ".cursorrules").write_text(content, encoding="utf-8")


def generate_session_state(output_dir: Path, task: dict) -> None:
    state = {
        "task_name": task.get("name", "unknown"),
        "created_at": datetime.now().isoformat(),
        "status": "initialized",
        "progress": {
            "layers_generated": list(LAYER_DIRS.keys()),
            "acceptance_criteria": task.get("acceptance_criteria", []),
            "completed_criteria": [],
            "failed_criteria": [],
        },
        "checkpoints": [],
    }
    memory_dir = output_dir / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    with open(memory_dir / "session-state.yaml", "w", encoding="utf-8") as f:
        yaml.dump(state, f, default_flow_style=False, allow_unicode=True)

    long_term_dir = memory_dir / "long-term"
    long_term_dir.mkdir(parents=True, exist_ok=True)
    (long_term_dir / ".gitkeep").write_text("", encoding="utf-8")


def generate_evolution_genome(output_dir: Path, task: dict, template: dict) -> None:
    parsed = template.get("parsed", {})
    domain_constraints = parsed.get("constraints", [])

    constraints = [
        {"id": "C001", "rule": "every task must have acceptance criteria", "source": "initial design", "last_triggered": None, "trigger_count": 0},
        {"id": "C002", "rule": "no agent self-certifies", "source": "initial design", "last_triggered": None, "trigger_count": 0},
        {"id": "C003", "rule": "every mistake produces a new constraint", "source": "initial design", "last_triggered": None, "trigger_count": 0},
    ]
    for i, dc in enumerate(domain_constraints, 4):
        constraints.append({"id": f"C{i:03d}", "rule": dc, "source": f"domain template: {template.get('name', 'unknown')}", "last_triggered": None, "trigger_count": 0})

    domain_workflows = parsed.get("workflows", [])
    workflows = [{"id": "W001", "name": "base flow", "steps": ["define", "plan", "execute", "verify", "record"], "source": "initial design"}]
    for i, wf in enumerate(domain_workflows, 2):
        workflows.append({"id": f"W{i:03d}", "name": wf.get("name", "custom"), "steps": wf.get("steps", []), "source": f"domain template: {template.get('name', 'unknown')}"})

    genome = {
        "version": 1,
        "created_at": datetime.now().isoformat(),
        "last_evolved": None,
        "total_mutations": 0,
        "harness_genome": {
            "constraints": constraints,
            "workflows": workflows,
            "skills": [
                {"id": "S001", "name": "self-verify", "source": "initial design"},
                {"id": "S002", "name": "task-decompose", "source": "initial design"},
            ],
        },
        "agent_genome": {
            "topology_rules": ["always add verifier", "merge tightly coupled roles", "split when context exceeds budget"],
            "default_scope": {"max_context_lines": 60, "handoff_format": "structured YAML"},
        },
        "evolution_genome": {
            "fitness_weights": {
                "evidence_satisfaction_rate": 0.35,
                "loop_efficiency": 0.25,
                "root_cause_hit_rate": 0.2,
                "goal_drift_rate": 0.2,
            },
            "mutation_rate": 0.1,
            "selection_threshold": "fitness must improve or complexity must decrease",
            "safety_constraints": [
                "never remove verification layer",
                "never remove evolution system",
                "mutation rate <= 30%",
                "all mutations reversible",
            ],
        },
    }
    evo_dir = output_dir / "evolution"
    evo_dir.mkdir(parents=True, exist_ok=True)
    with open(evo_dir / "genome.yaml", "w", encoding="utf-8") as f:
        yaml.dump(genome, f, default_flow_style=False, allow_unicode=True)

    log = {"version": 1, "mutations": []}
    with open(evo_dir / "log.yaml", "w", encoding="utf-8") as f:
        yaml.dump(log, f, default_flow_style=False, allow_unicode=True)


def generate_format_validators(output_dir: Path) -> None:
    validators_dir = output_dir / "verification" / "format-validators"
    validators_dir.mkdir(parents=True, exist_ok=True)

    api_contract_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "API Contract",
        "type": "object",
        "required": ["endpoint", "method", "request", "response"],
        "properties": {
            "endpoint": {"type": "string", "pattern": "^/"},
            "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]},
            "request": {"type": "object"},
            "response": {"type": "object", "required": ["status", "body"]},
            "auth_required": {"type": "boolean", "default": True},
        },
    }
    with open(validators_dir / "api-contract.schema.json", "w", encoding="utf-8") as f:
        json.dump(api_contract_schema, f, indent=2, ensure_ascii=False)

    config_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Config File",
        "type": "object",
        "required": ["version", "type"],
        "properties": {
            "version": {"type": "integer", "minimum": 1},
            "type": {"type": "string"},
            "description": {"type": "string"},
        },
    }
    with open(validators_dir / "config.schema.json", "w", encoding="utf-8") as f:
        json.dump(config_schema, f, indent=2, ensure_ascii=False)


def verify_completeness(output_dir: Path) -> dict:
    results = {}
    for layer, artifacts in LAYER_ARTIFACTS.items():
        layer_dir = output_dir / layer
        found = []
        missing = []
        for artifact in artifacts:
            if (layer_dir / artifact).exists():
                found.append(artifact)
            else:
                missing.append(artifact)
        results[layer] = {
            "description": LAYER_DIRS[layer],
            "found": found,
            "missing": missing,
            "complete": len(missing) == 0,
        }
    return results


def print_verification(results: dict) -> bool:
    all_complete = True
    print("\n" + "=" * 60)
    print("GENERATION COMPLETENESS VERIFICATION")
    print("=" * 60)

    for layer, info in results.items():
        status = "✅ COMPLETE" if info["complete"] else "❌ INCOMPLETE"
        print(f"\n{info['description']} ({layer}/)")
        print(f"  Status: {status}")
        if info["found"]:
            print(f"  Found: {', '.join(info['found'])}")
        if info["missing"]:
            print(f"  Missing: {', '.join(info['missing'])}")
            all_complete = False

    print("\n" + "=" * 60)
    if all_complete:
        print("✅ ALL LAYERS COMPLETE — every layer has concrete artifacts")
    else:
        print("❌ SOME LAYERS INCOMPLETE — missing executable artifacts")
    print("=" * 60)
    return all_complete


def generate(task: dict, template_name: str, output_dir: Path) -> None:
    template = load_template(template_name)
    print(f"Generating harness project: {output_dir}")
    print(f"Task: {task.get('name', 'unnamed')}")
    print(f"Template: {template_name}")
    print(f"Domain constraints from template: {len(template.get('parsed', {}).get('constraints', []))}")
    print(f"Domain workflows from template: {len(template.get('parsed', {}).get('workflows', []))}")

    if output_dir.exists():
        print(f"WARNING: Output directory exists, overwriting: {output_dir}")
        shutil.rmtree(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    scripts_dir = output_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "task.yaml", "w", encoding="utf-8") as f:
        yaml.dump(task, f, default_flow_style=False, allow_unicode=True)

    src_dirs = _get_src_dirs(template_name)
    for src_dir in src_dirs:
        (output_dir / src_dir).mkdir(parents=True, exist_ok=True)
        (output_dir / src_dir / "__init__.py").write_text("", encoding="utf-8")

    orchestrator_seed = SEEDS_DIR / "orchestrator.py"
    if orchestrator_seed.exists():
        shutil.copy2(orchestrator_seed, output_dir / "orchestrator.py")

    guard_seed = SEEDS_DIR / "guard.py"
    if guard_seed.exists():
        shutil.copy2(guard_seed, output_dir / "guard.py")

    evolve_script = HARNESS_ROOT / "scripts" / "evolve.py"
    if evolve_script.exists():
        shutil.copy2(evolve_script, scripts_dir / "evolve.py")

    for layer in LAYER_DIRS:
        layer_dir = output_dir / layer
        layer_dir.mkdir(parents=True, exist_ok=True)
        copied = copy_seed_artifacts(output_dir, layer)
        if copied:
            print(f"  Copied {len(copied)} seed artifacts to {layer}/")

    customize_knowledge_index(output_dir, template)
    customize_architecture_rules(output_dir, template)
    customize_flow_control(output_dir, template)
    customize_sub_agent_dispatch(output_dir, template)
    customize_cost_budget(output_dir, template)

    generate_agents_md(output_dir, task, template)
    generate_session_state(output_dir, task)
    generate_evolution_genome(output_dir, task, template)
    generate_format_validators(output_dir)

    meta_framework = HARNESS_ROOT / "evolution" / "framework.md"
    if meta_framework.exists():
        evo_dir = output_dir / "evolution"
        evo_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(meta_framework, evo_dir / "framework.md")

    innovation_seeds = SEEDS_DIR / "evolution"
    evo_output = output_dir / "evolution"
    evo_output.mkdir(parents=True, exist_ok=True)
    for seed_file in ["product-analyzer.py", "innovation-engine.py"]:
        src = innovation_seeds / seed_file
        if src.exists():
            shutil.copy2(src, evo_output / seed_file)

    domain_adv = SEEDS_DIR / "evolution" / f"domain-advancements-{template_name}.yaml"
    generic_adv = SEEDS_DIR / "evolution" / "domain-advancements.yaml"
    if domain_adv.exists():
        shutil.copy2(domain_adv, evo_output / "domain-advancements.yaml")
    elif generic_adv.exists():
        shutil.copy2(generic_adv, evo_output / "domain-advancements.yaml")

    results = verify_completeness(output_dir)
    all_complete = print_verification(results)

    generation_log = {
        "timestamp": datetime.now().isoformat(),
        "task_name": task.get("name", "unnamed"),
        "template": template_name,
        "domain_constraints_applied": len(template.get("parsed", {}).get("constraints", [])),
        "domain_workflows_applied": len(template.get("parsed", {}).get("workflows", [])),
        "output_dir": str(output_dir),
        "completeness": {k: v["complete"] for k, v in results.items()},
        "all_complete": all_complete,
    }

    meta_log_dir = HARNESS_ROOT / "memory"
    meta_log_dir.mkdir(parents=True, exist_ok=True)
    log_file = meta_log_dir / "generation-log.yaml"
    existing_logs = []
    if log_file.exists():
        with open(log_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if data and "entries" in data:
                existing_logs = data["entries"]

    existing_logs.append(generation_log)
    with open(log_file, "w", encoding="utf-8") as f:
        yaml.dump({"entries": existing_logs}, f, default_flow_style=False, allow_unicode=True)

    if not all_complete:
        print("\n⚠️  Generation incomplete. Some layers are missing artifacts.")
        sys.exit(1)
    else:
        print(f"\n✅ Generation complete: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Meta-Harness Generator")
    parser.add_argument("--task", required=True, help="Path to task definition file (YAML/JSON)")
    parser.add_argument("--template", default=None, help="Domain template name (auto-detected if not specified)")
    parser.add_argument("--output", default=None, help="Output directory (default: generated/<task-name>)")

    args = parser.parse_args()

    task_file = Path(args.task)
    task = load_task(task_file)

    template_name = args.template or detect_template(task)
    task_name = task.get("name", "unnamed").lower().replace(" ", "-")
    output_dir = Path(args.output) if args.output else HARNESS_ROOT / "generated" / task_name

    generate(task, template_name, output_dir)


if __name__ == "__main__":
    main()
