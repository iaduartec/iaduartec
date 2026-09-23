# Project Bridge structured handoffs

Project Bridge is a local coordination inbox for Codex, OpenCode and AGY. It
does not start agents, execute shell commands on their behalf, schedule work or
replace Git. Git remains authoritative for code; `record_change` remains the
separate record of code changes.

## Daily use

When the user asks another agent to review recent work:

```text
request_handoff(
  to_agent="opencode",
  type="review",
  task="review-auth-refactor",
  title="Review authentication changes",
  summary="Check correctness, regressions and unnecessary complexity.",
  scope=["app/api/auth/", "lib/auth.ts"]
)
```

When the user asks OpenCode to leave implementation work for Codex:

```text
request_handoff(
  to_agent="codex",
  type="implement",
  task="fix-auth-expiration",
  title="Implement the requested auth fixes",
  summary="Apply the accepted findings from the authentication review.",
  scope=["lib/auth.ts"]
)
```

For a second opinion, use `type="second_opinion"` and `to_agent="agy"`.

Do not launch `codex`, `opencode` or `agy` from Project Bridge. The user starts
the receiving agent. At session start the receiving agent should call
`get_handoffs()` (the default inbox is the current agent), inspect the Git HEAD
warning, accept the handoff, do the requested work, and complete it with only a
concise conclusion.

## Lifecycle

```text
pending -> accepted -> in_progress -> completed
       \-> declined
       \-> cancelled
accepted --------------------------> completed
accepted --------------------------> cancelled
in_progress -----------------------> cancelled
```

Phase 2 exposes `request_handoff`, `get_handoffs`, `accept_handoff`,
`complete_handoff` and `cancel_handoff`. There is intentionally no generic
workflow engine, delete operation, decline tool or automatic worker.

`complete_handoff` stores summary, outcome, bounded findings, tests and a
recommended action. It never stores prompts, chain-of-thought, full diffs,
files, credentials or response transcripts. If code changed, call
`record_change` separately.

The source branch, source HEAD and optional base commit are captured when the
handoff is created. A later HEAD change produces `SOURCE STATE CHANGED`; it is
an advisory warning, not a block. Scope is advisory but must stay inside the
repository and cannot contain traversal or secret-bearing paths.

Completed results can be read by the creator with
`get_handoffs(from_agent="<current-agent>", status="completed")`. Reading that
creator inbox marks those results acknowledged. There is no notification
daemon or separate acknowledgement tool in Phase 2.

## CLI and troubleshooting

```bash
.agents/scripts/bridge handoffs
.agents/scripts/bridge handoff H-000001
.agents/scripts/bridge status
.agents/scripts/bridge doctor
```

The SQLite database is `.agents/state/project-bridge.sqlite` and is local and
ignored. Upgrade is automatic and transactional from schema 1 to schema 2;
existing changes, claims and decisions are retained. If an upgrade fails, the
transaction rolls back. Install/upgrade backups are stored in
`.agent-coordination-backup-*/` with `FILES.txt` and `ROLLBACK.md`.
