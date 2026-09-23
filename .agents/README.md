# Project Bridge — portable multi-agent coordination kit

Project Bridge is a small, offline, per-repository coordination layer for
Codex, OpenCode and Antigravity (AGY). Git remains authoritative for code,
`AGENTS.md` remains authoritative for rules, and Project Bridge stores only
coordination metadata in local SQLite. It is not an LLM, daemon, scheduler,
workflow engine or agent runtime.

## Phase 2 layout

| Path | Purpose |
|---|---|
| `.agents/project-bridge/bridge.py` | SQLite engine and compact CLI |
| `.agents/project-bridge/server.py` | MCP stdio server (13 tools) |
| `.agents/project-bridge/test_bridge.py` | offline unit/integration tests |
| `.agents/skills/project-bridge-handoff/SKILL.md` | agent handoff protocol |
| `.agents/state/project-bridge.sqlite` | ignored runtime state |
| `.agents/config/bridge.json` | versioned project configuration |

## Handoffs

The five MCP handoff tools are `request_handoff`, `get_handoffs`,
`accept_handoff`, `complete_handoff` and `cancel_handoff`. Valid recipients are
`codex`, `opencode` and `agy`; valid types are `review`, `implement`,
`investigate`, `test` and `second_opinion`. Project Bridge never starts the
recipient. The user opens the next agent normally.

The receiver sees pending work at SessionStart and through `get_handoffs()`.
`accept_handoff` is an atomic pending-to-accepted transition. Completion is
allowed only from accepted or in-progress and must include a structured result.
Cancellation is allowed for either participant while pending, accepted or
in-progress. Invalid transitions and wrong recipients are rejected.

Every handoff captures `source_branch`, `source_head`, optional `base_commit`,
scope and timestamps. If the repository HEAD changed, reads include an
advisory `SOURCE STATE CHANGED` warning. Scope is repo-relative and rejects
absolute paths, traversal and secret-bearing paths. Payload limits and the
existing secret filter apply before SQLite storage.

Results contain only a conclusion, outcome, bounded findings, tests and a
recommended action. Prompts, chain-of-thought, complete responses, diffs,
files, credentials, cookies, tokens and private keys are not stored. A code
change must still be recorded separately with `record_change`.

## Schema and upgrade

The kit is Project Bridge `1.1.0` with SQLite schema `2`. Opening a schema-1
database performs an automatic, transactional, idempotent migration. Existing
`changes`, `claims` and `decisions` remain intact. The new tables are
`handoffs`, `handoff_results` and `handoff_sequence`, with indexes for recipient
and sender status queries. A migration failure rolls back.

## CLI

```bash
.agents/scripts/bridge handoffs
.agents/scripts/bridge handoff H-000001
.agents/scripts/bridge status
.agents/scripts/bridge doctor
```

`status` injects at most a compact pending/result summary; full details require
`get_handoffs`. Creator-side completed results are acknowledged when read via
the creator filter. There is no notification system or delete API in Phase 2.

## Rollback and reset

Each install/upgrade creates a scoped `.agent-coordination-backup-*/` with
`FILES.txt` and `ROLLBACK.md`. Runtime state is not copied. To reset local
coordination state, remove `.agents/state/project-bridge.sqlite`; it will be
recreated and migrated on the next command.

# >>> project-bridge-handoffs >>>
## Structured agent handoffs (Phase 2)

Project Bridge 1.1.0 adds a local SQLite inbox between Codex, OpenCode and AGY.
It coordinates work but never starts an agent, executes an LLM, schedules jobs
or replaces Git. The five MCP tools are `request_handoff`, `get_handoffs`,
`accept_handoff`, `complete_handoff` and `cancel_handoff`.

Valid recipients are `codex`, `opencode` and `agy`; valid types are `review`,
`implement`, `investigate`, `test` and `second_opinion`. The receiver calls
`get_handoffs()`, compares the source HEAD warning, accepts the work, and
completes it with a concise result. If code changed, it calls `record_change`
separately. Project Bridge never launches the recipient.

The lifecycle is `pending -> accepted -> in_progress -> completed`, with
`cancelled` available from pending, accepted and in-progress. Invalid
transitions and wrong recipients are rejected atomically. Results contain only
summary, outcome, bounded findings, tests and recommended action; prompts,
chain-of-thought, full diffs, files and secrets are not stored.

Schema 1 migrates transactionally and idempotently to schema 2 while retaining
changes, claims and decisions. The new tables are `handoffs`,
`handoff_results` and `handoff_sequence`. Scope is repo-relative and payloads
are bounded and secret-filtered. A changed source HEAD is advisory only.

Use `.agents/scripts/bridge handoffs` for a summary and
`.agents/scripts/bridge handoff H-000001` for details. Creator-side completed
results are acknowledged when read with `get_handoffs(from_agent="...")`;
there is no notification daemon or separate acknowledgement tool in Phase 2.
# <<< project-bridge-handoffs <<<
