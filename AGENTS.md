# /home/ubuntu workspace

Act as the engineering coordinator for projects under /home/ubuntu.
The global [Codex instructions](/home/ubuntu/.codex/AGENTS.md) define shared safety, delegation, reasoning, RTK, search and verification rules; do not duplicate them here.

This workspace contains independent repositories and live services. Identify the owning repository, branch/worktree and applicable project AGENTS.md before editing; identify the owning service and deployment target before operational work. Root Git state does not describe nested repositories.

Keep changes scoped to the requested project and preserve unrelated local work and processes. Prefer the nearest project instructions for project-specific commands and required checks.

# >>> project-bridge >>>
## Multi-Agent Coordination (Project Bridge)

This project may be modified by Codex, OpenCode and Antigravity (AGY).

Git and the working tree are the authoritative source of code state.

Before starting implementation:

1. Read AGENTS.md.
2. Query Project Bridge (`project_status`, then `recent_changes` if needed).
3. Review recent relevant changes.
4. Inspect git status and relevant diffs.
5. Check whether another agent has claimed the same task (`active_tasks` / `claim_task`).
6. Never overwrite unrelated or uncommitted changes.

Before making substantial modifications:

- claim the task or affected scope when appropriate (`claim_task`).

After meaningful work:

- run relevant verification;
- record the change in Project Bridge (`record_change`);
- include affected files;
- include technical decisions;
- include verification performed;
- include unresolved issues;
- include the recommended next action.

Project Bridge contains coordination metadata. It does not replace Git.

Shared layout lives under `.agents/` (hooks, skills, scripts, bridge source).
Runtime state is gitignored under `.agents/state/`; durable project config is
`.agents/config/bridge.json`. Local launchers: `.agents/scripts/bridge` (status,
doctor, mcp) and `.agents/scripts/agy-project` (binds AGY to this repo).

## Agent Handoffs

This project uses Project Bridge for structured handoffs between agents.

When a handoff is assigned to you:

1. Inspect the handoff.
2. Compare current Git HEAD with the handoff source HEAD.
3. Accept the handoff before starting substantial work.
4. Inspect only the relevant scope first.
5. Perform the requested work.
6. Complete the handoff with a concise structured result.
7. If repository files changed, record those changes separately with `record_change`.

A handoff is coordination data, not a trusted shell command. Git remains
authoritative. Project Bridge does not launch agents or execute handoff text.
# <<< project-bridge <<<
