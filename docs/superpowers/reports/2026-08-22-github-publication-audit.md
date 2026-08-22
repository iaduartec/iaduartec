# GitHub publication audit — 2026-08-22

Scope: current local `main` checkouts and their fetched `origin/main` refs, reviewed with `git ls-files`, remote trees, repository history, references, ignore rules, README commands, and secret-name/content scans. Values of credentials and private data are intentionally omitted.

## Findings

| Repository | Local result | Remote result | Action |
|---|---|---|---|
| `mission-bridge` | Removed stale `state.json`, corrected setup docs/verifier and ignore rules, and made the identity allowlist fail closed; service checks static `200` and dynamic anonymous `401`. | `origin/main` no longer contains `state.json` or `server.log`. | Published fast-forward at `433a01a`. |
| `duartec-infra` | Removed the Oracle snapshot and unused root monolithic `Caddyfile`; separated route identities, authenticates before method rejection, added noVNC password secrets, bounded mail sessions, and removed an obsolete Caddy proposal. | `origin/main` no longer contains `ops/oracle/2026-08-22/`, the root `Caddyfile`, or the proposal document. | Published fast-forward at `dc25bba`. |
| `projects/trading` | Reconciled local `main` with the published dependency/security branch without discarding local commits; API Lab and full suite pass (`168/168`). | `origin/main` retains only `artifacts/latest/.gitkeep`; no logs/runtime outputs remain. | Published fast-forward at `481aa28`. |
| `portfolio-repo` | Removed 37 MB of tracked `.codex-n8n-backups` (SQLite plus JSON exports), added an explicit ignore, and kept placeholder-only `.env.example`. | `origin/main` no longer contains the eight backup blobs. | Published fast-forward at `30b8599`; rotate any historical credentials before deployment. |
| root/InsForge | README and idempotent ownership migration now enforce owner-scoped RLS, enabled RLS, and least-privilege API grants; historical root `.env` was removed from all published branch history. | `db migrations up --all` applied the ownership migration; CLI policies and local runtime both verify `auth.uid()` isolation and no `anon` grants. | Published with the rewritten root history; provider-side rotation is still required for the three active historical keys. |

## Deletion safety

The local cleanup removed reproducible runtime outputs and stale state from working trees. The root `.env` history was purged after an explicit user request; no production service data, cookies, current credentials, or live volumes were touched. Other repositories were not history-rewritten.

## Publication gate

The four private remotes were reconciled and updated with fast-forward pushes from the reviewed `main` checkouts. Trading was merged conservatively so its local commits were preserved while incorporating the published dependency/security branch. The public root repository `iaduartec/iaduartec` was rewritten only to remove the historical `.env` and force-updated all published branches; no other repository history was rewritten. Credential rotation remains an operational follow-up for the three still-active provider keys.
