# Decisión G — CNMV PDMR Tracker

**Fecha verificación:** 2026-09-06 03:32 UTC · **Host:** kiri-vnic (Oracle ARM64) · **Verificador:** OpenCode

## Evidencia

- `crontab -l | grep -i cnmv` → `15 7 * * * /srv/automation/cnmv-pdmr/scripts/daily_ingest.sh >/dev/null 2>&1 # CNMV_PDMR_DAILY`
- `cat /home/ubuntu/cnmv*` → no existe. `ls ~/scripts/cnmv* ~/duartec-infra/scripts/cnmv*` → no existe. Ruta real: `/srv/automation/cnmv-pdmr/`.
- `ls -la /srv/automation/cnmv-pdmr/` → .venv, data/pdmr.sqlite 5.6M, logs/, reports/, scripts/cnmv_pdmr.py (57k) + daily_ingest.sh (9.4k).
- `journalctl --since "7 days ago" | grep -i cnmv` → CRON disparado diario 07:15 UTC Sep 02-05 (4 ejecuciones).
- `grep -r "cnmv\|CNMV" ~/duartec-infra /srv/apps --include="*.js" --include="*.sh" --include="*.yml"` → `duartec-infra/backups/*/BV9BwA_R.js` entry `cnmv-pdmr` (finance-tools, Active, "Scraping continuo + alertas de insiders"), `daily_ingest.sh` referencia `cnmv_pdmr.py ingest/report`.
- `docker ps | grep -i cnmv` → vacío. `systemctl list-timers | grep -i cnmv` → vacío (usa cron, no timer).

## Consumidores / Servicio

- **Cron diario:** 07:15 UTC, ventana 14 días, max_pages 20, timeout 90, flock lock `.daily_ingest.lock`.
- **SQLite:** `data/pdmr.sqlite` tables `pdmr_operations` (3973 filas, fecha 2025-01-24 → 2026-09-03) + `ingest_runs` (214 runs, last 2026-09-05 inserted 40, 2026-09-04 inserted 6).
- **Reportes:** `reports/insiders_latest.md|.html` + `reports/insiders_YYYY-MM-DD.md|.html` (último 2026-09-05 3595B md, 9858B html, 66 líneas, resumen 40 ops).
- **Notificación:** `openclaw message send --channel telegram --account default --target 1011126583` + adjunto HTML (TELEGRAM_SEND_REPORT_FILE=1).
- **Git sync:** `CNMV_PDMR_GIT_SYNC=1` repo `/home/ubuntu/portfolio` (inexistente, real `/srv/apps/portfolio`) → `PUBLIC_REPORT_PATH` no copiado; `insiders_latest.*` ausente en `/srv/apps/portfolio`.
- **Hub:** catálogo `cnmv-pdmr` en hub-v2 (backup JS).

## Actividad (últimos 7 días)

- Logs `daily_2026-09-05.log`: `scraped 188 generated 393 inserted 40 pdf_errors 0`, report generado 07:16:09Z, telegram enviado (según script).
- `daily_2026-09-04.log`: inserted 6, `daily_2026-09-03.log` inserted 20.
- Cola reports: Sep 02-05 diarios sin gap. `ls -lt reports` confirma frescura <24h. DB activa y creciente.

## Decisión

**CONSERVAR**

Uso activo diario documentado: cron ejecuta, SQLite crece, reports <24h, ingesta sin errores PDF, consumidores Telegram + hub. **Acción correctiva menor:** alinear `CNMV_PDMR_GIT_SYNC_REPO=/srv/apps/portfolio` y `PUBLIC_REPORT_PATH` para restaurar copia publica/git push (actualmente falla silenciosa). No CUARENTENA/RETIRAR.
