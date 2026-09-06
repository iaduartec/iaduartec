# Server Audit — Phase 13: Elimination Plan

**Date:** 2026-09-05
**Current:** 146G used / 194G total (76%)
**Target:** <120G (62%) — free ~26G

---

## Classification System

| Class | Meaning                       | Action                          |
| ----- | ----------------------------- | ------------------------------- |
| **A** | CRITICAL — Active, required   | DO NOT TOUCH                    |
| **B** | PROTECTED — Active, important | Keep unless explicitly approved |
| **C** | ACTIVE — Used, could optimize | Keep, note for future           |
| **D** | SAFE — Regenerable/temporary  | DELETE freely                   |
| **E** | PROBABLE — Likely unused      | DELETE after verification       |
| **F** | NEEDS DECISION                | User must approve               |
| **G** | ABANDONED — Clearly dead      | DELETE freely                   |

---

## ELIMINATION TABLE

### GROUP 1: Ollama Duplicates (~10G) — HIGH PRIORITY

| Component                             | Size          | Class | Consumer                                                                                                                                        | Action                                                                          |
| ------------------------------------- | ------------- | ----- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `/usr/share/ollama/` (system install) | 3.1G          | G     | No service uses it (`ollama.service` inactive, Docker uses `~/.ollama` bind mount)                                                              | **DELETE** — orphaned system install                                            |
| `/usr/local/lib/ollama/` (CUDA libs)  | 3.5G          | G     | Referenced by PID 4443 (root `ollama serve`), but Docker container `duartec-ollama` has its own `ollama/ollama:latest` image with built-in libs | **STOP PID 4443 + DELETE** — duplicate root process, container has its own libs |
| `~/.local/lib/ollama/` (user-level)   | 7.0G          | G     | PID 1939 (ubuntu `ollama serve`) — this is a THIRD ollama instance, not used by Docker or systemd                                               | **STOP PID 1939 + DELETE** — redundant with Docker container                    |
| `/usr/share/ollama/.ollama/`          | (inside 3.1G) | G     | Same as `/usr/share/ollama/`                                                                                                                    | Covered above                                                                   |

**Net savings: ~10G**
**Risk:** LOW — Docker container `duartec-ollama` uses its own image + `~/.ollama` bind mount (1.3G, preserved)

---

### GROUP 2: Rust (~2.5G) — ABANDONED

| Component    | Size | Class | Consumer                                                                              | Action     |
| ------------ | ---- | ----- | ------------------------------------------------------------------------------------- | ---------- |
| `~/.rustup/` | 1.9G | G     | No `Cargo.toml` in `/srv` or `~/projects`. `rustc` not in PATH. No project uses Rust. | **DELETE** |
| `~/.cargo/`  | 557M | G     | Crate registry cache only — no active builds                                          | **DELETE** |

**Net savings: ~2.5G**
**Risk:** NONE — zero consumers

---

### GROUP 3: Homebrew (~5.1G) — ABANDONED

| Component                     | Size | Class | Consumer                                                                                                                                                               | Action                 |
| ----------------------------- | ---- | ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------- |
| `/home/linuxbrew/.linuxbrew/` | 5.1G | G     | Not in PATH for any systemd service. Not in `.bashrc`/`.profile`. No project references it (only incidental docs in vendored node_modules). `brew list` returns empty. | **UNINSTALL + DELETE** |

**Net savings: ~5.1G**
**Risk:** NONE — zero consumers

---

### GROUP 4: Snap Disabled Versions (~800M)

| Component                    | Size  | Class | Consumer                   | Action                                                     |
| ---------------------------- | ----- | ----- | -------------------------- | ---------------------------------------------------------- |
| `chromium_3506.snap`         | ~200M | D     | Disabled — active is 3515  | **`snap remove --purge chromium --revision=3506`**         |
| `cmake_1559.snap`            | ~150M | D     | Disabled — active is 1561  | **`snap remove --purge cmake --revision=1559`**            |
| `core18_2983.snap`           | ~50M  | D     | Disabled — active is 3002  | **`snap remove --purge core18 --revision=2983`**           |
| `core20_2772.snap`           | ~50M  | D     | Disabled — active is 2870  | **`snap remove --purge core20 --revision=2772`**           |
| `core22_2412.snap`           | ~50M  | D     | Disabled — active is 2438  | **`snap remove --purge core22 --revision=2412`**           |
| `core24_1588.snap`           | ~50M  | D     | Disabled — active is 1644  | **`snap remove --purge core24 --revision=1588`**           |
| `cups_1231.snap`             | ~40M  | D     | Disabled — active is 1237  | **`snap remove --purge cups --revision=1231`**             |
| `google-cloud-cli_490.snap`  | ~100M | D     | Disabled — active is 492   | **`snap remove --purge google-cloud-cli --revision=490`**  |
| `lxd_40407.snap`             | ~100M | D     | Disabled — active is 40528 | **`snap remove --purge lxd --revision=40407`**             |
| `mesa-2404_1166.snap`        | ~50M  | D     | Disabled — active is 1836  | **`snap remove --purge mesa-2404 --revision=1166`**        |
| `oracle-cloud-agent_95.snap` | ~50M  | D     | Disabled — active is 112   | **`snap remove --purge oracle-cloud-agent --revision=95`** |
| `snapd_27595.snap`           | ~50M  | D     | Disabled — active is 27709 | **`snap remove --purge snapd --revision=27595`**           |

**Net savings: ~800M**
**Risk:** NONE — only removing disabled old versions

---

### GROUP 5: Playwright Old Versions (~1.6G)

| Component                      | Size | Class | Consumer                         | Action               |
| ------------------------------ | ---- | ----- | -------------------------------- | -------------------- |
| `chromium_headless_shell-1223` | 333M | D     | Old revision — 1243 is active    | **DELETE directory** |
| `chromium_headless_shell-1228` | 334M | D     | Old revision — 1243 is active    | **DELETE directory** |
| `chromium_headless_shell-1234` | 340M | D     | Old revision — 1243 is active    | **DELETE directory** |
| `chromium-1243`                | 393M | C     | Active Playwright chromium       | KEEP                 |
| `chromium_headless_shell-1243` | 266M | C     | Active Playwright headless shell | KEEP                 |
| `firefox-1511`                 | 264M | C     | Active Playwright firefox        | KEEP                 |
| `webkit-2272`                  | 269M | C     | Active Playwright webkit         | KEEP                 |
| `ffmpeg-1011`                  | 3.3M | C     | Active Playwright ffmpeg         | KEEP                 |

**Net savings: ~1G**
**Risk:** LOW — only old revisions deleted

---

### GROUP 6: npm/pnpm/yarn/pip Caches (~4G)

| Component               | Size  | Class | Consumer                                     | Action                        |
| ----------------------- | ----- | ----- | -------------------------------------------- | ----------------------------- |
| `~/.npm/_cacache/`      | 308M  | D     | npm cache — regenerable                      | **`npm cache clean --force`** |
| `~/.pnpm-store/`        | 538M  | D     | pnpm content-addressable store — regenerable | **`pnpm store prune`**        |
| `~/.playwright-cli/`    | 37M   | D     | Playwright CLI cache                         | **DELETE**                    |
| `/var/cache/pip/`       | ~200M | D     | pip HTTP cache — regenerable                 | **`pip cache purge`**         |
| `~/.cache/go-build/`    | ~200M | D     | Go build cache — regenerable                 | **`go clean -cache`**         |
| `~/.cache/pip/`         | ~100M | D     | User pip cache                               | **DELETE**                    |
| `~/.cache/huggingface/` | ~50M  | D     | HuggingFace model cache                      | **DELETE**                    |
| `~/.cache/uv/`          | ~50M  | D     | UV cache                                     | **DELETE**                    |
| `~/.cache/snyk/`        | ~20M  | D     | Snyk scan cache                              | **DELETE**                    |

**Net savings: ~1.5G**
**Risk:** NONE — all regenerable

---

### GROUP 7: NVM Old Version (~506M)

| Component                       | Size | Class | Consumer                                                                 | Action                     |
| ------------------------------- | ---- | ----- | ------------------------------------------------------------------------ | -------------------------- |
| `~/.nvm/versions/node/v26.8.1/` | 506M | D     | `nvm alias default` = v24.20.0. v26.8.1 not used by any systemd service. | **`nvm uninstall 26.8.1`** |

**Net savings: ~500M**
**Risk:** NONE — default is v24.20.0

---

### GROUP 8: Quarantine (~707M)

| Component        | Size | Class | Consumer                                                                                                                                                                   | Action     |
| ---------------- | ---- | ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| `~/.quarantine/` | 707M | G     | Contains: antigravity-ide-server backup, hub-v2-rollback, mission-bridge-session-artifacts, trading-env-backup — all from Sep 5, 2026. No active service references these. | **DELETE** |

**Net savings: ~707M**
**Risk:** LOW — these are backup/rollback artifacts, not active data

---

### GROUP 9: Codex Packages (~2.2G)

| Component                                | Size    | Class | Consumer                                                 | Action                               |
| ---------------------------------------- | ------- | ----- | -------------------------------------------------------- | ------------------------------------ |
| `~/.codex/packages/standalone/releases/` | 2.2G    | D     | Codex standalone release binaries — regenerable from npm | **DELETE old releases, keep latest** |
| `~/.codex/archived_sessions/`            | (empty) | —     | Already empty                                            | N/A                                  |
| `~/.codex/legacy-standalone-20260822/`   | (empty) | —     | Already deleted                                          | N/A                                  |
| `~/.codex/generated_images/`             | 26M     | D     | Old generated images                                     | **DELETE**                           |
| `~/.codex/skill-archive-20260822/`       | 3.2M    | D     | Old skill archive                                        | **DELETE**                           |

**Net savings: ~2.2G**
**Risk:** LOW — releases are regenerable

---

### GROUP 10: Python pipx (~5.5G) — NEEDS DECISION

| Component                                    | Size  | Class | Consumer                                                                     | Action       |
| -------------------------------------------- | ----- | ----- | ---------------------------------------------------------------------------- | ------------ |
| `~/.local/share/pipx/venvs/cocoindex-code/`  | ~3G   | F     | Used by CocoIndex daemon (running)                                           | **KEEP**     |
| `~/.local/share/pipx/venvs/oci-cli/`         | ~1.5G | F     | Oracle Cloud CLI — may be needed for server management                       | **ASK USER** |
| `~/.local/share/pipx/venvs/piper-tts/`       | ~500M | F     | Text-to-speech — check if whisper/mission-bridge uses it                     | **ASK USER** |
| `~/.local/share/pipx/venvs/yt-dlp/`          | ~200M | F     | YouTube downloader — mission-bridge uses it (`MISSION_BRIDGE_YTDLP` env var) | **KEEP**     |
| `~/.local/share/pipx/venvs/git-filter-repo/` | ~100M | F     | Git history rewriting tool — check if actively used                          | **ASK USER** |

**Net savings: POTENTIAL ~2.1G (if oci-cli, piper-tts, git-filter-repo removed)**
**Risk:** MEDIUM — need user confirmation

---

### GROUP 11: Python libs (~6G) — NEEDS INVESTIGATION

| Component                  | Size | Class | Consumer                                                               | Action                                        |
| -------------------------- | ---- | ----- | ---------------------------------------------------------------------- | --------------------------------------------- |
| `~/.local/lib/python3.12/` | 6.0G | F     | Contains 370 pip packages — needs audit of which are actually imported | **INVESTIGATE** — this is the biggest unknown |

**Net savings: POTENTIAL ~3-4G (if orphaned packages removed)**
**Risk:** MEDIUM — need to determine which packages are actually used

---

### GROUP 12: VS Code Server (~3.4G) — ACTIVE

| Component           | Size | Class | Consumer                                                         | Action   |
| ------------------- | ---- | ----- | ---------------------------------------------------------------- | -------- |
| `~/.vscode-server/` | 3.4G | B     | Active xrdp session, agent-host-stable.log being written (Sep 5) | **KEEP** |

**Net savings: 0**
**Risk:** N/A — active

---

### GROUP 13: Git Repos & Worktrees

| Component                                           | Size           | Class | Consumer                                     | Action                                       |
| --------------------------------------------------- | -------------- | ----- | -------------------------------------------- | -------------------------------------------- |
| `/home/ubuntu/.git/`                                | 5.1G           | B     | Main repo — 4.94G pack contains full history | **KEEP** (could `git gc --aggressive` later) |
| `~/.worktrees/web-workflows/`                       | 520M           | F     | Worktree for web workflows — check if active | **ASK USER**                                 |
| `~/.worktrees/scanner-ci-repro/`                    | 141M           | F     | Scanner CI reproduction worktree             | **ASK USER**                                 |
| `~/.worktrees/scanner-workflows/`                   | 141M           | F     | Scanner workflows worktree                   | **ASK USER**                                 |
| `~/.worktrees/mission-alpha-infra/`                 | 5.3M           | F     | Mission alpha infra worktree                 | **ASK USER**                                 |
| `portfolio-repo/.worktrees/virtual-tier-portfolio/` | (in portfolio) | F     | Portfolio worktree                           | **ASK USER**                                 |

**Net savings: POTENTIAL ~800M (if all worktrees removed)**
**Risk:** MEDIUM — need user confirmation

---

### GROUP 14: OpenClaw Cleanup (~500M potential)

| Component                                   | Size | Class | Consumer                       | Action       |
| ------------------------------------------- | ---- | ----- | ------------------------------ | ------------ |
| `~/.openclaw/repair-backups/`               | 109M | D     | Repair backups — not active    | **DELETE**   |
| `~/.openclaw/archive/`                      | 57M  | D     | Old archives                   | **DELETE**   |
| `~/.openclaw/canvas/`                       | 509M | F     | Canvas data — check if active  | **ASK USER** |
| `~/.openclaw/piper/`                        | 61M  | F     | Piper TTS data — check if used | **ASK USER** |
| `~/.openclaw/agents/telegram-orchestrator/` | 1.1G | B     | Active Telegram orchestrator   | **KEEP**     |

**Net savings: POTENTIAL ~166M (repair-backups + archive)**
**Risk:** LOW for backup/archive deletion

---

### GROUP 15: CocoIndex DB (~7.3G) — NEEDS INVESTIGATION

| Component                             | Size | Class | Consumer                                       | Action            |
| ------------------------------------- | ---- | ----- | ---------------------------------------------- | ----------------- |
| `~/.cocoindex_code/cocoindex.db/`     | 4.5G | F     | Main CocoIndex database — daemon running       | **KEEP** (active) |
| `~/.cocoindex_code/target_sqlite.db/` | 2.9G | F     | Target SQLite DB — check if separate from main | **INVESTIGATE**   |

**Net savings: POTENTIAL ~2.9G (if target_sqlite.db is orphaned)**
**Risk:** MEDIUM — need to verify if target_sqlite.db is actively used

---

### GROUP 16: Reports (~648M)

| Component    | Size | Class | Consumer                                                                                                | Action                              |
| ------------ | ---- | ----- | ------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| `~/reports/` | 648M | G     | Contains: dogfood-mission-bridge, duartec-healthcheck, oracle-storage, security report — all historical | **DELETE old reports, keep recent** |

**Net savings: POTENTIAL ~500M**
**Risk:** LOW — historical reports

---

### GROUP 17: Go Module Cache (~1.6G)

| Component         | Size | Class | Consumer                                                                | Action                   |
| ----------------- | ---- | ----- | ----------------------------------------------------------------------- | ------------------------ |
| `~/go/pkg/`       | 1.6G | D     | Go module cache — regenerable, only 1 consumer (openclaw-src docs-i18n) | **`go clean -modcache`** |
| `~/go/bin/alpaca` | 13M  | F     | Alpaca trading binary — check if actively used                          | **ASK USER**             |

**Net savings: ~1.6G**
**Risk:** LOW — cache is regenerable

---

### GROUP 18: Docker Deep Cleanup

| Component                   | Size  | Class | Consumer                                                    | Action                         |
| --------------------------- | ----- | ----- | ----------------------------------------------------------- | ------------------------------ |
| Docker build cache          | 5.2G  | D     | Build cache — regenerable                                   | **`docker builder prune -af`** |
| Docker unused volumes       | ~1G   | D     | Old n8n volumes, other unused                               | **VERIFY + DELETE unused**     |
| `n8n-data-1` + `n8n-data-2` | ~500M | D     | Duplicate n8n data volumes — n8n uses `n8n_data` bind mount | **ASK USER**                   |

**Net savings: ~6G**
**Risk:** LOW for build cache, MEDIUM for volumes

---

### GROUP 19: System Services

| Component              | Size     | Class | Consumer                                          | Action       |
| ---------------------- | -------- | ----- | ------------------------------------------------- | ------------ |
| `ModemManager.service` | ~5M      | G     | No modems detected, no `/dev/ttyUSB*`             | **DISABLE**  |
| `iscsid.service`       | ~5M      | G     | No iSCSI mounts, no Docker usage                  | **DISABLE**  |
| `multipathd.service`   | ~5M      | F     | Device-Mapper multipath — check if used           | **ASK USER** |
| `xrdp.service`         | (active) | B     | Remote desktop — actively used with vscode-server | **KEEP**     |

**Net savings: ~10M**
**Risk:** LOW for ModemManager/iscsid

---

### GROUP 20: APT Old Kernels

| Component                      | Size  | Class | Consumer                          | Action               |
| ------------------------------ | ----- | ----- | --------------------------------- | -------------------- |
| Old kernel configs (rc status) | ~500M | D     | 7 old kernels marked `rc` in dpkg | **`apt autoremove`** |

**Net savings: ~500M**
**Risk:** LOW — old kernels, current is 6.17.0-1020

---

## SUMMARY TABLE

| Group     | Component                 | Size | Class | Savings   |
| --------- | ------------------------- | ---- | ----- | --------- |
| 1         | Ollama duplicates         | 10G  | G     | **~10G**  |
| 2         | Rust                      | 2.5G | G     | **~2.5G** |
| 3         | Homebrew                  | 5.1G | G     | **~5.1G** |
| 4         | Snap disabled             | 800M | D     | **~800M** |
| 5         | Playwright old            | 1G   | D     | **~1G**   |
| 6         | Caches (npm/pnpm/pip/go)  | 1.5G | D     | **~1.5G** |
| 7         | NVM old version           | 500M | D     | **~500M** |
| 8         | Quarantine                | 707M | G     | **~707M** |
| 9         | Codex packages            | 2.2G | D     | **~2.2G** |
| 10        | pipx (needs decision)     | 5.5G | F     | **~2.1G** |
| 11        | Python libs (needs audit) | 6G   | F     | **~3G**   |
| 13        | Git worktrees             | 800M | F     | **~800M** |
| 14        | OpenClaw cleanup          | 166M | D     | **~166M** |
| 15        | CocoIndex target DB       | 2.9G | F     | **~2.9G** |
| 16        | Reports                   | 648M | G     | **~500M** |
| 17        | Go module cache           | 1.6G | D     | **~1.6G** |
| 18        | Docker deep               | 6G   | D     | **~6G**   |
| 19        | System services           | 10M  | G     | **~10M**  |
| 20        | Old kernels               | 500M | D     | **~500M** |
| **TOTAL** |                           |      |       | **~41G**  |

---

## SAFE TO DELETE NOW (D/G classes): ~27G

| Group             | Savings  |
| ----------------- | -------- |
| 1 (Ollama)        | ~10G     |
| 2 (Rust)          | ~2.5G    |
| 3 (Homebrew)      | ~5.1G    |
| 4 (Snap)          | ~800M    |
| 5 (Playwright)    | ~1G      |
| 6 (Caches)        | ~1.5G    |
| 7 (NVM)           | ~500M    |
| 8 (Quarantine)    | ~707M    |
| 9 (Codex)         | ~2.2G    |
| 14 (OpenClaw)     | ~166M    |
| 16 (Reports)      | ~500M    |
| 17 (Go cache)     | ~1.6G    |
| 18 (Docker build) | ~5G      |
| 19 (Services)     | ~10M     |
| 20 (Kernels)      | ~500M    |
| **TOTAL SAFE**    | **~27G** |

## NEEDS DECISION (F class): ~14G

| Group               | Savings | Decision Needed                             |
| ------------------- | ------- | ------------------------------------------- |
| 10 (pipx)           | ~2.1G   | Remove oci-cli, piper-tts, git-filter-repo? |
| 11 (Python libs)    | ~3G     | Audit 370 packages for orphans?             |
| 13 (Worktrees)      | ~800M   | Remove scanner/mission-alpha worktrees?     |
| 15 (CocoIndex)      | ~2.9G   | Is target_sqlite.db orphaned?               |
| 18 (Docker volumes) | ~1G     | Remove n8n-data-1/2?                        |
