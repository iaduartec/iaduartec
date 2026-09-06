# Pendientes G — timers / cron / demo — kiri-vnic

**Host:** kiri-vnic | **Fecha audit:** 2026-09-06 03:01 UTC | **Modo:** solo evidencia, sin modificar  
**Contenedores vistos:** 15 activos (docker ps 2026-09-06 03:01) — 24 declarados incluye stack InsForge/Caddy/n8n/OLLama; lista completa infra aparte.

---

## 1) trading-freqtrade / trading-streamlit (G, demo OKX)

### trading-freqtrade.service
- **Unit:** `/home/ubuntu/.config/systemd/user/trading-freqtrade.service` — `enabled`, `active (running)` desde `2026-08-24 04:11:56 UTC` (1w5d), PID 540226 (uv) → 540266 python.
- **Exec:** `uv run freqtrade trade --userdir freqtrade/user_data --config configs/freqtrade/okx_demo.json --strategy-path freqtrade/user_data/strategies --logfile /tmp/freqtrade-demo.log`
- **WorkingDirectory:** `%h/projects/trading` → `/home/ubuntu/projects/trading`
- **Env:** `%h/projects/trading/deploy/systemd/trading.env` (ver abajo)
- **Restart:** always, RestartSec 5
- **Recursos:** 397 MB (peak 802 MB), 22 tasks, CPU 12h22m
- **Config OKX demo:** `dry_run:true`, `sandbox:true`, `key:"FILL_OKX_DEMO_KEY"` / secret/passphrase placeholders — **sin credenciales reales**, solo demo/paper. `pair_whitelist` 32 pares (AAVE...XRP), `trading_mode:futures isolated`, `api_server.enabled:true listen 127.0.0.1:18080` (grep okx_demo.json + tests/test_console.py).
- **Puerto:** `ss -lntup` → `127.0.0.1:18080` LISTEN users:(("freqtrade",pid=540266,fd=39)). `curl http://127.0.0.1:18080/api/v1/ping` → `{"status":"pong"}` 2026-09-06 03:02.
- **Log evidencia:** `/tmp/freqtrade-demo.log` 5.1 MB, `stat modify 2026-09-06 03:01:36`, heartbeat cada ~60s `freqtrade.worker INFO Bot heartbeat. PID=540266, state='RUNNING'` — último `03:01:06 Wallets synced. + 03:01:36 heartbeat`. `journalctl --user -u trading-freqtrade --since 7d` replica heartbeats + `Whitelist 32 pairs` cada reinicio (~02:39).
- **DB dry-run:** `~/projects/trading/tradesv3.dryrun.sqlite` 184 KB + shm/wal (4.1 MB wal active `2026-09-06 00:07`). Último trade registrado `sqlite3 trades` → `2026-06-08 19:15:02 XLM/USDT:USDT 42070 4215.41` — **sin trades desde 2026-06-08** (2.9 meses sin cierre). Indica demo inactivo en mercado o estrategia sin señal.
- **Consumidores:** 
  - `trading-streamlit` (FREQTRADE_API_URL=http://127.0.0.1:18080/api/v1) — vigente.
  - `trading-bot-loop.service` (disabled, inactive dead) → no consume actualmente. `verify_user_services.sh` lo lista como service requerido pero está dead.
  - `trading-research.timer/service` → **no existe** (`Unit could not be found`), timer marcado `trading-ollama.service` dependencia no encontrada (`Unit trading-ollama.service could not be found.`). LLM vía `TRADING_LLM_HOST=http://127.0.0.1:11434` (ollama container `duartec-ollama` Up 13h, port 11434 tcp).
  - No hay consumidores externos; tailscale no expone 18080.

**Veredicto:** **VIGENTE / DEMO**. No tocar. Demo sandbox sin riesgo monetario, dry_run true, heartbeat vigente. Limpiar creds placeholder no requerido. Recomendación G: documentar que wal crece (4 MB) y último trade 2026-06-08 — validar si estrategia esperada sigue activa o es solo keeper demo. Verificar si habilitar `trading-bot-loop`/`trading-research` está pendiente G.

### trading-streamlit.service
- **Unit:** `/home/ubuntu/.config/systemd/user/trading-streamlit.service` + drop-in `20-tailscale-bind.conf` (redefine ExecStart idéntica).
- **Estado:** `active running` desde `2026-09-02 23:51:33` (3d), PID 3894165→3894169, 242 MB, 17 tasks.
- **Exec:** `uv run streamlit run streamlit_app.py --server.address 127.0.0.1 --server.port 8501`
- **Puerto:** `127.0.0.1:8501` LISTEN streamlit pid 3894169. `curl -I 127.0.0.1:8501` → 200. `ss` confirma solo localhost, no tailscale directo. Tailscale 100.103.134.102:8502 es otro servicio (no streamlit).
- **Journal:** `Sep02 23:51:35 Uvicorn server started on 127.0.0.1:8501` — previo restart `Sep02 23:51:26 Stopped/Started` consumió 44min CPU antes. No errores posteriores.
- **App:** `streamlit_app.py` 215 KB, imports `trading_lab.console.auth operator_authorized`, `runtime load_demo_bot_state`, `service launch_async_llm_review` — consola demo. `trading.env` define `TRADING_STREAMLIT_SERVICE=trading-streamlit`, `TRADING_LLM_*`, `TRADING_ALLOWED_USER_LOGIN=iaduartec@github`.
- **Consumidores:** acceso vía localhost/Caddy/SSH tunnel; no expuesto público. Tailscale-bind drop-in no efectiva (sigue 127.0.0.1). Verificar si intención era `100.103.134.102`.

**Veredicto:** **VIGENTE / DEMO CONSOLE**. Mantener. Último uso 2026-09-06 03:01 activo. Ruta `~/projects/trading` existe, git status presente (mod 2026-09-05). No candidato a baja.

### trading.env (consumidores cruzados)
```
TRADING_LLM_ENABLED=true
TRADING_RESEARCH_MODE=full
TRADING_LLM_BACKEND=ollama
TRADING_LLM_MODEL=qwen2.5:7b-instruct-q5_K_S
TRADING_LLM_HOST=http://127.0.0.1:11434
TRADING_LLM_TIMEOUT_SECONDS=240.0
FREQTRADE_API_URL=http://127.0.0.1:18080/api/v1
TRADING_BOT_LOOP_SERVICE=trading-bot-loop
TRADING_RESEARCH_SERVICE=trading-research
TRADING_RESEARCH_TIMER=trading-research.timer
TRADING_STREAMLIT_SERVICE=trading-streamlit
TRADING_OLLAMA_SERVICE=trading-ollama
```

---

## 2) Cron / timers

### Crontab global (ubuntu)
```cron
0 9 * * 0 /srv/automation/scripts/duartec-weekly-mail-maintenance.sh >> /srv/logs/legacy-output/duartec-weekly-mail-maintenance.log 2>&1 # duartec-weekly-mail-maintenance
15 7 * * * /srv/automation/cnmv-pdmr/scripts/daily_ingest.sh >/dev/null 2>&1 # CNMV_PDMR_DAILY
* * * * * /home/ubuntu/scripts/api_watchdog.sh
0 */4 * * * /home/ubuntu/mission-bridge/scripts/sync-youtube-cookies.sh
```
`/etc/cron.d` aporta `backup-openclaw.sh 0 3 * * *`, `certbot 0 */12`, `e2scrub`, `sysstat sa1`. `systemctl list-timers` 16 timers (ver sección 3).

### a) weekly-mail-maintenance (D — legado)
- **Script:** `/srv/automation/scripts/duartec-weekly-mail-maintenance.sh` 7.7 KB, 0775, mtime 2026-02-11, `set -euo pipefail`, ACCOUNT=duartec, LOG_DIR=/home/ubuntu/output, requiere `himalaya jq`, `DUARTEC_EMAIL_PASSWORD` desde `.bashrc`, crea folders 00_ACCION_HOY…90_ARCHIVO, mueve INBOX→subs, archiva por año.
- **Cron:** domingo 09:00 semanal. Instalado `Sat Sep 5 02:15:07 2026` (crontab reload).
- **Log:** `/srv/logs/legacy-output/duartec-weekly-mail-maintenance.log` 1.2 KB, 0664, modify `2026-08-30 09:00:01`, contenido **29 líneas idénticas `ERROR: DUARTEC_EMAIL_PASSWORD is not set.`** (últimas del file) — todos los domingos fallan desde creación (Birth 2026-02-19). `grep syslog weekly-mail` vacío, journalctl cron no registra porque redirige a log.
- **Último uso:** `2026-08-30 09:00:01` (última ejecución cron registrada). Vigencia: **NO VIGENTE / ROTO**. Password no exportado en entorno cron (source .bashrc falla en cron non-interactive sin valor). D etiquetado legado — confirmar con owner si Duartec mail aún requiere mantenimiento o migró a otro sistema.
- **Consumidores:** ninguno; script no mueve nada. Solo genera log de error semanal.
- **Veredicto:** **Candidato a BAJA o FIX** — o bien exportar `DUARTEC_EMAIL_PASSWORD` en `/etc/default/` + `EnvironmentFile`, o eliminar cron si ya no se usa (D). Mientras tanto, silencia ruido.

### b) api_watchdog.sh (1/min, genera postfix)
- **Cron:** `* * * * * /home/ubuntu/scripts/api_watchdog.sh` — cada minuto, sin redirección stdout/stderr → cron intenta mail.
- **Script:** **NO EXISTE**. `ls ~/scripts` → `No such file or directory`. `find ~ /srv -name "*watchdog*"` solo retorna node_modules foreground-child watchdog. `stat` falla.
- **Syslog evidencia:** `grep syslog api_watchdog` → cada minuto `CRON[xxx]: (ubuntu) CMD (/home/ubuntu/scripts/api_watchdog.sh)` seguido de `cron[xxx]: sendmail: fatal: open /etc/postfix/main.cf: No such file or directory` y `postfix/sendmail[xxx]: fatal...` + `CRON: MAIL (mailed 60 bytes ... got status 0x004b)`. Muestra tail 2026-09-06 02:43→03:01 cada minuto.
- **Postfix:** `/etc/postfix/` contiene `main.cf.proto` (27 KB), `dynamicmaps.cf`, `master.cf` pero **falta `main.cf`** (solo proto). `grep -c "postfix.*No such file" /var/log/syslog` → **368** ocurrencias (última semana). Cada minuto genera 2 líneas fatal + 1 MAIL status.
- **Último uso:** `2026-09-06 03:01:01` — continuo cada minuto, vigente en cron pero roto.
- **Consumidores/efectos:** inunda syslog, genera carga cron+postfix fallida, sin watchdog real. No hay vigilancia de API operativa.
- **Veredicto:** **ROTO / GENERADOR DE RUIDO — ACCIÓN PRIORITARIA**. Opción A: eliminar línea crontab (`crontab -e` quitar). Opción B: restaurar script desde backup `~/.astra-migration-backup`, `backups-2026-09-06`, o re-crear en `/srv/automation/scripts/` y apuntar cron allí, + `touch /etc/postfix/main.cf` desde proto o instalar `postfix` correctamente y `MAILTO=""` o `>/dev/null` en cron para evitar postfix.

### c) daily_ingest.sh CNMV 07:15
- **Cron:** `15 7 * * * /srv/automation/cnmv-pdmr/scripts/daily_ingest.sh >/dev/null 2>&1` — diario 07:15 UTC (09:15 CEST).
- **Script:** `/srv/automation/cnmv-pdmr/scripts/daily_ingest.sh` 9.4 KB, 0775, mtime 2026-02-26, `set -euo pipefail`, lockfile `.daily_ingest.lock`, DB `CNMV_PDMR_DB_PATH=$SKILL_DIR/data/pdmr.sqlite`, LOG_DIR `logs`, `FROM_DATE=14 days ago`, `MAX_PAGES=20`, `TIMEOUT=90`, genera report `reports/insiders_<today>.md/.html` + `latest`, sync git opcional a `/home/ubuntu/portfolio`, telegram vía `openclaw message send`.
- **Logs:** `/srv/automation/cnmv-pdmr/logs/daily_2026-*.log` — 20 archivos, `ls -lh` muestra `daily_2026-09-05.log 1012 B`, `daily_2026-09-04.log 1011 B`... consecutivos.
- **Último run:** `2026-09-05 07:16:09` — `run_id 214, scraped 188, generated 393, inserted 40, updated 353, pdf_errors 0`. Log tail:
  ```
  [2026-09-05T07:15:01+00:00] start daily ingest from=2026-08-22 to=2026-09-05
  { run_id:214 ... inserted 40 ... }
  [2026-09-05T07:16:08+00:00] generate report output=.../insiders_2026-09-05.md latest=.../insiders_latest.md
  [2026-09-05T07:16:09+00:00] done
  ```
  Run anterior `2026-09-04 run_id 213 inserted 6 updated 416`.
- **Reports:** `insiders_latest.md` 3595 B, `modify 2026-09-05 07:16:09`, `reports/` 20 KB (20 reports). Header `# Informe Diario Insiders España (2026-09-05) - Fuente: CNMV (PDMR)`.
- **Consumidores:** report MD/HTML en `/srv/automation/cnmv-pdmr/reports/`, copia opcional a `/home/ubuntu/portfolio/insiders_latest.*` (detectado git remote si existe), telegram (si TARGET configurado). Cron silencioso `>/dev/null` — errores solo a log.
- **Syslog:** `grep CNMV syslog` vacío porque cron redirige a /dev/null, pero logs internos evidencian éxito diario sin gaps desde `2026-08-17` continuo.

**Veredicto:** **VIGENTE / SALUDABLE**. Mantener 07:15. Último uso 2026-09-05. No tocar. Único cron sano de los tres.

### Otros crons visibles
- `sync-youtube-cookies.sh 0 */4 * * *` → script existe `/home/ubuntu/mission-bridge/scripts/sync-youtube-cookies.sh` (cookie Chromium → LOG /home/ubuntu/mission-bridge/cookie-sync.log) — no parte de G pero vigente.
- `backup-openclaw.sh 0 3 * * *` (etc/cron.d) — vigente.

---

## 3) portfolio-mtm.timer (G, dry-run)

- **Timer:** `/etc/systemd/system/portfolio-mtm.timer` enabled, `Active waiting` desde `2026-08-24 00:46:30`, `OnCalendar=Mon..Fri *-*-* 22:00:00 UTC`, `Persistent=true`, `RandomizedDelaySec=300`, `Unit=portfolio-mtm.service`, `WantedBy=timers.target`. `systemctl list-timers` → NEXT `Mon 2026-09-07 22:01:53` (1d19h), LAST `Fri 2026-09-04 22:04:01`.
- **Service:** `/etc/systemd/system/portfolio-mtm.service` — `Type=oneshot`, `After=network-online.target portfolio.service`, `ExecStart=/usr/bin/curl --fail --silent --show-error -X POST "http://127.0.0.1:3001/api/shadow-portfolio/run?mode=dry-run" --header @/etc/default/portfolio-mtm.headers`. Comentario: *Dry-run is the only mode enabled... Moving to persist requires separate gate*.
- **Header secret:** `/etc/default/portfolio-mtm.headers` → `x-shadow-portfolio-cron-secret: 50cb8b2977cc8617dec5e19b8f1b96ce517f96e61c7a71fd7fc5a8dd28fda5ec` (root-owned header file per spec).
- **Dependencia:** `portfolio.service` (`Next.js production`, `WorkingDirectory /srv/apps/portfolio`, `PORT` env, `ExecStart next start -H 127.0.0.1 -p ${PORT}`, active running since `2026-09-06 00:34:56`, PID 3430881, 176 MB). Logs muestran `fetch failed ETIMEDOUT` frecuentes (Finnhub?) pero timer curl succeed.
- **Journal últimos 7d (14d rotado):**
  ```
  Sep02 22:04:49 curl {"status":"dry_run","mode":"dry-run","markDate":"2026-09-02","portfolios":0,"results":[],"evidence":{"status":"no_active_shadow_portfolios","activePortfolios":0,"observedPortfolios":0,"missingPricePortfolios":0}}
  Sep03 22:03:43 curl {"status":"dry_run","markDate":"2026-09-03","portfolios":0,...}
  Sep04 22:04:01 curl {"status":"dry_run","markDate":"2026-09-04","portfolios":0,...}
  ```
  3 ejecuciones consecutivas, todas `portfolios:0`, `no_active_shadow_portfolios`.
- **Scripts MTM:** `ls /srv/apps/portfolio/scripts/*mtm*` → `No such file or directory`. No hay script local mtm; lógica está en API `/api/shadow-portfolio/run` (Next.js route).
- **Consumidores:** ninguno productivo; dry-run no persiste. Gate a producción cerrado hasta revisión.

**Veredicto:** **VIGENTE / DRY-RUN / SIN PORTAFOLIOS**. Último uso 2026-09-04 22:04 UTC. Mantener timer; no promover a persist hasta que `activePortfolios>0`. Si G esperaba datos, investigar por qué `no_active_shadow_portfolios` (¿seed faltante?).

---

## 4) duartec-static-sites :19180 (B, ruta frágil)

- **Unit:** `/home/ubuntu/.config/systemd/user/duartec-static-sites.service` enabled, `active running` desde `2026-08-23 00:43:31` (2w0d), PID 1874350 node.
- **Cat:** `Description Duartec static sites bridge for Espacio and Restaurante`, `After=network.target`, `Type=simple`, `ExecStart=/home/ubuntu/.nvm/versions/node/v24.10.0/bin/node /home/ubuntu/output/playwright/hub-link-audit/static-sites-server.mjs`, `Restart=always`. Sin `WorkingDirectory` explícito → `systemctl --user show` → `WorkingDirectory=!/home/ubuntu` (home).
- **Script:** `/home/ubuntu/output/playwright/hub-link-audit/static-sites-server.mjs` 2559 B, 2026-08-23 00:43.
  ```js
  host='100.103.134.102'; port=19180
  roots={'/espacio':'/srv/apps/espacio','/restaurante':'/srv/apps/restaurante/dist'}
  server.listen(port, host, ()=>log...)
  ```
  Resuelve `/espacio`→`/srv/apps/espacio/index.html`, `/restaurante`→`/srv/apps/restaurante/dist/index.html`, serve 200 con cache-control, x-nosniff, referer fallback. No hay auth.
- **Filesystem evidencia:**
  - `ls -ld /home/ubuntu` drwxr-xr-x (WorkingDirectory por defecto — frágil, depende de home).
  - `ls /home/ubuntu/output/playwright` → `hub-link-audit/` only (no `~/output/playwright` genérico, solo ese subdir).
  - `ls /srv/apps/espacio` → Jekyll site 12 entries (AGENTS.md, Dockerfile, assets, aviso-legal.html) presente `2026-09-06 00:57`.
  - `ls /srv/apps/restaurante/dist` → Astro build 14 entries `index.html 100KB, _astro/, menu/, ...` `2026-09-05 19:24`.
  - Ambos roots existen y son legibles.
- **Red:** `ss -lntup | grep 19180` → `100.103.134.102:19180 LISTEN users:(("MainThread",pid=1874350,fd=21))` — bind solo tailscale IP, no localhost ni 0.0.0.0. `curl -I http://100.103.134.102:19180/espacio/` → `HTTP/1.1 200 OK cache-control:no-cache content-type:text/html`.
- **Journal:** `journalctl --user -u duartec-static-sites --since 7d` → `-- No entries --` (rotado desde `2026-08-23`, nota `journal has been rotated since unit was started`).
- **Ruta frágil:** `~/output/playwright/hub-link-audit/` es **output de Playwright**, no `~/srv` ni `/srv/apps`. Si se limpia `~/output`, se pierde el server JS aunque roots sigan en `/srv`. `hub-v2-fixed.png 1.9 MB` cohabita. WorkingDirectory `/home/ubuntu` implica relativos inestables; mover script a `/srv/apps/static-sites/` con `WorkingDirectory=/srv/apps/static-sites` sería robusto. Permisos 0644 dentro de home, node v24.10.0 fijo (versión pinned).
- **Consumidores:** Hub-link-audit manual (visual diff), Espacio/Restaurante preview interno vía Tailscale. No hay healthcheck; Caddy no proxy 19180 (solo 443→19080). Se accede directo por Tailscale.

**Veredicto:** **VIGENTE PERO FRÁGIL (B)**. Último uso continuo listening desde 2026-08-23, request 200 verificado 2026-09-06 03:01. No candidato a baja, sí a **REUBICACIÓN**: mover `static-sites-server.mjs` a `/srv/apps/duartec-static-sites/` + unit con `WorkingDirectory=/srv/apps/duartec-static-sites` + `ReadWritePaths` si aplica, y añadir `journal` output a `StandardOutput=journal`.

---

## Tabla resumen: item | evidencia | último uso | veredicto

| item | evidencia | último uso | veredicto |
|------|-----------|-------------|-----------|
| **trading-freqtrade** (G, demo OKX) | unit `enabled active running` 2026-08-24 04:11, PID540266 397 MB, `ss 127.0.0.1:18080` LISTEN, `curl ping→pong`, `dry_run:true sandbox:true FILL_*` 32 pares, `/tmp/freqtrade-demo.log` 5.1 MB heartbeat cada 60s, DB wal 4 MB | 2026-09-06 03:01:36 heartbeat `Wallets synced` | **VIGENTE DEMO — no tocar**. Sin riesgo monetario. Gap trades desde 2026-06-08 revisar estrategia. |
| **trading-streamlit** (G) | unit `active running` 2026-09-02 23:51, PID3894169 242 MB, `127.0.0.1:8501` 200 OK, `streamlit_app.py` 215 KB, env `FREQTRADE_API_URL 18080`, drop-in tailscale-bind no efectivo | 2026-09-06 03:01 activo | **VIGENTE CONSOLE — mantener**. |
| **weekly-mail-maintenance** (D) `0 9 * * 0` | script 7.7 KB `/srv/automation/scripts/duartec-*.sh`, cron dom 09:00, log `/srv/logs/legacy-output/duartec-weekly-mail-maintenance.log` 1.2 KB **29× `ERROR: DUARTEC_EMAIL_PASSWORD is not set.`**, mtime 2026-08-30 | 2026-08-30 09:00:01 (fallido) | **NO VIGENTE / ROTO — candidato baja D**. Fix password o eliminar cron. |
| **api_watchdog.sh** `* * * * *` genera postfix | cron cada minuto **sin script** (`/home/ubuntu/scripts` no existe), `syslog` cada minuto `CRON CMD + sendmail fatal open /etc/postfix/main.cf` , `/etc/postfix/main.cf` faltante (solo .proto), **368 fatals** en syslog | 2026-09-06 03:01:01 cada minuto | **ROTO / RUIDO — PRIORITARIO**. Eliminar cron o restaurar script + arreglar postfix/`MAILTO=""`. |
| **daily_ingest.sh CNMV** `15 7 * * *` | script 9.4 KB `/srv/automation/cnmv-pdmr/scripts/daily_ingest.sh`, 20 logs `daily_2026-*.log`, último `run_id 214 inserted 40 updated 353`, report `insiders_latest.md` 3595 B, `scraped 188 generated 393` | 2026-09-05 07:16:09 success | **VIGENTE SALUDABLE — mantener**. |
| **portfolio-mtm.timer** (G dry-run) `Mon..Fri 22:00 UTC` | timer enabled waiting NEXT 2026-09-07 22:01, service `curl POST 127.0.0.1:3001/api/shadow-portfolio/run?mode=dry-run header @/etc/default/portfolio-mtm.headers`, `portfolio.service` running, journal `dry_run portfolios:0 no_active_shadow_portfolios` Sep02-04 | 2026-09-04 22:04:01 dry_run 0 portfolios | **VIGENTE DRY-RUN — mantener, no promover**. Sin portafolios activos; gate persist cerrado. |
| **duartec-static-sites :19180** (B ruta frágil) | unit enabled running 2026-08-23 00:43 PID1874350, `ExecStart node ~/output/playwright/hub-link-audit/static-sites-server.mjs`, `WorkingDirectory=!/home/ubuntu`, `roots /srv/apps/espacio + /srv/apps/restaurante/dist` existen, `ss 100.103.134.102:19180` LISTEN, `curl /espacio/ →200` | 2026-09-06 03:01:56 listening 200 OK | **VIGENTE PERO FRÁGIL — REUBICAR**. Mover fuera de `~/output/playwright` a `/srv/apps` y fijar WorkingDirectory. |

---

### Notas host
- `~/projects/trading/.venv` presente, `uv.lock`, `trading-ollama` container `Uptime 13h` (11434), `trading-bot-loop disabled dead`, `trading-research.timer not found` — G pendiente decidir si reactivar.
- Postfix proto presente sugiere `apt install postfix` interrumpido; restaurar `cp /etc/postfix/main.cf.proto /etc/postfix/main.cf` + `systemctl restart postfix` solo si se mantiene watchdog con mail, sino `MAILTO=""` en crontab es más limpio.
- No se modificó nada — solo `mkdir -p ~/infra-audit` + escritura de este markdown (read-only audit).

*Evidencia cruda disponible en `~/infra-audit/raw/` y `syslog` 2026-09-06 exigida.*
