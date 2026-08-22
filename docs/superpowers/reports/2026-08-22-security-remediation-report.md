# Codex Security remediation report — scan 94954225-f8ac-4093-b07c-94909f2f8620

Date: 2026-08-22
Scope: `/home/ubuntu` snapshot, 16 findings (2 high, 11 medium, 3 low), partial scan coverage.

## Delivered

| Area | Result |
| --- | --- |
| Portfolio auth | Removed the browser-exposed portfolio key from server authorization; privileged browser sync now fails closed to local fallback until product sessions exist. |
| Portfolio AI/backtest | Added bounded streaming JSON reads, body limits, rate limits with spoof-resistant global default, a 366-day backtest cap, and regression tests. |
| Mission Bridge | Replaced shell interpolation with argument execution and YouTube allowlisting; exact CORS; static-root confinement; request-size limits; bounded analysis concurrency including direct `/api/analyze`; chunked-body enforcement. |
| Duartec Infra | Required runtime secrets, exact identity matching for sensitive proxy routes, method restrictions, resource limits, Whisper streaming/concurrency caps, loopback CDP/VNC boundaries, and mail-relay limits. |
| InsForge | Added owner-scoped RLS for trading rows, owner-aware position uniqueness, and a migration for already-deployed schemas. |
| Trading API Lab | Restricted probes to loopback Freqtrade HTTP(S), rejected redirects, traversal, embedded credentials, and oversized responses. |
| GitHub hygiene | Removed tracked runtime logs/transcripts, dated infra backups, and trading `artifacts/latest` state; added ignores and recreated READMEs for Portfolio, Mission Bridge, Infra, Trading, and InsForge. |

## Finding disposition

- Fixed by code and focused tests: public portfolio key, inline Compose credential, unbounded backtest range, global InsForge RLS, arbitrary API Lab URL, Mission static-root exposure, Mission body/job limits, YouTube command injection, CDP binding, and the resource-exhaustion portions of mail, Whisper, noVNC, and Caddy routes.
- Partially fixed / deployment-dependent: Caddy `/mail` and `/data` now require one exact configured identity, but route-level roles and short-lived grants are not implemented; Whisper is bounded but its Caddy route has no identity matcher; Mission Bridge still relies on its private network for application authentication.
- Deferred product decision: AI/chat/market endpoints remain unauthenticated. Their body, chunked-stream, global-default rate, and cost-amplification controls reduce abuse, but do not authorize callers. Do not enable billable provider keys for public access until a real session or trusted-caller boundary is deployed.
- Deferred operational action: rotate any historical `PORTFOLIO_API_KEY` or other credentials that may have been exposed before this change, and assign `owner_id` to trusted existing InsForge rows before making ownership non-null.

## Verification

- Portfolio: 9 focused Node tests passed; `pnpm type-check` and `pnpm lint` passed.
- Mission Bridge: Node 2/2, Python 17/17, and `bash scripts/codex-verify.sh quick` passed.
- Duartec Infra: 8 focused Python tests, shell syntax, Python AST parsing, and placeholder `docker compose config` passed.
- Trading: API Lab pytest 2/2 and Ruff passed.
- InsForge: no `USING (true)`/`WITH CHECK (true)` remains in trading migrations; live `psql`/InsForge deployment was unavailable.
- All integrated local checkouts are on `main` with no tracked working-tree changes. No GitHub push, PR, service restart, deployment, credential rotation, or database migration was performed.

## Rollback / next step

Each repository has local commits and can be reverted with `git revert` of the remediation commits. Before deployment, configure the required secrets and approved identity, run the service-native checks in the target environment, apply the InsForge migrations after assigning owners, and make an explicit authentication decision for public AI routes.
