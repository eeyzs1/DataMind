# Meta-Harness-Generator: Task → Executable Harness Project

## Purpose
Generate a COMPLETE, RUNNABLE, SELF-EVOLVING harness engineering project.
Not documents. Not descriptions. An executable system with all seven layers.

## What Gets Generated
A full project in `generated/[project-name]/` that includes:

### Layer 1: Context Engineering
- AGENTS.md / CLAUDE.md — project-specific context files
- Dynamic context loader — script that assembles relevant context per task
- Knowledge index — maps which files contain what knowledge

### Layer 2: Tool Integration
- Tool schema definitions (OpenAPI/function-call format)
- Sandbox config (Docker/container config if applicable)
- Permission manifests (what each agent role can access)
- MCP server configs (if applicable)

### Layer 3: Memory & State
- Session state files (progress, checkpoints)
- Long-term memory structure (vector DB config or file-based index)
- Snapshot/rollback mechanism (git-based)
- Memory compression rules (what to keep, what to summarize, what to forget)

### Layer 4: Planning & Orchestration
- Task decomposition engine (DAG builder script)
- Execution flow controller (sequential, parallel, conditional, retry)
- Sub-agent dispatcher (role routing config)
- Reasoning budget config (step limits, time limits, token limits)

### Layer 5: Verification & Guardrails
- Output format validators (JSON/XML schema files)
- Logic consistency checks (test configs, linter rules)
- Security guardrails (sensitive data filters, dangerous operation blockers)
- Self-verification loop script (execute → check → reflect → fix)

### Layer 6: Feedback & Self-Healing
- Error capture and parser (structured error format)
- Auto-retry with backoff strategy config
- Error→constraint optimization loop (mistakes.md → constraints/)
- Human intervention interface (approval queue, escalation config)

### Layer 7: Constraints & Entropy Management
- Architecture constraint rules (dependency direction, layer rules)
- Code enforcement configs (custom linter rules, pre-commit hooks)
- Entropy reduction schedule (cleanup scripts, consistency checks)
- Resource/cost constraints (budget config, rate limits, circuit breakers)

### Cross-Cutting: Security & Isolation
- Environment isolation config (sandbox, network rules)
- Data security rules (encryption, masking, access control)
- Audit log config (traceability, immutability)

### Cross-Cutting: Observability & Governance
- Tracing config (call chains, timing, token consumption)
- Metrics dashboard config (success rate, error rate, latency, cost)
- Session replay config (conversation reconstruction, issue reproduction)
- Version & config management (harness versioning, reproducibility)

### Self-Evolution System
- evolution/framework.md — evidence-driven evolution algorithm
- evolution/genome.md — current evolvable state
- evolution/log.md — evolution history
- Evolution triggers: periodic, reactive, emergency, adaptive

## Generation Steps

1. **Read task definition** from interpreter output
2. **Select base template** from `templates/` as reference (NOT as starting point)
3. **For each layer**: analyze what the task requires, generate ONLY what's needed
4. **Wire layers together**: ensure each layer references the others correctly
5. **Generate entry points**: AGENTS.md, CLAUDE.md, main execution scripts
6. **Generate evolution system**: adapted to the task's specific metrics
7. **Verify completeness**: every layer has at least one concrete artifact

## Output Structure
```
generated/[project-name]/
├── AGENTS.md              ← Project context (auto-loaded by AI IDEs)
├── CLAUDE.md              ← Project context (Claude Code)
├── context/               ← Layer 1: Context Engineering
├── tools/                 ← Layer 2: Tool Integration
├── memory/                ← Layer 3: Memory & State
├── planning/              ← Layer 4: Planning & Orchestration
├── verification/          ← Layer 5: Verification & Guardrails
├── feedback/              ← Layer 6: Feedback & Self-Healing
├── constraints/           ← Layer 7: Constraints & Entropy
├── security/              ← Cross-cutting: Security & Isolation
├── observability/         ← Cross-cutting: Observability & Governance
├── evolution/             ← Self-Evolution System
└── scripts/               ← Executable scripts
```

## Anti-Patterns
- Do NOT generate documentation-only layers — every layer must have executable artifacts
- Do NOT generate boilerplate — only what the specific task requires
- Do NOT skip layers — even minimal implementations are required
- Do NOT generate without evidence traceability — every artifact traces to a requirement
