# Pendientes G — Tailscale / SQLite / Worktrees / Env+Postfix

**Host:** kiri-vnic — 15 contenedores activos (24 era pre-cuarentena 06-Sep; hoy 15 en `docker ps`)
**Fecha auditoría:** 2026-09-06 03:0x UTC
**Modo:** Solo lectura, no se modificó nada. Evidencia verificable con comandos del enunciado.

---

## 1. Tailscale 8082×2 + 5680 + 18889 (rutas muertas)

### 1.1 `tailscale serve status` (vivas fuera de Caddy)

```bash
tailscale serve status 2>&1 | head -60
sudo tailscale serve status 2>&1 | head -60
```

**Salida relevante (idéntica sin/con sudo):**

```
https://kiri-vnic.tail4b3cf6.ts.net:8443 (tailnet only)
|-- / proxy http://127.0.0.1:8082          ← MUERTA

https://openwebui.tail4b3cf6.ts.net (tailnet only) (svc:openwebui)
|-- / proxy http://127.0.0.1:8082          ← MUERTA (duplicada)
```

Otras 13 rutas vivas: `:9443→5800`, `:9444→19080`, `:9445→7130`, `:9446→3000`, `:9447→100.103.134.102:19180`, `:9448→3001`, `:9449→10.0.0.229:80`, `:9450→8090`, `:8502→8501`, `n8n.tail→19080`, `openclaw.tail→5800`, `+ 7 paths en :443 →19080/5800/8020`.

Origen declarativo: `~/duartec-infra/scripts/tailscale-serve-apply.sh`:

```bash
tailscale serve --bg --https=8443 http://127.0.0.1:8082
tailscale serve --service=svc:openwebui --bg http://127.0.0.1:8082
# log "✓ :8443 (Open WebUI) → http://127.0.0.1:8082"
# log "✓ svc:openwebui → http://127.0.0.1:8082"
```

Commit origen: `a9553d10 fix(tailscale): update Open WebUI port 3080 → 8082` (`duartec-infra/.git/logs/refs/heads/main`).

### 1.2 Caddy host limpio

```bash
cat /etc/caddy/Caddyfile | grep -n "8082\|5680\|18889\|openwebui" | head -20
grep -r "8082\|18889" ~/duartec-infra/ /etc/caddy/ | head -20
```

- `/etc/caddy/Caddyfile` (11 745 bytes, 395 líneas, `Sep 6 02:52`) → **0 hits** para `8082|5680|18889|openwebui`. Es symlink lógico a `~/duartec-infra/Caddyfile-host` (396 líneas). `caddy validate` → Valid (tanda5).
- `/etc/caddy/` tiene 23 `.bak/.backup` (208K total) ya cuarentenados en `~/infra-audit/backups-2026-09-06/caddy/` — también **0 hits** `8082/5680/18889` tras grep en `Caddyfile.bak*` (tanda5).
- `~/duartec-infra/Caddyfile-host | grep 8082|5680` → 0 hits. Docker Caddy `caddy/conf.d/*.caddy` → 0 menciones.

### 1.3 `ss` + `curl` confirman puertos muertos

```bash
ss -lntup | grep -E "8082|5680|18889" | head -10   # vacío (exit 0, 0 líneas)
curl -sv http://127.0.0.1:8082/   # Failed to connect: Connection refused (000)
curl -sv http://127.0.0.1:5680/   # Connection refused
curl -sv http://127.0.0.1:18889/  # Connection refused
ss -lntup | grep 5682            # tcp LISTEN 127.0.0.1:5682 (media-wrapper, no 5680)
```

`ss -lntup` completo muestra: `19080, 5800, 8020, 3000/3001/3002, 7130/7131, 8501, 5682, 5999/6080, 18080, 8080, 41641/udp tailscaled` — **ninguno en 8082/5680/18889**.

### 1.4 Journal confirma error

```bash
sudo journalctl -u tailscaled --since "7 days ago" --no-pager | grep -E "8082|openwebui" | head -20
```

```
Sep 02 00:50:52 tailscaled[1329]: http: proxy error: dial tcp 127.0.0.1:8082: connect: connection refused
Sep 04 17:55:59 tailscaled[1329]: monitor: RTM_DELROUTE: src=, dst=fe80::8082:e8ff:fef3:900f/128  (falso positivo IPv6, no puerto)
```

Resto son `context canceled` de healthchecks, sin más `8082`.

### 1.5 `grep -r` global (filtrado node_modules)

```bash
grep -r "8082\|18889" ~/duartec-infra/ /etc/caddy/ 2>&1 | grep -v node_modules | head -20
```

- `~/duartec-infra/.env` + `.env.backup-*` + `.env.example` + `.env.bak.*`: `OPENCLAW_URL=http://127.0.0.1:18889` (4 hits, muerto — no hay listener).
- `~/duartec-infra/scripts/tailscale-serve-apply.sh`: 2 hits `8082` (origen de la ruta muerta).
- `~/duartec-infra/docker-compose.yml:157`: comentario `# N8N_MCP_URL legado apunta a 100.103.134.102:5680 no listena host; se anula hasta migrar MCP canónico` — **5680 muerto pero ya anulado** (`.env:N8N_MCP_URL=http://100.103.134.102:5680/mcp-server/http` sin servicio).
- Resto son falsos positivos: `adjuntos.json` SHA256 que contienen `8082`/`18889` como subcadena, y `encoding-japanese` blob.

**Veredicto 8082×2:** Ruta muerta confirmada, doble (8443 + svc:openwebui). Sin contenedor Open WebUI (`docker ps -a | grep openwebui` vacío). Caddy no la referencia. Próximo paso propuesto (no ejecutado): `tailscale serve --https=8443 --set-path=/ off` + `tailscale serve --service=svc:openwebui off` o re-ejecutar `tailscale-serve-apply.sh` sin esas 2 líneas.

**Veredicto 5680:** Puerto 5680 muerto, no expuesto en tailscale ni Caddy. Solo referencia histórica en `N8N_MCP_URL` (tailnet IP 100.103.134.102:5680). 5682 sí vivo (media-wrapper). No requiere acción inmediata salvo limpiar `N8N_MCP_URL` cuando se migre MCP.

**Veredicto 18889:** OPENCLAW_URL muerto, sin listener ni ruta tailscale/Caddy. 0 impacto operativo. Limpiar cuando se defina nuevo OPENCLAW (ahora en :5800).

---

## 2. SQLite corrupted/recovered 13.4M (retenidos)

### 2.1 Volumen `duartec-voice-ai_n8n_data_unified`

```bash
docker volume inspect duartec-voice-ai_n8n_data_unified --format '{{.Mountpoint}}'
# /var/lib/docker/volumes/duartec-voice-ai_n8n_data_unified/_data
sudo ls -lh /var/lib/docker/volumes/duartec-voice-ai_n8n_data_unified/_data/ | head -40
```

```
total 78M
-rw-rw-r-- 1 opc opc 6.7M May 31 11:22 database-corrupted-backup.sqlite
-rw-rw-r-- 1 opc opc 6.7M May 31 11:21 database-recovered.sqlite
-rw-rw-rw- 1 opc opc  36M Sep  6 02:19 database.sqlite              ← VIVO
-rw-rw-rw- 1 opc opc  32K Sep  6 03:01 database.sqlite-shm
-rw-rw-rw- 1 opc opc 218K Sep  6 03:00 database.sqlite-wal
-rw-r--r-- 1 opc opc    0 Sep  6 02:19 crash.journal
```

`sudo sqlite3 ... "PRAGMA integrity_check;"` → `ok` en los tres (vivo, corrupted-backup, recovered). `stat` confirma `opc:opc` (por eso `ls` sin sudo falla con `Permission denied` / `No such file`).

### 2.2 Backups cuarentenados

```bash
ls -lh ~/infra-audit/backups-2026-09-06/sqlite-legacy/ | head -10
```

```
total 35M
-rw-rw-r-- 1 ubuntu ubuntu 6.7M May 31 11:22 database-corrupted-backup.sqlite  (copia del volumen)
-rw-rw-r-- 1 ubuntu ubuntu 6.7M May 31 11:21 database-recovered.sqlite         (copia)
-rw-r--r-- 1 ubuntu ubuntu  22M Jun  6 07:44 database.sqlite.v19.bak
```

El volumen retiene 13.4M (2×6.7M) + 36M vivo. La carpeta `sqlite-legacy` duplica esos 13.4M + 22M v19 = 35M. El tgz `cuarentena-n8n-unified.tgz` (52M) en `backups-2026-09-06/` ya contiene snapshot completo del volumen pre-limpieza.

**Veredicto:** 13.4M retenidos confirmados, duplicados. `integrity_check ok` en ambos legacy, sin divergencia aparente desde 31-May. No tocar `database.sqlite` vivo. Próximo paso propuesto (no ejecutado): tras 7 días de `ok` continuo, `sudo rm database-corrupted-backup.sqlite database-recovered.sqlite` en volumen y conservar solo `sqlite-legacy/*.v19.bak` + tgz como respaldo frío. Ahorro: 13.4M en volumen + 13.4M duplicado si se deduplica.

---

## 3. Worktrees gone

### 3.1 `git worktree list` (solo lectura)

```bash
git -C ~/snake-pentagon worktree list 2>&1 | head -20
# /home/ubuntu/snake-pentagon                       0d4c226 [main]
# /home/ubuntu/snake-pentagon/.worktrees/neon-game  a101d9a [codex/neon-snake-game]  ← VIVO, limpio

git -C ~/apps/duartec-hub worktree list 2>&1 | head -20
# /home/ubuntu/apps/duartec-hub                6a1f0d7 [main]
# /home/ubuntu/worktrees/hub-v2-v5             dc892aa [codex/hub-v2-v5]             ← VIVO
# /home/ubuntu/worktrees/mission-alpha-v3-hub  d6edcad [codex/mission-alpha-v3-hub]   ← VIVO

git -C /home/ubuntu/portfolio-repo worktree list 2>&1 | head -20
# /home/ubuntu/portfolio-repo  8aad524 [codex/instruction-safety-cleanup-20260906] ← solo main checkout

git -C /home/ubuntu worktree list 2>&1 | head -20
# /home/ubuntu  44cc6e84f [main]  (superrepo HOME, 125 tracked, 10 gitlinks)
```

### 3.2 Portfolio `.worktrees/virtual-tier-portfolio` — huérfano

```bash
ls -la ~/portfolio-repo/.worktrees/ 2>&1 | head -20
# drwx------ virtual-tier-portfolio (19 subdirs, .git propio, .continue, .codex-n8n-backups)
git -C ~/portfolio-repo worktree list --verbose        # NO lo lista → no es worktree link
ls -la ~/portfolio-repo/.worktrees/virtual-tier-portfolio/ | head -20
# total 348, checkout completo con .git independiente (4 ago 2026)
```

Es el duplicado documentado en `tanda5-junk.md` y `raw/repos-openclaw.md` (362M entre `~/portfolio-repo/.worktrees/virtual-tier-portfolio` y `/srv/apps/portfolio/.worktrees/virtual-tier-portfolio` idénticos, HEAD `e2f9ae5`). Hoy `/srv/apps/portfolio/.worktrees/` ya no existe (vaciado en cuarentena), pero `~/portfolio-repo/.worktrees/virtual-tier-portfolio` sigue como **checkout huérfano** (no registrado como worktree). `git status` en `portfolio-repo` → `clean`.

### 3.3 `~/apps/insforge` — espejo sin .gitmodules (confirmado)

```bash
ls -la ~/apps/insforge 2>&1 | head -20
# total 44, 4 ficheros + .insforge/ + migrations/
# .env, .env.bak-2026-05-27_211432, .env.local, AGENTS.md, README.md, docker-compose.yml
cat ~/apps/insforge/*.md 2>&1 | head -20
# AGENTS.md con bloque INSFORGE:START (project My-First-Project-Recovery gt6unhi5.eu-central.insforge.app)
ls -la ~/apps/insforge/.git 2>&1          # No such file
cat ~/apps/insforge/.gitmodules 2>&1      # No such file
cat ~/apps/insforge/.insforge/project.json # {"project_id":"7e9255df...","appkey":"gt6unhi5",...}
ls -lh ~/apps/insforge/migrations/       # 3 sql: create-trading-tables, revoke-anonymous, enforce-row-ownership
```

**Espejo local sin repo git**, no es worktree ni submódulo. Las credenciales están en `.insforge/project.json` + `.env.local`.

**Veredicto worktrees:** `snake-pentagon` y `duartec-hub` **vivos, no gone**. `portfolio-repo` **sin worktrees registrados** (1 solo checkout), el directorio `virtual-tier-portfolio` es huérfano no-worktree pendiente de auditoría `du -sh` + `git log` antes de `rm -rf`. `insforge` confirmado como espejo sin `.git`/`.gitmodules` (correcto, no requiere acción). Los `gone` históricos citados en `tanda5` (web-duartec `nuevo-prototype-review-remote` dirty, `mission-alpha-v3-scheduler` prunable) no están en este host `kiri-vnic` (son de `/srv/apps/*`), no reproducidos aquí.

---

## 4. .env.backup + postfix

### 4.1 `.env*` en `~/duartec-infra/`

```bash
ls -lh ~/duartec-infra/.env* 2>&1 | head -20
# -rw------- 4.8K Sep  2 23:50 .env                                          (119 líneas, activo)
# -rw------- 4.6K Aug 30 16:44 .env.backup-before-security-secrets-20260902T235045Z (115 líneas)
# -rw------- 3.9K Jul  4 23:53 .env.bak.20260710T095446Z                      (100 líneas)
# -rw-rw-r-- 2.7K Aug 29 07:11 .env.example                                  (73 líneas)
# -rw------- 4.4K Aug 23 02:12 .env.rollback-20260823-n8n-auth               (109 líneas)

diff .env .env.backup-before-security-secrets-... | head -40
# 116,119d115
# < MAIL_RELAY_READ_SECRET=d42e4527...
# < MAIL_RELAY_SEND_SECRET=c6b496eb...
# < (línea vacía)

md5sum .env .env.backup*  # 59492bc... vs aa504aa... (divergen solo por 2 secrets + blanks)
wc -l .env*               # 119 vs 115 vs 100 vs 73 vs 109
```

### 4.2 Postfix

```bash
ls -lh /etc/postfix/ 2>&1 | head -20
# -rw-r--r-- dynamicmaps.cf, master.cf (6.9K), main.cf.proto (27K), postfix-files, sasl/
# main.cf → No such file

cat /etc/postfix/main.cf 2>&1 | head -20   # No such file
postconf -n 2>&1 | head -20                # fatal: open /etc/postfix/main.cf: No such file
systemctl status postfix 2>&1 | head -20   # Loaded: disabled, Active: inactive (dead)
systemctl is-enabled postfix → disabled / is-active → inactive / dpkg -l postfix → not installed (solo restos config)
```

### 4.3 Crons / MAILTO

```bash
grep -r "MAILTO" /etc/cron* /var/spool/cron/* 2>&1 | head -10   # 0 hits (con sudo también)
cat /etc/crontab | head -20                                     # sin MAILTO
sudo cat /var/spool/cron/crontabs/ubuntu
# 0 9 * * 0 /srv/automation/scripts/duartec-weekly-mail-maintenance.sh >> /srv/logs/...  # duartec-weekly-mail-maintenance
# 15 7 * * * /srv/automation/cnmv-pdmr/scripts/daily_ingest.sh >/dev/null 2>&1            # CNMV_PDMR_DAILY
# * * * * * /home/ubuntu/scripts/api_watchdog.sh
# 0 */4 * * * /home/ubuntu/mission-bridge/scripts/sync-youtube-cookies.sh
crontab -l / sudo crontab -l → idéntico, sin MAILTO, sin postfix requerido (mail-relay va por contenedor duartec-parts-mail-relay en :8080)
```

**Veredicto .env.backup:** Retenido correctamente como respaldo pre-secrets (30-Ago). Divergencia mínima (2 `MAIL_RELAY_*_SECRET` añadidos el 02-Sep). Conservar 1-2 backups recientes, rotar `*.bak.20260710` si se quiere ahorrar 3.9K (no urgente).

**Veredicto postfix:** Ausencia **intencional** — `main.cf` nunca existió, servicio `disabled/inactive`, sin `MAILTO` en crons. El relay de mail lo hace el contenedor `duartec-parts-mail-relay` (Up 3 days, :8080), no postfix host. No requiere instalación.

---

## Resumen tabla

| item                               | evidencia                                                                                                                                                                                                                                                                                                                                                                   | tamaño / estado                                                                                                           | veredicto                                                                                                                                                                                   |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Tailscale :8443 → 8082**         | `tailscale serve status` → `kiri-vnic:8443 → 127.0.0.1:8082` + `scripts/tailscale-serve-apply.sh:8443` + `ss 8082` vacío + `curl 8082` refused + `journal: proxy error dial tcp 127.0.0.1:8082: connection refused (02-Sep)`                                                                                                                                                | Ruta viva, backend muerto, 0 bytes Caddy, 1 error en journal 7d                                                           | **RUTA MUERTA confirmada** — limpiar con `tailscale serve --https=8443 off` o re-aplicar script sin esa línea. Caddy limpio (0 hits), no rollback necesario                                 |
| **Tailscale svc:openwebui → 8082** | `tailscale serve status` → `openwebui.tail → 127.0.0.1:8082` + `scripts/tailscale-serve-apply.sh:svc:openwebui` + mismo `ss/curl` vacío                                                                                                                                                                                                                                     | Ruta viva duplicada del anterior, mismo backend muerto                                                                    | **RUTA MUERTA duplicada** — misma acción que 8443 (2×8082). `docker ps -a                                                                                                                   | grep openwebui` vacío confirma sin contenedor |
| **Puerto 5680**                    | `ss -lntup grep 5680` vacío (solo `5682` vivo media-wrapper) + `curl 5680` refused + `grep -r 5680` solo en `docker-compose.yml:157` comentario + `.env:N8N_MCP_URL=100.103.134.102:5680` + `n8n-runners: 5680/tcp` interno no publicado                                                                                                                                    | No hay listener host, `n8n-runners` expone 5680 solo interno, tailscale 0 rutas                                           | **MUERTO pero ya anulado** — no expuesto en Caddy/tailscale. Limpiar `N8N_MCP_URL` cuando se migre MCP canónico; sin acción urgente                                                         |
| **Puerto 18889**                   | `grep -r 18889` → `.env/.env.backup/.env.example/.env.bak` `OPENCLAW_URL=127.0.0.1:18889` + `ss 18889` vacío + `curl 18889` refused + 0 hits Caddy/tailscale                                                                                                                                                                                                                | `OPENCLAW` ahora en `:5800` (tailscale :9443 y /openclaw vivos), 18889 sin proceso                                        | **MUERTO desde tanda3** — 0 impacto, variable legacy. Limpiar `.env` cuando se cierre OPENCLAW 18889 (ya migrado a 5800)                                                                    |
| **sqlite 13.4M retenidos**         | `VOL=/var/lib/docker/volumes/duartec-voice-ai_n8n_data_unified/_data` + `sudo ls -lh` → `database.sqlite 36M` vivo + `database-corrupted-backup.sqlite 6.7M 31-May-11:22` + `database-recovered.sqlite 6.7M 31-May-11:21` + `sqlite3 integrity_check ok` ×3 + `~/infra-audit/backups-2026-09-06/sqlite-legacy/ 35M (2×6.7M+22M v19.bak)` + `cuarentena-n8n-unified.tgz 52M` | Volumen: 78M total, 36M vivo + 13.4M legacy (2×6.7M) + 250K wal/shm. Backups: 35M duplicado + 52M tgz. `crash.journal 0B` | **RETENIDOS duplicados, integrity ok** — no tocar vivo. Propuesta: borrar legacy en volumen tras 7d de `ok`, conservar `sqlite-legacy/` + tgz como frío. Ahorro inmediato 13.4M si se purga |
| **sqlite v19.bak 22M**             | `ls -lh sqlite-legacy/database.sqlite.v19.bak 22M 06-Jun-07:44` + `grep binary matches` + `VOL du -sh 105M`                                                                                                                                                                                                                                                                 | 22M en `infra-audit`, no en volumen                                                                                       | **BACKUP frío** — conservar como referencia v19, ya cuarentenado                                                                                                                            |
| **Worktrees snake-pentagon**       | `git -C ~/snake-pentagon worktree list` → `main 0d4c226` + `.worktrees/neon-game a101d9a [codex/neon-snake-game]`                                                                                                                                                                                                                                                           | 2 worktrees, ambos vivos, limpio                                                                                          | **VIVO — no gone**                                                                                                                                                                          |
| **Worktrees duartec-hub**          | `git -C ~/apps/duartec-hub worktree list` → `main 6a1f0d7` + `/worktrees/hub-v2-v5 dc892aa` + `/worktrees/mission-alpha-v3-hub d6edcad`                                                                                                                                                                                                                                     | 3 worktrees, todos vivos                                                                                                  | **VIVO — no gone**                                                                                                                                                                          |
| **Worktree portfolio-repo**        | `git -C ~/portfolio-repo worktree list` → solo `8aad524 [codex/instruction-safety-cleanup-20260906]` + `ls .worktrees/virtual-tier-portfolio` (348 bloques, checkout huérfano con `.git` propio, no listado)                                                                                                                                                                | Directorio huérfano 348 bloques, `git status clean`, no es worktree link                                                  | **HUÉRFANO pendiente** — no es gone, es duplicado 181M (tanda5: 362M con /srv/apps). Requiere `du -sh` + `git log` antes de `rm -rf`                                                        |
| **Worktree insforge**              | `ls -la ~/apps/insforge` → sin `.git`, sin `.gitmodules`, con `.insforge/project.json` + 3 migrations + README/AGENTS                                                                                                                                                                                                                                                       | Espejo 44K, `NO_GIT_SIN_GITMODULES`                                                                                       | **ESPEJO confirmado** — correcto, no es repo, no requiere worktree                                                                                                                          |
| **.env.backup**                    | `ls -lh .env*` → `.env 4.8K 119l` + `.env.backup-... 4.6K 115l` + `.env.bak 3.9K` + `.env.rollback 4.4K` + `diff` = 2 secrets + `md5` diverge                                                                                                                                                                                                                               | 4 variantes, delta 4 líneas (`MAIL_RELAY_*_SECRET`)                                                                       | **RETENIDO correcto** — respaldo pre-secrets 30-Ago. Rotar solo si se quiere (ahorro 3.9K)                                                                                                  |
| **Postfix**                        | `ls /etc/postfix/main.cf` → No such file (solo `main.cf.proto` 27K + `master.cf` 6.9K) + `systemctl postfix disabled/inactive` + `postconf fatal`                                                                                                                                                                                                                           | 116K de protos, sin instancia activa                                                                                      | **AUSENTE intencional** — no instalado, mail va por `duartec-parts-mail-relay` (:8080). No instalar                                                                                         |
| **MAILTO crons**                   | `grep -r MAILTO /etc/cron* /var/spool/cron/*` → 0 hits + `crontab -l` 4 jobs sin MAILTO                                                                                                                                                                                                                                                                                     | 4 crons ubuntu, 0 MAILTO                                                                                                  | **SIN MAILTO** — correcto sin postfix, logs van a `/srv/logs/legacy-output/` y `/dev/null`                                                                                                  |

---

## Comandos de verificación (copiar/pegar)

```bash
tailscale serve status 2>&1 | head -60
cat /etc/caddy/Caddyfile | grep -n "8082\|5680\|18889\|openwebui" | head -20
sudo journalctl -u tailscaled --since "7 days ago" --no-pager | grep -E "8082|openwebui" | head -20
ss -lntup | grep -E "8082|5680|18889" | head -10; curl -sv http://127.0.0.1:8082/ 2>&1 | head -10

VOL=$(docker volume inspect duartec-voice-ai_n8n_data_unified --format '{{.Mountpoint}}')
sudo ls -lh "$VOL"/ | head -40
sudo sqlite3 "$VOL/database.sqlite" "PRAGMA integrity_check;"   # ok
ls -lh ~/infra-audit/backups-2026-09-06/sqlite-legacy/ | head -10

git -C ~/snake-pentagon worktree list; git -C ~/apps/duartec-hub worktree list; git -C /home/ubuntu/portfolio-repo worktree list
ls -la ~/apps/insforge | head -20; test -d ~/apps/insforge/.git && echo HAS_GIT || echo NO_GIT_ESPEJO
ls -la ~/portfolio-repo/.worktrees/virtual-tier-portfolio/ | head -10

ls -lh ~/duartec-infra/.env* | head -20
ls -lh /etc/postfix/ | head -20; cat /etc/postfix/main.cf 2>&1 | head -20; systemctl is-enabled postfix; systemctl is-active postfix
sudo cat /var/spool/cron/crontabs/ubuntu; grep -r "MAILTO" /etc/cron* /var/spool/cron/* 2>&1 | head -10
```
