#!/usr/bin/env bash
set -euo pipefail

echo "=== Harness Quality Score ==="
echo ""

if [ -f "memory/meta-mistakes.md" ]; then
    TOTAL=$(grep -c "## Meta-Mistake" memory/meta-mistakes.md 2>/dev/null || echo 0)
    RESOLVED=$(grep -c "Status: Resolved" memory/meta-mistakes.md 2>/dev/null || echo 0)
    if [ "$TOTAL" -gt 0 ]; then
        RATE=$(( (TOTAL - RESOLVED) * 100 / TOTAL ))
    else
        RATE=0
    fi
    echo "  Mistake Recurrence Rate: ${RATE}% (lower is better)"
fi

GENERATION_COUNT=$(find generated -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')
echo "  Generated Projects: ${GENERATION_COUNT}"

TEMPLATE_COUNT=$(find templates -name "template.md" 2>/dev/null | wc -l | tr -d ' ')
echo "  Domain Templates: ${TEMPLATE_COUNT}"

echo ""
echo "=== Recommendations ==="
if [ "${RATE:-0}" -gt 20 ]; then
    echo "  HIGH recurrence rate. Review memory/meta-mistakes.md and improve pipeline."
fi
