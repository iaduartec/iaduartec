# GitHub publication audit — 2026-08-22

Scope: current local `main` checkouts and their fetched `origin/main` refs, reviewed with `git ls-files`, remote trees, repository history, references, ignore rules, README commands, and secret-name/content scans. Values of credentials and private data are intentionally omitted.

## Findings

| Repository | Local result | Remote result | Action |
|---|---|---|---|
| `mission-bridge` | Removed stale `state.json`, corrected setup docs/verifier and ignore rules, and made the identity allowlist fail closed; service checks static `200` and dynamic anonymous `401`. | `origin/main` no longer contains `state.json` or `server.log`. | Published fast-forward at `433a01a`. |
| `duartec-infra` | Removed the Oracle snapshot and unused root monolithic `Caddyfile`; separated route identities, added noVNC password secrets, bounded mail sessions, and removed an obsolete Caddy proposal. | `origin/main` no longer contains `ops/oracle/2026-08-22/`, the root `Caddyfile`, or the proposal document. | Published fast-forward at `d6eaf18`. |
| `projects/trading` | Reconciled local `main` with the published dependency/security branch without discarding local commits; API Lab and full suite pass (`168/168`). | `origin/main` retains only `artifacts/latest/.gitkeep`; no logs/runtime outputs remain. | Published fast-forward at `481aa28`. |
| `portfolio-repo` | Removed 37 MB of tracked `.codex-n8n-backups` (SQLite plus JSON exports), added an explicit ignore, and kept placeholder-only `.env.example`. | `origin/main` no longer contains the eight backup blobs. | Published fast-forward at `30b8599`; rotate any historical credentials before deployment. |
| root/InsForge | READMEs/migrations and owner-scoped policies are documented; no runtime data tracked. | Cloud CLI context currently reports owner-scoped policies/indexes; direct schema query was rejected by invalid API-key state. | No further backend write attempted. |

## Deletion safety

The local cleanup deliberately removed only reproducible runtime outputs, stale state, and dated configuration copies from the working trees; Git history still retains the old blobs until an explicitly approved history rewrite or repository-level purge. No production service data, cookies, current credentials, or live volumes were touched.

## Publication gate

The four private remotes were reconciled and updated with fast-forward pushes from the reviewed `main` checkouts. Trading was merged conservatively so its local commits were preserved while incorporating the published dependency/security branch. The public root repository `iaduartec/iaduartec` was also fast-forwarded with the reviewed InsForge/docs changes. No force-push or history rewrite was used. Historical Git objects may still contain removed blobs; credential rotation remains an operational follow-up.
