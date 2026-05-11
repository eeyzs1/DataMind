# Meta-Mistake Log

## Purpose
Log mistakes in the META-HARNESS itself — not in generated projects.
When the meta-harness generates a bad harness, that's a meta-mistake.
Meta-mistakes improve the generation pipeline, not individual projects.

## Format
```
## Meta-Mistake [N]
- Date: [when]
- Trigger: [what intent caused the bad generation]
- What went wrong: [what the generated harness got wrong]
- Root cause: [WHY the meta-harness made this mistake]
- Fix: [what changed in meta/ or templates/]
- Status: Resolved / Recurring / BLOCKER
```

## Meta-Mistakes

### Meta-Mistake 1
- Date: 2026-04-14
- Trigger: Initial project setup
- What went wrong: Templates generated only markdown descriptions, not executable artifacts
- Root cause: Template format was "description framework" instead of "generation factory" — templates listed what should exist but didn't specify executable artifacts per layer
- Fix: Upgraded all 5 templates to "Generation Factory" format with explicit per-layer executable artifact lists; created seeds/ directory with concrete template files (Python scripts, YAML configs, JSON schemas)
- Status: Resolved

### Meta-Mistake 2
- Date: 2026-04-14
- Trigger: Initial project setup
- What went wrong: ADR-001 documented 5-layer architecture but actual design had evolved to 7+2
- Root cause: ADR was written before architecture evolved and never updated
- Fix: Updated ADR-001 to reflect 7 layers + 2 cross-cutting + self-evolution architecture
- Status: Resolved

### Meta-Mistake 3
- Date: 2026-04-14
- Trigger: Running scripts on Windows
- What went wrong: All utility scripts were bash-only, couldn't run on Windows
- Root cause: Original scripts written for Unix without cross-platform consideration
- Fix: Created Python equivalents (verify.py, pre-task.py, quality-score.py) that work on Windows/macOS/Linux
- Status: Resolved
