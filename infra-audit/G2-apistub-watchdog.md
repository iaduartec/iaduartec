# G2 — api-stub eliminar + api_watchdog cron fix

**Host:** kiri-vnic — **Fecha:** 2026-09-06 03:07 UTC — **Operador:** subagente G2
**Tareas:** 1) deshabilitar `api-stub.service` (0 consumidores) 2) eliminar cron `api_watchdog.sh` fantasma (368 fatals/semana)

> NO toca mail-relay, trading, tailscale, whisper.

---

## 1. Pre-check

### api-stub.service

```bash
systemctl status api-stub | head -20
systemctl cat api-stub | head -40
systemctl is-enabled api-stub  # enabled
systemctl is-active api-stub   # active
```

**Resultado pre:**

```
● api-stub.service - API Stub (localhost)
     Loaded: loaded (/etc/systemd/system/api-stub.service; enabled)
     Active: active (running) since Sat 2026-08-22 06:07:15 UTC; 2 weeks ago
   Main PID: 1299 (MainThread)
     Memory: 6.6M (peak: 29.3M)
     CGroup: /home/ubuntu/.nvm/versions/node/v24.10.0/bin/node /srv/apps/api-service/server.js
```

**Unit file** (`/etc/systemd/system/api-stub.service`):
```ini
[Unit]
Description=API Stub (localhost)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/srv/apps/api-service
Environment=NODE_ENV=production
Environment=HOST=127.0.0.1
Environment=PORT=8080
ExecStart=/home/ubuntu/.nvm/versions/node/v24.10.0/bin/node /srv/apps/api-service/server.js
Restart=always
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/srv/apps/api-service /srv/logs
[Install]
WantedBy=multi-user.target
```

**Código** `/srv/apps/api-service/server.js` — stub minimal `http` con solo `GET /health` y `GET /` → `200 {service:"api-stub"}` else `404`.

**Consumidores — grep 0 hits relevantes:**

```bash
sudo grep -r "api-stub\|127.0.0.1:8080" /etc/caddy /etc/systemd  # 0 hits
cat /etc/caddy/Caddyfile | grep 8080  # 0 (solo 19080 docker Caddy, 3000 next, etc)
ss -lntup | grep 8080
# tcp LISTEN 127.0.0.1:8080 users:(("MainThread",pid=1299))  <- solo api-stub
# tcp LISTEN 127.0.0.1:18080 users:(freqtrade)               <- distinto servicio
```

Caddy host no proxea 8080. Tailscale serve apunta a 19080. n8n no referencia 8080. Veredicto **ELIMINAR**.

### cron api_watchdog

```bash
crontab -l | cat
sudo grep -r "api_watchdog" /etc/cron* /var/spool/cron/* | head
ls -la ~/scripts/ /home/ubuntu/scripts/
```

**Resultado pre:**

```
0 9 * * 0 /srv/automation/scripts/duartec-weekly-mail-maintenance.sh >> /srv/logs/legacy-output/duartec-weekly-mail-maintenance.log 2>&1
15 7 * * * /srv/automation/cnmv-pdmr/scripts/daily_ingest.sh >/dev/null 2>&1
* * * * * /home/ubuntu/scripts/api_watchdog.sh    # <-- fantasma cada minuto
0 */4 * * * /home/ubuntu/mission-bridge/scripts/sync-youtube-cookies.sh
```

```
sudo grep -r api_watchdog /etc/cron* /var/spool/cron/*
/var/spool/cron/crontabs/ubuntu:* * * * * /home/ubuntu/scripts/api_watchdog.sh
```

```
ls -la ~/scripts/  # No such file or directory
ls -la /home/ubuntu/scripts/  # No such file or directory
```

- `~/scripts` no existe → script no existe → cron falla cada minuto.
- Falta `MAILTO` (hereda `MAILTO` por defecto → cron intenta enviar mail vía `postfix/sendmail`).
- `/etc/postfix/main.cf` no existe (relay en contenedor `duartec-parts-mail-relay`, no postfix host) → cada fallo genera `fatal: open /etc/postfix/main.cf: No such file`.

**Impacto:** `* * * * *` = 1440 intentos/día → 368 fatals/semana observados en `journalctl -p err` (muestra + cron suspendido intermitente). Prioritario.

**Contenedores pre:** `docker ps | wc -l` = 14 (24 con sandboxes), whisper en cuarentena Exited — sin cambios esperados.

---

## 2. Comandos ejecutados

### Backups (antes de tocar)

```bash
mkdir -p ~/infra-audit/backups-2026-09-06
systemctl cat api-stub > ~/infra-audit/backups-2026-09-06/api-stub.service.bak
crontab -l > ~/infra-audit/backups-2026-09-06/crontab.pre-G2.bak

ls -lh ~/infra-audit/backups-2026-09-06/
# api-stub.service.bak (588 B)
# crontab.pre-G2.bak   (385 B)
```

### api-stub — disable (NO rm aún)

```bash
sudo systemctl disable --now api-stub 2>&1 | head -10
# Removed "/etc/systemd/system/multi-user.target.wants/api-stub.service".

systemctl status api-stub | head -10
# ○ api-stub.service - API Stub (localhost)
#      Loaded: loaded (/etc/systemd/system/api-stub.service; disabled)
#      Active: inactive (dead)
# Deactivated successfully — Consumed 8.923s CPU, 29.3M peak
```

> Intencionalmente **no** `rm /etc/systemd/system/api-stub.service` — quedará para borrado definitivo en siguiente tanda tras ventana de observación.

Verificación socket:

```bash
ss -lntup | grep 8080
# (vacío host - OK) — solo queda 127.0.0.1:18080 freqtrade
# docker expose 8080 interno no afecta host (no -p 8080:8080 en host)
```

### api_watchdog cron — eliminar línea

```bash
(crontab -l | grep -v "api_watchdog" | crontab -) 2>&1 | head -10
# exit 0

crontab -l | grep api_watchdog || echo "EMPTY - no api_watchdog"
# EMPTY

sudo cat /var/spool/cron/crontabs/ubuntu
# 0 9 * * 0  /srv/automation/scripts/duartec-weekly-mail-maintenance.sh ...
# 15 7 * * * /srv/automation/cnmv-pdmr/scripts/daily_ingest.sh ...
# 0 */4 * * * /home/ubuntu/mission-bridge/scripts/sync-youtube-cookies.sh

diff -u ~/infra-audit/backups-2026-09-06/crontab.pre-G2.bak <(crontab -l)
# -* * * * * /home/ubuntu/scripts/api_watchdog.sh   (única línea eliminada)
```

**MAILTO:** no añadido. Los 3 crons restantes redirigen todo a `>> log` o `>/dev/null`, no generan mail. Postfix host seguirá sin `main.cf` pero sin disparos. Si se añaden crons nuevos sin redirect, considerar `MAILTO=""` al inicio del crontab.

---

## 3. Validación

```bash
systemctl is-enabled api-stub  # disabled
systemctl is-active api-stub   # inactive

ss -lntup | grep 8080
# (vacío) — host 8080 libre

crontab -l
# 0 9 * * 0 /srv/automation/scripts/duartec-weekly-mail-maintenance.sh >> /srv/logs/legacy-output/duartec-weekly-mail-maintenance.log 2>&1 # duartec-weekly-mail-maintenance
# 15 7 * * * /srv/automation/cnmv-pdmr/scripts/daily_ingest.sh >/dev/null 2>&1 # CNMV_PDMR_DAILY
# 0 */4 * * * /home/ubuntu/mission-bridge/scripts/sync-youtube-cookies.sh

docker ps --format "{{.Names}}" | wc -l  # 14 (estable)
# openclaw-sbx-workspace-978141e8e94438903a502f1cf4baa3bb
# duartec-email-store, n8n-unified, duartec-parts-caddy, duartec-media-wrapper,
# duartec-parts-mail-relay, insforge-* (4), duartec-parts-mariadb, duartec-parts-db-api,
# n8n-runners, duartec-ollama

curl -s http://127.0.0.1:8080/health  # FAILED — expected (servicio detenido)
```

**journalctl -p err últimas 5 min (03:03-03:08):**

```
Sep 06 03:03:01 postfix/sendmail[3996499]: fatal: open /etc/postfix/main.cf: No such file
Sep 06 03:04:01 postfix/sendmail[3997615]: fatal: ...
Sep 06 03:05:01 postfix/sendmail[3998783]: fatal: ...
Sep 06 03:06:01 postfix/sendmail[4000138]: fatal: ...
Sep 06 03:07:01 postfix/sendmail[4002190]: fatal: ...  # último antes del fix (03:07:51)
# Fix aplicado 03:07:51 — próximo minuto 03:08:01 debe NO generar fatal
# (no inmediato en ventana de 5 min; observar `journalctl -p err --since "10 min ago" | grep postfix | wc -l` cada minuto)
```

> Tras ~5 min del fix, `journalctl -p err --since "5 min ago"` debe tender a 0 fatals/min (solo notar `networkctl: Interface veth* not found` ocasional de docker, irrelevante).

**Archivos preservados:**

```bash
ls -lh /etc/systemd/system/api-stub.service  # -rw-r--r-- 549 B (disabled, no borrado)
cat ~/infra-audit/backups-2026-09-06/api-stub.service.bak  # presente
cat ~/infra-audit/backups-2026-09-06/crontab.pre-G2.bak    # con api_watchdog
```

---

## 4. Rollback

### api-stub

```bash
# Restaurar y reactivar
sudo systemctl enable --now api-stub
systemctl status api-stub --no-pager | head -15
ss -lntup | grep 8080
curl -s http://127.0.0.1:8080/health | head -5
# {"status":"ok","service":"api-stub",...}

# Si se borró el unit file en futuro:
sudo cp ~/infra-audit/backups-2026-09-06/api-stub.service.bak /etc/systemd/system/api-stub.service
sudo systemctl daemon-reload
sudo systemctl enable --now api-stub
```

### crontab api_watchdog

```bash
# Restaurar backup completo
crontab ~/infra-audit/backups-2026-09-06/crontab.pre-G2.bak
crontab -l | cat
# verifica que vuelve "* * * * * /home/ubuntu/scripts/api_watchdog.sh"

# O solo re-añadir esa línea:
(crontab -l; echo "* * * * * /home/ubuntu/scripts/api_watchdog.sh") | crontab -
```

> Si rollback es parcial y postfix sigue sin `main.cf`, volverán 368 fatals/semana → considerar crear `~/scripts/api_watchdog.sh` real o añadir `MAILTO=""` + `>/dev/null 2>&1` a la línea.

---

## Estado final

- [x] `api-stub` **disabled/inactive**, `ss :8080` vacío host, unit file conservado, backup en `backups-2026-09-06/`
- [x] `api_watchdog` eliminado de crontab, backup `crontab.pre-G2.bak`, `grep api_watchdog` vacío
- [x] `docker ps` 14 contenedores estables, sin tocar mail-relay/trading/tailscale/whisper
- [ ] Observación 10-15 min `journalctl -p err | grep postfix` debe bajar a 0/min — validar en siguiente tanda
- [ ] Borrado definitivo `rm /etc/systemd/system/api-stub.service` post-ventana (no hecho en G2)

