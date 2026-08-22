# SDD ledger — plan: /home/ubuntu/docs/superpowers/plans/2026-08-22-security-remediation.md

## Preflight plan-conflict scan

| Pair/task | Shared file/interface | Result and ruling |
|---|---|---|
| 1 / 3 | Portfolio route auth and AI route limits | Disjoint files and shared principle only; Task 1 removes browser privileged keys, Task 3 keeps AI limits independent. Proceed. |
| 1 / 6 | Portfolio source and README audit | Task 6 audits tracked output after source changes; no source overlap. Proceed. |
| 2 / 5 | Mission Bridge server and infra proxy | Task 2 owns application request boundaries; Task 5 owns Caddy/container boundaries. Both must preserve explicit origins/private bindings. Proceed. |
| 3 / 4 | Trading API Lab and InsForge schema | Separate repositories and interfaces. Proceed. |
| 5 / 6 | Infra tracked files and publication audit | Task 5 changes config; Task 6 scans final tracked content and documents safe publication. Task 6 runs after Task 5. |
| 6 / 7 | Reports and final verification | Task 6 creates publication audit; Task 7 consumes it and records unresolved items. Proceed. |

| Task | Self-consistency check | Ruling |
|---|---|---|
| 1 | Files, browser-key invariant, and focused security test agree. | Proceed. |
| 2 | Node/Python boundaries and malicious/legitimate controls agree. | Proceed. |
| 3 | Route limits and SSRF validator are independently testable. | Proceed. |
| 4 | RLS requires caller ownership evidence before migration. | If no owner identity exists, park as blocked; never weaken policy. |
| 5 | Secret/config changes have syntax-only verification and no runtime restart. | Proceed. |
| 6 | Audit precedes deletion and README regeneration; publication remains separate. | Proceed. |
| 7 | Final report records fixed, blocked, and deferred findings with evidence. | Proceed. |

Ruling: use isolated `/tmp/codex-security-remediation-*` worktrees because all source checkouts were on clean `main` and the objective requires local changes without direct publication. Cost: branches/worktrees require later explicit integration or cleanup.

## Task status

- Task 1: completed — commit `11be309`, independent review approved; browser privileged sync remains a product-auth follow-up.
- Task 2: completed — commits `c73ba63` and `b48cf9f`; reviewer bypasses closed and regression checks passed; second review receipt pending.
- Task 3: completed — commits `dd3f4ee`, `79dcdba`, `ad68e0d`, `1f1c264`, `aaf9766`, and `5a2e3b7`; bounded AI/backtest controls and spoof-resistant chunked-body/rate-limit regression checks passed; InsForge SSR session authentication, login, refresh, and anonymous-route regression checks are now implemented.
- Task 4: completed — commits `4110af441` and `622f0b764`; owner-scoped InsForge migrations, owner-aware uniqueness, and README added; live database deployment unavailable, so rollout remains pending.
- Task 5: completed — commits `2b31480`, `e486924`, `12b7322`, and `df4bcc8`; reviewer bypasses closed, Whisper now requires exact configured Tailscale identity, and infrastructure checks passed; second review receipt pending.
- Task 6: completed — publication audit recorded; generated runtime/backups removed only from tracked project worktrees and ignored going forward.
- Task 7: completed — reviewed commits integrated into clean local `main` checkouts; final verification and remediation/publication reports recorded. Mission Bridge identity enforcement was activated in the local user service after status/log inspection. No push or deployment performed.
