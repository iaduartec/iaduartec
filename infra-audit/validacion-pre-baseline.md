# Validación Pre-Baseline Canónico — 2026-09-06 03:35 UTC

> Solo lectura. Comandos reales ejecutados. No se modificó infraestructura.

## Resumen: 6/9 PASS estricto · 7/9 PASS si se acepta n8n interno | NO listo para baseline

| #   | Dominio               | Veredicto                | Evidencia (comando → salida)                                                                                                                                                                                                                                                                                                                                                                    |
| --- | --------------------- | ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **Servicios systemd** | **PASS**                 | `systemctl is-active caddy`→`active`; `ollama`→`inactive` (esperado: docker); `systemctl --failed`→`0 loaded units`; `systemctl --user is-active trading-freqtrade trading-streamlit duartec-static-sites openclaw-gateway`→`active` x4                                                                                                                                                         |
| 2   | **Docker**            | **PASS**                 | `docker ps --format`→14 ct Up: n8n-unified, email-store(healthy), ollama(13h), parts-caddy/mariadb/db-api, media-wrapper(healthy), insforge x4, runners, sbx-workspace; `volume ls \|wc -l`→14 (13+header); `network ls`→5 nets; `stats`→CPU <5% (postgres 4.49% pico), mem 369M email-store / 318M n8n                                                                                         |
| 3   | **n8n**               | **FAIL(host)/PASS(int)** | `curl 127.0.0.1:5679/healthz`→vacío; `curl 5678/healthz` host→vacío; `docker exec n8n-unified wget 127.0.0.1:5678/healthz`→`{"status":"ok"}`; `N8N_PORT=5678` interno; `inspect Ports`→`5678/tcp:[]` sin binding host (detrás de Caddy); `logs --tail`→error openclaw module no afecta health                                                                                                   |
| 4   | **OpenClaw**          | **PASS**                 | `openclaw status`→Gateway local ws://127.0.0.1:5800 reachable 272ms, service systemd user enabled running pid2822210, Agents 1, 3 sessions, telegram-orchestrator activo hace 35m; `ps aux\|grep openclaw`→4 procs; `ls ~/.openclaw/`→backups/agents/canvas ok; gateway mem 757M pico 1.1G                                                                                                      |
| 5   | **Mission Bridge**    | **PASS**                 | `curl 127.0.0.1:8020/health`→`{"status":"ok"}`; `ss -tlnp\|grep 8020`→LISTEN 127.0.0.1:8020 python3 pid265273; `systemctl status mission-bridge`→active(running) 21h Main PID 265273 `/usr/bin/python3 -u server.py`; docker→`No such container: duartec-mission-bridge` (systemd, no docker) correcto                                                                                          |
| 6   | **Ollama**            | **FAIL**                 | `systemctl is-active ollama`→`inactive`; host `curl 127.0.0.1:11434/api/tags`→vacío; `ollama list` host→not found; docker `duartec-ollama` Up 13h; `docker exec duartec-ollama ollama list`→`qwen3:1.7b 1.4GB 14h ago`; `inspect PortBindings`→`map[]` null / `11434/tcp:null` sin expose host; logs gin 200 OK interno                                                                         |
| 7   | **Bases**             | **PASS**                 | `docker exec duartec-parts-mariadb mariadb -e` requiere pass pero health→`healthy`; `insforge-postgres-1 pg_isready`→`accepting connections`; `docker exec insforge-postgres-1` OK; sqlite ruta solicitada `~/duartec-infra/*.sqlite`/`/srv/automation/cnmv-pdmr/*.sqlite`→no existe; real→`~/duartec-infra/n8n_data/email.sqlite 12K` + backups n8n database.sqlite                            |
| 8   | **Rutas**             | **PASS***                | `curl -w %{http_code} 127.0.0.1:3000`→`200`; `3001`→`200`; `18080`→`200`; `19080`→`200`; `tailscale serve status`→`https://kiri-vnic.tail4b3cf6.ts.net` 16 proxies (/→:80, /canvas→:8020, /openclaw→:5800 etc); `caddy validate /etc/caddy/Caddyfile`→`Valid configuration`; `~/duartec-infra/Caddyfile-host`→`Valid` (warn fmt); *observación: 2 procesos caddy (2600105 /etc/caddy + 3907278) |
| 9   | **Logs & Cron**       | **FAIL**                 | `journalctl -p err --since 24h`→1951 líneas, spam `postfix/sendmail fatal main.cf No such file` cada minuto + `networkctl veth* not found`; `docker logs --since 24h duartec-email-store`→loop `[imap] ETIMEOUT / NoConnection backoff 30s`; `crontab -l`→2 jobs (`cnmv-pdmr daily_ingest 15 7 *` + `sync-youtube-cookies 0 */4 *`) ok                                                          |

## Detalle adicional verificado

- `docker inspect duartec-ollama Network`→`duartec-voice-ai_duartec-net` aislada explica host inaccesible.
- `caddy ps`→dual instancia revisar antes de baseline (riesgo reload).
- Postfix sin `/etc/postfix/main.cf` genera ~1440 err/día — silenciar o instalar.
- email-store IMAP timeout intermitente, no crítico pero documentar.

## ¿Listo para baseline canónico?

**NO.** Corregir antes de congelar:

1. Ollama: exponer 11434 al host o documentar acceso solo vía docker-net + decidir modelo base (solo qwen3:1.7b).
2. Postfix: desinstalar o configurar main.cf para eliminar spam journal.
3. n8n: confirmar diseño sin host-port intencional (acceso solo Caddy/tailscale) y dejar constancia.
4. Caddy dual-process: unificar a una sola unidad.
   Tras fixes, re-validar dominios 3,6,9 y emitir baseline. Con fixes → 9/9 alcanzable.
