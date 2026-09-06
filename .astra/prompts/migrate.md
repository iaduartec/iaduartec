Use /home/ubuntu/ASTRA_MIGRATION_AUDIT.md as the baseline.

Design and execute a staged migration toward GPT-6 Astra and the current
Codex architecture.

Use GPT-6 Astra as root orchestrator.

Delegate implementation to cheaper capable subagents whenever appropriate.

Prefer:

Astra:
- architecture
- orchestration
- difficult debugging
- critical decisions
- final integration
- security-sensitive review

Terra:
- implementation
- refactors
- testing
- infrastructure
- normal debugging

Luna:
- discovery
- inventory
- documentation
- mechanical changes
- repetitive checks

Before migrating all repositories:

1. choose one representative canary;
2. record baseline;
3. migrate it;
4. verify;
5. compare;
6. correct architecture if needed.

Do not blindly replace model strings.

For OpenAI API projects:

- prefer Responses API for agentic/tool workflows;
- migrate to gpt-6-astra where intelligence justifies cost;
- remove Astra-incompatible sampling parameters;
- preserve or tune reasoning effort based on workload;
- use caching-compatible stable prompt prefixes;
- evaluate parallel tool calling where useful.

Reduce duplicated AGENTS.md instructions.

Reduce oversized skills.

Remove obsolete hooks only when safely identified.

Do not remove unrelated provider integrations.

Produce:

/home/ubuntu/ASTRA_MIGRATION_REPORT.md
