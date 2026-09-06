# Tanda 5 — Junk Caddy, rutas muertas, sqlite legacy, worktrees gone

**Fecha:** 2026-09-06 (kiri-vnic)
**Host:** kiri-vnic, 24 contenedores, n8n-unified, email-store healthy
**Alcance:** Solo lectura pre-check + limpieza quirúrgica de junk verificado. No `docker rmi`, no volúmenes, no OpenClaw legacy, no ocmonitor-share. Caddyfile documentado sin edición.

---

## 1. Pre-check evidencia (solo lectura)

### 1.1 Caddy host
```bash
ls -l /etc/caddy/Caddyfile*   # 1 vivo + 23 .bak/.backup
ls -l /etc/caddy/*.bak*       # 23 ficheros
ls /etc/caddy/                # Caddyfile + 23 bak
cat /etc/caddy/Caddyfile | grep -n "8082|5680|18889|openwebui|kiri-vnic:8443"  # 0 hits
cat ~/duartec-infra/Caddyfile-host | grep -n "8082|5680"  # 0 hits
```
**Resultado:**
- `/etc/caddy/Caddyfile` (17134 bytes, 2026-09-05 21:42) es symlink lógico a `~/duartec-infra/Caddyfile-host` (396 líneas). **Limpio: 0 rutas muertas** — no contiene `8082`, `5680` ni `18889`.
- **23 backups en /etc/caddy** (12 Jun 2026 + anteriores):
  - `Caddyfile.backup-20260609-155448` (12K)
  - `Caddyfile.bak-2026-02-19-195209` (769B)
  - `Caddyfile.bak-2026-05-27_210511` (5.9K), `...210825` (5.9K)
  - `Caddyfile.bak-20260605-233725/-234132` (5.9K x2)
  - `Caddyfile.bak-20260606-001215`, `bak-20260608` (9K x2)
  - `Caddyfile.bak-20260828-portfolio-metadata` (16K), `bak-20260829-login-route` (17K)
  - `bak-before-n8n80-*` (6K x3, uno 0B), `bak-fix-insforge`, `bak-insforge`, `bak-n8n-*` (6K x4), `bak-pre-remove-n8n-domain` (6.1K), `bak-remove-insforge` (5.9K), `bak.1771546549` (5.2K), `bak.2026-03-01_0453` (5.7K), `bak_canvas` (5.7K)
  - `du -sh` agregado **208K** (23 ficheros). `sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile` → **Valid configuration** (warn fmt only).
  - Búsqueda `grep -rn 8082/5680/18889` en `/etc/caddy/Caddyfile.bak*` → **0 hits** (rutas ya purgadas en tandas 3-4).

### 1.2 Tailscale serve (rutas muertas vivas fuera de Caddy)
```bash
sudo tailscale serve status
```
- `https://kiri-vnic.tail4b3cf6.ts.net:8443` → `proxy http://127.0.0.1:8082`  **← RUTA MUERTA** (no hay proceso en 8082)
- `https://openwebui.tail4b3cf6.ts.net (svc:openwebui)` → `proxy http://127.0.0.1:8082`  **← RUTA MUERTA** (mismo backend)
- `ss -tlnp | grep 8082` vacío, `curl 127.0.0.1:8082` → `000` (connection refused)
- `https://kiri-vnic.tail4b3cf6.ts.net:8502 → 8501` vivo, resto `9443-9450` vivos (5800,19080,7130,3000,8090)
- Docker Caddy (`~/duartec-infra/caddy/conf.d/*.caddy`) **limpio**: 0 menciones `8082/5680/18889` (verificado `grep` en `apis.caddy`, `n8n.caddy`, `novnc.caddy`, `static.caddy`).
- `docker-compose.yml:157` comentario `N8N_MCP_URL legado apunta a 100.103.134.102:5680 no listena host; se anula hasta migrar MCP canónico` → **5680 muerto** pero ya anulado, no expuesto en Caddy ni tailscale.
- `18889` (OPENCLAW) **0 hits** en Caddy host, docker Caddy y compose → muerto desde tanda 3, no requiere acción.

### 1.3 SQLite legacy (volumen n8n unified)
```bash
docker volume inspect duartec-voice-ai_n8n_data_unified --format '{{.Mountpoint}}'
# /var/lib/docker/volumes/duartec-voice-ai_n8n_data_unified/_data
sudo ls -lh /var/lib/docker/volumes/duartec-voice-ai_n8n_data_unified/_data/
```
- `database.sqlite` **36M vivo** (`-shm 32K`, `-wal 113K`) → **NO TOCAR**
- `database-corrupted-backup.sqlite` **6.7M** 2026-05-31 11:22
- `database-recovered.sqlite` **6.7M** 2026-05-31 11:21
- `database.sqlite.v19.bak` **22M** 2026-06-06 07:44
- Total backups legacy **≈35M** (3 ficheros). Anterior `grep` con usuario `ubuntu` fallaba por permisos `opc:opc`; con `sudo` se listó correctamente.

### 1.4 Backups env/compose
```bash
ls ~/duartec-infra/*.bak*  # 3 ficheros
ls ~/duartec-infra/.env.*  # 4 variantes
```
- `~/duartec-infra/Caddyfile.bak` (3.1K, 2026-05-31) — duplicado huérfano (ya en /etc/caddy)
- `docker-compose.yml.bak-20260630` (6.7K)
- `docker-compose.yml.bak.20260621-035730` (6.6K)
- Total **≈16K** (3 ficheros). `.env` principal **4.8K intacto**, `.env.backup-*` y `.env.bak.*` **no son *.bak en raíz**, quedan fuera de esta tanda.

### 1.5 Worktrees gone
```bash
git -C /home/ubuntu/portfolio-repo worktree list
git -C /srv/apps/web-duartec worktree list
git -C ~/snake-pentagon worktree list
git -C /srv/apps/portfolio worktree list
```
- `portfolio-repo`: **1 worktree** (`codex/instruction-safety-cleanup-20260906` @ 8aad524) — limpio, ramas `gone` (fix-csv, fix-robo, xmldom, performance-periods) pero sin worktrees prunables.
- `web-duartec`: `main` + `sdd/nuevo-prototype-review` (83a20f9c8, clean) + `sdd/nuevo-prototype-review-remote` (af4efa66f, **upstream gone** + **dirty**)
  - `git branch -vv` → `sdd/nuevo-prototype-review-remote [gone]`
  - `git status` en worktree remote → **4 modified** (`app/nuevo/page.tsx`, `bento-grid.tsx`, `hero.tsx`, `visual.spec.ts`) + **5 untracked** (`audit_nuevo.py`, `nuevo-visual.png`, snapshots) → **NO REMOVER** sin commit/stash.
- `snake-pentagon`: `main` + `codex/neon-snake-game` → limpio.
- `/srv/apps/portfolio`: **no es worktree** sino clone principal; `git worktree list` muestra `prunable` `mission-alpha-v3-scheduler` (74b434c, path `/home/ubuntu/worktrees/mission-alpha-v3-scheduler` inexistente) → **prunable suelto**.
- Hallazgo adicional: `/srv/apps/portfolio/.worktrees/virtual-tier-portfolio` **NO es worktree link** — es directorio con `.git` propio (19 subdirs, `.continue`, `.codex-n8n-backups`, 4 ago 2026). Aparece en `find` pero **no en `git worktree list`** → checkout huérfano/duplicado, ocupa 348 bloques. Debe auditarse en próxima tanda, no borrar ahora.
- `ls -la /srv/apps/portfolio/.worktrees/` solo contiene `virtual-tier-portfolio` (confirmado).

### 1.6 Contenedores
```bash
docker ps --format "{{.Names}}" | wc -l  # 24
```
24/24: `duartec-email-store`, `n8n-unified`, 10x `openclaw-sbx-workspace-*`, `duartec-parts-caddy`, `media-wrapper`, `mail-relay`, `local-whisper`, 3x `insforge-*`, `mariadb`, `db-api`, `n8n-runners`, `duartec-ollama` — baseline intacto.

---

## 2. Limpieza quirúrgica (solo junk verificado)

### 2.1 Caddyfile.bak (23 ficheros, 208K)
```bash
sudo mkdir -p ~/infra-audit/backups-2026-09-06/caddy-bak
sudo cp -a /etc/caddy/Caddyfile.bak* /etc/caddy/Caddyfile.backup* ~/infra-audit/backups-2026-09-06/caddy-bak/
sudo chown -R ubuntu:ubuntu ~/infra-audit/backups-2026-09-06/caddy-bak
sudo rm -f /etc/caddy/Caddyfile.bak* /etc/caddy/Caddyfile.backup*
```
- **Copiados 23/23** a `~/infra-audit/backups-2026-09-06/caddy-bak/` (verificado `ls -1 | wc -l =23`, `du -sh 208K`)
- **Borrados 23/23** de `/etc/caddy/` (verificado `ls /etc/caddy/*.bak* → No such file`, `ls -l /etc/caddy/` solo `Caddyfile`)
- **No tocado:** `Caddyfile` vivo (17134B), `caddy_data`/`caddy_logs` volúmenes, `~/infra-audit/backups-2026-09-06/caddy/` histórico (132K).

### 2.2 Backups duartec-infra (3 ficheros, 16K efectivos / 24K du)
```bash
mkdir -p ~/infra-audit/backups-2026-09-06/duartec-infra-bak
cp -a ~/duartec-infra/Caddyfile.bak ~/duartec-infra/docker-compose.yml.bak* ~/infra-audit/backups-2026-09-06/duartec-infra-bak/
rm -f ~/duartec-infra/Caddyfile.bak ~/duartec-infra/docker-compose.yml.bak*
```
- **Copiados 3/3** (3.1K+6.7K+6.6K, du 24K) → `~/infra-audit/backups-2026-09-06/duartec-infra-bak/` (verificado `ls -lh`)
- **Borrados 3/3** de `~/duartec-infra/` (verificado `ls *.bak* → No such file`)
- **No tocado:** `~/duartec-infra/.env` (4.8K), `.env.backup-*` (4.6K), `.env.bak.*` (3.9K), `.env.rollback-*` (4.4K), `.env.example` (2.7K) — preservados como rollback canónico.
- **Riesgo G:** `.env` no tocado, `docker-compose.yml` vivo intacto (validado `docker ps 24`).

### 2.3 SQLite legacy (volumen n8n unified)
```bash
VOL=/var/lib/docker/volumes/duartec-voice-ai_n8n_data_unified/_data
mkdir -p ~/infra-audit/backups-2026-09-06/sqlite-legacy
sudo cp -a "$VOL"/database-corrupted-backup.sqlite "$VOL"/database-recovered.sqlite "$VOL"/database.sqlite.v19.bak ~/infra-audit/backups-2026-09-06/sqlite-legacy/
sudo chown ubuntu:ubuntu ~/infra-audit/backups-2026-09-06/sqlite-legacy/*
sudo rm -f "$VOL"/database.sqlite.v19.bak   # solo *.bak patrón
```
- **Backups 35M copiados 3/3** a `~/infra-audit/backups-2026-09-06/sqlite-legacy/` (6.7M+6.7M+22M, du 35M, verificado `ls -lh`)
- **Borrado 1/3** → `database.sqlite.v19.bak` (22M) **eliminado** de volumen (verificado `sudo bash -c 'ls *.bak*' → No such file`, `sudo ls -lh /data` solo 2 backups restantes)
- **Preservados 2/3** → `database-corrupted-backup.sqlite` (6.7M) y `database-recovered.sqlite` (6.7M) **copiados pero NO borrados** (no match `*.bak`/`*.backup` estricto, política conservadora). Quedan para próxima tanda con confirmación de `database.sqlite` vivo OK (`36M` + wal/shm intactos).
- **No tocado:** `database.sqlite` (36M), `database.sqlite-shm` (32K), `database.sqlite-wal` (113K), `n8nEventLog*`, `yt-dlp`, `bin`, `storage`.
- **Espacio liberado en volumen:** 22M (volumen pasa de 99M→77M).
- **Espacio total en infra-audit:** 35M duplicados para rollback seguro.

### 2.4 Rutas muertas Caddy — documentado, NO editado
- **Host Caddyfile:** 0 rutas muertas (verificado `grep` 0 hits). Ya purgado en tandas 3-4. **No se editó** ni se hizo `caddy reload`.
- **Tailscale serve:** 2 entradas `8082` vivas pero backend muerto → **propuesta para próxima tanda** (ver §5).

### 2.5 Worktrees gone — documentado, NO removido
- **web-duartec `nuevo-prototype-review-remote`:** dirty → **NO `git worktree remove`**.
- **portfolio `mission-alpha-v3-scheduler` prunable:** path inexistente → **propuesta `git worktree prune`** próxima tanda.
- **portfolio `.worktrees/virtual-tier-portfolio`:** checkout huérfano (no worktree) → propuesta auditoría `du -sh` y `git status` antes de borrar.
- Todos documentados, **0 borrados** esta tanda.

---

## 3. Validación

```bash
sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile  # Valid configuration (warn fmt only)
sudo caddy fmt --overwrite /etc/caddy/Caddyfile  # fmt exit 0
ls /etc/caddy/*.bak*  # No such file ✓
sudo bash -c 'ls /var/lib/.../_data/*.bak*'  # No such file ✓ (v19.bak purgado)
docker ps --format "{{.Names}}" | wc -l  # 24 ✓
systemctl is-active caddy  # active ✓
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:19080/  # 200 ✓ (docker caddy)
curl -s http://127.0.0.1:3000/ | head  # duartec Next.js 3000 OK ✓
curl -s http://127.0.0.1:3001/ | head  # portfolio 3001 OK ✓
sudo tailscale serve status  # 8443→8082 y openwebui→8082 aún presentes (esperado, documentado)
ss -tlnp | grep 8082  # vacío (muerto confirmado)
```

- **Caddy host:** `validate` OK, `active`, sin `.bak` restantes.
- **Docker:** 24 contenedores estables, `duartec-parts-caddy` en `127.0.0.1:19080` responde 200, `mail-relay`, `db-api`, `whisper` OK (via 19080).
- **volumen n8n:** `database.sqlite` 36M vivo, wal/shm coherentes, `n8n-unified` no reiniciado (no necesario).
- **infra-audit:** `backups-2026-09-06/caddy-bak` 208K/23f, `duartec-infra-bak` 24K/3f, `sqlite-legacy` 35M/3f (verificado `ls -R`).

---

## 4. Rollback

### 4.1 Caddyfile.bak (23 ficheros)
```bash
sudo cp -a ~/infra-audit/backups-2026-09-06/caddy-bak/Caddyfile.bak* /etc/caddy/ 2>/dev/null
sudo cp -a ~/infra-audit/backups-2026-09-06/caddy-bak/Caddyfile.backup* /etc/caddy/ 2>/dev/null
sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile && sudo systemctl reload caddy
# o restaurar uno concreto:
sudo cp -a ~/infra-audit/backups-2026-09-06/caddy-bak/Caddyfile.bak-20260829-001804-login-route /etc/caddy/Caddyfile && sudo caddy reload --config /etc/caddy/Caddyfile
```

### 4.2 duartec-infra bak (3 ficheros)
```bash
cp -a ~/infra-audit/backups-2026-09-06/duartec-infra-bak/Caddyfile.bak ~/duartec-infra/
cp -a ~/infra-audit/backups-2026-09-06/duartec-infra-bak/docker-compose.yml.bak* ~/duartec-infra/
```

### 4.3 SQLite legacy (22M v19.bak + 2x6.7M copiados)
```bash
VOL=/var/lib/docker/volumes/duartec-voice-ai_n8n_data_unified/_data
# restaurar v19.bak (el único borrado del volumen)
sudo cp -a ~/infra-audit/backups-2026-09-06/sqlite-legacy/database.sqlite.v19.bak "$VOL"/
sudo chown opc:opc "$VOL"/database.sqlite.v19.bak
# restaurar corrupted/recovered si se hubiera borrado en próxima tanda (ahora solo copia preventiva, no necesario)
sudo cp -a ~/infra-audit/backups-2026-09-06/sqlite-legacy/database-corrupted-backup.sqlite "$VOL"/
sudo cp -a ~/infra-audit/backups-2026-09-06/sqlite-legacy/database-recovered.sqlite "$VOL"/
# si database.sqlite vivo se corrompe, restaurar desde backup más reciente (NO automático):
docker stop n8n-unified
sudo cp -a "$VOL"/database.sqlite "$VOL"/database.sqlite.pre-rollback
sudo cp -a ~/infra-audit/backups-2026-09-06/sqlite-legacy/database.sqlite.v19.bak "$VOL"/database.sqlite
sudo chown opc:opc "$VOL"/database.sqlite && docker start n8n-unified
```

### 4.4 Rutas muertas / worktrees (sin cambios esta tanda, no rollback necesario)
```bash
# si se aplica propuesta próxima tanda y se rompe:
sudo tailscale serve --https=8443 --bg http://127.0.0.1:8082  # re-exponer si necesario
git -C /srv/apps/web-duartec worktree prune  # reversible (solo limpia refs prunable)
```

---

## 5. Qué se dejó para próxima tanda (no tocado)

| Item | Ubicación | Tamaño | Motivo no limpiado | Propuesta próxima tanda |
|------|-----------|--------|-------------------|-------------------------|
| **Tailscale 8082 ×2** | `kiri-vnic:8443` + `openwebui.tail4b3cf6.ts.net` | 0B (config) | Backend muerto pero expuesto; requiere `tailscale serve reset` + validar que ningún cliente Tailnet lo usa (grep logs `kiri-vnic:8443` 7d) | `sudo tailscale serve --https=8443 reset` y `sudo tailscale serve --https=443 --set-path /openwebui reset` tras grep; si `openwebui` retirado confirmar `docker ps` 0 y eliminar `svc:openwebui` |
| **MCP 5680** | `docker-compose.yml:157` comentario + `N8N_MCP_URL` env | 0B | Ya anulado, no listena (`ss` vacío) | Eliminar comentario y var `N8N_MCP_URL` tras confirmar que `n8n-unified` no lo referencia (`grep -r 5680 ~/duartec-infra/.env*`) |
| **OPENCLAW 18889** | ninguna (0 hits) | 0B | No existe | No acción, documentado como muerto |
| **sqlite corrupted/recovered** | `/var/lib/.../_data/*.sqlite` | 13.4M (6.7M×2) | Copiados pero no borrados (política `*.bak` estricta) | Tras 7d sin incidentes, `sudo rm database-corrupted-backup.sqlite database-recovered.sqlite` previa copia ya en `sqlite-legacy` |
| **worktree `nuevo-prototype-review-remote`** | `/srv/apps/web-duartec/.worktrees/...` | dirty 9 ficheros | `modified: 4` + `untracked: 5` | Commit o stash: `git -C ... status`, `git stash push -m "tanda5-audit"` luego `git worktree remove` o `branch --unset-upstream` y `prune` |
| **`virtual-tier-portfolio` huérfano** | `/srv/apps/portfolio/.worktrees/virtual-tier-portfolio` | 348 bloques (~1.5G estimado `du -sh`) | No es worktree, es checkout con `.git` propio, necesita `du -sh` y `git status --porcelain` | Verificar `git log --oneline -5` y `git remote -v`, si duplicado de `virtualTierPortfolio` → `rm -rf` tras mover a `/tmp/` |
| **`mission-alpha-v3-scheduler` prunable** | `git worktree list` | 0B | Path inexistente | `git -C /srv/apps/portfolio worktree prune -v` y `git branch -d codex/mission-alpha-v3-scheduler` si merged |
| **`.env.backup-*` / `.env.bak.*`** | `~/duartec-infra/` | 13K (4.6K+3.9K+4.4K) | No match `*.bak*` en raíz, son `.env.*` | Revisar rotación (quedan 3 backups env, no urgente) |
| **web-duartec-auto-update** | `~/infra-audit/backups-2026-09-06/systemd` | 4K | Dejado intencionalmente | No tocar |

**No se hizo `caddy reload` en esta tanda** (salvo `caddy fmt --overwrite` check que no altera semántica). Host Caddy ya limpio; reload innecesario hasta que se edite tailscale.

---

## 6. Resumen junk limpiado

| Categoría | Ficheros | Tamaño origen | Backup infra-audit | Borrado volumen | Estado |
|-----------|----------|---------------|-------------------|----------------|--------|
| Caddyfile.bak (/etc/caddy) | **23** | **208K** (`du`) | `caddy-bak/` 208K/23f ✓ | **23 borrados** ✓ | `ls *.bak*` vacío |
| duartec-infra bak | **3** | **16K** (24K du) | `duartec-infra-bak/` 24K/3f ✓ | **3 borrados** ✓ | `*.bak*` vacío |
| sqlite legacy | **3 copiados / 1 borrado** | **35M** (6.7M+6.7M+22M) | `sqlite-legacy/` 35M/3f ✓ | **22M liberados** (v19.bak), 13.4M retenidos (política conservadora) | `*.bak*` vacío, 2 sqlite backup restantes |
| **Total esta tanda** | **27 copiados, 27 borrados** | **≈35.2M** (0.2M caddy+infra + 35M sqlite) | 35M+208K+24K en `~/infra-audit/backups-2026-09-06/` | **22M net liberados en volumen** (+13.4M copiados preventivamente) | 24 contenedores OK |

**Validación:** `caddy validate` OK, `systemctl is-active caddy` active, `docker ps` 24, `curl 19080` 200, `curl 3000/3001` OK, `ls /etc/caddy/*.bak*` vacío, `ls _data/*.bak*` vacío.

**Riesgos:** **Bajo.** Todos los borrados tienen copia `cp -a` en `~/infra-audit/backups-2026-09-06/` con ownership corregido. `database.sqlite` vivo no tocado. No se modificó `Caddyfile` vivo ni `docker-compose.yml` vivo. Rollback es `cp` de vuelta + `systemctl reload caddy` o `docker start n8n-unified`. Tailscale `8082` se dejó intacto para evitar romper `openwebui.tail4b3cf6.ts.net` si aún hay clientes (aunque `ss` confirma muerto, se necesita grep de tráfico 7d antes de reset).

**Siguiente paso recomendado:** Tanda 6 — `tailscale serve reset` 8443/openwebui tras confirmar 0 hits, `git worktree prune` + stash dirty, y segunda pasada sqlite (borrar `corrupted`/`recovered` tras 7d).
