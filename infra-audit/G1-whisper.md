# G1 — Whisper cuarentena 30d — kiri-vnic — 2026-09-06

**Host:** `kiri-vnic` (hostname confirmado)  
**Operador:** subagente G1 — whisper cuarentena 30d  
**Ventana:** 2026-09-06 a 2026-10-06 (30d)  
**Contenedor:** `duartec-local-whisper` — imagen `duartec-voice-ai-whisper:latest` (54fcf2509ae2, 521MB)  
**Referencia investigación previa:** `~/infra-audit/pending-whisper-mail-apistub.md` — verificada y reproducida

---

## 1. Veredicto y alcance

**CUARENTENA — stop 30d, keep image + whisper_cache.** No `rm`, no `volume rm`, no `rmi`. Único consumidor activo `Duartec Telegram Voz OpenClaw Polling Completo` (active=1, execution count=0 en 9d). Coste 0.11-0.13% CPU, ~14-16 MiB. Servicio intacto para rollback <30s.

**NO tocado en esta tanda:** `duartec-parts-mail-relay`, `api-stub`, `tailscale`, `duartec-net`, `caddy`.

---

## 2. Pre-check (2026-09-06T03:05-03:06Z)

### 2.1 Estado contenedor y compose

```bash
docker ps --format "{{.Names}} {{.Status}}" | grep whisper
# duartec-local-whisper Up 9 days (healthy)

docker inspect duartec-local-whisper --format '{{.Config.Image}} {{.State.Status}} {{.HostConfig.RestartPolicy.Name}}'
# duartec-voice-ai-whisper running unless-stopped
# (detalle: Image=duartec-voice-ai-whisper Status=running Restart=unless-stopped StartedAt=2026-08-27T19:48:20Z)

docker volume ls | grep whisper
# (vacío) — whisper NO usa named volume; usa bind mount ./whisper_cache:/cache/huggingface

docker volume ls
# local   duartec-voice-ai_caddy_data etc — sin volumen whisper dedicado

grep -n -A 22 "whisper:" ~/duartec-infra/docker-compose.yml
# 54:  whisper:
#      build: context . dockerfile Dockerfile.whisper
#      container_name: duartec-local-whisper
#      restart: unless-stopped
#      init: true
#      environment: LOCAL_WHISPER_MODEL=tiny LOCAL_WHISPER_PORT=5681 ...
#      volumes: ./whisper_cache:/cache/huggingface
#      networks: duartec-net
#      mem_limit: 2g cpus:1.0 pids_limit:256
#      healthcheck: CMD-SHELL python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5681/health'..."
#                   interval 15s timeout 5s retries 5
```

**Whisper_cache (bind, preservado):**

```bash
ls -lh ~/duartec-infra/whisper_cache
# hub  xet
du -sh ~/duartec-infra/whisper_cache
# 75M

docker images duartec-voice-ai-whisper
# duartec-voice-ai-whisper:latest 54fcf2509ae2 521MB
```

### 2.2 Conectividad interna (pre-stop = OK)

```bash
docker exec n8n-unified wget -qO- http://whisper:5681/health
# {"ok":true,"model":"tiny"}
docker exec n8n-unified wget -qO- http://duartec-local-whisper:5681/health
# {"ok":true,"model":"tiny"}
```

### 2.3 Evidencia 0 POST (reproducida)

```bash
docker logs duartec-local-whisper 2>&1 | head -30
# INFO: Started server process [7]
# INFO: Uvicorn running on http://0.0.0.0:5681
# INFO: 127.0.0.1:xxxxx - "GET /health HTTP/1.1" 200 OK  (repetido cada 15s = healthcheck)

docker logs duartec-local-whisper 2>&1 | grep -c POST
# 0

docker logs duartec-local-whisper 2>&1 | grep -v health | grep -v "Started"
# (vacío tras arranque — sin /transcribe, sin errores)

docker stats --no-stream --format "{{.Name}} {{.CPUPerc}} {{.MemUsage}}" duartec-local-whisper
# duartec-local-whisper 0.11% 16.74MiB / 2GiB  (investigación previa: 0.13% CPU 14.39MiB)

docker exec caddy cat /var/log/caddy/access.log | grep whisper  (según pending)
# Sin hits en ventana retenida (10MB x7) — cero POST /whisper*
# Caddy apis.caddy:6: tailnet-only, 0 hits confirmado

# n8n DB (pending): kc208PLh3kml8a1J "Duartec Telegram Voz OpenClaw Polling Completo" active=1 → execution count=0 en 9d (158 totales en DB, 0 para este workflow)
```

**Conclusión pre-check:** 0 uso real desde 2026-08-27 (solo GET /health cada 15s). Consumidor declarado existe pero idle. Caddy tailnet-only sin tráfico. Condiciones para cuarentena cumplidas.

---

## 3. Cuarentena — stop (no rm)

**Comando ejecutado:**

```bash
docker stop duartec-local-whisper 2>&1 | head -10
# duartec-local-whisper
# STOP_EXIT:0

docker ps -a --format "{{.Names}} {{.Status}}" | grep whisper
# duartec-local-whisper Exited (143) 2 seconds ago

docker inspect duartec-local-whisper --format '{{.State.Status}} {{.State.ExitCode}} {{.HostConfig.RestartPolicy.Name}}'
# exited 143 unless-stopped

docker inspect duartec-local-whisper --format '{{.HostConfig.RestartPolicy.Name}}'
# unless-stopped  (documentado — ver §6 nota sobre reboot)

# Validación NO destrucción:
docker images duartec-voice-ai-whisper  # 521MB sigue presente
docker volume ls | grep whisper         # n/a bind mount, no borrado
ls -lh ~/duartec-infra/whisper_cache    # 75M intacto
docker ps -a | grep whisper             # Exited, no Removed
# NO se ejecutó: docker rm / docker volume rm / docker rmi
```

**Compose:** `~/duartec-infra/docker-compose.yml` **NO editado** (sin `cp` backup necesario). Justificación: `docker stop` es suficiente para cuarentena 30d; recreación solo ocurre con `up -d`. Editar compose añadiría riesgo de drift y conflicto con otros subagentes. Decisión documentada aquí en lugar de comentar servicio.

Si se requiriese persistir cuarentena tras reboot (ver §6), alternativa reversible es añadir `profiles: ["cuarentena"]` o `restart: "no"` con `cp docker-compose.yml docker-compose.yml.bak.20260906` previo — no aplicada en esta tanda por directiva "solo documenta".

---

## 4. Validación post (2026-09-06T03:06Z)

### 4.1 Contadores docker

```bash
docker ps --format "{{.Names}}" | wc -l
# 14   (antes: 15 con whisper Up => 14 tras stop; lista: ver abajo)
docker ps --format "{{.Names}}" | cat
# openclaw-sbx-workspace-978141e8e94438903a502f1cf4baa3bb
# duartec-email-store
# n8n-unified
# duartec-parts-caddy
# duartec-media-wrapper
# duartec-parts-mail-relay
# insforge-postgrest-1
# insforge-insforge-1
# insforge-deno-1
# insforge-postgres-1
# duartec-parts-mariadb
# duartec-parts-db-api
# n8n-runners
# duartec-ollama
# (whisper ausente de `docker ps`, presente en `docker ps -a` Exited)

# Nota conteo: investigación previa reportó 16 (o 24 en contexto tarea) según host/fecha.
# En esta ejecución real kiri-vnic: 15→14 running. Delta -1 correcto.
# No hay contenedores perdidos adicionales.

docker ps -a --format "{{.Names}} {{.Status}}" | cat
# duartec-local-whisper Exited (143) 20 seconds ago — resto Up
```

### 4.2 Conectividad rota esperada

```bash
docker exec n8n-unified wget -qO- http://whisper:5681/health 2>&1 | head -5
# wget: bad address 'whisper:5681'
# (DNS deja de resolver al estar stopped — embed DNS duartec-net no publica alias de contenedor parado)

docker exec n8n-unified wget -qO- http://duartec-local-whisper:5681/health 2>&1 | head -5
# wget: bad address 'duartec-local-whisper:5681'
# Equivalente a "Failed to connect / ENOTFOUND" — documentado como esperado.
# Workflow kc208 con continueOnFail=true no fallará el workflow pero logueará ENOTFOUND/bad address en execution log.
```

### 4.3 n8n y sistema sanos

```bash
docker logs n8n-unified --tail 20 2>&1 | tail -20
# Activated workflow "DUARTEC - Comparar modelos IA ..." ...
# Editor is now accessible via: https://n8n.tail4b3cf6.ts.net
# (sin crash nuevo, sin stacktrace whisper)

systemctl --failed 2>&1 | cat
# 0 loaded units listed.
# UNIT LOAD ACTIVE SUB DESCRIPTION — 0 failed

docker ps -a --format "{{.Names}} {{.Status}}" | grep -v whisper
# todos Up / healthy — mail-relay Up 3 days, email-store healthy, caddy Up 3 days, etc.
```

**Validación:** stop hecho sin impacto sistémico.

---

## 5. Ahorro y coste liberado

| Métrica                   | Antes (running)             | Después (Exited)             | Ahorro                      |
| ------------------------- | --------------------------- | ---------------------------- | --------------------------- |
| CPU                       | 0.11–0.13% (1 core cap 1.0) | 0%                           | ~0.13% 1 core               |
| RAM real                  | 14.3–16.7 MiB               | 0 MiB                        | ~16 MiB                     |
| RAM reservada (mem_limit) | 2 GiB                       | 0 (no reserva cuando Exited) | 2 GiB libres para scheduler |
| Disk image                | 521 MB (keep)               | 521 MB (keep)                | 0 (intencional cuarentena)  |
| Cache modelo tiny         | 75 MB (keep)                | 75 MB (keep)                 | 0 (intencional)             |
| Healthcheck IO            | GET /health cada 15s + logs | 0                            | ~5760 req/día menos         |
| PID limit                 | 256                         | 0                            | —                           |

**No se libera imagen/cache en cuarentena** por diseño reversible. Si tras 30d se confirma ELIMINAR: `docker rmi duartec-voice-ai-whisper` libera 521 MB + `rm -rf whisper_cache` 75 MB.

---

## 6. Notas y riesgos

- **RestartPolicy `unless-stopped`**: `docker stop` NO persiste tras reboot del host o `systemctl restart docker` — Docker reiniciará `unless-stopped` contenedores automáticamente. Para cuarentena estricta de 30d que sobreviva reboot, aplicar en próximo mantenimiento: `cp ~/duartec-infra/docker-compose.yml ~/duartec-infra/docker-compose.yml.bak.20260906-whisper &&` editar servicio a `restart: "no"` o añadir `profiles: ["cuarentena"]`. Hoy se optó por no editar compose para evitar drift; documentar y monitorizar `docker ps -a | grep whisper` tras cada reboot.
- **Caddy ruta intacta:** `caddy/conf.d/apis.caddy` mantiene `handle @whisper_authorized → reverse_proxy whisper:5681` → con whisper parado, Caddy responderá 502 Bad Gateway si alguien hace `POST /whisper*` autenticado por Tailscale. Dado que hubo 0 hits en 9d, riesgo despreciable; se mantiene para validar rollback sin recargar Caddy.
- **Workflow n8n:** `kc208PLh3kml8a1J` sigue `active=1`. El nodo HTTP `POST http://whisper:5681/transcribe` debe tener `continueOnFail=true` (verificado en pending: "ya está"). Si no, n8n marcará execution como error pero no crashea. Próxima auditoría (2026-10-06) consultar `execution_entity` filtrando `workflowId=kc208` y buscar `ENOTFOUND|bad address|ECONNREFUSED`.
- **Volumen bind:** `~/duartec-infra/whisper_cache` es directorio host, no volumen Docker; `docker volume ls` no lo lista — es esperado. No tocar.

---

## 7. Rollback (reversible en <1 min)

**Opción A — start directo (más rápido, usa imagen existente):**

```bash
docker start duartec-local-whisper
docker ps --format "{{.Names}} {{.Status}}" | grep whisper  # debe volver a Up (healthy) ~5s
docker exec n8n-unified wget -qO- http://whisper:5681/health  # {"ok":true,"model":"tiny"}
```

**Opción B — compose (recrea si se limpió, respeta compose):**

```bash
docker compose -f ~/duartec-infra/docker-compose.yml up -d whisper
# o: docker compose -f ~/duartec-infra/docker-compose.yml up -d --build whisper  (si Dockerfile cambió)
docker logs duartec-local-whisper --tail 20
```

**Si se había aplicado `restart: "no"` / `profiles` en compose:**

```bash
# restaurar backup
cp ~/duartec-infra/docker-compose.yml.bak.20260906-whisper ~/duartec-infra/docker-compose.yml
docker compose -f ~/duartec-infra/docker-compose.yml up -d whisper
```

Verificación post-rollback: `curl -s http://whisper:5681/health` vía `docker exec n8n-unified` debe dar `200 {"ok":true}` y `docker logs` sin POST previos (normal).

---

## 8. Próximos pasos (auditoría 2026-10-06)

1. `docker ps -a | grep whisper` — ¿sigue Exited?
2. `docker logs n8n-unified | grep -i "whisper.*bad address\|whisper.*ENOTFOUND\|transcribe" | tail -20` — ¿workflow intentó usarlo?
3. `docker exec caddy cat /var/log/caddy/access.log | grep whisper` — ¿alguien llamó `/whisper*` Tailnet?
4. `sqlite n8n.db: SELECT count(*) FROM execution_entity WHERE workflowId='kc208PLh3kml8a1J'` — ¿siguió en 0?
5. Si 0 errores/0 hits → proponer ELIMINAR: `docker rm -f duartec-local-whisper; docker rmi duartec-voice-ai-whisper; rm -rf ~/duartec-infra/whisper_cache;` + comentar bloque `apis.caddy` whisper + `docker compose restart caddy`.
6. Si >0 errores con necesidad voz → `docker start` y cerrar cuarentena.

---

**Estado final:** ✅ STOP hecho, validación OK, sin destrucción, rollback documentado. Artefacto: este fichero `~/infra-audit/G1-whisper.md`. No se tocó mail-relay, api-stub, tailscale.

**Evidencia base:** `pending-whisper-mail-apistub.md` + logs arriba reproducibles.
