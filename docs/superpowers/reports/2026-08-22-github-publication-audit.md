# GitHub publication audit — 2026-08-22

Scope: current local `main` checkouts and their fetched `origin/main` refs, reviewed with `git ls-files`, remote trees, repository history, references, ignore rules, README commands, and secret-name/content scans. Values of credentials and private data are intentionally omitted.

## Findings

| Repository | Local result | Remote result | Action |
|---|---|---|---|
| `mission-bridge` | Removed stale `state.json`, corrected setup docs/verifier, and ignore rules; service checks static `200` and dynamic anonymous `401`. | `origin/main` still contains `state.json` and `server.log`. | Local commit `419701b`; remote cleanup still requires reviewed publication. |
| `duartec-infra` | Removed the 2026-08-22 Oracle snapshot (including stale Caddy and credential-bearing Compose copy), added an Oracle snapshot ignore, and corrected its documentation. | `origin/main` still contains `ops/oracle/2026-08-22/`. | Local commit `4837f09`; remote cleanup still requires reviewed publication. |
| `projects/trading` | `artifacts/latest` runtime outputs remain removed/ignored; security API Lab gate passes. Full suite is 166/168 because two existing fixture/runtime-sensitive tests need an isolated Freqtrade/data window. A local `codex/security-publication` branch rebased the cleanup onto `origin/main` without conflicts. | `origin/main` still contains old `artifacts/latest` logs. | Publication branch `codex/security-publication` at `fcbf265`; remote cleanup still requires reviewed publication. |
| `portfolio-repo` | Removed 37 MB of tracked `.codex-n8n-backups` (SQLite plus JSON exports), added an explicit ignore, and kept placeholder-only `.env.example`. | `origin/main` still contains all eight backup blobs. | Local commits `68e5dea` and `30b8599`; rotate any historical credentials before publication. |
| root/InsForge | READMEs/migrations and owner-scoped policies are documented; no runtime data tracked. | Cloud CLI context currently reports owner-scoped policies/indexes; direct schema query was rejected by invalid API-key state. | No further backend write attempted. |

## Deletion safety

The local cleanup deliberately removed only reproducible runtime outputs, stale state, and dated configuration copies from the working trees; Git history still retains the old blobs until an explicitly approved history rewrite or repository-level purge. No production service data, cookies, current credentials, or live volumes were touched.

## Publication gate

Before any push or PR, reconcile each local branch against its fetched `origin/main` without reset, run explicit-path `git diff --check`, tracked-file secret scanning, repository-native tests, and review `git diff --stat`/`git diff --name-status`. The four remotes are private, but they still retain the pre-cleanup files. No push, merge, force-push, or history rewrite is authorized by this report.
