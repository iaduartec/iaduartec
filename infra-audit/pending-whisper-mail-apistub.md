# Auditoría pendientes G — kiri-vnic — whisper / mail-relay / api-stub
**Fecha:** 2026-09-06T03:02Z — host `kiri-vnic` (up 14d, 16 contenedores `docker ps`)
**Alcance:** Solo lectura. No se modificó nada. Comandos listados son reproducibles.
**Artefacto:** `~/infra-audit/pending-whisper-mail-apistub.md` + `/tmp/n8n.db` (copia sqlite n8n-unified)

---

## 1. duartec-local-whisper — E, 0 POSTs desde 2026-08-27 — CUARENTENA

### Evidencia cruda (comando → salida)

| Comando | Salida clave |
|---------|--------------|
| `docker ps --format "{{.Names}} {{.Status}} {{.Ports}}"` | `duartec-local-whisper Up 9 days (healthy) 5681/tcp` — **sin PortBinding host** (`{"5681/tcp":null}`) — solo `expose` interno |
| `docker inspect --format '{{json .NetworkSettings.Ports}}'` | `{"5681/tcp":null}` ; `HostConfig.PortBindings={}` |
| `docker inspect --format '{{json .State}}'` | `Image=duartec-voice-ai-whisper Created=2026-08-27T19:48:16Z StartedAt=2026-08-27T19:48:20Z Health=healthy FailingStreak=0` |
| `docker logs --tail 50` | Solo `GET /health 200` cada 15s (healthcheck). Cabecera única `Started server process [7] Uvicorn running on http://0.0.0.0:5681` — resto health |
| `docker logs | grep -c POST` | `0` — **confirma “0 POSTs desde 2026-08-27”** |
| `docker logs | grep -v health` | Vacío tras el arranque — sin `/transcribe`, sin errores |
| `docker stats --no-stream` | `0.13% CPU 14.39MiB / 2GiB (0.70%)` — límite `mem_limit: 2g cpus:1 pids:256` infrautilizado |
| `docker inspect --format '{{json .Config.Env}}'` | `LOCAL_WHISPER_MODEL=tiny LOCAL_WHISPER_PORT=5681 MAX_UPLOAD=26214400 MAX_CONCURRENCY=1 QUEUE_TIMEOUT=2 HF_HOME=/cache/huggingface` |
| `ss -lntup | grep 5681` | Sin listener host — `ss` solo muestra `127.0.0.1:19080, 5682` — whisper solo en `duartec-net` |
| Caddy `caddy/conf.d/apis.caddy:6` | `# Backends: whisper:5681, db-api:8080, mail-relay:8080` — ruta `handle @whisper_authorized { path /whisper* method POST header Tailscale-User-Login {$TAILSCALE_WHISPER_USER_LOGIN} } → uri strip_prefix /whisper reverse_proxy whisper:5681` + 405 si no POST + 401 si no Tailscale — **no expuesto sin auth** |
| `curl` host | `curl -s http://127.0.0.1:5681/` → timeout / no escucha (esperado: no binding) |
| `docker exec whisper python -c "urllib.request.urlopen('http://127.0.0.1:5681/health').read()"` | `{"ok":true,"model":"tiny"}` |
| `docker exec n8n-unified wget -qO- http://whisper:5681/health` | `{"ok":true,"model":"tiny"}` — también `http://duartec-local-whisper:5681/health` OK ; `curl` no existe en images slim |
| `docker exec whisper python ... /` | `404 Not Found` — solo `/health` y `/transcribe` existen |
| `local_whisper_server.py` | FastAPI `/health` + `POST /transcribe` (multipart `file` o raw body), semáforo `MAX_CONCURRENCY=1`, modelo `faster-whisper tiny` CPU int8, `language=es vad_filter=True beam_size=1`, límite 25 MB, puertos/boundaries validados. Sin auth interna (delega a Caddy). |
| `grep -r whisper ~/duartec-infra` | `docker-compose.yml:54 whisper → Dockerfile.whisper`, `Caddyfile` apis.caddy, `scripts/healthcheck.sh` + `update_stack.sh` — **ningún `/srv/apps/*`, `~/mission-bridge`, `/home/ubuntu/DUARTEC` referencia whisper** fuera de docker-infra |
| `grep -r whisper /srv/apps/portfolio /srv/apps/web-duartec ~/mission-bridge` | Sin resultados |
| `python3 sqlite /tmp/n8n.db` (copia de `n8n-unified:/home/node/.n8n/database.sqlite`, 36 MB, 32 workflows) | Workflows con `whisper:5681/transcribe` = 3: <br>• `kc208PLh3kml8a1J` **“Duartec Telegram Voz OpenClaw Polling Completo” active=1 updated 2026-06-06** → `POST http://whisper:5681/transcribe` (binaryData audio) tras `Telegram getFile → Download voice` <br>• `7mVRFDrhrAPMWKgN` “Duartec Mission Bridge (Webhook)” active=0 <br>• `mission-bridge-webhook` (polling) active=0 <br>— y `workflows/mission-bridge-webhook.json:481` repite la URL |
| `execution_entity` para `kc208PLh3kml8a1J` | `count(*)=0` — **0 ejecuciones en historial (158 totales: 56 success, 100 error, 2 crashed)** — `last=None`. El workflow de voz nunca ha corrido según DB recuperada (incluye `database.sqlite-wal` del 2026-09-06 05:01). |
| `workflows` activos totales | 17 activos de 32 — `kc208` es el único activo que consume whisper |
| `journalctl --since "7 days ago" | grep -i whisper` | Vacío |
| Caddy access `docker exec caddy cat /var/log/caddy/access.log | grep whisper` | Sin hits en ventana retenida (10 MB ×7) — cero `POST /whisper*` |

### ¿Quién lo consume?
- **Declarado:** Solo n8n workflow `Duartec Telegram Voz OpenClaw Polling Completo` (Telegram voz → whisper → prompt_text → routers email/work-order/calendar). Documentado como “E”.
- **Real:** Nadie desde 2026-08-27. 0 POSTs en logs del contenedor, 0 ejecuciones n8n, 0 accesos Caddy. La cadena Telegram→whisper es funcional (health OK vía `whisper:5681`) pero idle.

### Último uso
- **Logs contenedor:** Nunca (0 POST). Último arranque 2026-08-27T19:48:20Z, solo healthchecks desde entonces.
- **n8n executions:** Nunca para ese workflow.
- **Caddy:** Sin registro en las últimas rotaciones.

### Veredicto: **CUARENTENA** (no ELIMINAR directo)
- **Evidencia para mantenerlo vivo hoy:** Existe consumidor activo declarado (workflow `kc208` enabled). Borrar rompe la feature voz de Telegram — rollback requiere rebuild `faster-whisper` y descarga de modelo `tiny` (~150 MB cache en `./whisper_cache:/cache/huggingface`).
- **Evidencia para no mantenerlo indefinido:** 0 uso en 9 días, 0 ejecuciones, 14 MB reales vs 2 GB reservados, sin tráfico Tailnet. La propia tarea lo marca E (experimental).
- **Acción reversible propuesta (no ejecutada):** `docker compose stop whisper` + comentar `caddy/conf.d/apis.caddy` bloque whisper + dejar workflow n8n activo con `continueOnFail=true` (ya está) para medir errores 30 días. Si 0 errores de “whisper:5681 ENOTFOUND” → ELIMINAR. Si se necesita voz, `docker compose up -d --build whisper` restaura en <2 min. No borrar `whisper_cache` hasta ELIMINAR definitivo.

---

## 2. duartec-parts-mail-relay — G, “sin evidencia” — MANTENER

### Evidencia cruda

| Comando | Salida clave |
|---------|--------------|
| `docker ps` | `duartec-parts-mail-relay Up 3 days 8080/tcp` — `expose 8080`, sin binding host (`{"8080/tcp":null}`), `restart: unless-stopped`, `mem 512m cpus 0.5` |
| `docker inspect Image` | `duartec-voice-ai-mail-relay:latest sha256:ed3e1113e…70.4 MB Created 2026-09-02T23:53:02Z StartedAt 2026-09-02T23:53:13Z` — build `context: ./mail-relay` Dockerfile `EXPOSE 8080` |
| `docker logs --tail 50` | **0 líneas** (`wc -l 0`) — la app solo `print` en `requests.post revolut-parser` fallido; operación normal es silenciosa |
| `docker stats` | `0.01% CPU 8.363MiB / 512MiB` |
| `docker inspect Env` | `MAIL_*` desde `.env` + `MAIL_RELAY_READ_SECRET/MAIL_RELAY_SEND_SECRET` requeridos, `MAIL_MAX_REQUEST_BYTES=65536, MAIL_MAX_MAILBOX_MESSAGES=100, MAIL_MAX_MESSAGE_BYTES=5242880, MAIL_IO_TIMEOUT=20, MAX_CONCURRENT=4` |
| `docker exec ps aux` | `1 root python /app/app.py` |
| `docker exec python http.client GET /health` | `200 {"ok": true}` — igual desde n8n: `wget -qO- http://mail-relay:8080/health` → `{"ok": true}` |
| `cat mail-relay/app.py` | `ThreadingHTTPServer("0.0.0.0",8080)` — endpoints: `GET /health`, `GET /mail*`, `POST /search /thread /send` con `X-Duartec-Mail-Secret` HMAC, IMAP `imap.serviciodecorreo.es:993` user `sgomez@duartec.es`, SMTP `smtp.serviciodecorreo.es:465`, fetch con `RFC822.SIZE` guard, `BoundedSemaphore(4)`, forward opcional `http://n8n:5678/webhook/revolut-parser` |
| `grep -rn mail-relay ~/duartec-infra` | `docker-compose.yml:265 mail-relay build ./mail-relay`, `caddy/conf.d/apis.caddy:# mail-relay — SMTP relay + IMAP polling` + 3 `reverse_proxy mail-relay:8080`, `Caddyfile: /mail* → mail-relay:8080`, `db-api/app.py: {"name":"mail-relay","role":"mail processing","status":"online"}` |
| `caddy/conf.d/apis.caddy` detalle | `handle @mail_read_authorized { path /mail* method GET header Tailscale-User-Login {$TAILSCALE_MAIL_READ_USER_LOGIN} } → uri strip_prefix /mail reverse_proxy mail-relay:8080 header_up X-Duartec-Mail-Secret {$MAIL_RELAY_READ_SECRET}` + `search/thread POST` + `send POST` con `$MAIL_RELAY_SEND_SECRET` — **Tailnet-only con dos secretos distintos** |
| `grep -rn mail-relay /srv/apps` | Sin hits fuera de node_modules/pyc |
| `sqlite n8n.db: nodes LIKE '%mail-relay%'` | 3 workflows: `WQblBSQ0jzTPXgLb Duartec - Captura de partes` ( `http://mail-relay:8080/search` + `send`×2 ), `eTLrmG8ItS3nHYfD Duartec - Recordatorio fin de jornada` (send), `IslKhJpAxYKHgulI Duartec - Recordatorio multicanal` (send). `eTLrm active=0` (los otros no se consultaron active pero “Captura de partes” es workflow core). Backup `n8n-before-mission-alpha-bullish-preview-20260903.json` también referencia `mail-relay:8080/search|send`. |
| `execution_entity` para esos workflows | `count=0` para `eTLrm…` (otros con count 0 también en snapshot) — pero **esto no implica no uso**: el relay también es consumido fuera de n8n executions (dashboard y directo IMAP polling) |
| `docker exec caddy cat /var/log/caddy/access.log | grep mail` | **Evidencia de uso:** `GET /mail/health 200` dos veces: `2026-09-03T01:20:55Z` y `2026-09-05T01:36:49Z` (`host kiri-vnic.tail4b3cf6.ts.net:9444` referer `https://kiri-vnic.tail4b3cf6.ts.net:9444/dashboard/` Tailscale `iaduartec@github`) + `GET /data/emails/recent` (db-api) en misma ventana. Confirma que el dashboard via Caddy sí consulta el relay. |
| `ss -lntup | grep 8080` | Solo `127.0.0.1:8080` del `api-stub` host — **no hay colisión**: mail-relay/db-api solo `expose` sin publish, aislados en `duartec-net` |
| `journalctl --since 7 days | grep mail-relay` | Sin entries (normal: docker logs vacío) |

### ¿Quién lo consume?
- **Declarado (G):** n8n workflows de captura de partes y recordatorios (search/send). Además Caddy `/mail*` es consumido por el **dashboard** (`/dashboard` → fetch `/mail/health`).
- **Real (evidencia):** Caddy access log demuestra **uso el 2026-09-05** (hace <24 h). n8n DB muestra 0 executions en el snapshot, pero el relay está healthy y respondiendo; el IMAP polling es on-demand (no cron interno), por lo que la ausencia de logs n8n no es “sin evidencia”.

### Último uso
- **Caddy:** `2026-09-05T01:36:49Z GET /mail/health 200` (dashboard) — **último log 1 día atrás**.
- **Contenedor:** Health 200 ahora mismo; sin logs de error.

### Veredicto: **MANTENER**
- **Evidencia:** Servicio con tráfico tailnet reciente, necesario para IMAP/SMTP de `sgomez@duartec.es`, sin alternativa en `email-store` (éste es Node/MariaDB archive, no relay). Eliminar rompe `Captura de partes` y `mail/*` del dashboard. Coste 8 MB / 0.01% CPU, sin riesgo. La etiqueta “G sin evidencia” queda refutada por `apis.caddy` + Caddy access logs.
- **Mejora sugerida (no ejecutada):** Añadir logging estructurado en `mail-relay/app.py` (hoy silencioso) y métrica Caddy `handle /mail/health` para auditoría futura.

---

## 3. api-stub.service :8080 — G — ELIMINAR (previa CUARENTENA corta)

### Evidencia cruda

| Comando | Salida clave |
|---------|--------------|
| `systemctl status api-stub` | `Loaded enabled Active running since Sat 2026-08-22 06:07:15 UTC (2w0d) Main PID 1299 /home/ubuntu/.nvm/versions/node/v24.10.0/bin/node /srv/apps/api-service/server.js Memory 6.6M CPU 8.9s Restart=always` |
| `systemctl cat api-stub` | `After=network-online.target WorkingDirectory=/srv/apps/api-service Environment NODE_ENV=production HOST=127.0.0.1 PORT=8080 ExecStart=node server.js NoNewPrivileges PrivateTmp ProtectSystem=strict ReadWritePaths=/srv/apps/api-service /srv/logs` |
| `ss -lntup | grep 8080` | `127.0.0.1:8080 LISTEN MainThread pid 1299` — **solo localhost**, no `0.0.0.0`. `freqtrade` escucha aparte en `127.0.0.1:18080`. |
| `curl -s http://127.0.0.1:8080/health` | `{"status":"ok","service":"api-stub","ts":"2026-09-06T03:02:11.073Z"}` |
| `curl -s http://127.0.0.1:8080/` | `{"service":"api-stub","message":"API stub running on localhost only","endpoints":["/health"]}` |
| `curl -s http://127.0.0.1:8080/v1` | Idem anterior |
| `cat /srv/apps/api-service/server.js` | 28 líneas: `http.createServer` — solo `GET /health` y `GET /,/v1` → JSON estático, sin lógica, sin Caddy, sin auth. |
| `ls -la /srv/apps/api-service/` | `AGENTS.md package.json server.js compose/compose.yaml` — `package.json: {"name":"api-stub","description":"Local-only API stub for Caddy reverse proxy"}` — `compose.yaml: "127.0.0.1:8080:8080"` (no usado en prod, solo artefacto) |
| `grep -rn "api-stub|:8080" ~/duartec-infra/Caddyfile* /etc/caddy/Caddyfile` | Sin referencias a `api-stub` — los `8080` en Caddy son `db-api:8080` y `mail-relay:8080` **internos docker**, no `127.0.0.1:8080` host |
| `grep -rn 8080 ~/duartec-infra --exclude-dir=node_modules` | Solo `mail-relay/Dockerfile EXPOSE 8080`, `db-api/Dockerfile EXPOSE 8080`, `docker-compose.yml expose 8080` — **cero routing hacia api-stub** |
| `grep -rn "api-stub|127.0.0.1:8080" /srv/apps/* ~/mission-bridge /home/ubuntu/DUARTEC` | Solo hits en `node_modules/.pnpm` docs y el propio `api-stub` — **0 consumidores productivos** |
| `grep -rn api-stub ~/duartec-infra/ops/workspaces/inventory.json` | `systemd_units":["api-stub.service","caddy.service","tailscale-serve.service"]` — listado como unidad pero sin dependencias |
| `journalctl --since "7 days ago" -u api-stub` | `-- No entries --` (tras rotación) — `journalctl --since 7 days | grep api-stub` solo sudo `du -sh /tmp/systemd-private-...api-stub.service-*` |
| `cat /srv/logs/caddy/https-access.log` | `Permission denied` (caddy:caddy 750) — `docker caddy access.log` no contiene `api-stub` ni `:8080` host |
| `tailscale serve` config `scripts/tailscale-serve-apply.sh` | Rutas `/`, `/dashboard`, `/openclaw`, `/canvas`, `/api/n8n`, `:9443-9450` — **ninguna apunta a :8080** |
| Colisión 8080 | **No colisiona:** `ss` muestra host `127.0.0.1:8080` (api-stub) y docker `expose 8080` sin publish — redes distintas. `docker inspect db-api/mail-relay NetworkSettings.Ports {"8080/tcp":null}` |

### ¿Quién lo consume?
- **Nadie.** 0 referencias en Caddy host/docker, Tailscale serve, n8n workflows (0/32), dashboard, `/srv/apps/*`, `DUARTEC`. `AGENTS.md` en `/srv/apps/api-service` dice explícitamente “Do not infer a deployment target … from this directory name” — es un stub de ejemplo.

### Último uso
- **Logs:** Ninguno en 7 días. Único tráfico observable es el `curl` manual de esta auditoría.

### Veredicto: **ELIMINAR** (con cuarentena de 7 días si se exige ventana)
- **Evidencia:** Placeholder sin routing, sin consumidores, 2 semanas corriendo consumiendo 6.6 MB y un puerto localhost reservado sin propósito. Su existencia genera confusión con `db-api:8080`/`mail-relay:8080` (mismo puerto, distinta red) y aparece en `healthchecks` de `ops/workspaces/inventory.json` como `systemctl is-active api-stub.service` sin necesidad.
- **Acción reversible propuesta (no ejecutada):** `sudo systemctl disable --now api-stub && sudo rm /etc/systemd/system/api-stub.service && sudo systemctl daemon-reload` — mantener `/srv/apps/api-service/` en disco 7 días; si nadie reclama `127.0.0.1:8080`, borrar directorio o dejarlo como doc. Downgrade a **CUARENTENA** si el equipo prefiere `systemctl stop` sin `disable` una semana.

---

## Tabla resumen (máx. 100 líneas pedidas)

| Servicio | Evidencia uso | Último log | Consumidor | Veredicto |
|---|---|---|---|---|
| **duartec-local-whisper** `1681? 5681` `tiny` | `docker logs grep -c POST =0`; `health 200` cada 15 s solo; `ss` sin listener host; Caddy `/whisper* POST Tailscale-only` sin hits; `n8n.db` 1 workflow activo con `http://whisper:5681/transcribe` pero `execution count 0/158`; 0 refs en `/srv/apps`/`mission-bridge`/`DUARTEC` | `2026-08-27T19:48:16Z` arranque; último health `2026-09-06T03:02Z` (healthcheck) — **0 POST desde creación** | Solo declarado: n8n `Duartec Telegram Voz OpenClaw Polling Completo` (kc208, active=1) — **real: nadie** | **CUARENTENA** — stop 30 d, keep image+cache, si 0 errores n8n → ELIMINAR |
| **duartec-parts-mail-relay** `expose 8080` | `docker logs 0 líneas` (app silenciosa) pero `python http GET /health 200`; `docker exec caddy access.log GET /mail/health 200 2026-09-03 y 2026-09-05` via dashboard; `caddy/conf.d/apis.caddy` 3× `reverse_proxy mail-relay:8080` con `TAILSCALE_MAIL_*_LOGIN` + `X-Duartec-Mail-Secret`; `ss` no expone host | `2026-09-05T01:36:49Z GET /mail/health 200` (Caddy) — **<24 h** | n8n `Captura de partes` + `Recordatorio fin jornada/multicanal` (`mail-relay:8080/search|send`) y **dashboard** (`/mail/health` polling) — **uso real tailnet** | **MANTENER** — IMAP/SMTP `sgomez@duartec.es` productivo, 8 MB, sin alternativa |
| **api-stub.service** `127.0.0.1:8080` | `systemctl active 2w curl /health 200` pero `grep -r api-stub/Caddy/Tailscale/n8n` =0; `Caddy` solo proxya `db-api:8080`/`mail-relay:8080` internos; `journalctl -u api-stub --since 7d` vacío; `ss` `127.0.0.1:8080` aislado | Sin tráfico en 7 d (solo curl auditoría) | **Nadie** — 0 consumidores en host, docker, tailnet | **ELIMINAR** (o CUARENTENA 7 d `systemctl stop`) — stub sin routing ni función |

---

## Comandos de solo lectura ejecutados (reproducibles)

```bash
docker ps --format "{{.Names}} {{.Status}} {{.Ports}}" ; docker stats --no-stream --format "{{.Name}} {{.CPUPerc}} {{.MemUsage}}"
docker logs duartec-local-whisper --tail 50 2>&1 | tail -50 ; docker logs duartec-local-whisper 2>&1 | grep -c POST
docker inspect duartec-local-whisper --format '{{json .Config.Env}}' | tr ',' '\n' | head -40
docker inspect duartec-local-whisper --format '{{json .NetworkSettings.Ports}}' ; docker inspect duartec-local-whisper --format '{{json .HostConfig.PortBindings}}'
docker inspect duartec-local-whisper --format '{{json .State}}' | tr ',' '\n' | head -20
ss -lntup | grep -E "5681|8080|19080"
cat ~/duartec-infra/docker-compose.yml | grep -A30 "whisper:" ; cat ~/duartec-infra/Dockerfile.whisper ; cat ~/duartec-infra/local_whisper_server.py
grep -rn "whisper\|5681" ~/duartec-infra/ /etc/caddy/Caddyfile 2>&1 | grep -v ".pyc"
grep -r "whisper" /srv/apps/portfolio /srv/apps/web-duartec ~/mission-bridge 2>&1 | head -20
docker exec n8n-unified wget -qO- http://whisper:5681/health || docker exec duartec-local-whisper python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:5681/health',timeout=3).read().decode())"
docker cp n8n-unified:/home/node/.n8n/database.sqlite /tmp/n8n.db && python3 -c "import sqlite3; con=sqlite3.connect('/tmp/n8n.db'); ..."
journalctl --since "7 days ago" --no-pager | grep -i whisper | head -10

docker logs duartec-parts-mail-relay --tail 50 2>&1 | tail -50 ; docker inspect duartec-parts-mail-relay --format '{{json .Config.Env}}' | tr ',' '\n' | head -40
docker exec duartec-parts-mail-relay ps aux ; docker exec duartec-parts-mail-relay python -c "import http.client; ..."
cat ~/duartec-infra/mail-relay/app.py | head -200 ; cat ~/duartec-infra/caddy/conf.d/apis.caddy
docker exec duartec-parts-caddy cat /var/log/caddy/access.log | grep -i "mail" | head -20
grep -rn "mail-relay" /srv/apps/* ~/mission-bridge 2>&1 | head -20

systemctl status api-stub 2>&1 | head -30 ; systemctl cat api-stub 2>&1 | head -50
ss -lntup | grep 8080 ; curl -s http://127.0.0.1:8080/health | head -20 ; curl -s http://127.0.0.1:8080/ | head -20
cat /srv/apps/api-service/server.js ; ls -la /srv/apps/api-service/
grep -rn "api-stub\|:8080" ~/duartec-infra/Caddyfile* /etc/caddy/Caddyfile 2>&1 | head -20
journalctl --since "7 days ago" -u api-stub --no-pager | head -20
```

---

## Notas de riesgo
- **8080 no colisiona:** Host `api-stub 127.0.0.1:8080` vs docker `db-api 8080/tcp expose` y `mail-relay 8080/tcp expose` — distintos netns, verificado `ss` + `docker inspect`.
- **Whisper coste hundido:** Modelo `tiny` ya cacheado en `./whisper_cache` — parar contenedor no libera modelo hasta `docker system prune` + borrar cache.
- **Mail-relay silencioso:** No usar `docker logs` como única señal de “sin evidencia”; Caddy access log es la fuente de verdad tailnet.
