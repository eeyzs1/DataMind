# Genome State

## Purpose
Snapshot of the current evolvable configuration.
This is what gets mutated during evolution.

## Current Genome

### Harness Genome
```yaml
constraints:
  - id: C001
    rule: "every task must have acceptance criteria"
    source: "initial design"
    last_triggered: null
    trigger_count: 0

  - id: C002
    rule: "no agent self-certifies"
    source: "initial design"
    last_triggered: null
    trigger_count: 0

  - id: C003
    rule: "every mistake produces a new constraint"
    source: "initial design"
    last_triggered: null
    trigger_count: 0

workflows:
  - id: W001
    name: "base flow"
    steps: [define, plan, execute, verify, record]
    source: "initial design"

skills:
  - id: S001
    name: "self-verify"
    source: "initial design"

  - id: S002
    name: "task-decompose"
    source: "initial design"
```

### Agent Genome
```yaml
topology_rules:
  - "always add verifier"
  - "merge tightly coupled roles"
  - "split when context exceeds budget"

default_scope:
  max_context_lines: 60
  handoff_format: "structured YAML"
```

### Evolution Genome (Meta)
```yaml
fitness_weights:
  verification_pass_rate: 0.3
  task_completion_rate: 0.25
  error_recurrence_rate: 0.2
  time_to_completion: 0.15
  constraint_efficiency: 0.1

mutation_rate: 0.1
selection_threshold: "fitness must improve or complexity must decrease"
safety_constraints:
  - "never remove verification layer"
  - "never remove evolution system"
  - "mutation rate <= 30%"
  - "all mutations reversible"
```

## Genome Version
- Version: 1
- Last evolved: 2026-04-14
- Total mutations applied: 0
