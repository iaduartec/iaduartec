# G3 — Tailscale rutas muertas + weekly-mail + sqlite/worktrees limpieza

**Host:** kiri-vnic  
**Fecha:** 2026-09-06  
**Contenedores:** 14 (validado `docker ps` — ver § Validación)  
**Contexto:** whisper cuarentena, api-stub disabled, api_watchdog removido  
**Ejecutor:** subagente G3 (DevOps)

---

## Resumen ejecutivo

| Qué se limpió                                                                                                                                 | Qué se dejó (intencionalmente)                                                                                                | Validación                                                                              |
| --------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| **8082×2 off:** `kiri-vnic:8443→127.0.0.1:8082` y `svc:openwebui→8082` eliminados del handler vivo + comentados en `tailscale-serve-apply.sh` | sqlite 13.4M (`corrupted` 6.7M + `recovered` 6.7M) conservado vivo 7d (política Tanda5)                                       | `tailscale serve status \| grep 8082` vacío (exit 1), `ss -lntup \| grep 8082` vacío    |
| **cron weekly-mail-maintenance off:** 1 línea `0 9 * * 0 duartec-weekly-mail-maintenance.sh` borrada                                          | Script `/srv/automation/scripts/duartec-weekly-mail-maintenance.sh` conservado (7.7K) para posible fix futuro                 | `crontab -l` 2 líneas (CNMV + youtube-cookies), `grep weekly` vacío                     |
| **worktree huérfano 181M:** `~/portfolio-repo/.worktrees/virtual-tier-portfolio` cuarentenado y borrado                                       | worktrees vivos intactos (`snake-pentagon` 2, `duartec-hub` 3, `portfolio-repo` 1) + `.env.backup-*` + sqlite `.bak` ya vacío | `git worktree list` sin huérfanos, `du -sh .worktrees` 4.0K, `docker ps -q \| wc -l` 14 |

---

## 1. Tailscale 8082×2 rutas muertas

### Pre

```bash
tailscale serve status 2>&1 | head -60
sudo tailscale serve status 2>&1 | head -60
cat ~/duartec-infra/scripts/tailscale-serve-apply.sh | grep -n "8443\|8082\|openwebui"
ss -lntup | grep 8082
```

**Salida pre (ambos usuarios):**

```
https://kiri-vnic.tail4b3cf6.ts.net:8443 (tailnet only)
|-- / proxy http://127.0.0.1:8082

https://openwebui.tail4b3cf6.ts.net (tailnet only) (svc:openwebui)
|-- / proxy http://127.0.0.1:8082
```

Script:

```
102:tailscale serve --bg --https=8443 http://127.0.0.1:8082
103:log "  ✓  :8443 (Open WebUI) → http://127.0.0.1:8082"
115:tailscale serve --service=svc:openwebui --bg http://127.0.0.1:8082
116:log "  ✓  svc:openwebui (openwebui.tail...) → http://127.0.0.1:8082"
```

`ss -lntup | grep 8082` → vacío (confirmado: backend muerto, ningún listener en 8082, coherente con 14 contenedores sin Open WebUI).

### Backup

```bash
mkdir -p ~/infra-audit/backups-2026-09-06
cp ~/duartec-infra/scripts/tailscale-serve-apply.sh ~/infra-audit/backups-2026-09-06/tailscale-serve-apply.sh.bak
ls -lh ~/infra-audit/backups-2026-09-06/tailscale-serve-apply.sh.bak
# -rwxr-xr-x 1 ubuntu ubuntu 6.1K Sep 6 03:11
bash -n ~/duartec-infra/scripts/tailscale-serve-apply.sh  # validación pre-edit
```

### Comandos (limpieza)

```bash
# Edición del script apply — comentar 2 backends muertos
# Antes:
# tailscale serve --bg --https=8443 http://127.0.0.1:8082
# log "  ✓  :8443 (Open WebUI) → http://127.0.0.1:8082"
# Después:
# retirado 2026-09-06: backend muerto — 8082 sin listener (14 contenedores, Open WebUI no desplegado)
# # tailscale serve --bg --https=8443 http://127.0.0.1:8082
# # log "  ✓  :8443 (Open WebUI) → http://127.0.0.1:8082"

# Igual para svc:openwebui:
# retirado 2026-09-06: backend muerto — svc:openwebui → 8082 sin listener
# # tailscale serve --service=svc:openwebui --bg http://127.0.0.1:8082
# # log "  ✓  svc:openwebui (openwebui.tail...) → http://127.0.0.1:8082"

bash -n ~/duartec-infra/scripts/tailscale-serve-apply.sh  # exit 0

# Limpieza handlers vivos (ephemeral serve, no persistente tras reboot sin script):
sudo tailscale serve --https=8443 off 2>&1 | head -20   # exit 0
sudo tailscale serve --service=svc:openwebui off 2>&1 | head -20  # exit 0
```

> Nota: `serve` es ephemeral; el fix duradero es la edición del script `tailscale-serve-apply.sh` (que se ejecuta vía systemd en boot). Los `off` limpian la sesión actual.

### Post

```bash
tailscale serve status 2>&1 | grep 8082; echo exit:$?  # 1 vacío OK
tailscale serve status 2>&1 | grep -E "8443|openwebui"  # vacío
sudo tailscale serve status 2>&1 | grep 8082  # vacío
ss -lntup | grep 8082  # vacío
tailscale serve status | grep -E "8443|openwebui|8082" | head -10  # vacío para 8082
```

**Estado final tailscale (sin 8443 ni svc:openwebui):**

```
https://kiri-vnic.tail4b3cf6.ts.net:8502  -> 127.0.0.1:8501
https://kiri-vnic.tail4b3cf6.ts.net:9443  -> 127.0.0.1:5800
https://kiri-vnic.tail4b3cf6.ts.net:9444  -> 127.0.0.1:19080
https://kiri-vnic.tail4b3cf6.ts.net:9445  -> 127.0.0.1:7130
https://kiri-vnic.tail4b3cf6.ts.net:9446  -> 127.0.0.1:3000
https://kiri-vnic.tail4b3cf6.ts.net:9447  -> 100.103.134.102:19180
https://kiri-vnic.tail4b3cf6.ts.net:9448  -> 127.0.0.1:3001
https://kiri-vnic.tail4b3cf6.ts.net:9449  -> 10.0.0.229:80
https://kiri-vnic.tail4b3cf6.ts.net:9450  -> 127.0.0.1:8090
https://n8n.tail4b3cf6.ts.net (svc:n8n)        -> 127.0.0.1:19080
https://openclaw.tail4b3cf6.ts.net (svc:openclaw) -> 127.0.0.1:5800
# ya NO aparecen:
# https://kiri-vnic.tail4b3cf6.ts.net:8443 -> 8082
# https://openwebui.tail4b3cf6.ts.net (svc:openwebui) -> 8082
```

Script validado `bash -n` exit 0, grep script:

```
102:# retirado 2026-09-06: backend muerto — 8082 sin listener (14 contenedores, Open WebUI no desplegado)
103:# tailscale serve --bg --https=8443 http://127.0.0.1:8082
116:# retirado 2026-09-06: backend muerto — svc:openwebui → 8082 sin listener
117:# tailscale serve --service=svc:openwebui --bg http://127.0.0.1:8082
```

---

## 2. weekly-mail-maintenance cron (D, roto, 29× ERROR)

### Pre

```bash
cat /srv/automation/scripts/duartec-weekly-mail-maintenance.sh 2>&1 | head -40
crontab -l | grep weekly
crontab -l
ls -lh /srv/automation/scripts/duartec-weekly-mail-maintenance.sh
```

**Script head (causa raíz):**

```bash
if [ -z "${DUARTEC_EMAIL_PASSWORD:-}" ]; then
  echo "ERROR: DUARTEC_EMAIL_PASSWORD is not set."
  exit 1
fi
```

**Crontab pre (3 líneas):**

```
0 9 * * 0 /srv/automation/scripts/duartec-weekly-mail-maintenance.sh >> /srv/logs/legacy-output/duartec-weekly-mail-maintenance.log 2>&1 # duartec-weekly-mail-maintenance
15 7 * * * /srv/automation/cnmv-pdmr/scripts/daily_ingest.sh >/dev/null 2>&1 # CNMV_PDMR_DAILY
0 */4 * * * /home/ubuntu/mission-bridge/scripts/sync-youtube-cookies.sh
```

**Log:** `/srv/logs/legacy-output/duartec-weekly-mail-maintenance.log` 29 líneas, 29× `ERROR: DUARTEC_EMAIL_PASSWORD is not set.` (1.2K, última `Aug 30 09:00`).

### Backup

```bash
crontab -l > ~/infra-audit/backups-2026-09-06/crontab.pre-G3.bak  # 338 bytes
cp /srv/automation/scripts/duartec-weekly-mail-maintenance.sh ~/infra-audit/backups-2026-09-06/
ls -lh ~/infra-audit/backups-2026-09-06/crontab.pre-G3.bak
ls -lh ~/infra-audit/backups-2026-09-06/duartec-weekly-mail-maintenance.sh # 7.7K
```

### Comandos (limpieza)

```bash
(crontab -l | grep -v "weekly-mail-maintenance" | crontab -) 2>&1 | head -10  # exit 0
crontab -l | grep weekly; echo exit:$?  # 1 vacío OK
crontab -l
```

> NO se borró el script, solo el cron. Queda para posible fix futuro (inyectar secret o migrar a vault).

### Post

```bash
crontab -l
# 15 7 * * * /srv/automation/cnmv-pdmr/scripts/daily_ingest.sh >/dev/null 2>&1 # CNMV_PDMR_DAILY
# 0 */4 * * * /home/ubuntu/mission-bridge/scripts/sync-youtube-cookies.sh

crontab -l | wc -l  # 2 líneas
crontab -l | grep weekly  # exit 1 vacío
ls -lh /srv/automation/scripts/duartec-weekly-mail-maintenance.sh  # 7.7K conservado
```

Validación: **cron weekly off**, quedan 2 líneas (CNMV + youtube-cookies) como exige la tarea.

---

## 3. sqlite corrupted/recovered 13.4M + env backups

### Pre

```bash
VOL=$(docker volume inspect duartec-voice-ai_n8n_data_unified --format '{{.Mountpoint}}')
sudo bash -c 'ls -lh /var/lib/docker/volumes/duartec-voice-ai_n8n_data_unified/_data/database* 2>&1 | head -20'
sudo bash -c 'ls -lh /var/lib/docker/volumes/duartec-voice-ai_n8n_data_unified/_data/*.bak 2>&1 | head -20'
ls -lh ~/duartec-infra/.env* 2>&1 | head -10
ls -lh ~/infra-audit/backups-2026-09-06/sqlite-legacy/ 2>&1 | head -10
```

**Vivo (kiri-vnic):**

```
-rw-rw-r-- 1 opc opc 6.7M May 31 11:22 database-corrupted-backup.sqlite
-rw-rw-r-- 1 opc opc 6.7M May 31 11:21 database-recovered.sqlite
-rw-rw-rw- 1 opc opc  36M Sep  6 02:19 database.sqlite
-rw-rw-rw- 1 opc opc  32K Sep  6 03:01 database.sqlite-shm
-rw-rw-rw- 1 opc opc 218K Sep  6 03:00 database.sqlite-wal
```

Total vivo: 36M sqlite + 6.7M+6.7M legacy = **49.4M** en volumen. `*.bak` vivo → `No such file` (vacío, `database.sqlite.v19.bak` ya borrado como en Tanda5).

**Cuarentena tars ya existentes (sqlite-legacy 35M):**

```
~/infra-audit/backups-2026-09-06/sqlite-legacy/
  database-corrupted-backup.sqlite  6.7M
  database-recovered.sqlite         6.7M
  database.sqlite.v19.bak          22M   (copia cuarentenada)
# además tars:
cuarentena-n8n-unified.tgz 52M
cuarentena-n8n-data.tgz 427K
```

**Env backups:**

```
-rw------- 1 ubuntu ubuntu 4.8K /home/ubuntu/duartec-infra/.env
-rw------- 1 ubuntu ubuntu 4.6K .env.backup-before-security-secrets-20260902T235045Z
-rw------- 1 ubuntu ubuntu 3.9K .env.bak.20260710T095446Z
-rw------- 1 ubuntu ubuntu 4.4K .env.rollback-20260823-n8n-auth
-rw-rw-r-- 1 ubuntu ubuntu 2.7K .env.example

diff .env vs .env.backup-before-security... → delta 4 líneas (MAIL_RELAY secrets):
+MAIL_RELAY_READ_SECRET=...
+MAIL_RELAY_SEND_SECRET=...
```

### Acción

**Por política conservadora (Tanda5) NO se borran `corrupted`/`recovered` aún — se deja 7d estable.** Solo documentación y cuarentena ya realizada.

Verificaciones realizadas:

```bash
sudo bash -c 'ls -lh /var/lib/docker/volumes/duartec-voice-ai_n8n_data_unified/_data/*.bak'  # vacío OK
du -sh ~/infra-audit/backups-2026-09-06/sqlite-legacy  # 35M
ls -lh ~/duartec-infra/.env*  # documentado, no borrar
```

### Post

- Vivo: 36M + 13.4M legados, `ls *.bak` vacío.
- Backup cuarentena: 35M en `~/infra-audit/backups-2026-09-06/sqlite-legacy` (ya existente, no modificado).
- Env: `.env.backup-*` no tocados (delta 4 líneas documentado).

---

## 4. Worktrees gone

### Pre

```bash
git -C ~/snake-pentagon worktree list 2>&1 | head -10
git -C ~/apps/duartec-hub worktree list 2>&1 | head -10
git -C ~/portfolio-repo worktree list 2>&1 | head -10
ls -ld ~/portfolio-repo/.worktrees/virtual-tier-portfolio 2>&1 | head -5
du -sh ~/portfolio-repo/.worktrees/virtual-tier-portfolio 2>&1 | head -5
```

**Vivos, no tocar:**

```
~/snake-pentagon
  /home/ubuntu/snake-pentagon                       0d4c226 [main]
  /home/ubuntu/snake-pentagon/.worktrees/neon-game  a101d9a [codex/neon-snake-game]

~/apps/duartec-hub
  /home/ubuntu/apps/duartec-hub                6a1f0d7 [main]
  /home/ubuntu/worktrees/hub-v2-v5             dc892aa [codex/hub-v2-v5]
  /home/ubuntu/worktrees/mission-alpha-v3-hub  d6edcad [codex/mission-alpha-v3-hub]

~/portfolio-repo
  /home/ubuntu/portfolio-repo  8aad524 [codex/instruction-safety-cleanup-20260906]
  # .worktrees/virtual-tier-portfolio NO aparece en list → huérfano
```

**Huérfano:**

```
drwx------ 19 ubuntu ubuntu 4096 Aug 22 04:09 ~/portfolio-repo/.worktrees/virtual-tier-portfolio
181M  ~/portfolio-repo/.worktrees/virtual-tier-portfolio
```

### Comandos (cuarentena + limpieza)

```bash
tar czf ~/infra-audit/backups-2026-09-06/cuarentena-portfolio-repo-virtual-tier.tgz \
  -C ~/portfolio-repo/.worktrees virtual-tier-portfolio 2>&1 | head -5  # exit 0
ls -lh ~/infra-audit/backups-2026-09-06/cuarentena-portfolio-repo-virtual-tier.tgz
# -rw-rw-r-- 1 ubuntu ubuntu 146M Sep 6 03:11

rm -rf ~/portfolio-repo/.worktrees/virtual-tier-portfolio 2>&1 | head -5  # exit 0 (solo tras verificar huérfano)
ls -la ~/portfolio-repo/.worktrees 2>&1 | head -20  # vacío 4.0K
git -C ~/portfolio-repo worktree list 2>&1 | head -10  # sigue 1 entrada
```

### Post

```bash
git -C ~/snake-pentagon worktree list  # 2 entradas vivas
git -C ~/apps/duartec-hub worktree list  # 3 entradas vivas
git -C ~/portfolio-repo worktree list  # 1 entrada (portfolio-repo)
ls -ld ~/portfolio-repo/.worktrees  # 4.0K vacío
du -sh ~/portfolio-repo/.worktrees  # 4.0K
ls -lh ~/infra-audit/backups-2026-09-06/cuarentena-portfolio-repo-virtual-tier.tgz  # 146M
```

Validación: huérfano eliminado, vivos preservados.

---

## Validación global

```bash
tailscale serve status 2>&1 | grep 8082; echo exit:$?  # 1 vacío
tailscale serve status 2>&1 | grep -E "8443|openwebui"  # vacío
ss -lntup | grep 8082  # vacío
crontab -l | wc -l  # 2
crontab -l  # CNMV + youtube-cookies
docker ps -q | wc -l  # 14
docker ps --format "{{.Names}}" | head -20
```

**docker ps 14 (ok):**

```
openclaw-sbx-workspace-978141e8e94438903a502f1cf4baa3bb
duartec-email-store
n8n-unified
duartec-parts-caddy
duartec-media-wrapper
duartec-parts-mail-relay
insforge-postgrest-1
insforge-insforge-1
insforge-deno-1
insforge-postgres-1
duartec-parts-mariadb
duartec-parts-db-api
n8n-runners
duartec-ollama
```

---

## Archivos tocados / Backups

| Archivo                                                      | Acción                        | Backup                                                                                               |
| ------------------------------------------------------------ | ----------------------------- | ---------------------------------------------------------------------------------------------------- |
| `~/duartec-infra/scripts/tailscale-serve-apply.sh`           | comentar 2 backends 8082      | `~/infra-audit/backups-2026-09-06/tailscale-serve-apply.sh.bak` (6.1K)                               |
| crontab                                                      | borrar 1 línea weekly         | `~/infra-audit/backups-2026-09-06/crontab.pre-G3.bak` (338 bytes) + `crontab.pre-G2.bak` previo      |
| `/srv/automation/scripts/duartec-weekly-mail-maintenance.sh` | **no borrado**, solo cron off | `~/infra-audit/backups-2026-09-06/duartec-weekly-mail-maintenance.sh` (7.7K)                         |
| `~/portfolio-repo/.worktrees/virtual-tier-portfolio` (181M)  | cuarentenado + `rm -rf`       | `~/infra-audit/backups-2026-09-06/cuarentena-portfolio-repo-virtual-tier.tgz` (146M)                 |
| sqlite `corrupted`/`recovered` 13.4M                         | **conservado**                | ya en `~/infra-audit/backups-2026-09-06/sqlite-legacy` (35M) + tars `cuarentena-n8n-unified.tgz` 52M |
| `.env.backup-*`                                              | **no borrado**                | delta 4 líneas documentado                                                                           |

---

## Rollback

### Tailscale 8082×2

```bash
# Restaurar script:
cp ~/infra-audit/backups-2026-09-06/tailscale-serve-apply.sh.bak ~/duartec-infra/scripts/tailscale-serve-apply.sh
bash -n ~/duartec-infra/scripts/tailscale-serve-apply.sh
bash ~/duartec-infra/scripts/tailscale-serve-apply.sh
# o manual:
tailscale serve --bg --https=8443 http://127.0.0.1:8082
tailscale serve --service=svc:openwebui --bg http://127.0.0.1:8082
tailscale serve status | grep 8082  # debe mostrar 2 rutas
```

### Crontab weekly

```bash
crontab ~/infra-audit/backups-2026-09-06/crontab.pre-G3.bak
crontab -l | grep weekly  # debe mostrar 0 9 * * 0 ...weekly...
# alternativa manual:
(crontab -l; echo "0 9 * * 0 /srv/automation/scripts/duartec-weekly-mail-maintenance.sh >> /srv/logs/legacy-output/duartec-weekly-mail-maintenance.log 2>&1 # duartec-weekly-mail-maintenance") | crontab -
```

> Si se quiere fix en lugar de rollback: inyectar `DUARTEC_EMAIL_PASSWORD` en `.bashrc`/vault y validar `bash /srv/automation/scripts/duartec-weekly-mail-maintenance.sh` antes de re-habilitar cron.

### sqlite

```bash
# No se borró nada vivo; rollback solo si se hubiese limpiado:
sudo bash -c 'ls -lh /var/lib/docker/volumes/duartec-voice-ai_n8n_data_unified/_data/database*'
# restaurar desde cuarentena:
sudo tar xzf ~/infra-audit/backups-2026-09-06/cuarentena-n8n-unified.tgz -C /  # contiene volumen
# o restaurar legacy específico:
cp ~/infra-audit/backups-2026-09-06/sqlite-legacy/database-corrupted-backup.sqlite /tmp/
cp ~/infra-audit/backups-2026-09-06/sqlite-legacy/database-recovered.sqlite /tmp/
```

### Worktree portfolio

```bash
tar xzf ~/infra-audit/backups-2026-09-06/cuarentena-portfolio-repo-virtual-tier.tgz -C ~/portfolio-repo/.worktrees
ls -ld ~/portfolio-repo/.worktrees/virtual-tier-portfolio  # 181M restaurado
du -sh ~/portfolio-repo/.worktrees/virtual-tier-portfolio
# Nota: git worktree list seguirá sin mostrarlo (huérfano no registrado); para re-registrar:
# git -C ~/portfolio-repo worktree add .worktrees/virtual-tier-portfolio <branch>
```

---

## Reporte final (para entrega)

- **Limpio:** 8082×2 off (kiri-vnic:8443 off + svc:openwebui off), cron weekly off (3→2 líneas), worktree huérfano 181M → 146M tgz + `rm -rf`.
- **Dejado:** sqlite 13.4M vivo (corrupted+recovered) + 36M db principal, `.env.backup-*` (delta 4 líneas), worktrees vivos (snake 2, hub 3, portfolio 1), script weekly 7.7K.
- **Validación:** `serve status` vacío 8082 (exit 1), `ss -lntup` vacío 8082, `crontab -l` 2 líneas CNMV+youtube, `docker ps -q | wc -l` 14, `worktree list` sin huérfanos.
- **Rollback:** `cp tailscale-serve-apply.sh.bak`, `crontab crontab.pre-G3.bak`, `tar xzf cuarentena-portfolio-repo-virtual-tier.tgz`.

**Comandos de verificación para auditor externo:**

```bash
tailscale serve status | grep 8082; echo "debe ser exit 1 vacío"
crontab -l | wc -l; echo "debe ser 2"
docker ps -q | wc -l; echo "debe ser 14"
git -C ~/portfolio-repo worktree list; ls -lh ~/portfolio-repo/.worktrees
sudo bash -c 'ls -lh /var/lib/docker/volumes/duartec-voice-ai_n8n_data_unified/_data/database*'
```
