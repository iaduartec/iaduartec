# Security Findings Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remediate the validated scan findings and produce safe, current README files and GitHub publication diffs.

**Architecture:** Fix shared authorization and input boundaries first, then apply bounded resource controls and infrastructure secret/config changes. Keep each repository on its own `codex/security-remediation-*` branch; the root controller reviews diffs and decides whether any external GitHub write is separately authorized.

**Tech Stack:** Next.js/TypeScript/pnpm, Python stdlib/Streamlit, Node.js, InsForge SQL/RLS, Docker Compose, Caddy, shell, GitHub CLI.

**Spec:** `/home/ubuntu/docs/superpowers/specs/2026-08-22-security-remediation-design.md`

## Global Constraints

- Do not expose, print, commit, or copy credential values; rotate externally only with explicit authorization.
- Do not edit raw portfolio data, production databases, cookies, backups, or running services.
- Do not publish, push, merge, or open PRs in this plan.
- Preserve existing legitimate fallback behavior and document any blocked product-auth decision.
- Stage only explicit reviewed paths; never use `git add -A`.

### Task 1: Portfolio privileged authorization boundary

**Files:**
- Modify: `/home/ubuntu/portfolio-repo/src/lib/server/auth.ts`
- Modify: `/home/ubuntu/portfolio-repo/src/hooks/usePortfolioData.ts`
- Modify: `/home/ubuntu/portfolio-repo/src/components/upload/CsvDropzone.tsx`
- Modify: `/home/ubuntu/portfolio-repo/src/components/integrations/IntegrationManager.tsx`
- Modify: `/home/ubuntu/portfolio-repo/src/hooks/useWatchlistIdeas.ts`
- Modify: `/home/ubuntu/portfolio-repo/app/api/n8n/[...path]/route.ts`
- Test: `/home/ubuntu/portfolio-repo/tests/security-routes.test.ts`

**Contract:** `requireApikey` may accept only `PORTFOLIO_API_KEY` from a server request; browser code must not read or send `NEXT_PUBLIC_PORTFOLIO_CLIENT_KEY`. If no real user session exists, keep privileged routes fail-closed and make browser callers use the existing local fallback/error path rather than silently becoming public.

- [ ] Add a regression proving a request carrying only the former public key receives 401.
- [ ] Remove browser-side privileged-key reads and keep unauthenticated local fallback behavior.
- [ ] Run `pnpm test -- tests/security-routes.test.ts`, `pnpm type-check`, and `pnpm lint`.

### Task 2: Mission Bridge command and request boundaries

**Files:**
- Modify: `/home/ubuntu/mission-bridge/skills/youtube_manager/index.js`
- Modify: `/home/ubuntu/mission-bridge/server.py`
- Test: `/home/ubuntu/mission-bridge/skills/youtube_manager/test_index.js` or the repository-native focused test location.

**Contract:** Accept only HTTPS YouTube URLs, invoke `yt-dlp` without a shell, cap request bodies and concurrent jobs, restrict static serving to a dedicated public root, and replace wildcard CORS with an explicit configured origin.

- [ ] Add malicious URL cases for shell metacharacters, non-YouTube hosts, and alternate encodings.
- [ ] Add legitimate YouTube control and existing API smoke checks.
- [ ] Run Node syntax/tests and `bash scripts/codex-verify.sh quick` where available.

### Task 3: Portfolio AI/backtest and trading API limits

**Files:**
- Modify: `/home/ubuntu/portfolio-repo/app/api/chat/route.ts`
- Modify: `/home/ubuntu/portfolio-repo/app/api/ai/route.ts`
- Modify: `/home/ubuntu/portfolio-repo/app/api/ai-agents/route.ts`
- Modify: `/home/ubuntu/portfolio-repo/app/api/virtual-portfolio/backtest/route.ts`
- Modify: `/home/ubuntu/projects/trading/streamlit_app.py`
- Test: owning route tests under `/home/ubuntu/portfolio-repo/tests/` and a focused Python test under `/home/ubuntu/projects/trading/tests/`.

**Contract:** Enforce bounded request size, date range, provider work, and per-client rate limits. API Lab permits only configured HTTP(S) API origins, rejects loopback/private/link-local/metadata destinations and redirects outside the allowlist, and never forwards credentials to a non-allowlisted host.

- [ ] Add failing tests for overlong prompts, excessive date ranges, private IP/localhost/file URLs, redirect attempts, and legitimate bounded requests.
- [ ] Implement shared validators at the route/probe boundary.
- [ ] Run route tests, `pnpm type-check`, `pnpm lint`, and Python syntax/tests.

### Task 4: InsForge row ownership

**Files:**
- Modify: `/home/ubuntu/apps/insforge/migrations/20260822044039_create-trading-tables.sql`
- Create: a focused migration/test note only if repository conventions require it.

**Contract:** Add owner/tenant columns and `auth.uid()`-based policies for read/write; fail closed when no authenticated owner exists. Do not import managed data or secrets.

- [ ] Confirm callers provide an authenticated owner before changing policy shape.
- [ ] Replace `USING (true)`/`WITH CHECK (true)` with owner predicates and verify SQL parsing/migration checks.
- [ ] Run the repository-native InsForge migration/lint validation; report blocked deployment separately if CLI access is unavailable.

### Task 5: Infrastructure secrets and service exposure

**Files:**
- Modify: `/home/ubuntu/duartec-infra/docker-compose.yml`
- Modify: `/home/ubuntu/duartec-infra/caddy/conf.d/apis.caddy`
- Modify: `/home/ubuntu/duartec-infra/caddy/conf.d/novnc.caddy`
- Modify: `/home/ubuntu/duartec-infra/media-api/entrypoint.sh`
- Modify: `/home/ubuntu/duartec-infra/mail-relay/app.py`
- Modify: `/home/ubuntu/duartec-infra/local_whisper_server.py`
- Modify: `/home/ubuntu/duartec-infra/db-api/app.py` only if the same request-boundary helper is required.

**Contract:** Replace inline credentials with required runtime secret references, constrain `/mail` and `/data` by explicit identity/method policy, bind noVNC/CDP privately or authenticate it, and cap body/mailbox/transcription work. Preserve service routes and document rollback for config changes.

- [ ] Add redacted config/syntax tests; never print values.
- [ ] Run `bash -n`, `docker compose config` only with safe example/env inputs, Caddy validation if installed, and focused Python tests.

### Task 6: GitHub publication audit, stale-content cleanup, and README regeneration

**Files:**
- Modify: `README.md` in each affected repository.
- Modify: repository `.gitignore`/tracking rules only when evidence shows a tracked artifact should be excluded.
- Create: `/home/ubuntu/docs/superpowers/reports/2026-08-22-github-publication-audit.md`.

**Contract:** Compare each branch to `origin/main`, inspect `git ls-files`, scan tracked content for secret patterns and generated/private artifacts, and remove only files proven unused by references/history/configuration. README files must state purpose, setup, safe env examples, tests, deployment boundaries, and known limitations without secrets.

- [ ] Produce a redacted inventory and candidate list before any deletion.
- [ ] Validate README commands against the repository files and native checks.
- [ ] Review explicit diffs and leave publication/push as a separately approved action.

### Task 7: Final verification and remediation report

**Files:**
- Create: `/home/ubuntu/docs/superpowers/reports/2026-08-22-security-remediation-report.md`.

- [ ] Run all repository checks applicable to changed files.
- [ ] Rerun focused malicious-input tests and tracked-file secret scan.
- [ ] Record fixed, blocked, and deferred findings with exact evidence, rollback, and external-access limitations.
