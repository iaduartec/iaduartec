# Auditoría Arquitectónica kiri-vnic — FASE 1–8 (solo lectura)
**Fecha:** 2026-09-06 · **Host:** Oracle Cloud ARM64 · Ubuntu 24.04 · **Modo:** solo lectura, sin modificaciones
**Informes crudos:** `raw/docker.md` (41KB) · `raw/host.md` (35KB) · `raw/repos-openclaw.md` (26KB)

---

## Métricas ANTES (verificadas)

| Métrica | Valor |
|---|---|
| Contenedores | **29 activos / 0 parados** (verificado `docker ps -a` = 29) |
| Proyectos compose | 3: `duartec-voice-ai` (10), `insforge` (4), `n8n` (5) + 10 openclaw-sbx efímeros |
| Imágenes | 20 tagged + 1 dangling (ace03195c465, n8n 2.35.7, 1.48GB) = 13.77GB |
| Volúmenes | 13 (1.94GB: dind 894M, mariadb 843M, n8n-unified 130M, postgres 91M) |
| Redes | 6 (bridge/host/none + 3 de proyecto) |
| RAM | ~7G sistema; contenedores ~2.05 GiB (top: media-wrapper 606M, n8n-unified 287M, n8n-n8n-1 241M) |
| Disco | 88G/194G (46%): /var/lib/docker 34G, /home 39G, /srv 13G |

---

## FASE 2 — Mapa Funcional (A–G)

**Clasificación:** A=obligatorio · B=útil consolidable · C=duplicado funcional · D=legacy · E=sin consumidor · F=solo desarrollo · G=incierto

### Docker / Data plane

| Componente | Función | Consumidor | Prod/Dev | Clasif. |
|---|---|---|---|---|
| `n8n-unified` (duartec-voice-ai, 33 wf, 73 exec/7d, sqlite 37.7M activo) | Orquestación workflows canónica | Editor via caddy interno 19080 + tailnet | PROD | **A** |
| `n8n-runners` (duartec-voice-ai, 358 líneas log, broker n8n-unified:5679) | Task runner del canónico | n8n-unified | PROD | **A** |
| `n8n-n8n-1` (n8n, dangling 1.48G, 0 wf, 0 exec, sin escritura desde 2026-08-25) | n8n duplicado | NADIE (expuesto 0.0.0.0:5678) | — | **C** |
| `n8n-runners-1` (n8n, 7 líneas desde 2026-08-23, "waiting for task offer") | Runner del duplicado | n8n-n8n-1 | — | **C** |
| `n8n-sandbox-api-1` + `n8n-sandbox-runner-1` (dind) | Infra sandbox AI de n8n | n8n-n8n-1 (n8n-unified apunta pero en red distinta → inalcanzable) | — | **C** |
| `n8n-searxng-1` (0 req/48h) | Buscador para AI sandbox | n8n legacy | — | **C/E** |
| `duartec-ollama` (qwen3:1.7b, 1.4GB, usado hace 12h) | LLM local | n8n-unified, media-wrapper, db-api, email-store | PROD | **A** |
| `duartec-parts-mariadb` 11.4 (843M) + `duartec-parts-db-api` (160 req/48h) | DB + API partes | Mission Bridge, portfolio, email-store | PROD | **A** |
| `duartec-email-store` (crash-loop RC 2603 cada ~5min) | Store emails → MariaDB | db-api/MariaDB | PROD | **A** (roto) |
| `duartec-parts-mail-relay` (8080, sin evidencia uso) | Relay IMAP/SMTP | — | — | **G** |
| `duartec-local-whisper` (0 POST desde 2026-08-27, transcripción va por OpenAI) | STT local | — | — | **E** |
| `duartec-media-wrapper` (606M RAM, chromium+noVNC 5682/5999/6080) | Browser headless Mission Bridge | Mission Bridge | PROD | **A** |
| `duartec-parts-caddy` (2.8.4, 127.0.0.1:19080) | Proxy interno con gating | n8n-unified, whisper, db-api, mail-relay, media | PROD | **A** |
| `insforge-*` (insforge 7130/7131, postgrest 3002, deno 7133, postgres 5432) | Backend OSS + REST + edge + DB | Usuario real 100.112.222.48 (09-05 20:39) | PROD | **A** |
| `openclaw-sbx-*` ×10 (red none, idle 27-40h) | Sandboxes efímeros agentes | openclaw-gateway | PROD | **F** (activos Sep 4) |

### Host / Systemd

| Componente | Función | Consumidor | Clasif. |
|---|---|---|---|
| `caddy.service` (host, 2600105, 10.0.0.229:80/443 + :8090) | Frontal público TLS duartec.es | Internet | **A** |
| `web-duartec.service` (:3000, /srv/apps/web-duartec) | Next.js duartec.es | Caddy | **A** (desalineado) |
| `portfolio.service` (:3001, /srv/apps/portfolio) | Next.js portfolio | Caddy+tailnet | **A** (deploy bloqueado) |
| `mission-bridge.service` (:8020) | Ingesta YouTube→portfolio | portfolio, tailnet :9448 | **A** |
| `tailscale-serve.service` (12 handlers 9443-9450, 8443, 8502…) | Exposición tailnet | — | **A** |
| `actions.runner.*` (kiri-vnic, iaduartec/Web_Duartec, ARM64) | CI self-hosted | GitHub | **A** |
| `api-stub.service` (:8080, /srv/apps/api-service) | Mock API | NADIE detectable | **G** |
| `openclaw-gateway` (user, :5800) | Gateway OpenClaw | agentes | **A** |
| `1mcp` (user, :3050) | MCP aggregator | agentes | **A** |
| `duartec-static-sites` (user, :19180, `output/playwright/…`) | Static hub | tailnet | **B** (ruta frágil) |
| `trading-freqtrade/streamlit` (user, 18080/8501) | Demo trading OKX | — | **G** |
| `vite preview` :4173 (/home/ubuntu/apps/duartec-hub, sin unit, desde 08-23) | Preview manual | — | **E** |
| `n8n` nativo ×2 (usuario `opc`, sin unit/crontab, desde 08-23/09-03) | n8n host huérfano | — | **D** |
| `ollama.service` (disabled), `n8n.service`, `openclaw.service`, `openclaw-agents.service` | Units legacy sustituidas por Docker/user | — | **D** |
| `postfix` enabled sin `main.cf` (fatal cada minuto) | MTA | cron api_watchdog | **D** |
| `firewalld`+`ufw` ambos enabled | Firewall | — | **D** (duplicado) |
| `podman.{service,socket}` + timer (0 containers) | Runtime alternativo | — | **E** |
| `open-vm-tools`/`vgauth` en ARM Oracle | Guest tools VMware | — | **D** |

### Timers / Cron

| Item | Cadencia | Clasif. |
|---|---|---|
| `web-duartec-auto-update.timer` (cada 5 min, pull+restart) | 5 min | **C** (duplica CI) |
| `portfolio-mtm.timer` (daily 22:00, siempre dry-run) | daily | **G** |
| cron `api_watchdog.sh` (cada minuto, genera error postfix) | 1/min | **G** |
| cron `duartec-weekly-mail-maintenance` (auto-declarado legacy) | weekly | **D** |
| cron `daily_ingest.sh` CNMV (07:15) | daily | **G** |
| `n8n-update.timer` (user, Sun 03:00, auto-update n8n) | weekly | **A** |

### Repositorios

| Ruta | Tamaño | Últ. act. | Dirty | Remote | Clasif. |
|---|---|---|---|---|---|
| /srv/apps/portfolio | 2.7G | 09-06 | 3 | iaduartec/portfolio | PROD deploy (bloqueado) |
| ~/portfolio-repo | 2.8G | 09-06 | 1 | iaduartec/portfolio | DEV (misma app) |
| /srv/apps/web-duartec | 4.0G | 09-06 | 3 | iaduartec/Web_Duartec | PROD (rama≠main) |
| ~/mission-bridge | 129M | 09-06 | 1 | iaduartec/Mission-Bridge | DEV+systemd |
| ~/duartec-infra | 555M | 09-05 | 0 | iaduartec/duartec-infra | PROD-INFRA |
| /srv/apps/restaurante | 871M | 05-30 | 1 | iaduartec/restaurante | PROD desactualizada |
| /srv/apps/espacio | 345M | 05-30 | 4 | iaduartec/espaciox | PROD desactualizada |
| ~/.openclaw | 7.0G | 09-05 | 16363 | — | RUNTIME (no código) |
| ~/ocmonitor-share | 288M | 09-03 | 0 | SIN REMOTE | **G** (riesgo pérdida) |
| /srv/ai/openclaw-config | ~1M | 05-13 | — | legacy | **D** |
| ~/projects/trading | 1.6G | 09-05 | 0 | iaduartec/trading-bot | DEV **G** |
| ~/apps/duartec-hub | 91M | 09-05 | 0 | iaduartec/duartec-hub | DEV |

### Herramientas AI

| Herramienta | Instalación | Último uso | Proc. | Veredicto |
|---|---|---|---|---|
| codex 0.153.4 | npm global, ~/.codex 1.8G | hoy | daemon+MCPs | **MANTENER** |
| opencode 1.18.21 | npm global, ~949M+67M+418M | hoy | ×2 sesiones | **MANTENER** |
| gemini 0.58.0 | npm global, ~/.gemini 1.1G | 09-03 | no | **MANTENER** (limpiar 1.1G) |
| openclaw 2026.9.1 | npm global, ~/.openclaw 7.0G | hoy | gateway+10 sbx | **MANTENER** (limpiar interno) |
| 1mcp | /usr/local/bin | hoy | :3050 | **MANTENER** |
| vscode-server | ~/.vscode-server 3.4G | hoy | sí | **MANTENER** (purgar viejas) |
| claude 2.1.159 | npm global, ~/.claude 208K | 2026-05-31 | no | **REVISAR→ELIMINAR** |
| n8n nativo | /usr/local/bin/n8n (opc) | 08-23/09-03 | ×2 | **ELIMINAR** |

---

## FASE 3 — Duplicidades (evidencia)

### n8n —Stack legacy completo es duplicado muerto
- **Canónico n8n-unified:** 33 workflows (20 activos), 73 exec/7d, última 2026-09-05 03:15, sqlite 37.7M WAL 09-05 11:04, logs activos, editor via `n8n.tail4b3cf6.ts.net`.
- **Duplicado n8n-n8n-1:** 0 workflows, 0 execuciones (max=NULL), sqlite 1.5M sin escritura desde 2026-08-25, imagen dangling ace03195c465 (1.48GB), expone 0.0.0.0:5678 sin consumidores. `ss -lntp` lo confirma.
- **Runners:** `n8n-runners` → broker n8n-unified:5679, 358 líneas, reconexiones Sep 2-3 → activo. `n8n-runners-1` → broker n8n-n8n-1, 7 líneas desde 08-23, atascado → nunca trabajó.
- **sandbox-api + sandbox-runner dind:** actividad Sep 3 pero n8n-unified tiene `SANDBOX_API_URL=sandbox-api:8080` y `searxng:8080` en otra red (`duartec-net` vs `n8n_default`) → inalcanzables, config heredada muerta.
- **searxng:** 0 requests/48h, solo servía al stack muerto, errores wikidata 403.
- **Conclusión:** ambos n8n no son necesarios; el duplicado no sirve nada desde hace 12 días. Un solo n8n cubre todo.

### Caddy — no es duplicado literal, pero hay capas y rutas muertas
- Host Caddy sirve 80/443 público (verificado `ss` + `Caddyfile` md5 idéntico a `~/duartec-infra/Caddyfile-host`).
- Docker Caddy solo 127.0.0.1:19080 con gating (secret, Tailscale-User-Login) hacia n8n-unified, whisper, db-api, etc.
- **No hay proxy duplicado funcional** (roles distintos: edge vs interno). Candidata a simplificar a futuro, pero NO consolidar ahora (viola FASE 9: ciclos de actualización distintos y evitar SPOF sin motivo).
- **Rutas muertas:** `openwebui.tail…→8082` y `kiri-vnic:8443→8082` (8082 no listena, verificado `ss`), `N8N_MCP_URL→5680` (no listena), `OPENCLAW_URL→18889` (gateway real :5800), ~25 `Caddyfile.bak` (2 de 2022).

### Bases — no unificar, detectar abandonadas
- **MariaDB duartec_parts (843M):** consumidores reales db-api (160 req/48h) y email-store. ACTIVA.
- **PostgreSQL insforge (91M):** consumidores insforge/postgrest/deno, tráfico real 09-05 20:39. ACTIVA.
- **SQLite n8n-unified (37.7M) ACTIVA / n8n-n8n-1 (1.5M) MUERTA.** No hay DB sin consumidor.
- `insforge_storage-data` 8K vacío, 3 backups sqlite legacy (36M) dentro del volumen vivo.

### Ollama — canónica confirmada
- **Solo Docker canónico** `duartec-ollama` con qwen3:1.7b (1.4GB, usado hace 12h). Host: sin binario en PATH, servicio disabled, 0 procesos host, `~/.ollama` (1.3G) montado en el contenedor (storage compartido, no duplicado).
- Inconsistencia: 5 contenedores referencian modelos inexistentes (llama3.2, qwen2.5 variants) — corregir envs al fijar canónico.

### Repos prod/dev
- **portfolio:** ~/portfolio-repo (DEV, 2.8G, rama codex) vs /srv/apps/portfolio (PROD deploy, 2.7G, rama main). Mismo remote+pkg. Patrón sano (dev checkout + deploy ff-only). NO eliminar dev. Worktree duplicado `virtual-tier-portfolio` ×2 (+181M) → consolidar.
- **OpenClaw config:** ~/.openclaw (ACTIVA 09-05, 7G) vs /srv/ai/openclaw-config (LEGACY sin cambios desde 05-13). Duplicado muerto.
- **OpenClaw npm:** 4.5G en `~/.openclaw/npm/projects/openclaw-*` con variantes duplicadas.

### Runners — 1+2 vs 1 canónico
- Docker: `n8n-runners` (canónico, activo) vs `n8n-runners-1` (muerto). Host: 2 procesos n8n nativos del usuario `opc` sin unit (huérfanos). Una sola instancia cubre todo.

---

## FASE 4 — OpenClaw (10 sandboxes + skills-workspaces)

- **Gateway activo:** `openclaw-gateway` (user systemd :5800, 10 sbx openclaw-sbx-* con red none, idle 27-40h, 0.5M RAM).
- **Config activa:** `~/.openclaw/openclaw.json` (sandbox mode:all).
- **Skills-workspaces (11 dirs):** `agent-telegram-orchestrator-76d93488` (3.5M, 268 archivos 30d, ACTIVO) + `workspace-978141e8` (3.7M, 299 archivos 30d, ACTIVO) + 9 workspaces (1.9M c/u, 186 c/u, patron masivo 4-Sep). Sin node_modules en sandboxes (24M total). Los 11 NO están registrados por id en config (derivados por sesión).
- **Pesados:** `~/.openclaw/npm` 4.5G + `agents/` 1.1G + `canvas/` 509M + `.worktrees/modernize` 658M (abandonado 15-May, 171M/658M) = 6.7G recuperables con cuarentena.
- **Legacy:** /srv/ai/openclaw-config (1 sandbox registrado Apr, 40+ .bak/.clobbered). Abandonado.

## FASE 5 — Actions Runner

- **kiri-vnic** (iaduartec/Web_Duartec, labels `self-hosted, Linux, ARM64`, online/idle). Última ejecución **hoy 01:26** (CI push failure + Auto-Fix scheduled diario 09-05 success).
- `_work` 2.3G + `_tool` 1.8G (CodeQL+node) + bin viejo 2.336.0 en disco. Solo 1 runner, sin duplicado.
- **Veredicto:** permanente JUSTIFICADO (uso diario + cache CodeQL). NO ephemeral. Limpiar bin viejo; consolidar mecanismo deploy.

## FASE 6 — Herramientas AI

Ver tabla arriba. **Evitar 8 herramientas solapadas:** codex+opencode+gemini+openclaw+1mcp+vscode-server son complementarias con evidencia de uso reciente. claude (05-31) y n8n nativo huérfano son candidatas a eliminar. antigravity no instalado.

## FASE 7 — Servicios host

Ver tablas arriba. Hallazgo clave: **api-stub, vite :4173, trading demo, CNMV cron, weekly-mail legacy, web-duartec 5min timer duplicado, postfix roto, firewalld+ufw doble, podman sin uso** son los candidatos.

---

## FASE 8 — Diseño Objetivo

### Tabla propuesta

| Componente actual | Función | Problema | Propuesta | Riesgo |
|---|---|---|---|---|
| Stack `n8n` legacy (5 contenedores: n8n-n8n-1, runners-1, sandbox-api, sandbox-runner dind, searxng) | Duplica n8n canónico | 0 wf desde 08-25, dangling 1.48G, dind 894M, runners sin tareas, sandbox inalcanzable | **Retirar stack completo**; limpiar envs muertas de n8n-unified (SANDBOX_API_URL, SEARXNG) si no hay nodos AI sandbox activos | Bajo (cuarentena volúmenes). Verificar: no hay workflows en unified que usen Code Sandbox / AI sandbox con éxito en últimos 30d |
| `n8n-unified:latest` | Orquestación | Drift sin pin | **Fijar tag** (ej. 1.114.x) + update via n8n-update.timer | Bajo |
| `n8n` nativo ×2 (usuario opc) | Duplica docker | Procesos huérfanos sin unit | **Matar procesos + purgar binario host** (`which -a n8n` → /usr/local/bin/n8n) | Bajo |
| `duartec-local-whisper` | STT local | 0 POST desde 08-27 (transcripción por OpenAI) | **G→ preguntar:** retirar con cuarentena o conservar como capacidad local | Medio si hay flujos offline no detectados |
| `duartec-email-store` | Store emails | Crash-loop RC 2603 (ImapFlow ETIMEOUT sin handler) | **Fix primero** (handler + backoff), luego evaluar consolidación con mail-relay | Medio (bloquea validación si no se fixa) |
| `duartec-parts-mail-relay` | Relay IMAP/SMTP | Sin evidencia de uso | **G→ preguntar** | Medio |
| `web-duartec` triple deploy (timer 5min + Actions runner + Vercel) | Deploy | Dos mecanismos locales duplicados + rama prod ≠ main | **Unificar a 1:** mantener Actions (ya corre daily), **eliminar timer 5min**, alinear checkout /srv/apps/web-duartec a `main` | Bajo si CI verde |
| `/srv/apps/portfolio` dirty (3 archivos) → deploy bloqueado | Deploy | `git merge --ff-only` rechazado | **Resolver dirty** (stash/cuarentena + reset) antes de cualquier retiro | Bajo |
| `postfix` enabled sin main.cf | MTA | Fatal cada minuto (ruido journalctl, rompe sendmail del cron 1/min) | **Deshabilitar o proveer main.cf mínimo** | Bajo |
| `firewalld` + `ufw` | Firewall | Doble firewall | **Quedarse con uno** (ufw en Ubuntu) | Medio (validar reglas antes) |
| `podman` + timer (0 containers) | Runtime alt. | Sin uso | **Deshabilitar podman.{service,socket} + timer** | Bajo |
| `open-vm-tools`/`vgauth` | Guest VMware | Oracle ARM no es VMware | **Deshabilitar** | Bajo |
| `rsync.service` enabled-inactive | — | Sin uso | **Deshabilitar** | Bajo |
| Units legacy disabled (ollama, n8n, openclaw, openclaw-agents) + 13 user units legacy | — | Archivos huérfanos | **Borrar unit files** | Bajo |
| `vite preview :4173` (sin unit, 0.0.0.0, manual 08-23) | Preview | Huérfano expuesto | **Matar proceso** | Bajo |
| `api-stub.service` :8080 | Mock API | Sin consumidor detectable | **G→ confirmar consumidor** antes de tocar | Medio |
| Trading demo (`freqtrade`/`streamlit` + CNMV cron) | Demo OKX | 13 días, sin evidencia prod | **G→ preguntar** | Bajo |
| `portfolio-mtm.timer` (dry-run) + `api_watchdog.sh` (1/min) + `weekly-mail-maintenance` | Timers/cron | No-op / ruido / legacy | **G/D→ preguntar y limpiar legacy** | Bajo |
| Caddy ~25 `.bak` + rutas muertas (8082×2, MCP 5680, OPENCLAW 18889) + 4 backups .env/compose + 3 sqlite backups | Junk | Ruido y confusión | **Limpiar .bak/junk; corregir rutas muertas** en Caddyfile + tailscale-serve | Bajo |
| `~/.openclaw`: 7G (npm 4.5G, agents 1.1G, canvas 509M, worktree modernize 658M) | Runtime | Bloat + 16k dirty | **Cuarentena:** borrar `worktrees/modernize`, dedup `npm/`, auditar `canvas/agents` | Bajo con cuarentena |
| HOME superrepo (125 tracked, 10 gitlinks sin .gitmodules) | — | Riesgo limpiezas | **NO TOCAR** ahora; documentar y proponer .gitmodules/worktree plan aparte | — |
| `ocmonitor-share` (288M, sin remote) | Proyecto activo | Riesgo pérdida | **Crear remote / backup** | Bajo |
| Worktrees gone/dirty (`nuevo-prototype-review-remote` 10 dirty, etc.) | — | Confusión | **Limpiar selectivos** tras confirmar | Bajo |
| Caddy host vs docker-caddy | Proxy edge vs interno | Capas (tailscaled→docker caddy→upstream) | **NO consolidar** (FASE 9: ciclos distintos, evitar SPOF) | — |

### Stack ACTUAL vs PROPUESTO

| Dimensión | ACTUAL | PROPUESTO | Δ |
|---|---|---|---|
| Contenedores | 29 (10 openclaw-sbx + 10 duartec-voice-ai + 4 insforge + 5 n8n legacy) | **24** (retira 5 legacy) | **-5** |
| Si también whisper+mail-relay confirmados sin uso | 29 | 22 | -7 |
| Bases | 2 (MariaDB + Postgres) | 2 (no se tocan) | 0 |
| Proxies | 2 (host edge + docker interno) | 2 (roles distintos) | 0 (limpia rutas) |
| Runners n8n | 2 + 2 nativos huérfanos | 1 | -3 |
| Mecanismos deploy web-duartec | 3 (timer+CI+Vercel) | 1 (CI) | -2 |
| Timer 5min + timers legacy | 6+ | 2–3 | -3/4 |
| Units legacy host | ~17 archivos huérfanos | 0 | -17 |
| Imágenes dangling/huérfanas | 1 dangling en uso | 0 | -1 (+ ~2.6GB) |

### Estimaciones (con evidencia, no promesas)

| Recurso | Inmediato (seguro) | Con cuarentena home | RAM liberada |
|---|---|---|---|
| Disco Docker | **~2.6GB** imágenes + **894M** vol dind = **~3.5GB** (verificado `docker system df` + `docker volume ls`) | + junk Caddy/sqlite/env backups <100M | — |
| Disco home | — | `worktrees/modernize` 658M + `npm` dedup ~2–3G + `canvas` 509M + `.vscode-server` viejas ~1G + `.cache` 2.3G + `~/.gemini` 1.1G parcial + worktree duplicado 181M = **~8–13G** | — |
| RAM | **~450–500M** (n8n-n8n-1 241M + dind 144M + runners-1 + searxng) | + whisper ~46M + mail-relay si se retiran | **~600M** pico si email-store deja de reiniciar `npm ci` cada 5min |
| Mantenimiento | -5 contenedores, -2 procesos nativos, -3 timers, -17 units | - triple deploy y doble firewall | Validación más simple |

---

## FASE 9 — Reglas de consolidación aplicadas

- No se mezcla MariaDB con Postgres (consumidores y ciclos distintos).
- No se consolida Caddy host con docker-caddy (edge público TLS vs proxy interno con gating; juntarlos crearía SPOF).
- Cada retiro exige rollback: cuarentena de volúmenes/imágenes, backup de compose/Caddyfile/units, y validación funcional (FASE 12) antes de `docker rmi`/`rm`.

## FASE 10 — Backup / rollback (a ejecutar ANTES de cada cambio)

- `~/duartec-infra/compose.yml` + `.env` (copia con fecha) + `docker inspect` de los 5 legacy + `docker volume ls` + `ss -lntup` + `systemctl list-units` + `git status` de repos afectados.
- Cuarentena: volúmenes legacy → tar en `~/infra-audit/cuarentena/<fecha>/` con expiración 14 días (no duplicar DBs vivas).
- Comando rollback documentado por cada retiro (ej.: `docker compose -p n8n up -d` desde backup).

## FASE 11 — Orden de ejecución propuesto (una consolidación a la vez, validando entre pasos)

1. **Fix email-store** (bloqueante para validación limpia) → valida.
2. **Junk seguro:** Caddy .bak, env/compose backups, sqlite backups legacy → valida.
3. **Units/timers muertos:** postfix/firewalld/podman/vm-tools/rsync + 13 user units → valida.
4. **Procesos huérfanos:** vite :4173 + n8n nativos (opc) + pin n8n-unified tag → valida.
5. **Deploy web-duartec:** eliminar timer 5min + alinear rama a main + resolver dirty portfolio → valida CI.
6. **Stack n8n legacy (5 contenedores) + envs muertas + red n8n_default** → valida n8n-unified.
7. **Decisiones G (solo si confirmás):** whisper, mail-relay, api-stub, trading/CNMV.

## FASE 12 — Validación funcional (después de CADA paso)

Checks reales (no solo `Up`): `docker ps` + `systemctl --failed` + `ss -lntup` + `journalctl -p err -S -1h` + HTTP: n8n-unified (workflows list), portfolio :3001, web-duartec :3000, Caddy 80/443, Tailscale handlers, Insforge 7130/7131, Postgres, MariaDB, PostgREST 3002, Deno 7133, Ollama `ollama list` + inferencia qwen3:1.7b, Actions Runner `systemctl status`.

## FASE 13 — Limpieza post-consolidación

Solo tras validar: `docker rmi` de imágenes legacy, `docker volume rm` cuarentenados tras 14 días, `rm` de configs/units huérfanas, `apt autoremove` de paquetes sin consumidor si aplica.

---

## Pendientes — G (incierto, NO tocar sin evidencia)

1. `api-stub.service` :8080 — ¿tiene consumidor?
2. `duartec-local-whisper` — ¿se necesita STT offline?
3. `duartec-parts-mail-relay` — ¿algún flujo lo usa?
4. Trading demo + CNMV `daily_ingest.sh` — ¿proyecto vigente?
5. `portfolio-mtm.timer` (dry-run) + `api_watchdog.sh` (1/min) — ¿propósito real?
6. `duartec-static-sites` :19180 ruta frágil — ¿consumidor?

---

*Auditoría FASE 1–8 completa. Ningún cambio ejecutado. Próximo paso requiere aprobación explícita.*
