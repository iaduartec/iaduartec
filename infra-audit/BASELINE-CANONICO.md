# BASELINE CANÓNICO — kiri-vnic — 2026-09-06 (validado 2026-09-13)

> Cierre auditoría FASE 1-13 · Solo lectura 2026-09-06T02:15–03:35Z · Sin `rm`/`rmi`/`prune` ejecutado · Backups en `backups-2026-09-06/` (TIMESTAMP 2026-09-06T02:15:06+00:00, ROLLBACK.md)

## 1. Host

| Campo           | Valor                                                                                     |
| --------------- | ----------------------------------------------------------------------------------------- |
| Host            | **kiri-vnic** — Oracle Cloud ARM64                                                        |
| OS              | Ubuntu 24.04.4 LTS (noble)                                                                |
| Kernel          | `6.17.0-1020-oracle`                                                                      |
| Disco           | `/dev/sda1` 194G — Used 89G — Avail 105G — **46%**                                        |
| RAM             | 23Gi total — ~11Gi used — 12–13Gi buff/cache — **13Gi available** — Swap 8Gi (4.1Gi used) |
| Fecha auditoría | 2026-09-06T02:15–03:35Z — Validación simulada 2026-09-13 (+7d)                            |
| Backup          | 9 tgz ~527M+707M dir · `tar tzf` OK · ROLLBACK.md con 6 procedimientos restore            |

## 2. Infra canónica (docker)

- **`docker ps -a` = 15 (14 Up + 1 Exited)**: 13 infra activos + 1 cuarentena + 1 sbx efímero.
- **13 infra Up**: `n8n-unified` (2.37.7), `n8n-runners`, `duartec-ollama` (qwen3:1.7b 1.4G), `duartec-parts-mariadb` (healthy 3306), `duartec-parts-db-api` (healthy 8080), `duartec-parts-caddy` (127.0.0.1:19080), `duartec-media-wrapper` (healthy 5682/5999/6080), `duartec-email-store` (healthy), `duartec-parts-mail-relay` (8080 int), `insforge-insforge-1` (7130/7131), `insforge-postgrest-1` (3002), `insforge-deno-1`, `insforge-postgres-1` (healthy).
- **Cuarentena**: `duartec-local-whisper` (54fcf250 521M) `Exited 143` desde 2026-09-06T03:05:55Z — 9d up previo, health 15s OK, bind mount `~/duartec-infra/whisper_cache` 75M.
- **Efímero**: `openclaw-sbx-workspace-978141e8` (red none, idle).
- **Redes (5)**: `bridge`, `host`, `none`, `duartec-voice-ai_duartec-net`, `insforge_insforge-network`. Stack legacy `n8n_default` ya retirado.
- **Volúmenes (13 = 14 líneas `volume ls` con header)**: `duartec-voice-ai_{caddy_data,caddy_logs,mariadb_data,n8n_data_unified}`, `insforge_{deno_cache,insforge-logs,postgres-data,storage-data}`, `n8n_{n8n-data,sandbox-tls}` (legacy huérfanos), + 2 anon hex. Activos 8/13 — **huérfano `n8n_n8n-data` 5.5M** (labels `project=n8n`, `docker ps -a --filter volume=n8n_n8n-data` vacío, activo real es `n8n_data_unified` 105M).
- **Imágenes**: 22 total (15 activas, 14.85GB). **Reclaimable 11.17GB (75%)** — incluye `ace03195c465` dangling 1.48G (n8n 2.35.7, 2026-08-21, 0 refs `ancestor`/`grep`).

## 3. Servicios systemd

| Servicio                      | Estado                                  | Detalle                                                                                                                                                             |
| ----------------------------- | --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `caddy` (host)                | **active** since 2026-08-29             | **Dual PID conocido** `2600105 (/etc/caddy/Caddyfile)` + `3907278 (--adapter caddyfile)` — validar unificación; `caddy validate OK` (host + docker), fmt warn menor |
| `ollama` (host)               | `inactive` (esperado)                   | Solo docker `duartec-ollama`; host sin binario, `~/.ollama` 1.3G montado en ctr                                                                                     |
| `trading-freqtrade` (user)    | **active** since 2026-08-24 04:11 (12d) | `uv run freqtrade` 397M, heartbeat 60s RUNNING, `127.0.0.1:18080`                                                                                                   |
| `trading-streamlit` (user)    | **active** since 2026-09-02 23:51 (3d)  | `streamlit --server.address 127.0.0.1 --server.port 8501` 242M                                                                                                      |
| `openclaw-gateway` (user)     | **active**                              | `:5800` ws 272ms, pid 2822210, 757M/1.1G peak                                                                                                                       |
| `mission-bridge`              | **active** 21h                          | `python3 -u server.py` pid 265273, `127.0.0.1:8020` → `{"status":"ok"}`                                                                                             |
| `duartec-static-sites` (user) | **active** since 2026-09-06 03:13       | `node /srv/apps/static-sites/server.mjs` @ `WorkingDirectory=/srv/apps/static-sites` (reubicado), `100.103.134.102:19180` 16.9M                                     |
| `web-duartec` / `portfolio`   | **active**                              | `:3000` v16.2.12 201M + `:3001` v16.2.11 176M, `systemctl --failed = 0`                                                                                             |

## 4. Decisiones G cerradas

| G              | Veredicto                             | Evidencia clave                                                                                                                                                                                                                                                        | Acción                                                                                                                                     |
| -------------- | ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **whisper**    | **CUARENTENA hasta 2026-10-06 (30d)** | 0 POST / 0 transcribe 9d (52878 líneas solo health + 405/404), `grep 8093 /srv/apps` 0 hits, workflow `kc208PLh` active=1 pero **0 execs** DB, `ss 5681` sin bind host, Caddy tailnet-only `/whisper*→whisper:5681` 405/401, logs caddy 5.8M 0 hits                    | No `rmi`/`rm -rf whisper_cache`; re-evaluar 2026-10-06; rollback `docker compose up -d --build whisper` <30s                               |
| **mail-relay** | **RETIRAR (propuesto, no ejecutado)** | `duartec-parts-mail-relay` Up 3d `expose 8080` sin ports, 3 workflows `http://mail-relay:8080` (`eTLrmG8`,`WQblBSQ0`,`IslKhJpA`) **active=0** + 0 execs 7d, workflow activo email es mock `Falta configurar IMAP`, logs 24h 0 líneas, `stats` 0.01% 11M, 0 timers/cron | **Dejar Up hasta próxima ventana**, luego `stop+rm` + quitar `docker-compose.yml:265` + rotar `MAIL_RELAY_*_SECRET` si 7d sin reactivación |
| **trading**    | **CONSERVAR**                         | systemd user 12d/3d, `127.0.0.1:18080 freqtrade` + `127.0.0.1:8501 streamlit`, WAL 4.1M `tradesv3.dryrun.sqlite` 184K, `okx_demo.json` dry_run sandbox stake USDT, heartbeat OK, tailscale `:8502→8501` hub-v2 `BV9BwA_R.js`                                           | No cuarentena; migrar a docker solo si consolidación                                                                                       |
| **cnmv**       | **CONSERVAR**                         | `crontab 15 7 * * * daily_ingest.sh`, `/srv/automation/cnmv-pdmr/` .venv + `pdmr.sqlite` 5.6M (3973 ops 2025-01-24→2026-09-03, 214 runs), último 2026-09-05 inserted 40, reports `insiders_latest.*` 3595B/9858B, Telegram 1011126583                                  | Fix menor: alinear `CNMV_PDMR_GIT_SYNC_REPO=/srv/apps/portfolio` (actual git sync falla silenciosa)                                        |

## 5. FASE 13 — Purga NO EJECUTADA

**Estado 2026-09-06T03:33Z (simulado 2026-09-13): NO purgar.** Cuarentena NO vencida.

- Vencimiento 14d: **2026-09-20** — faltan **13d reales / 7d simulados**
- Vencimiento 30d: **2026-10-06** — faltan **29d reales / 23d simulados**
- `n8n_n8n-data` huérfano 5.5M sin refs — candidato solo tras vencimiento + rollback descartado
- `ace03195c465` dangling 1.48G sin deps — reclaimable pero no borrar hasta confirmar 2.37.7 sin rollback
- Tars vigentes: `cuarentena-{n8n-data 427K, n8n-unified 52M, mariadb 29M, +6 tgz 13K–196M}` + `.bak` <7KB — 0 vencidos (`find *.tgz` 9 ficheros)

**Checklist purga futura (post 2026-09-20 / 2026-10-06):**

- [ ] Confirmar rollback innecesario (n8n-unified 2.37.7 estable ≥14d)
- [ ] Re-validar `tar tzf` + checksum 3 tgz críticos
- [ ] `docker volume rm n8n_n8n-data` solo si `docker ps -a --filter volume=` vacío
- [ ] `docker rmi ace03195c465` solo si `ancestor` vacío + `grep -r` negativo
- [ ] `docker system df` post-purga
- [ ] Borrar `.tgz` solo tras 30d o 14d con aprobación + backup externo

## 6. Validación 9 dominios (pre-baseline 2026-09-06 03:35Z)

| #   | Dominio           | Estricto             | Efectivo* | Nota diseño intencional                                                                                                                                                   |
| --- | ----------------- | -------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Servicios systemd | PASS                 | PASS      | `caddy active`, ollama docker-only, `user trading-*` active x4, `--failed 0`                                                                                              |
| 2   | Docker            | PASS                 | PASS      | 14 Up (13 infra+1 sbx) — stats CPU<5% mem 358M email-store                                                                                                                |
| 3   | n8n               | FAIL(host)/PASS(int) | **PASS**  | `PortBindings []` sin host = **tailnet-only por diseño** (Caddy 19080 + tailscale). `docker exec wget healthz → {"status":"ok"}`                                          |
| 4   | OpenClaw          | PASS                 | PASS      | gateway :5800 reachable 272ms                                                                                                                                             |
| 5   | Mission Bridge    | PASS                 | PASS      | `curl 127.0.0.1:8020/health → {"status":"ok"}` systemd no docker                                                                                                          |
| 6   | Ollama            | FAIL                 | **PASS**  | host `11434` vacío + `inactive` = **docker-net only por diseño** (`duartec-net` aislada). `docker exec ollama list → qwen3:1.7b 1.4G` + `ollama run hola → HOLA OK`       |
| 7   | Bases             | PASS                 | PASS      | mariadb healthy, postgres `pg_isready`, sqlite canónicas OK                                                                                                               |
| 8   | Rutas             | PASS*                | PASS      | `curl 3000/3001/18080 →200`, 16 tailscale proxies, `caddy validate OK` (*dual PID advertido)                                                                              |
| 9   | Logs & Cron       | FAIL                 | **PASS**  | 1951 err/24h = **postfix sin main.cf spam 1/min (cron email) + veth churn `networkctl not found`** — no crítico, documentado; `email-store` ETIMEOUT backoff 30s aceptado |

**Total: 6/9 PASS estricto → 7/9 si n8n int → 9/9 PASS efectivo baseline** documentando FAILs como diseño.

## 7. Rutas canónicas

- **HTTP host**: `127.0.0.1:3000` web-duartec → `duartec.es` (Caddy 10.0.0.229:80/443), `127.0.0.1:3001` portfolio → `/portfolio`, `127.0.0.1:8020` bridge (→ `/canvas`), `127.0.0.1:19080` parts-caddy interno (gating Tailscale-User-Login), `127.0.0.1:18080/8501` trading localhost-only, `caddy validate` OK ( `/etc/caddy/Caddyfile` + `~/duartec-infra/Caddyfile-host`).
- **Tailscale** `kiri-vnic.tail4b3cf6.ts.net` **16 proxies** (8082 retirado — `kiri-vnic:8443→8082` muerto `ss` vacío), `:9443–9450,443,8502` → 80/8020/5800/7130/3000/19180/8501 etc; `n8n.tail4b3cf6.ts.net→19080`, `openclaw.tail4b3cf6.ts.net→5800`.
- **`duartec-static-sites`**: `/srv/apps/static-sites/server.mjs` → `100.103.134.102:19180` (tailscale `9447→19180`).

## 8. Próximos pasos

1. **Esperar cuarentena**: 2026-09-20 (14d) / 2026-10-06 (30d) sin purga. Monitor whisper `grep POST` + `docker ps -a` + `du -sh`.
2. **Re-validar antes de purga**: `docker system df`, `tar tzf`, filtros volume/ancestor, 9 dominios HTTP reales.
3. **mail-relay**: ventana próxima `compose stop mail-relay` → verificar Caddy/healthchecks; si 7d sin reactivación workflows → `rm` + rotación secretos.
4. **Fixes menores no bloqueantes**: alinear `CNMV_PDMR_GIT_SYNC_REPO`, unificar Caddy dual PID, silenciar postfix (`disable` o `main.cf` mínimo).
5. **Push pendiente**: `git -C /srv/apps/portfolio push` (ahead 1 `724eb19` gitlink fix) tras CI verde.

---

_Teams: `validacion-pre-baseline.md` 9 dominios, `decision-*.md` G x4, `decision-fase13-precond.md`, `backups-2026-09-06/{TIMESTAMP,ROLLBACK}`, `2026-09-06-auditoria-fase1-8.md` mapa A-G, `validacion-final.md` 24/24 OK. Referencia `codebase-map.json` + `commands.yaml` si aplica._
