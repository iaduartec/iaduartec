# Auditoría de Repos + OpenClaw (MODO SOLO LECTURA)

Servidor: Oracle Cloud ARM64, Ubuntu 24.04 · Fecha auditoría: 2026-09-06
Alcance: `/home/ubuntu`, `/srv`, `/opt`. Lectura única; no se modificó nada (solo se creó este reporte).
Nota: Docker/contenedores NO auditados aquí (otro agente). Se registra la evidencia en disco del despliegue.

---

## 1. Inventario de repos git

Método: `find /home/ubuntu /srv /opt -maxdepth 4 -name .git (d+f)` + pasada profunda en `.openclaw`, `/srv/ai`, `/srv/apps`. `/opt` sin repos (solo containerd + unified-monitoring-agent).
Repos de herramientas excluidos del análisis de negocio: `.nvm`, `.gemini/extensions/{superpowers,code-review}`, `.codex/{vendor_imports/skills,memories}`, `.warp/themes` (todos limpios y actualizados, uso de tooling).

| Ruta                                                       | Tamaño (total / sin node_modules) | Últ. commit | Dirty                                                               | Rama                                      | Remote                                   | Clasificación                                                  |
| ---------------------------------------------------------- | --------------------------------- | ----------- | ------------------------------------------------------------------- | ----------------------------------------- | ---------------------------------------- | -------------------------------------------------------------- |
| /home/ubuntu/portfolio-repo                                | 2.8G / 2.2G                       | 2026-09-06  | 1 (`?? ai/`)                                                        | codex/instruction-safety-cleanup-20260906 | github.com/iaduartec/portfolio           | DESARROLLO                                                     |
| /srv/apps/portfolio                                        | 2.7G / 2.1G                       | 2026-09-06  | 3 (SKILL.md ×2, AGENTS.md)                                          | main                                      | github.com/iaduartec/portfolio (mismo)   | PRODUCCIÓN (deploy target)                                     |
| /srv/apps/web-duartec                                      | 4.0G / 3.0G                       | 2026-09-06  | 3 (scripts/auto-update.sh, dev-server.sh, tests e2e — sin trackear) | codex/instruction-safety-cleanup-20260906 | github.com/iaduartec/Web_Duartec         | PRODUCCIÓN (deploy target)                                     |
| /home/ubuntu/mission-bridge                                | 129M                              | 2026-09-06  | 1 (`?? analysis_output.json`)                                       | codex/instruction-safety-cleanup-20260906 | github.com/iaduartec/Mission-Bridge.git  | DESARROLLO + servicio systemd activo                           |
| /home/ubuntu/duartec-infra                                 | 555M / 515M                       | 2026-09-05  | 0                                                                   | main (sync)                               | github.com/iaduartec/duartec-infra.git   | PRODUCCIÓN-INFRA                                               |
| /home/ubuntu/projects/trading                              | 1.6G                              | 2026-09-05  | 0                                                                   | main                                      | github.com/iaduartec/trading-bot.git     | DESARROLLO (Python/freqtrade)                                  |
| /home/ubuntu/apps/duartec-hub                              | 91M / 13M                         | 2026-09-05  | 0                                                                   | main (sync)                               | github.com/iaduartec/duartec-hub.git     | DESARROLLO (pkg `hub-v2`, vite, `build/`)                      |
| /home/ubuntu/apps/insforge                                 | 56K                               | 2026-09-06  | 4 (M mission-bridge, M portfolio-repo, ?? ai/plans, ?? dev-patches) | main                                      | github.com/iaduartec/iaduartec.git       | DESCONOCIDO (superrepo-espejo, ver §5)                         |
| /home/ubuntu/ocmonitor-share                               | 288M                              | 2026-09-03  | 0                                                                   | main                                      | SIN REMOTE                               | DESARROLLO (OpenCode Monitor, Python, Dockerfile)              |
| /home/ubuntu/sites/mission-alpha-connections               | 464K                              | 2026-09-05  | 0                                                                   | main (sync)                               | git.chatgpt-team.site/…appgprj_6a9287be… | DESARROLLO (tiene `dist/`)                                     |
| /home/ubuntu/snake-pentagon                                | 4.2M                              | 2026-07-31  | 0                                                                   | main (sync)                               | github.com/iaduartec/snake-pentagon.git  | DESARROLLO (juego, inactivo ~5 sem)                            |
| /home/ubuntu/docs/github-profile                           | 520K                              | 2026-03-08  | 0                                                                   | main                                      | SIN REMOTE                               | ABANDONADO-rel (perfil GitHub, 6 meses sin actividad)          |
| /home/ubuntu/.openclaw                                     | 7.0G / 2.1G                       | 2026-09-05  | **16.363**                                                          | master                                    | SIN REMOTE                               | PRODUCCIÓN-CONFIG (OpenClaw activo)                            |
| /home/ubuntu/.openclaw-rescue/workspace-oracle-rescue      | 5.4M                              | 2026-07-11  | 11 (AGENTS.md + ?? MEMORY/SOUL/…)                                   | master                                    | SIN REMOTE                               | DESARROLLO (workspace del agente telegram-orchestrator ACTIVO) |
| /srv/apps/restaurante                                      | 871M / 189M                       | 2026-05-30  | 1 (M AGENTS.md)                                                     | main **[ahead 1, behind 10]**             | github.com/iaduartec/restaurante         | PRODUCCIÓN-DESATUALIZADA (pkg `la-canada`, Astro, `dist/`)     |
| /srv/apps/espacio                                          | 345M / 99M                        | 2026-05-30  | 4                                                                   | main **[ahead 1, behind 13]**             | github.com/iaduartec/espaciox            | PRODUCCIÓN-DESATUALIZADA (pkg `espaciox`, Dockerfile)          |
| /srv/ai/openclaw-config/workspace{,-cheap,-analista-value} | 164–184K c/u                      | SIN COMMITS | 8–10 c/u                                                            | master (vacío)                            | —                                        | ABANDONADO (config OpenClaw antigua, Abr–May 2026)             |
| /home/ubuntu/.git (HOME)                                   | 125 tracked                       | —           | 1 (`? mission-bridge`)                                              | main (sync)                               | origin/main                              | ANÓMALO (ver §5)                                               |

---

## 2. Mapeo PROD vs DEV + mecanismos de despliegue

**portfolio (myinvestview)**

- FUENTE dev: `/home/ubuntu/portfolio-repo` (checkout en rama de trabajo, worktrees, agentes act. 6-Sep).
- PROD: `/srv/apps/portfolio`. Mecanismo: `.github/workflows/deploy-production.yml` (manual `workflow_dispatch`): verify→build→SSH (appleboy/ssh-action con secrets PROD_SSH_*) → `cd /srv/apps/portfolio && git merge --ff-only origin/main && SKIP_GIT_SYNC=1 bash ./scripts/deploy-production.sh`. El script existe en ambas rutas (idéntico, 3156B).
- Runtime: systemd `portfolio.service` (running) "Portfolio (Next.js production)"; también existe `portfolio-mtm.service`+`.timer` (con .rollback del 27-Ago).
- ⚠️ `/srv/apps/portfolio` tiene 3 ficheros tracked modificados → el workflow REFUSA el deploy (`git diff --quiet` falla). Deploy bloqueado hasta limpiar.

**web-duartec (duartec-web)**

- FUENTE dev: worktrees `.worktrees/nuevo-prototype-review{,-remote}` + ramas `sdd/*`. PROD: `/srv/apps/web-duartec`.
- Mecanismo triple: (1) systemd `web-duartec.service` (running) + `web-duartec-auto-update.service` → `scripts/auto-update.sh` (SIN trackear en git, timer cada 5 min: fetch+pull main+restart servicio, logs en /var/log/web-duartec); (2) GitHub Actions runner local `actions.runner.iaduartec-Web_Duartec.kiri-vnic.service` (running); (3) Vercel (`vercel-build` en package.json, workflows ci-code.yml + vercel-cleanup.yml).
- ⚠️ El checkout de prod está en rama `codex/instruction-safety-cleanup-20260906`, NO en `main` → el auto-update (que fuerza `main`) está desalineado con el estado del checkout.

**mission-bridge**

- Fuente única: `/home/ubuntu/mission-bridge` (Python, sin package.json). Runtime: systemd `mission-bridge.service` (running). Crontab: `scripts/sync-youtube-cookies.sh` cada 4h. Sin node_modules/Dockerfile: se ejecuta directo.

**duartec-infra**

- `/home/ubuntu/duartec-infra`: compose central (docker-compose.yml) con servicios: mariadb, email-store, whisper, media, n8n+n8n-runners, caddy, db-api, ollama, mail-relay (+volumes/redes). systemd: n8n-update.service, tailscale-serve.service. Caddyfile-host + backups. Contiene `dashboard/`, `data/`, `migrations/`, `n8n-docker/`.

**restaurante / espacio**

- `/srv/apps/restaurante` (Astro, `dist/`) y `/srv/apps/espacio` (Dockerfile) atrás de origin (behind 10/13, ahead 1). Fallback de espacio: `/srv/apps-espacio-fallback/app.py` (root-owned, 5-Sep) — servicio Python de respaldo.
- Servidos presumiblemente por caddy (estático/dist); sin workflows de deploy propios relevantes (ci-restaurante.yml, flow-compare/meta-guard en espacio).

**api-service / n8n (/srv/apps)**

- `/srv/apps/api-service`: server.js + compose + package.json (mar 7). `/srv/apps/n8n`: solo `.env` + `data/` (datos de n8n docker). No son repos git.

**Workflows CI por repo (resumen)**

- portfolio (×2 rutas): deploy-production.yml, ai-pr-review.yml, dependency-sweep(+retry).yml, dependabot-automerge.yml, security-audit.yml.
- web-duartec: actionlint, ai-pr-review, auto-fix, ci-code, ci-web-duartec, codeql, dependabot-auto-merge, maintenance-server, security-audit, vercel-cleanup.
- duartec-infra / duartec-hub: solo dependabot-automerge.yml. trading: sin workflows. espacio: flow-compare, meta-guard. restaurante: ci-restaurante.yml.

**Crontab (ubuntu)**

- `0 9 * * 0` weekly-mail-maintenance (→ /srv/automation) · `15 7 * * *` CNMV PDMR ingest · `* * * * *` /home/ubuntu/scripts/api_watchdog.sh · `0 */4 * * *` mission-bridge sync-youtube-cookies.

---

## 3. Duplicados detectados

| Par                                                                                                            | Evidencia                                                                                                                                                                                 | Fuente vs copia                                                                                                                                                                          |
| -------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/home/ubuntu/portfolio-repo` ↔ `/srv/apps/portfolio`                                                          | Mismo remote (iaduartec/portfolio), mismo `package.json` name (`myinvestview`), dependencias package.json IDÉNTICAS, mismo deploy-production.sh                                           | FUENTE dev: `~/portfolio-repo` (rama de trabajo + worktrees). COPIA/DEPLOY: `/srv/apps/portfolio` (target del workflow SSH, ff-only main). El "source of truth" de prod es GitHub `main` |
| `~/portfolio-repo/.worktrees/virtual-tier-portfolio` ↔ `/srv/apps/portfolio/.worktrees/virtual-tier-portfolio` | Mismo HEAD `e2f9ae5` (11-Jul), 181M c/u, dirty 0                                                                                                                                          | Copia exacta duplicada en ambas rutas; 362M recuperables en total                                                                                                                        |
| `~/.openclaw` ↔ `/srv/ai/openclaw-config`                                                                      | Misma app (OpenClaw): ambos tienen openclaw.json, workspace, agents, sandbox…                                                                                                             | ACTIVA: `~/.openclaw` (modificada 5-Sep, config 16KB). LEGACY/ABANDONADA: `/srv/ai/openclaw-config` (sin cambios desde 13-May, +30 backups .bak/.clobbered)                              |
| `agent-telegram-orchestrator-76d93488` (×3)                                                                    | En `~/.openclaw/sandbox/skills-workspaces/` (3.5M, activo), en `/srv/ai/openclaw-config/sandboxes/` (36K, legacy) y registrado en `/srv/ai/openclaw-config/sandbox/containers.json` (Abr) | Fuente: la de `~/.openclaw` (activa). Las 2 legacy = ABANDONADAS                                                                                                                         |
| `workspace-telegram-orchestrator` legacy                                                                       | `/srv/ai/openclaw-config/workspace-telegram-orchestrator` (44K, Abr)                                                                                                                      | Sombra del workspace actual del mismo agente (`~/.openclaw-rescue/workspace-oracle-rescue`)                                                                                              |
| `~/apps/insforge` (superrepo) contiene `mission-bridge/` y `portfolio-repo/` como contenido                    | Carpetas tracked planas (no gitlinks, sin .gitmodules), 56K                                                                                                                               | Espejo-índice del mismo contenido; NO fuente                                                                                                                                             |
| `~/.openclaw/npm/projects/openclaw-*`                                                                          | 4.5G de installs npm de plugins con variantes `__openclaw-generation__g-*` duplicadas por instalación                                                                                     | Cache/installs de plugins, candidatos a limpieza (evidencia, no acción)                                                                                                                  |

---

## 4. OpenClaw: sandboxes y config

### Config principal ACTIVA: `/home/ubuntu/.openclaw/openclaw.json` (16KB, 5-Sep 19:59, +openclaw.json.last-good idéntico)

- `.agents.entries`: solo `telegram-orchestrator` → workspace `/home/ubuntu/.openclaw-rescue/workspace-oracle-rescue`, modelo primario `ollama/qwen2.5:0.5b` con fallbacks gemini.
- `.agents.defaults`: workspace `/home/ubuntu/.openclaw/workspace` (EXISTE en disco, act. 4-Sep), sandbox `{mode:"all", scope:"agent", workspaceAccess:"rw"}`.
- Servicios systemd: `openclaw.service`, `openclaw-agents.service` (+ `openclaw-gateway.service.d`), y dir legacy `gateway.systemd.env`.
- `/srv/ai/openclaw-gateway/config.yml`: gateway `gateway-oci-burgos`, mqtt:1883, api_key = PLACEHOLDER (no es secreto real).

### Sandboxes en disco: `~/.openclaw/sandbox/skills-workspaces/` — 11 (se esperaban ~10 ✓)

Todos: contienen solo `.openclaw/` (sandbox-skills, memory…), SIN git propio (el `dirty:16363` que heredan es del repo `~/.openclaw` padre), sin node_modules.

| id                                   | Tamaño  | Archivos mod. 30d (todo profundidad) | Últ. uso                   | Clasificación             |
| ------------------------------------ | ------- | ------------------------------------ | -------------------------- | ------------------------- |
| agent-telegram-orchestrator-76d93488 | 3.5M    | 268                                  | 2026-08-23 (nuevo archivo) | ACTIVO (agente en config) |
| workspace-978141e8…                  | 3.7M    | 299                                  | 2026-09-04                 | ACTIVO                    |
| workspace-461a0689…                  | 1.9M    | 186                                  | 2026-09-04                 | ACTIVO                    |
| workspace-51c1d045…                  | 1.9M    | 186                                  | 2026-09-04                 | ACTIVO                    |
| workspace-6e57dcec…                  | 1.9M    | 186                                  | 2026-09-04                 | ACTIVO                    |
| workspace-6fae6e1f…                  | 1.9M    | 186                                  | 2026-09-04                 | ACTIVO                    |
| workspace-76e25507…                  | 1.9M    | 186                                  | 2026-09-04                 | ACTIVO                    |
| workspace-920d7871…                  | 1.9M    | 186                                  | 2026-09-04                 | ACTIVO                    |
| workspace-9fffcb1e…                  | 1.9M    | 186                                  | 2026-09-04                 | ACTIVO                    |
| workspace-e7abd7d8…                  | 1.9M    | 186                                  | 2026-09-04                 | ACTIVO                    |
| workspace-ff1b0ebb…                  | 1.9M    | 186                                  | 2026-09-04                 | ACTIVO                    |
| **Total sandbox dir**                | **24M** |                                      |                            |                           |

Nota: el patrón de fechas (todo el bloque tocado el 4-Sep, y el telegram el 23-Ago) sugiere un barrido/mantenimiento de skills masivo, no 11 proyectos distintos. Ningún sandbox registra actividad de proyecto npm (sin package.json).

### Config LEGACY: `/srv/ai/openclaw-config/openclaw.json` (21KB, 13-May) + sandboxes/containers.json (Abr)

- Legacy registra 1 sandbox docker: `openclaw-sbx-agent-telegram-orchestrator-76d93488` (image `openclaw-sandbox:bookworm-slim`; created 24-Abr, last used 24-Abr).
- MISMATCH config vs disco: la config ACTIVA no lista ningún id de skills-workspace (se generan por sesión); la LEGACY referencia sandboxes que solo existen en su árbol (ya muertos). El dir legacy `sandbox/` y `sandboxes/` no son referenciados por la config activa.

### Otros restos OpenClaw

| Ruta                                                   | Tamaño             | Últ. uso                                                                                                                            | Clasificación                 |
| ------------------------------------------------------ | ------------------ | ----------------------------------------------------------------------------------------------------------------------------------- | ----------------------------- |
| ~/.openclaw/npm                                        | **4.5G**           | installs de plugins (groq, tokenjuice, diffs, codex, acpx, deepseek, diagnostics-prometheus, memory-lancedb) + variantes generation | Cache pesado, limpiable       |
| ~/.openclaw/agents                                     | 1.1G               | agent main + telegram-orchestrator                                                                                                  | ACTIVO                        |
| ~/.openclaw/.worktrees/modernize                       | 171M / 658M con nm | commit 15-May, rama modernize-infrastructure                                                                                        | ABANDONADO (>60d, dirty 0)    |
| ~/.openclaw/canvas                                     | 509M               | —                                                                                                                                   | Revisar                       |
| ~/.openclaw/piper                                      | 61M                | TTS                                                                                                                                 | Revisar                       |
| /srv/ai/openclaw-lite                                  | ~80K               | Feb 2026                                                                                                                            | ABANDONADO (experimento lite) |
| /srv/ai/openclaw-gateway                               | 249B               | Feb 2026                                                                                                                            | OBSOLETO (placeholder)        |
| /home/ubuntu/openclaw-backups/codex-migration-*.tar.gz | 3.4MB              | 11-Jul                                                                                                                              | BACKUP puntual                |
| ~/.openclaw-rescue/workspace-oracle-rescue             | 5.4M               | 11-Jul (config lo referencia)                                                                                                       | ACTIVO-por-config             |

---

## 5. Anomalías

1. **HOME como superrepo** (`/home/ubuntu/.git`, branch main, remote origin/main): 125 ficheros tracked mezclando dotfiles (.bashrc, .mcp.json, README.md) con restos de un proyecto Next.js (`app/page.tsx`, `components/`) y **10 gitlinks SIN .gitmodules** (duartec-hub, docs/github-profile, duartec-infra, mission-bridge, ocmonitor-share, portfolio-repo, projects, sites/mission-alpha-connections, worktrees/hub-v2-v5, worktrees/mission-alpha-v3-hub). Status muestra `? mission-bridge` (gitlink roto/externalizado). Peligro: cualquier `git clean/pull` en HOME podría tocar subárbol de repos reales.
2. **`~/apps/insforge` superrepo-espejo**: trackea `mission-bridge/` y `portfolio-repo/` como contenido plano duplicado (sin .gitmodules), status muestra ambos como modificados siempre.
3. **Deploy de portfolio bloqueado**: `/srv/apps/portfolio` tiene 3 ficheros tracked modificados → el workflow `deploy-production.yml` aborta por diseño ("Refusing deploy: tracked checkout has local changes").
4. **web-duartec prod desalineado**: checkout en rama `codex/instruction-safety-cleanup-20260906` mientras `auto-update.sh` (timer 5 min) fuerza `main`; los scripts `auto-update.sh`/`dev-server.sh` del deploy están SIN trackear en git (se perderían con un clone limpio).
5. **Rama multi-repo en curso**: `codex/instruction-safety-cleanup-20260906` está activa simultáneamente en portfolio-repo, mission-bridge y /srv/apps/web-duartec (campaña de agente, no duplicado de contenido).
6. **restaurante y espacio divergidos**: ahead 1 / behind 10 y 13 respectivamente; con ficheros tracked modificados (AGENTS.md). Copias de prod antiguas.
7. **Worktrees con rama upstream [gone]**: `snake-pentagon/.worktrees/neon-game` (codex/neon-snake-game, 11-Ago) y `web-duartec/.worktrees/nuevo-prototype-review-remote` (10 dirty files, 3-Sep). El worktree `-remote` con 10 cambios sin commit es el único worktree sucio.
8. **`~/.openclaw` es un repo git sobre runtime**: master sin remote, 16.363 ficheros dirty, 7GB (4.5G solo npm-cache). El repo git no sirve como fuente; es ruido de versionado sobre datos vivos.
9. **Repos de negocio SIN remote**: `ocmonitor-share` (288M, activo 3-Sep — riesgo de pérdida), `docs/github-profile`, workspaces openclaw legacy.
10. **`.openclaw/.worktrees/modernize`** (171M): sin actividad desde 15-May → candidato ABANDONADO.
11. `/srv/apps-espacio-fallback/app.py` (52K, root, 5-Sep): código de servicio fuera de control de versiones.
12. `missionAlphaLab/` (22M, sin .git, 29-Ago) y `quarantine/` (3.9M): dirs sueltos sin repo — clasificar con owner antes de tocar.

## 6. Clasificación preliminar consolidada

- **PRODUCCIÓN**: /srv/apps/portfolio (⚠️ dirty bloquea deploy), /srv/apps/web-duartec (⚠️ rama≠main), /home/ubuntu/duartec-infra, /home/ubuntu/mission-bridge (servicio activo), /srv/apps/restaurante + espacio (servidas, desactualizadas), ~/.openclaw (config+runtime).
- **DESARROLLO**: ~/portfolio-repo, ~/projects/trading, ~/apps/duartec-hub, ~/ocmonitor-share, ~/sites/mission-alpha-connections, ~/snake-pentagon, ~/.openclaw-rescue/workspace-oracle-rescue, worktrees activos (hub-v2-v5, mission-alpha-v3-hub, nuevo-prototype-review).
- **BACKUP/COPIA**: /srv/apps/portfolio (copia deploy de portfolio), insforge (espejo), virtual-tier-portfolio ×2, /srv/ai/openclaw-config (config antigua + 40+ backups json).
- **ABANDONADO**: /srv/ai/openclaw-config/workspace* (sin commits, Abr), /srv/ai/openclaw-lite (Feb), /srv/ai/openclaw-gateway (Feb), ~/.openclaw/.worktrees/modernize (15-May), ~/docs/github-profile (Mar, sin remote), openclaw-backups/*.tar.gz (puntual).
- **DESCONOCIDO**: ~/apps/insforge (rol del superrepo), missionAlphaLab/, quarantine/, /home/ubuntu/.git (superrepo HOME).
- **HERRAMIENTAS (no tocar)**: .nvm, .gemini/extensions/_, .codex/_, .warp/themes.

## 7. Recomendaciones (sin ejecutar — solo lectura)

1. Resolver dirty en /srv/apps/portfolio y volver a `main` para desbloquear el deploy (o actualizar el workflow).
2. Alinear /srv/apps/web-duartec con `main` (el timer de auto-update lo exige) y versionar auto-update.sh/dev-server.sh en el repo.
3. Decidir destino de los pares duplicados portfolio (conservar ~/portfolio-repo como dev, /srv/apps/portfolio como deploy; borrar worktree virtual-tier duplicado → −181M).
4. Limpieza OpenClaw con evidencia: ~/.openclaw/.worktrees/modernize (−171M−658M nm), ~/.openclaw/npm variants (−hasta 4.5G), /srv/ai/openclaw-config legacy (−89M con backups), openclaw-lite/gateway (Kb).
5. Dar remote (push a GitHub) a ocmonitor-share antes de cualquier limpieza.
6. Aclarar/convertir el superrepo HOME (gitlinks sin .gitmodules) — alto riesgo de colisión con los repos reales.
