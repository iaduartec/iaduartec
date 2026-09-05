# Conservative Skills Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce the active Codex skills surface conservatively while preserving the normal Duartec engineering workflow, model configuration, and an easy rollback path.

**Architecture:** Treat skills in `/home/ubuntu/.agents/skills` and `/home/ubuntu/.codex/skills` as local discovered skills, plugin entries in `/home/ubuntu/.codex/config.toml` as the active integration layer, and plugin caches as reinstallable artifacts. First create an inventory and backup, then change only explicit enablement flags; defer deletion of local skills and caches until usage has been observed.

**Tech Stack:** Codex `config.toml`, Markdown `SKILL.md` files, local plugin caches, Bash read-only inventory commands.

**Spec:** This plan is based on the 2026-09-04 local audit of `/home/ubuntu/.codex/config.toml`, `/home/ubuntu/.agents/skills`, `/home/ubuntu/.codex/skills`, and plugin caches.

## Global Constraints

- Do not modify the model, model availability entries, authentication, secrets, cookies, project repositories, or production services.
- Do not delete skill directories or plugin caches in the first pass.
- Preserve the currently useful engineering and security workflow: bugfix, browser testing, repository review, status, defensive shell, Playwright, frontend review, and security guidance.
- Treat the existing dirty `/home/ubuntu` worktree as unrelated user work; do not stage or clean it.
- Back up `config.toml` before any persistent configuration change.
- Validate the resulting TOML and relaunch Codex before considering the change complete.

---

### Task 1: Capture a reversible baseline

**Files:**
- Read: `/home/ubuntu/.codex/config.toml`
- Read: `/home/ubuntu/.agents/skills/*/SKILL.md`
- Read: `/home/ubuntu/.codex/skills/*/SKILL.md`
- Create during execution: `/home/ubuntu/.codex/backups/skills-cleanup-YYYYMMDDTHHMMSSZ/config.toml`
- Create during execution: `/home/ubuntu/.codex/backups/skills-cleanup-YYYYMMDDTHHMMSSZ/inventory.txt`

**Interfaces:**
- Produces an inventory of local skills, enabled plugins, explicit disabled overrides, duplicate skill names, and cache sizes.

- [ ] **Step 1: Check the current configuration and worktree boundary**

```bash
git -C /home/ubuntu status --short --branch
sed -n '1,220p' /home/ubuntu/.codex/config.toml
```

Expected: observe the existing dirty root worktree and confirm that only the Codex configuration is in scope.

- [ ] **Step 2: Create a timestamped backup directory and copy the configuration**

```bash
backup_dir="/home/ubuntu/.codex/backups/skills-cleanup-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$backup_dir"
cp -p /home/ubuntu/.codex/config.toml "$backup_dir/config.toml"
```

Expected: the backup contains the exact pre-change `config.toml`.

- [ ] **Step 3: Save a non-secret inventory**

```bash
{
  date -u
  find /home/ubuntu/.agents/skills /home/ubuntu/.codex/skills -type f -name SKILL.md -print | sort
  rg -n '^(model|\[plugins\.|enabled =|\[\[skills\.config\]\]|path =)' /home/ubuntu/.codex/config.toml
  du -sh /home/ubuntu/.codex/plugins/cache /home/ubuntu/.codex/vendor_imports/skills /home/ubuntu/.agents/skills /home/ubuntu/.codex/skills
} > "$backup_dir/inventory.txt"
```

Expected: inventory contains paths and configuration flags only, never secret values.

### Task 2: Apply only low-risk enablement changes

**Files:**
- Modify: `/home/ubuntu/.codex/config.toml`

**Interfaces:**
- Consumes the Task 1 backup and inventory.
- Produces an explicit, reversible set of disabled plugin flags.

- [ ] **Step 1: Leave the core local engineering skills untouched**

Keep enabled/discoverable for normal work: `bash-defensive-patterns`, `browser-test-fix`, `bugfix`, `ccc`, `repo-review`, `status`, `stop-slop`, `playwright`, `playwright-interactive`, `frontend-review`, `security-best-practices`, `security-ownership-map`, `security-threat-model`, `oracle-storage-auditor`, `oracle-storage-cleaner`, and `vercel-deploy`.

Expected: no local skill directory is deleted or renamed.

- [ ] **Step 2: Keep only integrations with a confirmed current use**

Before changing the flags, confirm whether Cloudflare, Vercel, Sentry, Supabase, Neon Postgres, Visualize, or Sites was used in the last active project. Disable only integrations the user explicitly identifies as unused. Do not infer that a cached plugin is active merely because its files exist.

Expected: no plugin is disabled solely because it is large or unfamiliar.

- [ ] **Step 3: Record explicit disabled overrides for any selected plugin**

Use the existing format in `config.toml`, for example:

```toml
[plugins."sites@openai-bundled"]
enabled = false
```

Do not alter `model = "gpt-5.6-luna"`, `[tui.model_availability_nux]`, authentication, or workspace trust settings.

Expected: the diff contains only selected plugin enablement changes.

### Task 3: Handle duplicates without deletion

**Files:**
- Modify only if needed: `/home/ubuntu/.codex/config.toml`
- Preserve: `/home/ubuntu/.agents/skills/insforge*`, `/home/ubuntu/.agents/skills/superdesign`, and their remote counterparts

**Interfaces:**
- Consumes the duplicate inventory from Task 1.
- Produces one explicit preferred path per duplicate family, with the other path disabled rather than removed.

- [ ] **Step 1: Preserve the existing disabled InsForge and Superdesign entries**

The audit already found local and remote copies of InsForge and Superdesign with explicit `enabled = false` overrides. Leave these entries as-is unless a later usage check proves one copy is required.

Expected: no duplicate directory is deleted.

- [ ] **Step 2: Do not add broad disable rules for cached skills**

Plugin caches under `/home/ubuntu/.codex/plugins/cache` and vendor imports under `/home/ubuntu/.codex/vendor_imports/skills` remain untouched in this phase.

Expected: rollback is configuration-only and cached integrations remain reinstallable.

### Task 4: Validate and observe

**Files:**
- Read: `/home/ubuntu/.codex/config.toml`
- Create during execution: `/home/ubuntu/.codex/backups/skills-cleanup-YYYYMMDDTHHMMSSZ/post-change-inventory.txt`

- [ ] **Step 1: Validate TOML syntax with an available parser**

Use the Codex-native configuration check if available; otherwise use a local TOML parser already installed. Do not install packages merely for this check.

Expected: configuration parses successfully.

- [ ] **Step 2: Compare the model and safety-sensitive settings**

```bash
rg -n '^(model|approval_policy|default_permissions|sandbox_mode|web_search|\[tui\.model_availability_nux\])' /home/ubuntu/.codex/config.toml
```

Expected: model and safety-sensitive settings match the backed-up baseline.

- [ ] **Step 3: Relaunch Codex and verify normal behavior**

Open a fresh local Codex session, confirm the expected core skills remain available, and check whether the model selector behavior changed. Do not claim that Astra access was restored by this cleanup.

Expected: core engineering workflows remain available; model availability is unchanged unless the account rollout changes independently.

- [ ] **Step 4: Observe before any deletion**

Keep the backup and caches for at least one normal work cycle. Only then prepare a separate cleanup proposal for unused local directories or stale caches, with exact paths and a quarantine/restore procedure.

Expected: no destructive cleanup occurs in this first pass.

## Rollback

To restore the pre-change configuration, copy the backed-up `config.toml` over `/home/ubuntu/.codex/config.toml` from the timestamped backup directory, then relaunch Codex. Do not restore by deleting the current configuration or by touching project repositories.

## Self-review

- The plan changes no project code, services, secrets, or model identifiers.
- The plan explicitly preserves the existing duplicate disable overrides.
- No cache or skill deletion is proposed before observing actual use.
- Astra availability is treated as an account/product rollout issue, not as a skill-cleanup outcome.
