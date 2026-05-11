# Generation Log

## Purpose
Track every harness generation. This is the meta-harness's version control.
Enables: learning from past generations, avoiding repeated mistakes, measuring improvement.

The YAML version of this log is maintained by `scripts/generate.py` at
`memory/generation-log.yaml`. This markdown file serves as the human-readable
companion and manual entry point.

## Format
```
## Generation [N]
- Date: [when]
- Intent: [raw user intent]
- Task Name: [generated name]
- Domain: [classified domain]
- Template Used: [which template]
- Topology: [agent topology pattern]
- Output: [path to generated harness]
- Status: Success / Partial / Failed
- Notes: [what went well or wrong]
```

## Generations

(No generations yet. Run `python scripts/generate.py --task <task-file>` to start.)
