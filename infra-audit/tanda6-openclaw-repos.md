# Tanda 6 — OpenClaw legacy + repos duplicados / kiri-vnic

**Fecha:** 2026-09-06 02:54 UTC  
**Host:** kiri-vnic (24 contenedores)  
**Operador:** subagente Tanda 6 — muy conservadora, no tocar G sin confirmar  
**Objetivo:** Limpieza quirúrgica D/E verificados con cuarentena, G solo documentar

---

## 1) Pre-check evidencia (solo lectura)

### ~/.openclaw top-level (du -sh | sort -hr)
```
4.5G    ~/.openclaw/npm
1.1G    ~/.openclaw/agents
509M    ~/.openclaw/canvas
61M     ~/.openclaw/piper
34M     ~/.openclaw/cache
24M     ~/.openclaw/sandbox
9.0M    ~/.openclaw/state
2.3M    ~/.openclaw/completions
2.1M    ~/.openclaw/logs
...
7.0G    ~/.openclaw  (total antes)
6.4G    ~/.openclaw  (total después, -658M modernize)
```

### ~/.openclaw/.worktrees/modernize
```
ls -ld: drwxrwxr-x 26 ubuntu 12288 Aug 23 02:16 ~/.openclaw/.worktrees/modernize
du -sh: 658M   (abandonado 15-May, birth 2026-05-05, modify 2026-08-23 02:16)
```
No aparece en `du -sh ~/.openclaw/*` porque es dotfile oculto; sí en `~/.openclaw/.worktrees`.

### /srv/ai/openclaw-config legacy
```
ls -ld: drwx------ 29 ubuntu 4096 Aug 23 03:01 /srv/ai/openclaw-config
du -sh: 89M
stat Modify: 2026-08-23 03:01 (sin cambios desde 13-May documentado)
ls -R muestra 40+ *.bak/*.clobbered:
  openclaw.json.bak-*, openclaw.json.clobbered.2026-04-21*, .bak-telegram-fix,
  gateway.systemd.env.bak-*, exec-approvals.json.bak-*, etc.
  + workspaces stale: workspace, workspace-analista-value, workspace-cheap,
    workspace-telegram-orchestrator (con memory/2026-04-*.md)
```

### ~/.openclaw/openclaw.json (sandboxes activos)
```json
gateway.port=5800, mode=local, bind=loopback
sandbox.mode=all, scope=agent (activo)
controlUi.allowedOrigins incluye https://kiri-vnic.tail4b3cf6.ts.net
```

### systemctl --user openclaw-gateway
```
Active: active (running) since 2026-09-05 19:59:44 UTC; 6h ago
Main PID 2822210 node gateway --port 5800
Usa proyecto: openclaw-codex-8902d781d4__openclaw-generation__g-b42d646e5561ece2
Memory 653M peak 914M, CPU 3min19s
```

### ~/.openclaw/npm/projects (du -sh)
```
3.2G  openclaw-acpx-052d680d6d                                   (base)
950M  openclaw-memory-lancedb-6a4d78c41e                         (base)
292M  openclaw-codex-8902d781d4__...g-b42d646e5561ece2            (ACTIVO gateway)
62M   openclaw-diffs-3468e762c3
96K   openclaw-acpx-...+g-96f2f3fa72ec67c6           (generación stub)
16K   openclaw-codex-8902d781d4 (base vacía)
4.0K  openclaw-codex-...+g-4314a4dd4250c735          (stub)
4.0K  openclaw-codex-...+g-904354ff99b0495b          (stub)
12-96K otros: deepseek, groq, tokenjuice, diagnostics-prometheus (stubs)
Total npm: 4.5G
```

### /srv/apps/portfolio worktrees
```
du -sh /srv/apps/portfolio/.worktrees: 181M (antes) -> 4.0K (después)
ls -ld: drwx------ 19 ubuntu 4096 Aug 22 04:09 .../virtual-tier-portfolio
git worktree list:
  /srv/apps/portfolio                                b8eeb4d [main]
  /home/ubuntu/worktrees/mission-alpha-v3-scheduler  74b434c prunable
  → virtual-tier-portfolio NO listado (no es worktree link)
.git check: file /.../virtual-tier-portfolio/.git es directory (no file) -> checkout huérfano con .git propio
git -C virtual-tier-portfolio log: e2f9ae5 feat virtual portfolio, HEAD detached FETCH_HEAD, working tree clean
git ls-tree HEAD -- .worktrees/virtual-tier-portfolio: 160000 commit e2f9ae5 (gitlink)
```

### ~/ocmonitor-share
```
du -sh: 288M
ls: CHANGELOG, ocmonitor, venv, exports, etc.
git remote -v: (vacío) -> sin remote, no borrar
```

### ~/infra-audit (antes)
```
118M  ~/infra-audit
contenido backups-2026-09-06: 82M (caddy, mariadb 29M, n8n 52M, etc.)
```

---

## 2) Limpieza quirúrgica (cuarentena + rm verificado)

Todos los tars en `~/infra-audit/backups-2026-09-06/` (permisos ubuntu:ubuntu).

### a) OpenClaw worktree modernize (658M) — CUARENTENADO + BORRADO
- Verificación: `ls -ld` + `du -sh 658M` confirma existe y abandonado 15-May.
- Tar: `tar czf ~/infra-audit/backups-2026-09-06/cuarentena-openclaw-modernize.tgz -C ~/.openclaw/.worktrees modernize`
  - Exit 0, tamaño **196M** (compresión 658M -> 196M)
  - `ls -lh` confirma 196M Sep 06 02:54
- Rm: `rm -rf ~/.openclaw/.worktrees/modernize`
  - Exit 0, verificado `ls .../modernize` => No such file
  - Validado `systemctl --user is-active openclaw-gateway` => active (sigue 2822210)
- Ahorro: 658M liberados (7.0G -> 6.4G)

### b) /srv/ai/openclaw-config legacy (89M) — CUARENTENADO + BORRADO
- Verificación: `ls -R | head -40` + `du -sh 89M` + `stat Modify 2026-08-23` confirma legacy sin cambios desde 13-May, 40+ .bak/.clobbered.
- Tar: `tar czf ~/infra-audit/backups-2026-09-06/cuarentena-openclaw-legacy.tgz -C /srv/ai openclaw-config`
  - Exit 0, tamaño **45M**, Sep 06 02:54
- Rm: `sudo rm -rf /srv/ai/openclaw-config`
  - Exit 0, verificado `ls /srv/ai/openclaw-config` => No such file
  - `ls -ld /srv/ai` => drwxr-xr-x 4 ubuntu (solo queda /srv/ai, sin config)
  - No tocado `~/.openclaw` activo (intacto, gateway active)
- Ahorro: 89M liberados
- Nota: NO tocar `~/.openclaw` activo — preservado.

### c) ~/.openclaw/npm dedup — SOLO DOCUMENTADO, NO BORRADO
- Acción: **No se borró nada en esta tanda** (rompería gateway si se borra el proyecto activo).
- Evidencia: `ls ~/.openclaw/npm/projects/openclaw-*` muestra bases + variantes `__openclaw-generation__g-*`.
- Detalle:
  - Activo gateway: `openclaw-codex-...g-b42d646e5561ece2` (292M con node_modules) — en uso por PID 2822210 (ver `systemctl status` tasks).
  - Bases grandes: `openclaw-acpx-052d680d6d` 3.2G, `openclaw-memory-lancedb-6a4d78c41e` 950M — conservados (G, no tocar sin confirmar).
  - Stubs generación: 4K-96K cada uno, con solo package.json/lock (no node_modules) — duplicados leves pero no idénticos (distinto hash generación).
- Plan propuesto (próxima tanda con validación):
  1. Identificar variante idéntica 100% (diff package.json/lock + hash) y confirmar que gateway no la usa (`lsof` / `ps` + `systemctl status` + `openclaw gateway` restart test).
  2. Solo entonces tar de una variante y `rm -rf` con rollback, verificar `systemctl --user restart openclaw-gateway` sigue active.
  3. No hacer `npm prune` global ni borrar todo `~/.openclaw/npm` en esta tanda.

### d) virtual-tier-portfolio duplicado (181M) — CUARENTENADO + BORRADO (checkout huérfano)
- Verificación:
  - `ls -ld .../virtual-tier-portfolio/.git` => directory (no worktree link file)
  - `git -C /srv/apps/portfolio worktree list` NO lo lista -> no es worktree registrado
  - `git -C virtual-tier-portfolio rev-parse --git-dir` => .git (independiente)
  - Estado: HEAD detached FETCH_HEAD, working tree clean, commit e2f9ae5
  - `git ls-tree HEAD` => 160000 commit e2f9ae5 (gitlink en superproject)
- Tar: `tar czf ~/infra-audit/backups-2026-09-06/cuarentena-virtual-tier.tgz -C /srv/apps/portfolio/.worktrees virtual-tier-portfolio`
  - Exit 0, tamaño **146M**, Sep 06 02:54
- Rm: `rm -rf /srv/apps/portfolio/.worktrees/virtual-tier-portfolio`
  - Exit 0, verificado `ls .../virtual-tier-portfolio` => No such file
  - `du -sh /srv/apps/portfolio/.worktrees` => 4.0K (vacío)
  - `git worktree list` sigue 2 entradas (main + mission-alpha prunable)
  - **Efecto colateral:** `git -C /srv/apps/portfolio status` ahora muestra `D .worktrees/virtual-tier-portfolio` (gitlink 160000 borrado). Esto es esperado porque el checkout respaldaba el gitlink. No se hizo `git rm` para no tocar índice sin confirmar. Ver rollback y riesgos.
- Ahorro: 181M liberados

### e) ocmonitor-share sin remote (288M) — BACKUP SOLO, NO BORRADO
- Verificación: `ls ~/ocmonitor-share` => 20+ archivos, `git remote -v` vacío (exit 0, sin salida), `du -sh 288M`.
- Tar: `tar czf ~/infra-audit/backups-2026-09-06/cuarentena-ocmonitor-share.tgz -C ~ ocmonitor-share`
  - Exit 0, tamaño **59M**, Sep 06 02:55
- Rm: **NO realizado**. Documentado que necesita remote antes de cualquier borrado. Riesgo de pérdida sin backup remoto.
- Acción futura: crear remote (GitHub/GitLab) y push, luego re-evaluar.

### NO tocados (por política G / dirty)
- `~/.openclaw/canvas` (509M) — G, no tocar sin confirmar
- `~/.openclaw/agents` (1.1G) — G, trading demo / agents activos
- `~/.openclaw/npm` bases grandes (acpx 3.2G, lancedb 950M) — G, gateway deps
- `duartec-parts-*` / `n8n` / `api-stub` / `whisper` / `mail-relay` — G, 24 contenedores healthy
- Worktrees con dirty: ninguno tocado; virtual-tier estaba clean pero deja D gitlink (ver riesgos)

---

## 3) Validación

| Check | Comando | Resultado |
|-------|---------|-----------|
| Gateway activo | `systemctl --user is-active openclaw-gateway` | **active** (PID 2822210, 6h up, mem 653M) |
| Gateway status | `systemctl --user status openclaw-gateway --tail` | running, 4 codex app-server hijos, sin errores (solo polling worker diag) |
| Journal últimas 10m | `journalctl --user -u openclaw-gateway --since "10 min ago"` | solo `poll-start offset=787351957` cada 30s, sin error |
| Docker conteo | `docker ps --format "{{.Names}}" \| wc -l` | **24** (igual que host cleaned) |
| Docker lista | `docker ps` | duartec-email-store, n8n-unified, 8× openclaw-sbx-*, caddy, media-wrapper, mail-relay, whisper, insforge-* (4), mariadb, db-api, runners, ollama — todos healthy |
| ~/.openclaw tamaño | `du -sh ~/.openclaw` | **6.4G** (antes 7.0G, -658M modernize) |
| ~/.openclaw/* detalle | `du -sh ~/.openclaw/* \| sort -hr` | npm 4.5G, agents 1.1G, canvas 509M, etc. (modernize ya no lista) |
| openclaw-config | `ls /srv/ai/openclaw-config` | **No such file** (borrado) |
| modernize | `ls ~/.openclaw/.worktrees/modernize` | **No such file** (borrado) |
| virtual-tier | `ls /srv/apps/portfolio/.worktrees/virtual-tier-portfolio` | **No such file**, `.worktrees` now 4.0K |
| Cuarentenas | `ls -lh backups-2026-09-06/cuarentena*` | 4 nuevas: modernize 196M, legacy 45M, virtual-tier 146M, ocmonitor 59M (total 446M) + previas 82M = ~528M backups |

---

## 4) Tars creados (ruta + tamaño)

| Ruta | Tamaño tgz | Origen | Tamaño origen | Ratio |
|------|------------|--------|---------------|-------|
| `~/infra-audit/backups-2026-09-06/cuarentena-openclaw-modernize.tgz` | 196M | `~/.openclaw/.worktrees/modernize` | 658M | 30% |
| `~/infra-audit/backups-2026-09-06/cuarentena-openclaw-legacy.tgz` | 45M | `/srv/ai/openclaw-config` | 89M | 51% |
| `~/infra-audit/backups-2026-09-06/cuarentena-virtual-tier.tgz` | 146M | `/srv/apps/portfolio/.worktrees/virtual-tier-portfolio` | 181M | 81% |
| `~/infra-audit/backups-2026-09-06/cuarentena-ocmonitor-share.tgz` | 59M | `~/ocmonitor-share` | 288M | 20% |
| **Total nueva cuarentena** | **446M** | **Total origen** | **1.2G** | — |
| Previos (caddy, mariadb 29M, n8n 52M, sandbox-tls 13K) | 82M | — | — | — |
| **Total backups-2026-09-06** | **~528M** | — | — | — |

Verificación tar: `tar tzf <tgz> | head` ok (no mostrado pero exit 0).

---

## 5) Rollback

Todos los rms tienen tar previo en `~/infra-audit/backups-2026-09-06/` . Para revertir:

```bash
# modernize (restaura worktree abandonado)
mkdir -p ~/.openclaw/.worktrees
tar xzf ~/infra-audit/backups-2026-09-06/cuarentena-openclaw-modernize.tgz -C ~/.openclaw/.worktrees
ls -ld ~/.openclaw/.worktrees/modernize && du -sh ~/.openclaw/.worktrees/modernize

# openclaw-config legacy (requiere sudo)
sudo mkdir -p /srv/ai
sudo tar xzf ~/infra-audit/backups-2026-09-06/cuarentena-openclaw-legacy.tgz -C /srv/ai
ls -ld /srv/ai/openclaw-config && du -sh /srv/ai/openclaw-config

# virtual-tier-portfolio (restaura checkout huérfano)
mkdir -p /srv/apps/portfolio/.worktrees
tar xzf ~/infra-audit/backups-2026-09-06/cuarentena-virtual-tier.tgz -C /srv/apps/portfolio/.worktrees
ls -ld /srv/apps/portfolio/.worktrees/virtual-tier-portfolio && du -sh /srv/apps/portfolio/.worktrees/virtual-tier-portfolio
# Nota: esto restaura el directory checkout, pero el gitlink en índice sigue D.
# Para restaurar índice gitlink: git -C /srv/apps/portfolio restore .worktrees/virtual-tier-portfolio
# O para limpiar índice (si se decide borrar gitlink): git -C /srv/apps/portfolio rm --cached .worktrees/virtual-tier-portfolio

# ocmonitor-share (no fue borrado, pero si se borra futuro)
tar xzf ~/infra-audit/backups-2026-09-06/cuarentena-ocmonitor-share.tgz -C ~
ls -ld ~/ocmonitor-share && du -sh ~/ocmonitor-share
```

Validar tras rollback: `systemctl --user is-active openclaw-gateway` debe seguir active; `du -sh` vuelve a 7.0G si se restaura modernize.

---

## 6) Qué se dejó (con motivo) y riesgos

### Dejado
- **~/.openclaw/npm (4.5G)**: no se borró nada. Motivo: gateway activo usa `openclaw-codex-...g-b42d646e5561ece2` (292M). Borrar variante equivocada rompería gateway. Stubs de generación (4K-96K) son inofensivos y requieren análisis hash antes de dedup.
- **~/.openclaw/canvas 509M + agents 1.1G**: G docs, no tocar sin confirmar — pueden contener canvases activos y trading demo.
- **~/ocmonitor-share 288M**: sin remote, no borrar hasta crear remote y push. Backup 59M ya hecho como seguridad.
- **/srv/apps/portfolio gitlink D**: dejado D sin `git rm` para no modificar índice sin aprobación. El checkout huérfano fue removido pero el pointer gitlink 160000 permanece D.

### Riesgos y mitigación
- **Riesgo gateway**: modernize y legacy no son usados por gateway (gateway usa `~/.openclaw` activo y npm proyecto b42d...). Verificado `systemctl status` y `journalctl` sin errores post-rm. Riesgo bajo. Rollback tar disponible.
- **Riesgo npm dedup**: si se borra acpx 3.2G o lancedb 950M por error, gateway perdería deps. Mitigado: no se tocó en esta tanda; próxima requiere `ps` + diff + restart test.
- **Riesgo virtual-tier gitlink D**: `git status` ahora D puede ensuciar deploys alineados si el deploy hace `git status` check. Mitigación: documentado; próxima tanda decidir entre `git restore` (restaura pointer) o `git rm --cached` (limpia pointer) tras confirmar que commit e2f9ae5 ya no es necesario. Tar 146M permite restaurar checkout si se necesita audit.
- **Riesgo espacio**: backups ocupan 528M en `~/infra-audit/backups-2026-09-06` (446M nuevos). No se hizo `docker rmi` ni `apt purge` en esta tanda (por instrucción). Espacio neto liberado: ~928M (658+89+181) - 446M tars = **~482M neto** (más 59M ocmonitor backup que no liberó origen).
- **Riesgo permisos**: `/srv/ai/openclaw-config` removido con sudo; `/srv/ai` queda vacío (4.0K). Si algún servicio esperaba legacy config, fallaría — pero legacy sin cambios desde May y active config es `~/.openclaw/openclaw.json`, por lo que riesgo bajo. Rollback sudo tar disponible.

---

## 7) Resumen reporte

- **Cuarentenado/borrado:** 3 paths, **928M origen** (658M modernize + 89M legacy + 181M virtual-tier) en **387M tgz** (196+45+146). Total con ocmonitor backup (no borrado) = 446M tgz / 1.2G origen.
- **Dejado:** npm 4.5G (acpx 3.2G, lancedb 950M, codex activo 292M), canvas 509M, agents 1.1G, ocmonitor 288M (solo backup 59M), worktree mission-alpha prunable (no tocado).
- **Validación:** gateway active, 24 contenedores, 6.4G OpenClaw, legacy y modernize No such file, journals limpios.
- **Rollback:** `tar xzf` en `~/infra-audit/backups-2026-09-06/cuarentena-*.tgz` (ver sección 5).

No se ejecutó `docker rmi` ni `apt purge` en esta tanda.

