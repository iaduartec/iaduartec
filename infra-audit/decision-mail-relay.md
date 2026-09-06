# Decisión mail-relay — 2026-09-06 03:30 UTC

## Evidencia
- `docker ps --filter name=mail-relay`: `duartec-parts-mail-relay Up 3 days` (imagen `duartec-voice-ai-mail-relay`, `python /app/app.py`, `expose 8080/tcp`, no `ports` publicados). NO es MailHog; no hay puertos 8025/1025.
- `docker inspect`: `StartedAt 2026-09-02T23:53:13Z`, env `MAIL_USER=sgomez@duartec.es`, `MAIL_IMAP_HOST=imap.serviciodecorreo.es`, `MAIL_SMTP_HOST=smtp.serviciodecorreo.es`, `8080` interno, network `duartec-net` IP 172.18.0.11.
- `ss -tlnp | grep -E "8025|1025"`: sin resultados. `curl 127.0.0.1:8025` no responde (premisa MailHog inválida).
- `docker exec mail-relay python urllib health`: `{"ok": true}` — /health responde solo vía `duartec-net` (`http://mail-relay:8080/health`).
- `docker logs --since 24h duartec-parts-mail-relay`: 0 líneas (app suppress `log_message`; solo imprime error forwarding Revolut).

## Consumidores
- `grep -r mail-relay --include="*.json" *.py *.yml`: 3 workflows n8n con `http://mail-relay:8080/send|search`:
  - `eTLrmG8ItS3nHYfD` Duartec - Recordatorio fin de jornada — `active=0`
  - `WQblBSQ0jzTPXgLb` Duartec - Captura de partes (search+send) — `active=0`
  - `IslKhJpAxYKHgulI` Duartec - Recordatorio multicanal — `active=0`
- Workflow activo `Duartec Email Module Consolidated (9aee75b3162719e2)` **no** consume mail-relay: solo webhook `duartec-email-router` + mock `Falta configurar IMAP/SMTP. Módulo en mantenimiento.` (0 ejecuciones históricas).
- `db-api/app.py:3759` solo lista estado `"mail-relay":"online"` informativo, no cliente HTTP.
- `grep 8025|1025|MailHog|smtp.*mail-relay` en `~/duartec-infra /srv/apps ~/n8n*`: 0 hits relevantes (solo hashes `cc1025`, tamaños).
- Backup `n8n-before-mission-alpha-bullish-preview-20260903.json`: mismos 3 workflows inactivos.

## Actividad 24h
- Logs mail-relay 24h: 0 mensajes; `docker stats`: 0.01% CPU, 11.95MiB.
- `n8n execution_entity` últimos 7d: 2026-09-05:2, 2026-09-06:2 (errores `jqfWfcpXRonNC2gA` no relacionados). 0 ejecuciones para los 3 workflows mail-relay (`SELECT ... WHERE workflowId IN (...)` → 0 filas). `Email Module Consolidated` → 0 ejecuciones.
- `docker logs n8n-unified --since 24h | grep mail-relay`: 0 hits.
- `ss -tnp` sin conexiones a mail-relay.

## Cron / Timers
- `systemctl list-timers`: 17 timers, ninguno referencia mail-relay. `crontab -l`: `15 7 * * * daily_ingest.sh` y `sync-youtube-cookies.sh` — nada SMTP.
- `grep -r mail-relay /etc/cron* /etc/systemd`: 0 hits.

## Decisión: RETIRAR (no CONSERVAR)
No hay consumidores activos: los 3 workflows que usan `http://mail-relay:8080` están deshabilitados y sin actividad 24h/7d. El workflow activo de email es mock. Servicio interno sin `ports` expuestos, sin tráfico, sin logs. Criterio "CONSERVAR si hay consumidores activos" **no se cumple**.

### Acción recomendada
1. Mantener parado o `docker compose stop mail-relay` y verificar que no rompe Caddy/healthchecks (no está en `healthchecks` de `inventory.json`).
2. Si en 7d sigue sin reactivación de workflows, `docker compose rm` + eliminar del `docker-compose.yml:265` y rotar `MAIL_RELAY_*_SECRET`.
3. Alternativa: re-etiquetar como `G-mail-relay-legacy` / mover a perfil `infra-audit/archivado`.

> Nota corrección: no es MailHog 8025/1025; es relay Python IMAP/SMTP :8080. Re-evaluar decisión original "actividad <24h" — evidencia actual contradice actividad.
