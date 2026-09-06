# Decisión G — Trading (Freqtrade + Streamlit)

**Fecha verificación:** 2026-09-06 03:32 UTC · **Host:** kiri-vnic (Oracle ARM64) · **Verificador:** OpenCode

## Evidencia

- `docker ps --filter name=freqtrade|streamlit` → **0 contenedores** (no docker). `docker ps` total: 13 contenedores (n8n, caddy, ollama, etc.), ninguno trading.
- `ss -tlnp | grep -E "18080|8501|8080"` →
  - `127.0.0.1:18080 freqtrade pid=540266` (LISTEN 2048)
  - `127.0.0.1:8501 streamlit pid=3894169` (LISTEN 2048)
  - `8080` no vinculado a trading (solo duartec-parts-db-api en docker).
- `systemctl --user status trading-freqtrade` → **active (running)** since 2026-08-24 04:11 UTC (12d), `uv run freqtrade trade --userdir freqtrade/user_data --config configs/freqtrade/okx_demo.json`, CPU 12h, Mem 397M, heartbeat cada 60s, `Wallets synced` 2026-09-06 03:31.
- `systemctl --user status trading-streamlit` → **active (running)** since 2026-09-02 23:51 UTC (3d), `uv run streamlit run streamlit_app.py --server.address 127.0.0.1 --server.port 8501`, Mem 242M.
- `systemctl --user status trading-bot-loop` → inactive (disabled).
- `crontab -l | grep -i trading` → vacío. `systemctl list-timers --user | grep trading` → vacío. No cron/timer para trading.
- `ls ~/trading` → no existe. `ls ~/projects/trading` → existe (19 entries, uv.lock 729k, tradesv3.dryrun.sqlite 184k + WAL 4.1M), `configs/freqtrade/okx_demo.json` dry_run:true, sandbox:true, stake USDT.
- `cat /tmp/freqtrade-demo.log` → 5.0M, tail heartbeat RUNNING, `docker logs --since 24h duartec-trading-*` no aplica (no docker).

## Consumidores / Servicio

- **Runtime systemd user:** `~/.config/systemd/user/trading-freqtrade.service` + `trading-streamlit.service` (enabled, WantedBy=default.target), `deploy/systemd/trading.env` (FREQTRADE_API_URL=http://127.0.0.1:18080/api/v1).
- **Tailscale Serve:** `kiri-vnic.tail4b3cf6.ts.net:8502 → http://127.0.0.1:8501` (tailnet only) — único proxy público del trading.
- **Hub-v2 catálogo:** `trading-dashboard` (finance-tools, Active) `link: https://kiri-vnic.tail4b3cf6.ts.net:8502/` en `duartec-infra` + backups (`BV9BwA_R.js`, `77Fwwcak.js`).
- **API interna:** Streamlit consume `FREQTRADE_API_URL` vía loopback (deploy/systemd).
- No Caddy directo, no docker-compose, no cron.

## Actividad (últimas 24h)

- Heartbeat Freqtrade 60s continuo (`freqtrade.worker INFO Bot heartbeat PID=540266 version 2026.7 state=RUNNING`) — ver `journalctl --user -u trading-freqtrade --since 24h` y `/tmp/freqtrade-demo.log`.
- Streamlit escuchando 127.0.0.1:8501 sin errores (`Uvicorn server started` 2026-09-02).
- Tailscale bindings activos, puerto 8502 accesible tailnet.

## Decisión

**CONSERVAR**

Uso activo documentado: servicios systemd enabled y corriendo >3 días, heartbeat diario, Tailscale publicado y catalogado en hub-v2, proyecto con WAL activo y modo demo/paper (riesgo acotado). No CUARENTENA/RETIRAR. Migración a docker solo si se decide consolidación infra, no por inactividad.
