# GitHub publication audit — 2026-08-22

Scope: clean branches at the scan target revision, reviewed with `git ls-files`, repository history, references, ignore rules, and secret-name/content scans. Values of credentials and private data are intentionally omitted.

## Findings

| Repository | Tracked content | Evidence | Action in remediation branch |
|---|---|---|---|
| `mission-bridge` | `server.log` and three `transcript-runtime*` files | Runtime outputs/captions; last repository movement was the June 2026 migration; no application source references them; `.gitignore` already excludes runtime/output state but not these four legacy files. | Remove from tracking and add explicit runtime/caption ignores. |
| `duartec-infra` | 13 `*.bak*` Caddy, Compose, media and workflow snapshots | Every candidate is a dated backup; current counterparts exist; no non-backup source references them; `.gitignore` already says `*.bak`/`*.bak.*`. | Remove stale backups from tracking; preserve current files. |
| `projects/trading` | `artifacts/latest/*` runtime JSON/log/PID files and generated reports | Files contain dated runtime state and generated research output; source scripts regenerate/read the directory; most runtime names are already individually ignored, indicating accidental historical tracking. | Remove tracked runtime outputs and ignore the whole directory except a keep-file; retain generator scripts and notebooks. Reports remain until their generated-vs-curated ownership is confirmed in the README task. |
| `portfolio-repo` | `.env.example` only among secret-like names | It contains placeholders and is intended documentation; no credential value found in tracked file inventory. | Keep, rewrite examples to match server-only auth after the P1 fix. |
| root/InsForge | no README and no secret-like tracked filenames | Only migration/config source is tracked under `apps/insforge`; no runtime data or environment file is tracked. | Add a focused README with migration and secret-handling instructions. |

## Deletion safety

No backups, databases, cookies, raw portfolio imports, or production state will be deleted. The candidate deletions are reproducible runtime outputs or dated backup copies with current counterparts and no source references. Each deletion is confined to a remediation branch/worktree and can be recovered from Git history until any later external publication decision.

## Publication gate

Before any push or PR, run explicit-path `git diff --check`, tracked-file secret scanning, repository-native tests, and a review of `git diff --stat`/`git diff --name-status`. No push, merge, or PR is authorized by this report.
