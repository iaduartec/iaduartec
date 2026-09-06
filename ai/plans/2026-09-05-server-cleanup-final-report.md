# Server Cleanup — Final Report (Session 2: Deep Audit 15 Phases)

**Date:** 2026-09-05
**Host:** kiri-vnic (Oracle ARM64, Ubuntu 24.04.4, 194G disk)

## BEFORE / AFTER

| Metric                  | Start of session | End of session | Delta          |
| ----------------------- | ---------------- | -------------- | -------------- |
| Used                    | 146G (76%)       | **87G (45%)**  | **−59G**       |
| Available               | 48G              | **107G**       | +59G           |
| RAM used                | 10Gi             | **7.1Gi**      | −3Gi           |
| Original audit baseline | 182G (94%)       | 87G (45%)      | **−95G total** |

## ELIMINATED (this session, ~59G)

| #   | Item                                                                                                                                                                                                  | Size   | Class |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | ----- |
| 1   | Ollama duplicates: user systemd service + `~/.local/lib/ollama` (7G) + `/usr/share/ollama` (3.1G) + `/usr/local/lib/ollama` CUDA libs (3.5G) — zero consumers, no GPU on ARM                          | ~13.6G | G     |
| 2   | Python ML stack: torch, triton, 16× nvidia-*, transformers, ctranslate2, chromadb, onnxruntime, av, imageio-ffmpeg                                                                                    | ~4.5G  | G     |
| 3   | Homebrew `/home/linuxbrew` (no consumers, not in PATH)                                                                                                                                                | 5.1G   | G     |
| 4   | `/srv/ai/openclaw-src` (dev clone; local patch archived to `~/dev-patches/0001-*.patch`)                                                                                                              | 5.8G   | G     |
| 5   | Rust: `~/.rustup` + `~/.cargo` (no Cargo.toml anywhere)                                                                                                                                               | 2.5G   | G     |
| 6   | pipx: oci-cli, piper-tts, git-filter-repo (approved)                                                                                                                                                  | 2.1G   | F→ok  |
| 7   | Docker: `duartec-parts_*` abandoned volumes (old n8n ×2, ollama, mariadb, caddy ×2) + build cache                                                                                                     | 3.2G   | G/D   |
| 8   | Codex: 6 old standalone releases (kept 0.146.0) + generated_images + skill-archive                                                                                                                    | 1.9G   | D     |
| 9   | Go module cache + build cache                                                                                                                                                                         | 1.6G   | D     |
| 10  | Git worktrees: `~/.worktrees` (web-workflows, scanner ×2, mission-alpha)                                                                                                                              | 800M   | F→ok  |
| 11  | Snap: 12 disabled old revisions removed                                                                                                                                                               | 800M   | D     |
| 12  | Playwright: 4 old chromium_headless_shell revisions (kept active 1243 + firefox + webkit)                                                                                                             | 1G     | D     |
| 13  | `~/.quarantine` (4 backup/rollback artifacts)                                                                                                                                                         | 707M   | G     |
| 14  | `~/reports` (historical reports)                                                                                                                                                                      | 648M   | G     |
| 15  | NVM v26.8.1 (default is v24.20.0)                                                                                                                                                                     | 506M   | D     |
| 16  | Actions runner CI checkout `_work/Web_Duartec` (regenerates per job)                                                                                                                                  | 242M   | D     |
| 17  | OpenClaw `repair-backups` + `archive`                                                                                                                                                                 | 166M   | D     |
| 18  | Misc caches: node, jedi, typescript, codex/.tmp, playwright-cli                                                                                                                                       | ~300M  | D     |
| 19  | dpkg `rc` residual configs (28 packages purged)                                                                                                                                                       | ~10M   | D     |
| 20  | cocoindex-code: pipx venv + `~/.cocoindex_code` index (7.3G) + MCP entry in opencode.json + `ccc` skill + 3 daemons (744MB RAM). Local patch archived. Reinstalable con `pipx install cocoindex-code` | 7.3G   | F→ok  |
| 21  | /tmp: 734 archivos `.so` JIT de codex/opencode + n8n debug DBs (9×36M) + artefactos de sesiones Aug 22–Sep 3 (codex-security-remediation, mission-alpha replays, node-compile-cache)                  | ~4.6G  | D     |
| 22  | Snap limpieza total: 12 revisiones viejas + gcloud r492 (218M) + LXD (92M, servicio inactivo/0 contenedores) + chromium+gnome+mesa+gtk+cups (~1.1G)                                                   | ~2.1G  | F→ok  |
| 23  | Antigravity: browser_recordings (559M, debug del 29-ago) + gemini/tmp (48M) — IDE se conserva activo                                                                                                  | 607M   | D     |
| 24  | Docker: imágenes sin contenedor (n8n `<none>`, bases node/ubuntu/debian/caddy/alpine)                                                                                                                 | 254M   | D     |
| 25  | Logs: syslog.1 truncado + journald vacuum 50M                                                                                                                                                         | ~125M  | D     |

## RONDA 2 (post-reporte inicial) — hallazgos adicionales

- **opencode.db (804M)**: historial de chats del usuario — **CONSERVADO** (decisión explícita)
- **openclaw-compile-cache (1.4G, /var/tmp)**: ACTIVO (58k archivos escritos recientemente) — conservado
- **pnpm store (3.1G, ~/.local/share/pnpm)**: todo referenciado por proyectos activos vía hardlinks — conservado
- **~/.local/share/opencode (925M)**: sesiones/DB activas — conservado

## SYSTEM CHANGES

- **Disabled services:** ModemManager (no modems), iscsid (no iSCSI), multipathd (no multipath)
- **Removed user systemd unit:** `ollama.service` (host duplicate; containerized ollama is canonical)
- **Archived:** openclaw local patch → `~/dev-patches/0001-feat-add-build-patch-script-*.patch`

## STACK FINAL (verified operational)

**Docker — 29 containers, all Up:**

- 10× openclaw-sbx-workspace (sandboxes)
- n8n ×6 (n8n-1, unified, runners ×2, sandbox-api, sandbox-runner, searxng)
- insforge ×4 (postgres, postgrest, insforge, deno)
- duartec-parts ×4 (caddy, db-api, mail-relay, mariadb)
- whisper (healthy), media-wrapper (healthy), email-store (healthy), ollama

**Host services active:** caddy, tailscaled, mission-bridge, portfolio (:3000→200), web-duartec (:3001→200), api-stub (:8080→200), fail2ban, docker, actions-runner
**n8n :5678 → 200** | **mission-bridge :8020 → 302 (auth redirect, normal)**
**Ollama:** `qwen3:1.7b` inside `duartec-ollama` — inference verified ("hola" ✅)
**Tailscale:** kiri-vnic online
**Memory:** 23Gi total, 13Gi available

## KEPT (protected/active — flagged for future review)

| Item                                 | Size  | Note                                                                            |
| ------------------------------------ | ----- | ------------------------------------------------------------------------------- |
| `~/.openclaw`                        | 5.9G  | Active (npm/projects 4.5G = sandbox mounts; canvas 509M, agents/telegram 1.1G)  |
| `~/.git` (home repo)                 | 5.1G  | Protected — full history pack                                                   |
| `~/.vscode-server`                   | 3.4G  | Active (xrdp + agent-host writing)                                              |
| actions-runner `_tool`               | 1.8G  | CI tool cache (CodeQL, node) — kept to avoid CI re-downloads                    |
| `~/.pnpm-store`                      | 538M  | All content referenced (prune removed 0)                                        |
| `~/.local/lib/python3.12`            | 1.5G  | Remaining: pandas/scipy/sklearn/opencv/google-api/playwright (misc script deps) |
| duartec-infra/backups + /srv/backups | ~700M | Production backups                                                              |
| `~/go/bin/alpaca`                    | 13M   | Trading SDK binary                                                              |
| `~/portfolio-repo`                   | 2.8G  | Active dev repo (portfolio.service runs from /srv/apps/portfolio)               |
