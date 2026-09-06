# Tanda 3 — Host Legacy / Units Huérfanas / Procesos Huérfanos — kiri-vnic

**Fecha:** 2026-09-06T02:26:16Z — 02:27:53Z UTC  
**Host:** kiri-vnic (Oracle ARM, Ubuntu)  
**Ejecutor:** Muse Spark — subagente Tanda 3  
**Contexto previo Tanda 1:** 24 contenedores tras retiro n8n legacy, `0.0.0.0:5678` cerrado, `n8n` pin `2.37.7`, `email-store` fix healthy. Verificado al inicio de esta tanda.

---

## 0) Verificación Docker (no tocar)

```bash
docker ps -q | wc -l
# 24

docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -30
# NAMES                              STATUS                PORTS
# duartec-email-store                Up 3 minutes (healthy)
# n8n-unified                        Up 6 minutes          5678/tcp  -> NOT 0.0.0.0:5678, cerrado OK (interno)
# openclaw-sbx-workspace-* (6)       Up 28-40h
# duartec-... (caddy, media-wrapper, mail-relay, local-whisper, insforge-* etc) -> resto 24
# duartec-ollama                     Up 12h  11434/tcp
```

> No se tocó Docker salvo verificar. 24 contenedores, n8n-unified sin binding público.

---

## 1) Pre-check evidencia (solo lectura)

**Raw log completo:** `~/infra-audit/tanda3-precheck-raw.log` (52K, 2026-09-06T02:26:16Z). Resumen abajo con salidas recortadas.

### 1.1 `systemctl list-units --type=service --state=running | head -30`

```
actions.runner.iaduartec-Web_Duartec.kiri-vnic.service  active running
api-stub.service                                        active running
caddy.service                                           active running
containerd.service                                      active running
cron.service                                            active running
docker.service                                          active running
fail2ban, fwupd, getty, mission-bridge, multipathd, networkd-dispatcher, polkit,
portfolio.service, rsyslog, serial-getty, snap.oracle-cloud-agent*, snapd,
ssh, systemd-*, tailscaled, udisks2
# 29 units running, NO postfix/firewalld/podman/open-vm/rsync activos como servicio
```

### 1.2 `systemctl list-unit-files | grep -E "postfix|firewalld|ufw|podman|open-vm|vgauth|rsync|n8n|ollama|openclaw"`

```
postfix-resolvconf.path               disabled
firewalld.service                     enabled        <- INACTIVO pero enabled
n8n.service                           disabled       <- legacy, ver 1.6
ollama.service                        disabled
open-vm-tools.service                 enabled        <- INACTIVO condition unmet
openclaw{,-agents}.service            disabled
podman-*.service                      enabled (auto-update, clean-transient, restart, podman)
postfix.service                       enabled        <- INACTIVO condition unmet
postfix@.service                      indirect
rsync.service                         enabled        <- INACTIVO condition unmet
ufw.service                           enabled
vgauth.service                        enabled        <- INACTIVO condition unmet
podman.socket                         enabled
podman-auto-update.timer              enabled
```

### 1.3 `systemctl status postfix` + `ls -l /etc/postfix/main.cf`

```
○ postfix.service - Postfix MTA
  Loaded: loaded (/usr/lib/systemd/system/postfix.service; enabled; preset: enabled)
  Active: inactive (dead)
  Condition: start condition unmet at 2026-08-29 04:37:09 UTC

ls: cannot access '/etc/postfix/main.cf': No such file or directory
/etc/postfix/ total 116:
  dynamicmaps.cf, main.cf.proto (27460), master.cf, master.cf.proto, post-install, postfix-files etc.
  -> main.cf faltante, solo main.cf.proto. Documentado.
  postfix@-.service: loaded failed (exit-code) since 2026-08-29, enabled-runtime
```

### 1.4 `systemctl status firewalld` + `ufw status`

```
○ firewalld.service - dynamic firewall daemon
  Loaded: loaded (...; enabled; preset: enabled)
  Active: inactive (dead)  Docs: man:firewalld(1)

ufw status -> Status: active
  [1] 41641/udp  ALLOW Anywhere
  [2] 22        ALLOW 100.64.0.0/10
  [3] 80/tcp    ALLOW Anywhere
  [4] 443/tcp   ALLOW Anywhere
  [5] 5353/udp  DENY Anywhere
  [6] 11434     ALLOW 172.17.0.0/16
  [7] 11434/tcp ALLOW 172.18.0.0/16
  [8-9] Anywhere on eth0 <-> docker0 ALLOW FWD
  [10] 8020/tcp ALLOW 172.18.0.0/16  # Mission Bridge Canvas from Docker
  [11] 22/tcp  ALLOW 93.156.217.35  # current-admin-session
  [12] 3389/tcp DENY Anywhere  # RDP disabled - Tailnet only
  [13] 631/tcp  DENY Anywhere  # CUPS local only
  [14] 3456/tcp ALLOW 172.16.0.0/12 # n8n callback -> portfolio dev
  [15-18] v6 equivalentes, [19-22] FWD y DENY v6
  firewall-cmd --list-all -> FirewallD is not running
```

### 1.5 `systemctl status podman.socket podman.service` + `podman ps`

```
● podman.socket - Podman API Socket
  Loaded: loaded (...; enabled; preset: enabled)
  Active: active (listening) since 2026-08-22 06:07:15, Listen: /run/podman/podman.sock
○ podman.service - Podman API Service
  Loaded: loaded (...; enabled)
  Active: inactive (dead) since 2026-08-22 06:07:23 (7.459s), TriggeredBy: podman.socket
podman ps ->  CONTAINER ID  IMAGE  COMMAND  CREATED  STATUS  PORTS  NAMES  (vacía)
which podman -> /usr/bin/podman
```

### 1.6 `systemctl status open-vm-tools vgauth` + `systemctl status rsync`

```
○ open-vm-tools.service - Service for VMs hosted on VMware
  Loaded: loaded (...; enabled)  Active: inactive (dead)  Condition: start condition unmet at 2026-08-22

○ vgauth.service - Auth service for VMs hosted on VMware
  Loaded: loaded (...; enabled)  Active: inactive (dead)  Condition: start condition unmet

○ rsync.service - fast remote file copy program daemon
  Loaded: loaded (...; enabled)  Active: inactive (dead)  Condition: start condition unmet (PathExists=/etc/rsyncd.conf)
rsync.service  enabled  enabled  (único, no socket)
```

### 1.7 `systemctl --user list-units --type=service` y `list-unit-files`

```
UNIT                         ACTIVE SUB     DESCRIPTION
1mcp.service                 active running 1MCP Server (secure localhost)
dbus.service                 active running D-Bus User Message Bus
duartec-static-sites.service active running Duartec static sites bridge
openclaw-gateway.service     active running OpenClaw Gateway (v2026.9.1)
trading-freqtrade.service    active running Trading Freqtrade demo runtime
trading-streamlit.service    active running Trading Streamlit console
# 6 loaded active

User unit-files disabled legacy (14 servicios):
  duartec-healthcheck.service, duartec-whisper.service, llama-cpp.service,
  mission-bridge-8000.service, mission-bridge.service,
  ollama-docker-proxy.service, openclaw-rescue-gateway.service,
  podman-*.service (auto-update, kube@, restart, podman), systemd-tmpfiles-setup,
  telegram-bot.service, trading-bot-loop.service
  + sockets/timers: openclaw-rescue-gateway.socket, podman.socket, snapd.session-agent.socket,
    openclaw-telegram-watchdog.timer, podman-auto-update.timer, systemd-tmpfiles-clean.timer
Enabled user: 1mcp, duartec-static-sites, openclaw-gateway, session-migration,
  trading-freqtrade, trading-streamlit, sockets dirmngr/gpg-agent/keyboxd/pk-debconf,
  timers duartec-healthcheck, launchpadlib-cache-clean, n8n-update (16 total)
```

### 1.8 `ss -lntup | grep -E "4173|8090|8082|8443|9443"`

```
tcp LISTEN 127.0.0.1:4173  users:(("MainThread",pid=3695217,fd=21))   # VITE huérfano E
tcp LISTEN 0.0.0.0:3003   users:(("next-server (v1",pid=4173581,fd=22)) # NEXT worktree G - NO TOCAR
tcp LISTEN 100.103.134.102:9443 / 8443 (Tailscale), [fd7a:...]:8443/9443
tcp LISTEN *:8090
```

### 1.9 `ps aux --sort=-%mem | head -20` + `ps aux | grep -E "vite|next-server.*3003"`

```
vite huérfano:
  ubuntu 3695204  npm exec vite preview --port 4173 (Sl, 2026-08-23 00:00)
  ubuntu 3695216  sh -c 'vite' preview --port 4173 (S)
  ubuntu 3695217  node .../vite/bin/vite.js preview --port 4173 (Sl, 0:07)
next-server worktree G:
  ubuntu 4173505 pnpm dev --hostname 0.0.0.0 -p 3003
  ubuntu 4173516 sh -c pnpm dev:webpack ...
  ubuntu 4173550 sh -c node scripts/clear-next-lock.mjs && cross-env NEXT_DISABLE_TURBOPACK...
  ubuntu 4173558 cross-env.js ...
  ubuntu 4173570 node next dev --webpack --hostname 0.0.0.0 -p 3003
  ubuntu 4173581 next-server (v16.2.12) Sl 7:51 (port 3003)
  ubuntu 4173615 esbuild --service=0.28.1
```

### 1.10 `systemctl list-unit-files --state=enabled | head -40` + filtrado

```
110-118 enabled (varía con podman/firewalld etc). Incluye:
firewalld.service enabled, open-vm-tools.service enabled, podman-*.service/socket/timer enabled,
postfix.service enabled, rsync.service enabled, ufw.service enabled, vgauth.service enabled
-> legacy files n8n/ollama/openclaw NO en enabled (disabled correctamente)
```

### 1.11 Legacy files existencia

```
-rw-r--r-- /etc/systemd/system/n8n.service (547, 2026-02-23)          disabled
-rw-r--r-- /etc/systemd/system/ollama.service (520, 2026-04-26)       disabled + override.conf
-rw-r--r-- /etc/systemd/system/openclaw.service (380, 2026-04-24)     disabled
-rw-r--r-- /etc/systemd/system/openclaw-agents.service (214, 2026-04-24) disabled
# Verificados disabled, presentes en disco. NO borrar en esta tanda (G para Tanda 5/6).
```

### 1.12 `sudo ufw status numbered` + `sudo firewall-cmd --list-all`

```
ufw numbered: 22 reglas (ver 1.4) -> activas, coherentes con Docker y Tailscale
firewall-cmd --list-all -> FirewallD is not running (vacío, default)
=> Decisión: ufw con reglas, firewalld vacío -> deshabilitar firewalld (E)
```

---

## 2) Limpieza quirúrgica (solo D/E verificados, G no tocar)

**Política:** No `apt purge`, no `rm /etc/systemd/system/*.service`. Solo `disable --now` y `kill` huérfano. Rollback = `enable --now` o recrear proceso.

### 2.1 postfix sin main.cf (D)

**Pre:** `postfix.service` enabled, inactive dead, `main.cf` faltante, `postfix@-.service` failed `enabled-runtime`.

```bash
# Verificación
systemctl status postfix@-.service 2>&1 | head -10
systemctl list-units | grep postfix
sudo systemctl disable --now postfix@-.service 2>&1 | head -5
# exit code: 0 (silencioso, ya estaba indirect)

sudo systemctl disable --now postfix.service 2>&1 | head -5
# Synchronizing state ... disable postfix
# Removed "/etc/systemd/system/multi-user.target.wants/postfix.service".
# exit code: 0

systemctl is-enabled postfix.service postfix@-.service 2>&1
# postfix.service: disabled
# postfix@-.service: enabled-runtime (template indirect, permanece pero sin symlink)
# postfix: disabled

systemctl reset-failed postfix@-.service 2>&1 | head -5
systemctl --failed  # 0 units
ls -l /etc/postfix/main.cf  # ls: cannot access ... No such file (esperado, documentado)
```

**Resultado:** `postfix.service` → **disabled**, `postfix@-.service` limpiado de `failed` (0 failed). `main.cf` sigue faltante (no purgado, deja rastro para diagnóstico). Spam `journalctl` persiste porque `cron` invoca `/usr/sbin/sendmail` directo (no servicio), ver 2.8 y post-check.

**Rollback:**

```bash
sudo systemctl enable --now postfix.service
# si se restaura main.cf: sudo cp /etc/postfix/main.cf.proto /etc/postfix/main.cf  # o restaurar desde backup
sudo systemctl status postfix@-.service
sudo systemctl reset-failed
```

### 2.2 firewalld vs ufw (E)

**Pre:** Ambos `enabled`, `ufw.service` active con 22 reglas, `firewalld.service` inactive dead, `FirewallD is not running`.

```bash
sudo ufw status numbered 2>&1 | head -30   # 22 reglas (ver 1.4)
sudo firewall-cmd --list-all 2>&1 | head -30  # FirewallD is not running

sudo systemctl disable --now firewalld 2>&1 | head -5
# Removed "/etc/systemd/system/multi-user.target.wants/firewalld.service".
# Removed "/etc/systemd/system/dbus-org.fedoraproject.FirewallD1.service".
# exit code: 0

systemctl is-enabled firewalld  # disabled
systemctl status firewalld | head -10  # disabled; inactive (dead)
```

**Resultado:** `firewalld.service` → **disabled**, muerto. `ufw` permanece `active` como único firewall. Se documenta que ambos estaban `enabled` y se optó por `ufw` porque tiene reglas y `firewalld` estaba vacío.

**Rollback:**

```bash
sudo systemctl enable --now firewalld
sudo firewall-cmd --list-all
sudo ufw status numbered
```

### 2.3 podman (E)

**Pre:** `podman.socket` active listening, `podman.service` inactive dead, `podman ps` vacío, timers `podman-auto-update.timer` active waiting.

```bash
sudo systemctl disable --now podman.socket podman.service 2>&1 | head -10
# Removed "/etc/systemd/system/default.target.wants/podman.service".
# Removed "/etc/systemd/system/sockets.target.wants/podman.socket".
# Disabling 'podman.service', but its triggering units are still active: podman.socket

sudo systemctl disable --now podman-auto-update.timer 2>&1 | head -5
# Removed "/etc/systemd/system/timers.target.wants/podman-auto-update.timer".
sudo systemctl disable --now podman-auto-update.service 2>&1 | head -5
# Removed "/etc/systemd/system/default.target.wants/podman-auto-update.service".

sudo systemctl stop podman.socket 2>&1 | head -5  # necesario porque disable no hizo stop inmediato
systemctl status podman.socket  # disabled; inactive (dead) Closed podman.socket
systemctl is-enabled podman.socket podman.service podman-auto-update.timer  # disabled disabled disabled
podman ps  # CONTAINER ... (vacía)
ls -l /run/podman/podman.sock  # srw-rw---- 1 root root 0 Aug 22 06:07 (socket file queda, no listening)
```

**Resultado:** `podman.socket` → **disabled + inactive (Closed)**, `podman.service` → **disabled**, `podman-auto-update.timer` → **disabled**, `podman-auto-update.service` → **disabled**. Quedan `podman-clean-transient.service` y `podman-restart.service` **enabled** (intencional, no purgar paquete, solo sockets/timers huérfanos).

**Rollback:**

```bash
sudo systemctl enable --now podman.socket
sudo systemctl enable --now podman.service
sudo systemctl enable --now podman-auto-update.timer
sudo systemctl enable --now podman-auto-update.service
systemctl status podman.socket
```

### 2.4 open-vm-tools / vgauth (D, Oracle ARM no VMware)

```bash
sudo systemctl disable --now open-vm-tools vgauth 2>&1 | head -10
# Removed "/etc/systemd/system/vmtoolsd.service".
# Removed "/etc/systemd/system/open-vm-tools.service.requires/vgauth.service".
# Removed "/etc/systemd/system/multi-user.target.wants/open-vm-tools.service".
# exit code: 0

systemctl is-enabled open-vm-tools vgauth  # disabled disabled
systemctl status open-vm-tools vgauth | head -20  # disabled; inactive (dead)
```

**Rollback:**

```bash
sudo systemctl enable --now open-vm-tools
sudo systemctl enable --now vgauth
```

### 2.5 rsync.service enabled-inactive (D)

**Pre:** `rsync.service` enabled pero `ConditionPathExists=/etc/rsyncd.conf` → inactive dead.

```bash
cat /usr/lib/systemd/system/rsync.service | head -30  # ConditionPathExists=/etc/rsyncd.conf
systemctl list-units | grep rsync  # vacío (no activo)
sudo systemctl disable rsync.service 2>&1 | head -5
# Removed "/etc/systemd/system/multi-user.target.wants/rsync.service".
systemctl is-enabled rsync.service  # disabled
systemctl status rsync | head -10  # disabled; inactive (dead)
```

**Rollback:**

```bash
sudo systemctl enable rsync.service
# si se necesita daemon: sudo touch /etc/rsyncd.conf && sudo systemctl start rsync
```

### 2.6 units legacy disabled files (G — NO borrar, solo documentar)

```bash
ls -l /etc/systemd/system/n8n.service /etc/systemd/system/ollama.service /etc/systemd/system/openclaw*.service
# -rw-r--r-- n8n.service 547 Feb 23 2026
# -rw-r--r-- ollama.service 520 Apr 26 19:18 (+ override.conf)
# -rw-r--r-- openclaw-agents.service 214 Apr 24 16:04
# -rw-r--r-- openclaw.service 380 Apr 24 12:33
systemctl is-enabled n8n.service ollama.service openclaw.service openclaw-agents.service
# disabled disabled disabled disabled
systemctl status n8n.service ollama.service openclaw.service openclaw-agents.service | head -40
# todos inactive (dead), disabled
systemctl list-unit-files --state=enabled | grep -E "n8n|ollama|openclaw"  # vacío -> correcto
```

**Acción:** **Ninguna** — solo asegura `disabled`, deja archivos para **Tanda 5/6** (borrado tras validación). No `rm`.

**Rollback (si se quisiera re-activar legacy):**

```bash
sudo systemctl enable --now n8n.service
sudo systemctl enable --now ollama.service
sudo systemctl enable --now openclaw.service
```

### 2.7 user legacy units (G — solo documentar, no borrar)

```
20 disabled legacy (user):
  duartec-healthcheck.service, duartec-whisper.service, llama-cpp.service,
  mission-bridge-8000.service, mission-bridge.service,
  ollama-docker-proxy.service, openclaw-rescue-gateway.service,
  podman-auto-update.service, podman-kube@.service, podman-restart.service,
  podman.service, systemd-tmpfiles-setup.service, telegram-bot.service, trading-bot-loop.service,
  + sockets: openclaw-rescue-gateway.socket, podman.socket, snapd.session-agent.socket,
  + timers: openclaw-telegram-watchdog.timer, podman-auto-update.timer, systemd-tmpfiles-clean.timer

Enabled user activos (G, NO TOCAR):
  1mcp.service, duartec-static-sites.service, openclaw-gateway.service,
  trading-freqtrade.service, trading-streamlit.service (todos active running)
```

**Acción:** **Ninguna** — documentado. Archivos en `~/.config/systemd/user/` permanecen para limpieza futura.

### 2.8 vite :4173 huérfano (E)

**Pre:** `vite preview --port 4173` manual sin unit, `127.0.0.1:4173`, pids 3695204→3695216→3695217.

```bash
ps aux | grep -E "vite.*4173" | grep -v grep
# ubuntu 3695204 npm exec vite preview --port 4173 (Sl)
# ubuntu 3695216 sh -c 'vite' preview --port 4173 (S)
# ubuntu 3695217 node .../vite/bin/vite.js preview --port 4173 (Sl)

ss -lntup | grep 4173
# tcp LISTEN 0 511 127.0.0.1:4173 users:(("MainThread",pid=3695217,fd=21))

kill 3695217 2>&1 | head -5  # exit 0
sleep 2
ps aux | grep -E "vite.*4173" | grep -v grep  # vacío
ss -lntup | grep 4173  # vacío -> 4173 vacío - OK
ps -ef | grep -E "3695204|3695216|3695217" | grep -v grep  # vacío -> padres también terminaron en cascada

# Verificación G intacto:
ps aux | grep "next-server.*3003" | grep -v grep
# ... next-server (v16.2.12) pid 4173581 Sl 7:51
ss -lntup | grep 3003
# tcp LISTEN 0 511 0.0.0.0:3003 users:(("next-server (v1",pid=4173581,fd=22))  # INTACTO
pgrep -a vite  # vacío - OK
```

**Resultado:** vite huérfano **eliminado**, puerto 4173 liberado, next-server :3003 **no tocado** (worktree).

**Rollback:**

```bash
# recrear vite huérfano (si se necesitara):
cd /home/ubuntu/apps/duartec-hub && npm exec vite preview --port 4173 &
# o: npx vite preview --port 4173 --host 127.0.0.1
# verificar: ss -lntup | grep 4173
```

### 2.9 G no tocados (verificado intactos)

```
api-stub.service           active running (MainThread node /srv/apps/api-service/server.js, 6.6M)
mission-bridge.service     active running (python3 -u server.py, 1.0G)
portfolio.service          active running (next-server v16.2.11, 174M)
caddy.service              active running
docker.service             active running
containerd.service         active running
user: 1mcp, duartec-static-sites, openclaw-gateway, trading-freqtrade, trading-streamlit -> active running
timers: CNMV cron 15 7 * * * daily_ingest.sh, weekly-mail 0 9 * * 0, api_watchdog * * * * *
 -> TODOS active, no tocados
```

---

## 3) Post-check validación

### 3.1 `systemctl --failed`

```
UNIT LOAD ACTIVE SUB DESCRIPTION
0 loaded units listed.
# antes había 1 failed (postfix@-.service), ahora 0 tras reset-failed. OK.
```

### 3.2 `journalctl -p err --since "5 min ago" --no-pager | head -30`

```
Sep 06 02:23:01 kiri-vnic postfix/sendmail[3899101]: fatal: open /etc/postfix/main.cf: No such file or directory
Sep 06 02:24:01 kiri-vnic postfix/sendmail[3900697]: fatal: ...
Sep 06 02:25:01 kiri-vnic postfix/sendmail[3902435]: fatal: ...
Sep 06 02:26:01 kiri-vnic postfix/sendmail[3905367]: fatal: ...
Sep 06 02:27:02 kiri-vnic postfix/sendmail[3909363]: fatal: ...
# Persiste cada minuto. Causa: cron.service -> /usr/sbin/sendmail -FCronDaemon -i -B8BITMIME -oem ubuntu
# _SYSTEMD_UNIT=cron.service, _COMM=sendmail, _CMDLINE=/usr/sbin/sendmail -FCronDaemon ...
# Cron jobs: * * * * * /home/ubuntu/scripts/api_watchdog.sh (cada minuto genera mail)
# Disable postfix.service NO detiene sendmail binario; cron sigue intentando mail.
# Debe reducir postfix@ failure spam pero no el sendmail de cron. Fix futuro: MAILTO="" en crontab o silenciar output.
```

### 3.3 `ss -lntup | head -20` + filtrado

```
Netid ... ss -lntup | head -20 -> 127.0.0.1:19080, 127.0.0.1:3050, 127.0.0.1:3002, 127.0.0.1:3001/3000, 127.0.0.1:18080, Tailscale 9443/8443 etc.
ss -lntup | grep -E "4173|8090|8082|8443|9443|3003"
  tcp LISTEN 100.103.134.102:9443 / 8443, [fd7a:...]:8443/9443, 0.0.0.0:3003 (next-server), *:8090
  # 4173 ya NO aparece -> OK
  # 8090 (*) y 8443/9443 permanecen (Tailscale/caddy), 3003 intacto
```

### 3.4 `ps aux | grep -E "vite|postfix|firewalld|podman" | head -20`

```
# vacío -> ningún proceso vite/postfix/firewalld/podman corriendo (solo grep del propio comando)
ps aux --sort=-%mem | head -20 -> top: opencode (3.8-3.9%), next-server 2.4%, openclaw gateway 2.3%, codex, chromium, freqtrade, n8n, etc.
```

### 3.5 `systemctl list-unit-files --state=enabled | grep -E "postfix|firewalld|podman|vm-tools"`

```
podman-clean-transient.service  enabled enabled
podman-restart.service          enabled enabled
# Antes: firewalld, open-vm-tools, vgauth, postfix, podman.socket/service/timer etc. Ahora solo 2 podman auxiliares.
# Total enabled: 110 (antes ~118)
```

### 3.6 Verificación G + Docker

```
systemctl is-active api-stub mission-bridge portfolio caddy docker -> active active active active active
systemctl --user is-active 1mcp openclaw-gateway trading-freqtrade trading-streamlit -> active active active active
docker ps -q | wc -l -> 24
```

---

## 4) Rollback por cada acción

| Unit / Proceso                       | Comando deshabilitar (ejecutado)                                                                                                                          | Rollback `enable --now`                                                                                                                                                            |
| ------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **postfix.service**                  | `sudo systemctl disable --now postfix.service` <br> `sudo systemctl disable --now postfix@-.service` <br> `sudo systemctl reset-failed postfix@-.service` | `sudo systemctl enable --now postfix.service` <br> `sudo cp /etc/postfix/main.cf.proto /etc/postfix/main.cf` si se requiere main.cf <br> `sudo systemctl status postfix@-.service` |
| **postfix spam cron**                | No se tocó cron (solo servicio). Spam persiste vía `sendmail` de cron                                                                                     | `crontab -e` → añadir `MAILTO=""` al inicio o redirigir `* * * * * /home/ubuntu/scripts/api_watchdog.sh >/dev/null 2>&1`                                                           |
| **firewalld**                        | `sudo systemctl disable --now firewalld`                                                                                                                  | `sudo systemctl enable --now firewalld` <br> `sudo firewall-cmd --list-all` <br> `sudo ufw status numbered`                                                                        |
| **podman.socket/service**            | `sudo systemctl disable --now podman.socket podman.service` <br> `sudo systemctl stop podman.socket`                                                      | `sudo systemctl enable --now podman.socket` <br> `sudo systemctl enable --now podman.service`                                                                                      |
| **podman-auto-update**               | `sudo systemctl disable --now podman-auto-update.timer` <br> `sudo systemctl disable --now podman-auto-update.service`                                    | `sudo systemctl enable --now podman-auto-update.timer` <br> `sudo systemctl enable --now podman-auto-update.service`                                                               |
| **open-vm-tools**                    | `sudo systemctl disable --now open-vm-tools`                                                                                                              | `sudo systemctl enable --now open-vm-tools`                                                                                                                                        |
| **vgauth**                           | `sudo systemctl disable --now vgauth`                                                                                                                     | `sudo systemctl enable --now vgauth`                                                                                                                                               |
| **rsync.service**                    | `sudo systemctl disable rsync.service`                                                                                                                    | `sudo systemctl enable rsync.service`                                                                                                                                              |
| **vite :4173**                       | `kill 3695217` (cascade mató 3695204/3695216)                                                                                                             | `cd /home/ubuntu/apps/duartec-hub && npm exec vite preview --port 4173 &` <br> `ss -lntup                                                                                          | grep 4173` |
| **legacy files n8n/ollama/openclaw** | **No se hizo** `rm` — solo `is-enabled` check                                                                                                             | Si se borraran en Tanda 5/6: restaurar desde `~/infra-audit/backups-*` o git                                                                                                       |
| **user legacy units**                | **No se borraron** archivos                                                                                                                               | `systemctl --user enable ...` según lista 2.7                                                                                                                                      |

> **No se ejecutó** `apt purge postfix firewalld podman open-vm-tools` ni `rm /etc/systemd/system/*.service` en esta tanda.

---

## 5) Reporte ejecutivo

### Qué se deshabilitó (6 familias, 10 units)

1. **postfix.service** (enabled → disabled, inactive) + `postfix@-.service` failed limpiado. `main.cf` faltante dejado documentado.
2. **firewalld.service** (enabled active dead → disabled inactive dead). `ufw` queda como único firewall.
3. **podman.socket** (enabled active listening → disabled inactive Closed) + **podman.service** (enabled → disabled) + **podman-auto-update.timer** (enabled active waiting → disabled) + **podman-auto-update.service** (enabled → disabled).
4. **open-vm-tools.service** (enabled → disabled) — Oracle ARM no VMware.
5. **vgauth.service** (enabled → disabled).
6. **rsync.service** (enabled → disabled) — `ConditionPathExists=/etc/rsyncd.conf` no existe.
7. **vite :4173** huérfano (pid 3695217) → `kill`, puerto liberado. Padres 3695204/3695216 terminados en cascada.

### Qué se dejó (con motivo G)

- **api-stub, trading demo (freqtrade/streamlit), CNMV cron, weekly-mail, api_watchdog, portfolio-mtm, mission-bridge, portfolio, caddy, docker, containerd, tailscaled, 1mcp, openclaw-gateway, duartec-static-sites, n8n-unified, email-store, ollama container** → **G** servicios productivos, NO TOCAR.
- **n8n.service, ollama.service, openclaw.service, openclaw-agents.service** → archivos legacy **disabled** ya, pero **NO borrados** (Tanda 5/6 tras validación).
- **~14 user legacy units** (`duartec-whisper`, `llama-cpp`, `mission-bridge{,-8000}`, `ollama-docker-proxy`, `openclaw-rescue-gateway`, `podman-*`, `telegram-bot`, `trading-bot-loop` etc.) → **disabled**, solo documentados, no borrados.
- **podman-clean-transient.service + podman-restart.service** → quedan **enabled** (auxiliares, no socket, no riesgo).
- **next-server :3003** worktree (`/srv/apps/web-duartec/.worktrees/nuevo-prototype-review-remote`, pnpm dev) → **G**, no matado.
- **ufw.service** → permanece **enabled active** con 22 reglas (único firewall).

### Validación

- `systemctl --failed` → **0** (antes 1 failed postfix@-.service).
- `journalctl -p err --since "5 min ago"` → **persiste** `postfix/sendmail: fatal: open /etc/postfix/main.cf` cada minuto vía `cron.service` (`/usr/sbin/sendmail -FCronDaemon`). **No es servicio** sino binario cron; el `disable postfix.service` evita reinicios systemd pero cron sigue. Apunta a `* * * * * /home/ubuntu/scripts/api_watchdog.sh` sin `MAILTO=""`.
- `ss -lntup` → **4173 vacío OK**, **3003 intacto**, 8090/*, 8443/9443 Tailscale OK.
- `ps aux | grep vite|postfix|firewalld|podman` → **vacío OK** (sin procesos huérfanos).
- `systemctl list-unit-files --state=enabled | grep postfix|firewalld|podman|vm-tools` → solo `podman-clean-transient` y `podman-restart` (de 9 → 2).
- Docker → **24** contenedores, sin afectación.

### Próximos riesgos y deuda para Tanda 4-6

1. **Cron mail spam no resuelto** por solo `disable`: cada minuto `api_watchdog.sh` genera mail y `sendmail` falla. Riesgo: log flood, I/O. **Mitigación Tanda 4:** añadir `MAILTO=""` en `crontab -l` de `ubuntu` o redirigir output a `/dev/null`, y/o `sudo apt purge postfix` solo cuando se confirme que ningún cron necesita mail local (verificar `bsdmainutils` daily).
2. **Podman socket file residual** `/run/podman/podman.sock` queda aunque systemd Closed. No escucha pero podría confundir herramientas. **Tanda 4:** `sudo rm -f /run/podman/podman.sock` si no se re-enable, y considerar `apt purge podman` si no hay uso futuro (ahora vacío).
3. **UFW única defensa:** con `firewalld` disabled, validar `ufw` reglas tras cada reboot y que `docker0` FWD `ALLOW` no abra de más. Riesgo bajo porque `firewalld` estaba vacío, pero documentar `ufw status numbered` en runbook.
4. **Legacy files en disco:** 4 files `/etc/systemd/system/n8n.service|ollama.service|openclaw*.service` + ~14 user units siguen ocupando systemd. No causan carga (disabled) pero confunden `systemctl`. **Tanda 5/6:** `sudo rm` + `systemctl daemon-reload` tras validar 7 días sin referencia (hacer backup en `~/infra-audit/backups-*`).
5. **Vite 4173 podría resucitar:** si hay `pm2`, `npm run preview` en `~/.config/autostart` o `systemd` user timer que lo relance, volverá. **Tanda 4:** `grep -r "4173|vite preview" ~/ ~/.config  /etc/cron*` y `ps aux` post-reboot.
6. **rsync condición:** si se crea `/etc/rsyncd.conf` sin querer, el servicio disabled no arrancará. No riesgo, pero documentar que está **disabled** intencionalmente (no es socket).
7. **Open-vm-tools purge futuro:** ahora solo `disable`; en Oracle no aporta. **Tanda 5:** evaluar `apt purge open-vm-tools` para reducir superficie.

---

## Anexos — Comandos exactos ejecutados (copiar/pegar para auditoría)

```bash
# Pre-check (solo lectura, ver raw log)
systemctl list-units --type=service --state=running | head -30
systemctl list-unit-files | grep -E "postfix|firewalld|ufw|podman|open-vm|vgauth|rsync|n8n\.service|ollama\.service|openclaw"
systemctl status postfix 2>&1 | head -20; ls -l /etc/postfix/main.cf 2>&1
systemctl status firewalld 2>&1 | head -10; ufw status 2>&1 | head -20
systemctl status podman.socket podman.service 2>&1 | head -20; podman ps 2>&1 | head -10
systemctl status open-vm-tools vgauth 2>&1 | head -20; systemctl status rsync 2>&1 | head -10
systemctl --user list-units --type=service 2>&1 | head -30
systemctl --user list-unit-files 2>&1 | head -50
ss -lntup | grep -E "4173|8090|8082|8443|9443" | head -15
ps aux --sort=-%mem | head -20; ps aux | grep -E "vite|next-server.*3003" | head -10
systemctl list-unit-files --state=enabled | head -40
ls -l /etc/systemd/system/n8n.service /etc/systemd/system/ollama.service /etc/systemd/system/openclaw*.service 2>&1 | head -20
sudo ufw status numbered 2>&1 | head -30; sudo firewall-cmd --list-all 2>&1 | head -30

# Limpieza (solo D/E)
sudo systemctl disable --now postfix@-.service 2>&1 | head -5
sudo systemctl disable --now postfix.service 2>&1 | head -5
sudo systemctl disable --now firewalld 2>&1 | head -5
sudo systemctl disable --now podman.socket podman.service 2>&1 | head -5
sudo systemctl disable --now podman-auto-update.timer 2>&1 | head -5
sudo systemctl disable --now podman-auto-update.service 2>&1 | head -5
sudo systemctl stop podman.socket 2>&1 | head -5
sudo systemctl disable --now open-vm-tools vgauth 2>&1 | head -5
sudo systemctl disable rsync.service 2>&1 | head -5
ps aux | grep "vite.*4173"  # verificar pid
kill 3695217  # vite MainThread
sleep 2; ss -lntup | grep 4173; ps aux | grep vite

# Post-check
systemctl --failed
journalctl -p err --since "5 min ago" --no-pager | head -30
ss -lntup | head -20
ps aux | grep -E "vite|postfix|firewalld|podman" | head -20
systemctl list-unit-files --state=enabled | grep -E "postfix|firewalld|podman|vm-tools"
```

**Evidencia guardada:** `~/infra-audit/tanda3-precheck-raw.log`, este `tanda3-host-legacy.md`, y salida de cada `systemctl disable --now | head -5`.

**No se ejecutó:** `apt purge`, `rm /etc/systemd/system/*.service`, `docker rm/stop`, `ufw disable`, `kill next-server`.

---

_Fin Tanda 3 — Host legacy quirúrgico completo. Próxima Tanda: cron MAILTO fix + podman purge evaluación + borrado legacy files post-validación._
