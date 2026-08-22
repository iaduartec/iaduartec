# Codex Security remediation report — scan 94954225-f8ac-4093-b07c-94909f2f8620

Date: 2026-08-22
Scope: `/home/ubuntu` snapshot, 16 findings (2 high, 11 medium, 3 low), partial scan coverage.

## Delivered

| Area | Result |
| --- | --- |
| Portfolio auth | Removed the browser-exposed portfolio key from server authorization and added InsForge SSR login/refresh cookies for user-scoped access. |
| Portfolio AI/backtest | AI, market analysis, and backtest routes now require an InsForge session before body/provider work; added bounded streaming JSON reads, body limits, rate limits, a 366-day cap, and regression tests. |
| Mission Bridge | Replaced shell interpolation with argument execution and YouTube allowlisting; exact CORS; static-root confinement; request-size limits; bounded analysis concurrency including direct `/api/analyze`; chunked-body enforcement; and Tailscale identity checks on dynamic endpoints. The live user service now binds to loopback and enables identity enforcement. |
| Duartec Infra | Required runtime secrets, exact route-specific identities including Whisper, read/write separation for data and mail, password-protected noVNC, loopback CDP/VNC boundaries, and bounded/timeout-protected mail-relay operations. |
| InsForge | Added owner-scoped RLS for trading rows, owner-aware position uniqueness, and a migration for already-deployed schemas. |
| Trading API Lab | Restricted probes to loopback Freqtrade HTTP(S), rejected redirects, traversal, embedded credentials, and oversized responses. |
| GitHub hygiene | Removed tracked n8n backups (37 MB including SQLite) from Portfolio, stale `state.json`/setup references from Mission Bridge, and the outdated Oracle snapshot from Infra; added ignore rules and recreated READMEs for Portfolio, Mission Bridge, Infra, Trading, and InsForge. |

## Finding disposition

- Fixed by code and focused tests: public portfolio key, inline Compose credential, unbounded backtest range, global InsForge RLS, arbitrary API Lab URL, Mission static-root exposure, Mission body/job limits, YouTube command injection, CDP binding, and the resource-exhaustion portions of mail, Whisper, noVNC, and Caddy routes.
- Partially fixed / deployment-dependent: Caddy route-level identities, noVNC's password and Mission Bridge's exact allowlist require deployment values; the application must be configured with approved principals before restarting those services. Short-lived noVNC grants and full backend role propagation remain future hardening beyond this repository boundary.
- Operational follow-up: rotate any historical `PORTFOLIO_API_KEY` or other credentials that may have been exposed before these cleanup commits, assign `owner_id` to trusted existing InsForge rows before making ownership non-null, and configure deployment-specific identity grants.

## Verification

- Portfolio: 12 focused Node tests passed; `pnpm type-check` and `pnpm lint` passed.
- Mission Bridge: Python 20/20 and `bash scripts/codex-verify.sh quick` passed; live loopback probes returned 200 for static assets and 401 for unauthenticated dynamic API access.
- Duartec Infra: 8 focused Python tests, shell syntax, Python AST parsing, Caddy validation, and placeholder `docker compose config` passed.
- Trading: API Lab pytest 2/2, full local suite 168/168, focused Ruff, Pyright, and compileall passed. The two stale/runtime-sensitive fixtures were made deterministic; the publication branch based on `origin/main` passes its 165 tests because it contains fewer upstream test files.
- InsForge: no `USING (true)`/`WITH CHECK (true)` remains in trading migrations; the current CLI cloud context reports owner-scoped policies and `(owner_id, asset_symbol)` uniqueness. A direct schema query was rejected by the CLI's invalid API-key state, so no further write was attempted.
- All integrated local checkouts are on `main` with no tracked working-tree changes. Local Mission Bridge was restarted after inspecting status/logs to activate loopback binding and identity enforcement. The reviewed cleanup commits and the follow-up hardening were pushed fast-forward to all four private GitHub default branches; no PR, deployment restart, force-push, or credential rotation was performed.
- Post-push remote-tree checks show Portfolio backups, Mission Bridge `state.json`/`server.log`, and Infra `ops/oracle/2026-08-22`, the root Caddyfile, and the obsolete proposal are absent; Trading retains only the intentional `artifacts/latest/.gitkeep` placeholder.

## Rollback / next step

Each repository has local commits and can be reverted with `git revert` of the remediation commits; restore the previous Mission Bridge systemd drop-in only if a rollback is required. Before deployment, configure the required secrets and approved identity, run the service-native checks in the target environment, assign any future legacy owners in InsForge, and verify a real login before enabling provider keys.
