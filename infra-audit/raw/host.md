# Auditoría infra — host `kiri-vnic` (Oracle Cloud ARM64, Ubuntu 24.04)

- Fecha: 2026-09-06 01:50 UTC · Modo: **SOLO LECTURA** (no se modificó nada; escritura solo de este reporte)
- Kernel: 6.17.0-1020-oracle aarch64 · Uptime 14d 19h · Load 2.59 (con 2 sesiones de agente AI activas)
- RAM ~26G total según tmpfs/12G shm (host 24G+), usuario operativo `ubuntu`; existe usuario legacy `opc` con procesos vivos.
- 29 contenedores Docker corriendo · sudo disponible sin password (solo usado para lectura).

---

## 1. SYSTEMD SISTEMA — servicios CUSTOM

Activos (35 running units, se listan los no-estándar):

| Unidad                                                   | Binario / ExecStart                                                                                  | Corriendo desde                                | Unit file (fecha) | Consumidor aparente                                                                       | Clasif. |
| -------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | ---------------------------------------------- | ----------------- | ----------------------------------------------------------------------------------------- | ------- |
| `web-duartec.service`                                    | `/srv/apps/web-duartec/node_modules/.bin/next start -p ${PORT}` (3000)                               | 2026-09-03                                     | 2026-03-08        | Caddy :80/:443 → sitio público duartec.es                                                 | **A**   |
| `portfolio.service`                                      | `/srv/apps/portfolio/.../next start -p ${PORT}` (3001)                                               | 2026-09-06 (reinicia solo, ActEnter hoy 00:34) | 2026-07-10        | Caddy + tailscale-serve (portfolio)                                                       | **A**   |
| `caddy.service`                                          | `/usr/bin/caddy run --config /etc/caddy/Caddyfile`                                                   | 2026-08-29                                     | ~2026-02-19       | Frontal público :80/:443, :8090 (restaurante), :2019 metrics                              | **A**   |
| `mission-bridge.service`                                 | `python3 -u server.py` (127.0.0.1:8020), env-files `.env` + `/etc/mission-bridge-live-ingestion.env` | 2026-09-05 (editado 09-04 21:24)               | 2026-09-04        | Ingesta YouTube/Gemini para portfolio; cron cookies cada 4h; expuesto por tailscale :9448 | **A**   |
| `actions.runner.iaduartec-Web_Duartec.kiri-vnic.service` | `/srv/automation/actions-runner/runsvc.sh`                                                           | 2026-09-03                                     | 2026-02-08/19     | GitHub repo `iaduartec/Web_Duartec` (CI diaria)                                           | **A**   |
| `tailscale-serve.service`                                | oneshot `duartec-infra/scripts/tailscale-serve-apply.sh` (oneshot, RemainAfterExit)                  | 2026-08-22                                     | 2026-06-08        | Publica puertos en IP tailnet 100.103.134.102                                             | **A**   |
| `api-stub.service`                                       | `node /srv/apps/api-service/server.js` (127.0.0.1:8080)                                              | 2026-08-22                                     | 2026-02-19        | Desconocido: "API Stub" en localhost; sin refs claras en units/cron visibles              | **G**   |

No corriendo pero con unit file presente (huérfanos / legacy):

| Unidad                    | Estado                              | Origen                                                                                                        | Clasif.             |
| ------------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------- | ------------------- |
| `n8n.service`             | disabled/inactive (unit 2026-02-23) | `docker run n8n` ad-hoc → sustituido por stacks Docker actuales                                               | **D** (borrar unit) |
| `ollama.service`          | disabled/inactive (unit 2026-04-26) | `/usr/local/bin/ollama serve` nativo → sustituido por contenedor `duartec-ollama`                             | **D**               |
| `openclaw.service`        | disabled/inactive (2026-04-24)      | gateway desde `/srv/ai/openclaw-src` (repo fuente) → sustituido por user unit `openclaw-gateway` (npm global) | **D**               |
| `openclaw-agents.service` | disabled/inactive (2026-04-24)      | watchdog `/srv/ai/openclaw-config/scripts/check_agents.sh`                                                    | **D**               |

Enabled con sospecha de huérfano (paquete estándar mal aplicado a este host):

- `postfix.service` **enabled** pero sin `/etc/postfix/main.cf` → todo `sendmail` falla cada minuto (ver §8). Sin MTA funcional. **D** (purge o configure).
- `firewalld.service` enabled (alias dbus FirewallD1) mientras **ufw también enabled** → doble firewall. firewalld no aparece corriendo. **D** (elegir uno).
- `podman.service`, `podman.socket`, `podman-auto-update.timer`, `podman-restart`, `podman-clean-transient` enabled → **0 contenedores podman**. **E**.
- `open-vm-tools.service` + `vgauth.service` enabled → host Oracle/ARM (KVM), no VMware. **D**.
- `rsync.service` enabled, inactive → ¿rsyncd usado? Sin evidencia. **D**.
- `lxd-installer.socket`, `ubuntu-fan.service`, `nfs-client.target`, `remote-fs.target` → estándar sin uso aparente en este host. **D menor**.
- `xrdp` + `xrdp-sesman` corriendo (3389) → acceso RDP real en uso (sesión activa con chromium). **B** (consolidar: ¿RDP permanente en servidor headless?).

Estándar correctos: docker, containerd, cron, ssh, fail2ban, ufw, unattended-upgrades, snapd, oracle-cloud-agent (snap), unified-monitoring-agent (OCI), tailscaled, systemd-*.

## 2. USER SYSTEMD (uid 1001 ubuntu)

Activos (5 + dbus):

| Unidad                         | Qué corre                                                                                                          | Desde            | Clasif.                                                                                                               |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------ | ---------------- | --------------------------------------------------------------------------------------------------------------------- |
| `openclaw-gateway.service`     | `node .../openclaw/dist/index.js gateway --port 5800` (127.0.0.1) + 10 sandboxes docker `openclaw-sbx-workspace-*` | 2026-09-05 19:59 | **A**                                                                                                                 |
| `1mcp.service`                 | `1mcp serve --transport http --port 3050` (con auth)                                                               | 2026-08-22       | **A**                                                                                                                 |
| `duartec-static-sites.service` | `node /home/ubuntu/output/playwright/hub-link-audit/static-sites-server.mjs` (100.x:19180)                         | 2026-08-23       | **B** (sirve espacio/restaurante; cwd `/home/ubuntu`, artefacto dentro de `output/playwright/...` — ubicación frágil) |
| `trading-freqtrade.service`    | freqtrade OKX **demo** (configs/freqtrade/okx_demo.json), API :18080                                               | 2026-08-24       | **G** (demo desde hace 13 días; decidir si es viable o apagar)                                                        |
| `trading-streamlit.service`    | streamlit :8501                                                                                                    | 2026-09-02       | **G** (consola del demo)                                                                                              |

Inactivos pero instalados en `~/.config/systemd/user/` (disabled/static): `duartec-healthcheck`(+timer, activo vía timer), `duartec-whisper`, `llama-cpp`, `mission-bridge-8000`, `mission-bridge` (user, duplicado del system), `n8n-update`(+timer activo), `ollama-docker-proxy`, `openclaw-rescue-gateway`(+socket), `openclaw-telegram-watchdog`(+timer), `telegram-bot`, `trading-bot-loop`, `openclaw-gateway.service.bak` y `.bak-20260710` (backups). → Lote **D** de limpieza (13 files legacy en user units).

Otros user units: ninguno para `/home/opc` (usuario sin units, solo `.ssh`).

## 3. TIMERS Y CRON

Timers system propios:

| Timer                           | Cadencia       | Último / estado                                                  | Clasif.                                                                                                                  |
| ------------------------------- | -------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `web-duartec-auto-update.timer` | **cada 5 min** | corriendo OK, con 2 fallos intermitentes 01:20/01:25 (git fetch) | **B** — frecuencia excesiva y solapa con CI del runner (Auto-Fix scheduled + deploys). Consolidar en un único mecanismo. |
| `portfolio-mtm.timer`           | daily 22:00    | OK                                                               | **G** — hace POST `/api/shadow-portfolio/run?mode=dry-run`: si siempre es dry-run, es no-op → revisar intención.         |
| `certbot.timer`                 | 2×/día         | OK                                                               | **A** (renovación TLS Caddy/duartec.es)                                                                                  |

Timers user: `n8n-update.timer` (Sun 03:00, `update-n8n.js` del repo duartec-infra → mantiene contenedor n8n unificado) **A**; `duartec-healthcheck.timer` cada 30 min **A**; `launchpadlib-cache-clean` estándar.

Cron:

| Entrada                                                                  | Cadencia         | Estado                                                                                        | Clasif.                                           |
| ------------------------------------------------------------------------ | ---------------- | --------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| `~/scripts/api_watchdog.sh` (ubuntu)                                     | **cada minuto**  | genera fallo `postfix/sendmail` cada minuto (log spam §8); archivo no legible en modo lectura | **G** — revisar propósito y su `sendmail`         |
| `mission-bridge/scripts/sync-youtube-cookies.sh`                         | cada 4 h         | ok                                                                                            | **A**                                             |
| `daily_ingest.sh` CNMV/PDMR (`/srv/automation/cnmv-pdmr`)                | daily 07:15      | ok                                                                                            | **G** — ¿proyecto CNMV vigente?                   |
| `duartec-weekly-mail-maintenance.sh`                                     | weekly Sun 09:00 | log en `/srv/logs/legacy-output/`                                                             | **D** — marcado legacy por su propia ruta de logs |
| `/etc/cron.d/backup-openclaw` → `~/bin/backup-openclaw.sh`               | daily 03:00      | ok                                                                                            | **A**                                             |
| `/etc/cron.d/certbot`, `e2scrub_all`, `sysstat`                          | estándar         | ok                                                                                            | A (certbot cron es no-op con systemd, normal)     |
| cron.hourly: vacío; daily: estándar; root: sin crontab; opc: sin crontab |                  |                                                                                               |                                                   |

## 4. PUERTOS → PROCESO (no obvios)

| Puerto                                                     | Proceso / origen                                                                            | Consumidor         | Nota                                                              |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------- | ------------------ | ----------------------------------------------------------------- |
| **5678 (0.0.0.0 + [::])**                                  | docker-proxy → contenedor `n8n-n8n-1`                                                       | público en la VNIC | ⚠️ n8n **expuesto a todas las interfaces** (2ª instancia n8n)     |
| **3003 (0.0.0.0)**                                         | `next-server` con cwd `/srv/apps/web-duartec/.worktrees/nuevo-prototype-review-remote`      | público en la VNIC | ⚠️ servidor de producción de un **worktree de revisión** expuesto |
| 80 / 443 / 2019 / 8090                                     | caddy nativo                                                                                | público            | 8090 = sitio estático `/srv/apps/restaurante/dist`                |
| 3000 / 3001                                                | web-duartec / portfolio (localhost)                                                         | Caddy              | A                                                                 |
| 8080                                                       | api-stub (localhost)                                                                        | ¿?                 | G                                                                 |
| 3050                                                       | 1mcp (localhost, con auth)                                                                  | agentes AI         | A                                                                 |
| 5800                                                       | openclaw-gateway (localhost)                                                                | openclaw           | A                                                                 |
| 8020                                                       | mission-bridge (localhost)                                                                  | tailscale :9448    | A                                                                 |
| 4173                                                       | `vite preview` de `/home/ubuntu/apps/duartec-hub` — **sin unit, lanzado a mano 2026-08-23** | ninguno aparente   | **E** huérfano                                                    |
| 19180 (100.x)                                              | duartec-static-sites                                                                        | tailnet            | B                                                                 |
| 18080 / 8501                                               | freqtrade API / streamlit                                                                   | demo trading       | G                                                                 |
| 3002, 7130, 7131                                           | docker-proxy → insforge (postgrest/insforge)                                                | localhost          | A (stack insforge)                                                |
| 5682, 5999, 6080                                           | docker-proxy → `duartec-media-wrapper`                                                      | localhost          | A                                                                 |
| 19080                                                      | docker-proxy → `duartec-parts-caddy`                                                        | interno            | A                                                                 |
| 9443-9450, 8502, 8443, 65303, 5252, 443 en 100.103.134.102 | **tailscaled** (tailscale serve handlers)                                                   | tailnet            | A (12 handlers declarados; revisar que todos tengan consumidor)   |
| 22, 3389                                                   | sshd, xrdp                                                                                  | público/tailnet    | A/B                                                               |
| 41641/udp                                                  | tailscaled                                                                                  | —                  | A                                                                 |

## 5. PROCESOS NO-DOCKER persistentes (top RSS)

| Proceso                                        | PID                               | RAM         | Desde     | Origen                                                                                                                                                       |
| ---------------------------------------------- | --------------------------------- | ----------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `opencode` ×2 (sesiones interactivas)          | 3804436/3794088                   | ~1.0G       | hoy       | pts (sesiones de trabajo actuales)                                                                                                                           |
| `next-server` ×3                               | 4178435/3430881/4173581           | ~1.0G       | 09-03→hoy | systemd (3000/3001) + worktree (3003)                                                                                                                        |
| openclaw gateway                               | 2822210                           | 583M        | 09-05     | user unit                                                                                                                                                    |
| codex **app-server** (daemon)                  | 848576                            | 457M        | 09-05     | codex `--listen unix://` + 5 puertos localhost (35305, 36967, 43925, 41441, 44609)                                                                           |
| freqtrade (OKX demo)                           | 540266                            | 379M        | 08-24     | user unit                                                                                                                                                    |
| chromium root (mission-bridge YouTube)         | 2799073+renderers                 | ~600M total | 09-05     | contenedor duartec-media-wrapper (proceso en host vía docker? no — chromium con `--user-data-dir=/data/mission-bridge-chromium` corriendo en host como root) |
| playwright chromium ×2 perfiles + cliDaemon ×2 | varios                            | ~900M       | 09-05     | agentes AI (trabajos activos)                                                                                                                                |
| 1mcp serve                                     | 1929                              | 256M        | 08-22     | user unit                                                                                                                                                    |
| mission-bridge python                          | 265273                            | 256M        | 09-05     | system unit                                                                                                                                                  |
| **n8n nativo ×2 usuario `opc`**                | 373144 (Sep 03), 2044933 (Aug 23) | 262M+234M   | —         | **forastero**: `node /usr/local/bin/n8n`, cwd `/home/node`, sin unit, sin crontab → huérfanos de alguna instalación manual                                   |
| vscode-server agent                            | 4021164                           | 87M         | 09-03     | SSH remote                                                                                                                                                   |
| streamlit                                      | 3894169                           | 179M        | 09-02     | user unit                                                                                                                                                    |
| codex sesión interactiva                       | 3476526                           | 127M        | hoy 00:42 | pts/0                                                                                                                                                        |
| Runner.Listener                                | 3807456                           | 97M         | 09-03     | system unit                                                                                                                                                  |
| dockerd                                        | 2138                              | 87M         | 08-22     | system unit                                                                                                                                                  |

Duplicidades de proceso: 2× n8n nativo (opc) + 2× stack n8n en docker (`n8n-unified` y compose `n8n-n8n-1` + sus 2 runners + sandbox + searxng) + unit systemd disabled = **5 instalaciones de n8n coexistiendo**.

## 6. HERRAMIENTAS AI

| Herramienta          | Instalación                                                                                                                                                                       | Versión        | Tamaño config                                                                                                    | Último uso real                      | Proceso activo                                           | Integración con proyectos                                                                                                                        | Clasif.                                                                           |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- | ---------------------------------------------------------------------------------------------------------------- | ------------------------------------ | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------- |
| **codex**            | npm global `@openai/codex` (nvm v24.20.0)                                                                                                                                         | 0.153.4        | `~/.codex` **1.8G**, 46k files últimos 30d                                                                       | **hoy 01:48** (logs sqlite)          | sí: app-server daemon + sesión + MCP `codex-security` ×6 | `config.toml` declara proyectos: `/home/ubuntu`, `/home/ubuntu/portfolio-repo`, `~/.openclaw`, `/srv/apps/web-duartec`, `~/ruview` + hook propio | **MANTENER**                                                                      |
| **opencode**         | npm global `opencode-ai`                                                                                                                                                          | 1.18.21        | `~/.local/share/opencode` 949M + `~/.config/opencode` 67M + cache 418M (`~/.opencode` 63M congelado desde 08-23) | **hoy** (2 sesiones vivas)           | sí ×2                                                    | está ejecutando esta auditoría; proyectos duartec                                                                                                | **MANTENER**                                                                      |
| **gemini**           | npm global `@google/gemini-cli`                                                                                                                                                   | 0.58.0         | `~/.gemini` **1.1G**, 261 files/30d                                                                              | 2026-09-03 (state.json)              | no                                                       | mission-bridge lo usa como transcriptor (`gemini-3.1-flash-lite`, env del unit)                                                                  | **MANTENER** (uso por mission-bridge) / revisar 1.1G (¿caches?)                   |
| **claude**           | npm global `@anthropic-ai/claude-code`                                                                                                                                            | 2.1.159        | `~/.claude` 208K, 0 files/30d                                                                                    | **2026-05-31** (3+ meses)            | no (solo hooks MCP de codex lo referencian)              | `.claude.json.backup` mayo; sin actividad propia                                                                                                 | **REVISAR** (binario quizá usado por sub-agentes openclaw; config local inactiva) |
| **openclaw**         | npm global `openclaw`                                                                                                                                                             | 2026.9.1       | `~/.openclaw` **7.0G**, 24k files/30d                                                                            | **hoy 01:48** (agentes + sandboxes)  | sí: gateway + 10 contenedores sandbox                    | telegram-orchestrator con codex-home propio                                                                                                      | **MANTENER** (candidato a limpieza interna: 7G)                                   |
| **1mcp**             | `/usr/local/bin/1mcp`                                                                                                                                                             | (servidor MCP) | `~/.config/1mcp` 36K                                                                                             | hoy                                  | sí (puerto 3050, con auth)                               | hub MCP para agentes                                                                                                                             | **MANTENER**                                                                      |
| **vscode-server**    | `~/.vscode-server` (SSH remote)                                                                                                                                                   | code-08d4889f… | **3.4G**                                                                                                         | **hoy 00:09**                        | sí                                                       | sesión SSH remota                                                                                                                                | **MANTENER** + purgar versiones antiguas en `cli/servers/`                        |
| **antigravity**      | no instalado (`~/.antigravity` no existe)                                                                                                                                         | —              | —                                                                                                                | —                                    | —                                                        | —                                                                                                                                                | —                                                                                 |
| deno                 | `~/.local/bin/deno`                                                                                                                                                               | —              | —                                                                                                                | runtime de insforge (docker)         | en contenedor                                            | insforge functions                                                                                                                               | **MANTENER**                                                                      |
| yt-dlp               | pipx 2026.8.19                                                                                                                                                                    | —              | —                                                                                                                | hoy (mission-bridge, cookies cron)   | no persistente                                           | mission-bridge                                                                                                                                   | **MANTENER**                                                                      |
| Otros npm globales   | `@0dai-dev/cli@4.3.4`, `@steipete/oracle@0.8.6`, `agent-browser@0.26.0`, `clawhub@0.5.0`, `mcporter@0.7.3`, `ctx7@0.4.4`, `lighthouse@13.0.2`, `himalaya@1.1.1`, `vercel@59.11.2` | —              | —                                                                                                                | varios                               | —                                                        | ecosistema openclaw/duartec                                                                                                                      | **CONSOLIDAR** (auditar uso individual en 2ª pasada)                              |
| n8n (binario nativo) | `/usr/local/bin/n8n` ejecutado por **usuario `opc`**                                                                                                                              | —              | —                                                                                                                | procesos vivos sin dueño de servicio | sí ×2                                                    | ninguna detectada                                                                                                                                | **ELIMINAR** (huérfanos)                                                          |

## 7. GITHUB ACTIONS RUNNER

- Instalación única: `/srv/automation/actions-runner` (bin 2.337.0, symlink a versión; queda bin.2.336.0 viejo ~cada uno 20k dir entries).
- `.runner` (sin secretos): agentName `kiri-vnic`, agentId 23, repo **`iaduartec/Web_Duartec`**, pool Default, workFolder `_work`, V2 flow.
- `.credentials` / `.credentials_rsaparams` presentes (NO leídos).
- Servicio: `actions.runner.iaduartec-Web_Duartec.kiri-vnic.service` — **active (running) + enabled**, desde 2026-09-03 18:06.
- Labels (vía API gh): `self-hosted`, `Linux`, `ARM64` — status online, idle.
- Actividad real: `gh run list` → CI "Code quality" push **hoy 01:23** (failure), "Auto-Fix (Lint & Format)" **scheduled diario** (últ. 09-05 success), "AI · PR review (OpenAI)" 09-03. `_diag`: Worker log **2026-09-06 01:26** → ejecución de hace ~30 min.
- `_work`: **2.3G** total — solo repo `Web_Duartec/Web_Duartec`; `_tool`: **1.8G** (CodeQL + node) → cache de herramientas pesada, útil para CI.
- `_diag`: 2.1M.
- ¿Más runners? No: solo este (existe `.bak` del unit de 2026-02-19).
- **Veredicto: JUSTIFICADO como permanente** (trabajo real diario: schedule + pushes + reviews; cache _tool acelera CodeQL). Alternativa ephemeral no compensa: perdería cache 1.8G y el Auto-Fix scheduled diario lo despertaría igualmente. Duplicado de deploy: `web-duartec-auto-update.timer` (5 min, pull-based) **y** CI del runner → consolidar en un solo mecanismo de despliegue.

## 8. ERRORES RECIENTES (journal -p err, 48h)

1. **`postfix/sendmail`: `fatal: open /etc/postfix/main.cf: No such file or directory` — cada minuto, cientos de veces.** Causante: cron `api_watchdog.sh` (cada minuto) que llama sendmail. postfix enabled pero sin configurar. Ruido continuo + cola de logs.
2. **`web-duartec-auto-update.service`: "Failed to start" ×2 (01:20:41, 01:25:44)** — fallo intermitente del fetch git; a las 01:40+ termina OK ("Sin cambios"). Revisar timeout/red en el script.
3. **`networkctl`: "Interface vethXXXX not found"** ×2 cada pocos minutos — ruido benigno por contenedores docker + systemd-networkd.
4. Nada más relevante en err de los 48h (sin OOM, sin fallos de docker/caddy/runner en ese nivel).

## 9. DISCO

- `/` 194G: usado **88G (46%)** — sin presión.
- Top: `/var/lib/docker` **34G** · `/home/ubuntu` **39G** · `/srv` **13G** · `/var/log` 363M · `/opt` 328M · `/home/opc` 28K.
- Dentro de /home/ubuntu: `.openclaw` **7.0G**, `.vscode-server` 3.4G, `portfolio-repo` **2.7G** (¡repo+worktrees duplicando `/srv/apps/portfolio` en prod!), `.cache` 2.3G, `.codex` 1.8G, `projects` 1.6G, `duartec-infra` 555M, `ocmonitor-share` 288M, `ibex_charts2` 173M, `mission-bridge` 129M, `apps` 91M (`duartec-hub`), y restos pequeños (`ibex_charts` 43M, `missionAlphaLab` 22M, `snake-pentagon` 4M, `quarantine` 4M, `openclaw-backups` 3M).

---

## 10. SÍNTESIS DE LIMPIEZA (arquitectónica)

**Duplicaciones confirmadas (mayor impacto):**

1. **n8n ×5**: 2 stacks docker (uno expuesto en 0.0.0.0:5678), 2 procesos nativos del usuario `opc` (huérfanos), 1 unit systemd disabled. Decidir stack canónico (parece `n8n-unified` + `n8n-update.timer`) y eliminar el resto.
2. **Ollama ×3**: unit system disabled + contenedor `duartec-ollama` activo + binario local `~/.local/bin/ollama` con `~/.ollama` 1.3G.
3. **OpenClaw doble origen**: units system legacy apuntando a `/srv/ai/openclaw-src` (disabled) vs npm global en marcha.
4. **Deploy doble**: auto-update.timer cada 5 min + runner CI (Auto-Fix scheduled).
5. **Firewall doble**: ufw + firewalld habilitados.
6. **Portfolio duplicado**: `/home/ubuntu/portfolio-repo` 2.7G vs `/srv/apps/portfolio` prod.

**Riesgos:**

- `0.0.0.0:5678` (n8n) y `0.0.0.0:3003` (next de un **worktree**) expuestos en la VNIC.
- postfix roto (enabled, sin main.cf) — spam de errores cada minuto.
- procesos n8n corriendo como usuario `opc` (sin units, sin crontab → nadie los reinicia ni vigila; origen desconocido).
- `~/.openclaw` 7G sin política de retención.

**Sin consumidor aparente:** api-stub (:8080), vite preview :4173, cron semanal mail-maintenance, `portfolio-mtm` en modo dry-run permanente, trading demo (freqtrade+streamlit 13 días).
