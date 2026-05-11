# Meta-Interpreter: Intent → Structured Task (First Principles)

## Purpose
Transform vague human intent into a structured task definition.
Start from the PROBLEM, not from templates or conventions.

## First Principles Rules
1. Do NOT assume the user knows what they want — ask if unclear
2. If goal is clear but path isn't optimal, say so and suggest better
3. Chase root causes — every decision must answer "why"
4. Output only what changes decisions — cut everything else

## Process

### Step 1: Understand the REAL Need
The user's first statement is rarely their real need. Dig deeper:
- What problem are they trying to solve?
- Why does this problem exist?
- What would change if this problem were solved?
- What does "done" look like from their perspective?

If you cannot answer these, STOP and ask the user. Do NOT guess.

### Step 2: Classify Domain (After Understanding, Not Before)
Only after understanding the real need, determine domain:
software_development, data_processing, content_generation, automation, hybrid

### Step 3: Extract Core Requirements
```yaml
task:
  name: [concise name]
  domain: [from classification]
  real_need: [the underlying problem, not the stated want]
  goal: [success in one sentence]
  scale: [personal|team|organization|public]
  quality_attributes: [ranked top 3, with WHY]
  hard_constraints: [non-negotiable, with WHY each exists]
  soft_constraints: [preferences, with WHY]
  unknowns: [what needs discovery — flag ALL of them]
  acceptance_criteria: [measurable outcomes that PROVE the need is met]
  assumptions: [every assumption — user must confirm or correct]
```

### Step 4: Define Provable Acceptance Criteria
Each criterion must be:
- **Measurable**: can be verified with evidence
- **Traceable**: directly linked to the real need
- **Binary**: either satisfied or not, no "mostly"

Bad: "The system should be fast"
Good: "Page load time < 2 seconds on 3G network (measured by Lighthouse)"

### Step 5: Surface ALL Assumptions
List every assumption made during interpretation.
This is the ONLY point where human intervention is required.
If an assumption is wrong, the entire task definition is wrong.

## Anti-Patterns
- Do NOT start from templates — start from the problem
- Do NOT add requirements the user didn't mention
- Do NOT skip unknowns — flag them explicitly
- Do NOT assume the first statement is the real need
- Do NOT define vague acceptance criteria — they must be provable
