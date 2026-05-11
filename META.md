# META-HARNESS: Self-Bootstrapping Agent Infrastructure

## What This Is
A meta-harness that GENERATES complete, runnable, self-evolving harness engineering projects.
It does NOT do the work itself — it produces executable systems that do the work.
First principles driven. Evidence based. Never stops at one pass. Innovates beyond requirements.

## The Core Loop (NOT a Pipeline)
```
┌─→ INTERPRET: What does the user actually need? (first principles)
│       ↓
│   GENERATE: Create a COMPLETE harness project (7 layers + 2 cross-cutting + evolution)
│       ↓
│   PROVE:   Does every layer have concrete executable artifacts?
│       ↓
│   JUDGE:   Is the generated project sufficient? ──→ NO → root cause → loop back
│       ↓
│   YES
│       ↓
│   EVOLVE:  What did we learn about generation? Improve the meta-harness.
│       ↓
│   INNOVATE: What can go beyond the original requirements? Propose innovations.
│       ↓
└── LOOP:    Continuous improvement, never stop at "good enough"
```

## Architecture: 7 Layers + 2 Cross-Cutting + Self-Evolution + Innovation

Every generated harness project MUST have all of these layers with executable artifacts:

| Layer | Directory | Purpose | Key Artifacts |
|---|---|---|---|
| 1. Context Engineering | `context/` | Project context, knowledge index, dynamic loading | `loader.py`, `knowledge-index.yaml` |
| 2. Tool Integration | `tools/` | Tool schemas, sandbox, permissions, MCP | `schemas.yaml`, `sandbox.yaml`, `permissions.yaml` |
| 3. Memory & State | `memory/` | Session state, long-term memory, snapshots, compression | `snapshot.py`, `session-state.yaml`, `compression-rules.yaml` |
| 4. Planning & Orchestration | `planning/` | DAG builder, flow control, sub-agent dispatch, budgets | `dag-builder.py`, `flow-control.yaml`, `sub-agent-dispatch.yaml`, `budget.yaml` |
| 5. Verification & Guardrails | `verification/` | Format validators, consistency checks, security, self-check | `consistency-check.py`, `self-check.py`, `security-guardrails.yaml` |
| 6. Feedback & Self-Healing | `feedback/` | Error capture, retry, mistake→constraint, human interface | `error-capture.py`, `mistake-to-constraint.py`, `retry-config.yaml` |
| 7. Constraints & Entropy | `constraints/` | Architecture rules, linter config, entropy reduction, cost | `entropy-reduction.py`, `architecture-rules.yaml`, `cost-budget.yaml` |
| Cross-cutting A: Security | `security/` | Sandbox, encryption, audit | `sandbox-config.yaml`, `encryption-rules.yaml`, `audit-log.yaml` |
| Cross-cutting B: Observability | `observability/` | Tracing, metrics, replay, versioning | `tracing.yaml`, `metrics-dashboard.yaml`, `session-replay.yaml`, `versioning.yaml` |
| Self-Evolution | `evolution/` | Evidence-driven evolution with genome and fitness | `framework.md`, `genome.yaml`, `log.yaml` |
| Innovation | `evolution/` | Post-requirement innovation engine (推陈出新) | `innovation-engine.py`, `product-analyzer.py`, `domain-advancements.yaml` |
| Enforcement (Root) | `./` | Entry points and mandatory pre-action guard | `orchestrator.py`, `guard.py`, `AGENTS.md`, `CLAUDE.md` |

## Enforcement System: guard.py + orchestrator.py

Every generated project MUST have two root-level enforcement scripts:

### guard.py — Pre-Action Constraint Guard
- **Runs BEFORE any code change** — validates planned actions against architecture rules
- Blocks actions that violate constraints (wrong layer access, dependency direction, etc.)
- Returns PASS or BLOCKED with specific violation descriptions
- Checks that orchestrator has been run first
- Usage: `python guard.py --check "I plan to add a new API endpoint"`

### orchestrator.py — Active Execution Engine
- **THE entry point** — tracks progress, manages criteria, enforces verification
- `--status` shows current progress and next criterion
- `--verify` runs full verification suite (self-check + consistency + guard report)
- `--mark-complete` runs verification BEFORE allowing mark — prevents self-certification
- `--evolve` runs evolution cycle after all criteria met
- `--innovate` runs innovation engine (推陈出新)

### Enforcement Chain
```
AI starts → reads AGENTS.md → runs orchestrator.py --status
  → identifies next criterion → runs guard.py --check "plan"
  → if PASS → implements code → runs orchestrator.py --verify
  → if PASS → runs orchestrator.py --mark-complete
  → if ALL DONE → runs orchestrator.py --evolve → --innovate
```

## Innovation Engine: 推陈出新

After all acceptance criteria are met, the system does NOT stop. The innovation engine activates:

1. **Product State Analyzer** (`product-analyzer.py`) scans `src/`, identifies implemented features, endpoints, models, tests
2. **Domain Advancement Patterns** (`domain-advancements*.yaml`) define four stages per domain:
   - **Basic** → **Solid** → **Advanced** → **Excellent**
3. **Innovation Engine** (`innovation-engine.py`) proposes innovations for the next stage
4. Proposals are prioritized by impact/effort ratio and saved to `innovation-log.yaml`
5. High-effort or security innovations require human approval

## Four-Stage Advancement Model

| Stage | Meaning | Web App Examples | API Service Examples |
|-------|---------|-----------------|---------------------|
| Basic | Meets requirements | Core features, basic tests | CRUD endpoints, validation |
| Solid | Production-ready | Error boundaries, loading states, pagination | Rate limiting, health checks, logging |
| Advanced | Competitive quality | Offline support, dark mode, search | Cursor pagination, webhooks, caching |
| Excellent | Market-leading | Real-time collaboration, a11y, i18n | GraphQL, event sourcing, circuit breakers |

## Directory Structure
```
AGENTS.md                  ← Auto-loaded by Trae (primary entry point)
CLAUDE.md                  ← Auto-loaded by Claude Code
META.md                    ← You are here. Full specification.
meta/
  interpreter.md           ← Intent → Structured Task (first principles)
  harness-generator.md     ← Task → Executable Harness Project (7+2+evolution)
  agent-factory.md         ← Harness → Agent Topology (generated, not selected)
  orchestrator.md          ← Loop execution + evidence traceability across all layers
  examples/
    topologies.md          ← Example generated topologies
evolution/                 ← Meta-level evidence-driven self-evolution
  framework.md             ← Evolution algorithm (evidence-based)
  genome.md                ← Current evolvable state snapshot
  log.md                   ← Evolution history
templates/                 ← Domain templates (Generation Factory format)
  web-app/template.md      ← Each template specifies per-layer executable artifacts
  api-service/template.md
  automation/template.md
  data-pipeline/template.md
  content-system/template.md
seeds/                     ← Seed artifacts for each layer (copied by generate.py)
  context/                 ← loader.py, knowledge-index.yaml
  tools/                   ← schemas.yaml, sandbox.yaml, permissions.yaml, mcp-config.json
  memory/                  ← snapshot.py, compression-rules.yaml
  planning/                ← dag-builder.py, flow-control.yaml, sub-agent-dispatch.yaml, budget.yaml
  verification/            ← consistency-check.py, security-guardrails.yaml, self-check.py
  feedback/                ← error-capture.py, retry-config.yaml, mistake-to-constraint.py, human-interface.yaml
  constraints/             ← architecture-rules.yaml, linter-config.yaml, entropy-reduction.py, cost-budget.yaml
  security/                ← sandbox-config.yaml, encryption-rules.yaml, audit-log.yaml
  observability/           ← tracing.yaml, metrics-dashboard.yaml, session-replay.yaml, versioning.yaml
  evolution/               ← framework.md, genome.yaml, log.yaml
                           ← innovation-engine.py (推陈出新)
                           ← product-analyzer.py
                           ← domain-advancements.yaml (Web App)
                           ← domain-advancements-api.yaml (API Service)
  orchestrator.py          ← Entry point for generated projects
scripts/                   ← Executable scripts (cross-platform Python)
  generate.py              ← Core generation pipeline: task → complete harness project
  verify-generation.py     ← Verify 7+2 layer completeness of generated projects
  evolve.py                ← Evidence-driven evolution engine
  verify.py                ← Post-task verification (lint, typecheck, test, secrets)
  pre-task.py              ← Pre-task checks (task card, git status, blockers)
  quality-score.py         ← Harness quality metrics
generated/                 ← Output: generated harness projects (git-ignored)
memory/                    ← Meta-level memory (compounds over time)
  decisions.md             ← Architecture Decision Records
  generation-log.md        ← Generation history (human-readable)
  generation-log.yaml      ← Generation history (machine-readable, maintained by generate.py)
  meta-mistakes.md         ← Meta-harness mistake log
  progress.md              ← Cross-session progress tracking
  task-patterns.md         ← Known task pattern catalog
```

## First Principles (Override Everything)
1. Do not assume the user knows what they want — ask if unclear
2. If goal is clear but path isn't optimal, say so and suggest better
3. Chase root causes, never patch symptoms — every decision answers "why"
4. Output only what changes decisions — cut everything else

## Meta-Rules (Cannot Be Overridden)
1. No execution without interpretation
2. No agent without a harness
3. No constraint without a reason
4. No completion without EVIDENCE — output must prove it satisfies the original need
5. No single-pass execution — the loop continues until evidence proves success
6. No patching symptoms — always chase root causes
7. Generate EXECUTABLE systems, not just documents — every layer must have concrete artifacts
8. Every generated layer must have concrete artifacts — no empty or doc-only layers
9. Every generation is logged
10. Every failure improves the meta (with root cause)
11. The meta-harness follows its own rules
12. Evolution never removes verification (cancer prevention)
13. Evolution never removes itself (suicide prevention)
14. All mutations are reversible
15. After requirements are met, innovation engine MUST run (推陈出新)
16. Innovation proposals require human approval for high-effort or security changes
