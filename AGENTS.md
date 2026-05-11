# Meta-Harness — AGENT OPERATING INSTRUCTIONS

## ⚠️ THIS FILE IS YOUR OPERATING SYSTEM. YOU CANNOT DEVIATE.

This project is a META-HARNESS — it does NOT do the work itself.
It GENERATES a complete, runnable, self-evolving harness engineering project
that THEN does the work. Your job is to run the generation pipeline.

**YOU MUST follow the exact protocol below. No shortcuts. No assumptions.**

---

## 🔴 MANDATORY: First Action When Project Opens

1. Read this AGENTS.md completely
2. Understand that you are a GENERATOR, not a builder
3. Identify what the user actually needs (use `meta/interpreter.md`)
4. Follow the pipeline steps BELOW — in order — without skipping

---

## First Principles (Override Everything Else)

1. **Do not assume the user knows what they want.** When unclear, stop and ask.
2. **If the goal is clear but the path isn't optimal, say so.** Suggest the better way.
3. **Chase root causes, never patch symptoms.** Every decision must answer "why".
4. **Output only what changes decisions.** Cut everything else.

---

## 🔵 EXECUTION PIPELINE (MUST Follow Exactly)

```
STEP 1: INTERPRET
  → Read meta/interpreter.md
  → Understand the user's REAL need (not their stated want)
  → Extract acceptance criteria that are MEASURABLE and PROVABLE
  → Surface ALL assumptions — user MUST confirm before you proceed

STEP 2: GENERATE
  → Read meta/harness-generator.md
  → Generate ALL 7 layers + 2 cross-cutting + self-evolution
  → Every layer MUST have executable artifacts (Python scripts, YAML configs, JSON schemas)
  → Output to generated/[project-name]/
  → Run `python scripts/generate.py --task <task.yaml> --template <domain>`
  → VERIFY generation with `python scripts/verify-generation.py <output-dir>`

STEP 3: FACTORY
  → Read meta/agent-factory.md
  → Generate agent topology from task analysis (NOT from preset selection)
  → Configure roles with specific scope, tools, and boundaries
  → Always add an independent verifier agent

STEP 4: PROVE
  → For each of the 7 layers + 2 cross-cutting: verify at least one executable artifact
  → Run `python scripts/verify-generation.py <output-dir>` — MUST pass
  → If FAIL: diagnose root cause, fix the generator, loop back to STEP 2

STEP 5: JUDGE
  → Can the generated project actually run? Can it self-evolve?
  → Does it have guard.py? Does it have orchestrator.py?
  → If NO → root cause analysis → loop back to STEP 2

STEP 6: EVOLVE
  → What did we learn about generation? Improve meta/ and templates/
  → Log to memory/generation-log.yaml
  → Log failures to memory/meta-mistakes.md
  → Run `python scripts/evolve.py` to improve the meta-harness
```

---

## 🔴 ABSOLUTE RULES — CANNOT BE OVERRIDDEN

1. **NO execution without interpretation** — always run interpreter first
2. **NO agent without a harness** — every agent operates within constraints
3. **NO constraint without a reason** — every rule traces to a requirement
4. **NO completion without EVIDENCE** — output must prove it satisfies the need
5. **NO single-pass execution** — loop until evidence proves success
6. **NO patching symptoms** — always chase root causes
7. **Generate EXECUTABLE systems, not just documents** — every layer must have concrete artifacts
8. **Every generated layer must have concrete artifacts** — no empty or doc-only layers
9. **Every generation is logged** — to memory/generation-log.yaml
10. **Every failure improves the meta** — with root cause analysis
11. **The meta-harness follows its own rules** — do as I say AND as I do
12. **Evolution never removes verification** (cancer prevention)
13. **Evolution never removes itself** (suicide prevention)
14. **All mutations are reversible** — keep previous genome version
15. **After requirements are met, innovation engine MUST run** (推陈出新)
16. **Generated projects MUST include guard.py** — no guard, no generation complete

---

## 🛠️ Commands Reference

```bash
# Interpret user intent
python scripts/interpret.py --input "user request"

# Generate complete harness project
python scripts/generate.py --task <task.yaml> --template <domain>

# Verify generation completeness (7+2 layers)
python scripts/verify-generation.py <generated-project-dir>

# Run evolution engine
python scripts/evolve.py --project-root <generated-project-dir>

# Pre-task checks
python scripts/pre-task.py

# Post-task verification
python scripts/verify.py

# Quality score
python scripts/quality-score.py
```

---

## 📁 Key Reference Files

| File | Purpose | When to Read |
|------|---------|-------------|
| `META.md` | Complete system specification | When you need the full picture |
| `meta/interpreter.md` | Intent → Structured Task | STEP 1: Always first |
| `meta/harness-generator.md` | Task → Executable Project | STEP 2: When generating |
| `meta/agent-factory.md` | Harness → Agent Topology | STEP 3: After generation |
| `meta/orchestrator.md` | Loop execution + evidence | STEP 4-5: When proving/judging |
| `evolution/framework.md` | Evolution algorithm | STEP 6: When evolving |
| `seeds/guard.py` | Pre-action constraint guard | Template for generated projects |
| `templates/` | Domain templates | Reference during generation |
