# Decisión G-whisper — kiri-vnic — 2026-09-06

**Verificación:** 2026-09-06T03:3xZ | **Dictamen:** MANTENER EN CUARENTENA (no eliminar)

## Evidencia

- Contenedor `duartec-local-whisper` (`duartec-voice-ai-whisper:54fcf250 521M`) — `Exited (143) 2026-09-06T03:05:55Z`, Started `2026-08-27T19:48:20Z` (9d up), `restart: unless-stopped`, `mem_limit 2g cpus 1.0`.
- Bind mount `~/duartec-infra/whisper_cache` (no volumen docker) = **75M** (`hub/ xet/`) retenido. `docker volume ls | grep whisper` vacío — correcto.
- `docker-compose.yml:54` whisper definido, no borrado.
- `docker inspect` Health: interval 15s, últimos 5 checks OK (200) antes del stop.

## Consumidores encontrados

- `grep -r 8093 /srv/apps --exclude-dir=node_modules` → 0 hits (puerto legacy no usado; actual 5681 interno `expose` sin publish).
- `~/n8n-unified` no existe. `~/duartec-infra/workflows/mission-bridge-webhook.json:481` → `http://whisper:5681/transcribe` (workflow `kc208PLh3kml8a1J` activo, **0 ejecuciones** en DB 2026-09-06, reproducido pending-whisper).
- `media-api/app.py:61` `WHISPER_URL=http://whisper:5681/transcribe` → fallback local tras yt-dlp; tiers 1-2 son subtitles, no consume whisper si hay subtítulos.
- `grep -r whisper ~/duartec-infra` hit solo en `docker-compose.yml`, `Caddyfile apis.caddy`, `local_whisper_server.py`, `scripts/*`, `dashboard/app.js` — sin consumidores en `/srv/apps`, `~/mission-bridge`, `/srv/apps/*`.
- Red: `duartec-net` solo, sin binding host (`ss -lntup` sin 5681), Caddy tailnet-only `/whisper* → whisper:5681` con 405/401 guards.

## Logs

- `docker logs duartec-local-whisper` = 52878 líneas; `grep -v health` → 9 líneas (startup + `GET / 404` + shutdown); **`POST 0`, `transcribe 0`**; `docker logs --since 168h` idem 5 líneas no-health, 0 POST.
- `journalctl -u caddy --since "7 days ago" | grep -i whisper` → 0; `journalctl --since 9d | grep whisper\|8093` → solo error `container ... is not running` del 06/09 03:19.
- `journalctl --since 7d | grep -iE whisper` vacío; `docker logs n8n-unified | grep whisper` → 0.
- `/var/log/caddy/` vacío; `/srv/logs/caddy/http-access.log` (5.8M, 2872 l.) + 6×gz (10-28k l.) → `grep whisper|5681|transcribe|8093` → **0 hits**; `https-access.log` (3.4K) también 0.
- `/srv/logs/caddy/https-access` no relevante (solo `/`, `/portfolio`, etc). **0 POST reales vs health cada 15s confirmado 9d.**

## Decisión

**MANTENER EN CUARENTENA** — No eliminar imagen (521M) ni `whisper_cache` (75M). Cuarentena iniciada 2026-09-06, **vence 2026-10-06** (30d). Si no hay POST reales en ese periodo → eliminar; si hay uso → REACTIVAR `docker compose up -d --build whisper` (<30s rollback).

## Próximo paso

Esperar cuarentena. No `docker rmi` / `rm -rf whisper_cache`. Monitor 30d: checks ya cubiertos (logs + `docker ps -a` + `du -sh`). Workflow `kc208` queda `active=1 continueOnFail=true` para medir error `whisper:5681 ENOTFOUND` sin romper Telegram. Re-evaluar 2026-10-06.
