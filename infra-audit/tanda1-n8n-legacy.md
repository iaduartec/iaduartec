# Tanda 1 — Retiro stack n8n legacy (1 a 1) — kiri-vnic — 2026-09-06 02:16 UTC

> **Host:** kiri-vnic (Ubuntu 24.04, Oracle ARM64)  
> **Operator:** subagente Tanda 1 (muse-spark)  
> **Objetivo:** retirar SOLO proyecto compose `n8n` (5 servicios) sin tocar `n8n-unified` ni `duartec-voice-ai_n8n_data_unified`  
> **Compose:** `~/n8n/compose.yml` (idéntico a backup `~/infra-audit/backups-2026-09-06/compose/n8n-compose.yml`)  
> **Backup cuarentena:** `~/infra-audit/backups-2026-09-06/` (tars + ROLLBACK.md)

---

## 1. Pre-check (solo lectura, evidencia previa)

### docker ps -a (filtro n8n)
```
n8n-unified                 docker.n8n.io/n8nio/n8n:latest                        Up 3 days   5678/tcp
n8n-runners-1               ghcr.io/n8n-io/runners:2.35.7                         Up 2 weeks  5680/tcp
n8n-sandbox-runner-1-1      ghcr.io/n8n-io/n8n-sandbox-service-runner-dind:latest Up 2 weeks  2375-2376/tcp, 8080/tcp
n8n-n8n-1                   ace03195c465                                          Up 2 weeks  0.0.0.0:5678->5678/tcp, [::]:5678->5678/tcp
n8n-sandbox-api-1           ghcr.io/n8n-io/n8n-sandbox-service-api:latest         Up 2 weeks (healthy) 8080/tcp, 9090/tcp
n8n-searxng-1               ghcr.io/searxng/searxng:latest                        Up 2 weeks  8080/tcp
n8n-runners                 n8nio/runners:latest                                  Up 2 weeks  5680/tcp   ← runner canónico de n8n-unified (proyecto duartec-voice-ai)
+ 10 openclaw-sandbox workspaces, resto duartec/insforge = 29 activos
```

### docker volume ls | grep n8n
```
duartec-voice-ai_n8n_data_unified
n8n_n8n-data
n8n_sandbox-tls
```

### docker network ls | grep n8n
```
0c533ab473f9  n8n_default  bridge  local
0551a2d52c40  duartec-voice-ai_duartec-net  bridge  local
```

### ss -lntup | grep 5678/5680 (antes)
```
tcp LISTEN 0 4096 0.0.0.0:5678 0.0.0.0:*   ← n8n-n8n-1 (único puerto expuesto a internet)
tcp LISTEN 0 4096 [::]:5678 [::]:*
# 5680 NO escucha en host — solo 5680/tcp interno docker (n8n-runners y n8n-runners-1). Verificado con ss sin match.
```

### curl estado previo
- `curl -w %{http_code} http://127.0.0.1:5678/` → **200** body `<!DOCTYPE html> <title>n8n.io - Workflow Automation` (legacy n8n-n8n-1 respondía)
- `curl http://127.0.0.1:5680/` → **000** (no hay servicio host en 5680; runners solo internos — esperado, no es fallo)
- `which -a n8n` → vacío (exit 1)
- `ps aux | grep n8n` → 2 procesos `opc`:
  - PID 373144: `node /usr/local/bin/n8n`
  - PID 2044933: `node /usr/local/bin/n8n`
  - `docker top n8n-n8n-1` confirma hostPid 2044848 (tini) → hijo 2044933 (node) — indica user-namespace. Ver hallazgo falso positivo abajo.
- `docker images` dangling: `ace03195c465` 1.48GB <untagged> (legacy n8n image sin tag, N8N_VERSION=2.35.7)

---

## 2. Retiro stack legacy — comando 1 a 1

```bash
docker compose -f ~/n8n/compose.yml -p n8n down
```

**Salida (exit 0):**
```
 Container n8n-runners-1  Stopping → Stopped → Removing → Removed
 Container n8n-sandbox-runner-1-1  Stopping → Stopped → Removing → Removed
 Container n8n-n8n-1  Stopping → Stopped → Removing → Removed
 Container n8n-sandbox-api-1  Stopping → Stopped → Removing → Removed
 Container n8n-searxng-1  Stopping → Stopped → Removing → Removed
 Network n8n_default  Removing → Removed
```

**Verificación post-down:**
- `docker ps -a | grep -E "n8n-n8n-1|n8n-runners-1|n8n-sandbox|n8n-searxng"` → **vacío** (NONE legacy — OK)
- `docker network ls | grep n8n_default` → **vacío gone** (solo queda `duartec-voice-ai_duartec-net`, `insforge_insforge-network`, `bridge`)
- `docker volume ls | grep n8n` → **preservados** (NO borrados, cuarentena 14d):
  ```
  duartec-voice-ai_n8n_data_unified  ← canónico, NO tocado
  n8n_n8n-data                       ← cuarentena (tar ~/infra-audit/backups-2026-09-06/cuarentena-n8n-data.tgz 427K)
  n8n_sandbox-tls                    ← cuarentena (tar 12K)
  ```
- `docker ps --format ... | wc -l` → **24** (29−5=24) OK.

**Sin contenedores colgados** — no hizo falta `docker rm -f`.  
**No se ejecutó** `docker volume rm` ni `docker rmi` (cuarentena 14d, candidatos solo anotados).

### Candidatos cuarentena (NO borrados, anotados):
- Imagen dangling `ace03195c465` (1.48GB, N8N 2.35.7 sin tag)
- `ghcr.io/n8n-io/runners:2.35.7` (448MB, ab8e375962a9)
- `ghcr.io/n8n-io/n8n-sandbox-service-api:latest` (44.3MB, db58a48ab8eb)
- `ghcr.io/n8n-io/n8n-sandbox-service-runner-dind:latest` (382MB, 437ef7a9fde4)
- `ghcr.io/searxng/searxng:latest` (255MB, 8e2bca2a1402)

---

## 3. Documenta falso positivo "n8n nativo del usuario opc"

> **Conclusión:** NO hay n8n bare-metal. NO se purga `/usr/local/bin/n8n`. `which -a n8n` vacío en host confirma. Las evidencias FASE 8 estaban equivocadas por user-namespace de Docker.

**Pruebas:**

1. `which -a n8n` → exit 1 vacío (no hay binario en host).
2. `docker top n8n-n8n-1` (ANTES del down):
   ```
   UID  PID      PPID  CMD
   opc  2044848  2044793  tini -- /docker-entrypoint.sh
   opc  2044933  2044848  node /usr/local/bin/n8n
   ```
   → PID host 2044933 coincide con el "nativo" reportado como `opc 2044933 node /usr/local/bin/n8n` en `ps aux` host. Es el mismo proceso visto vía user namespace remapped a uid `opc`, no un proceso host.
3. `docker top n8n-unified` (DESPUÉS del down, persiste):
   ```
   opc  373089  373066  tini -- /docker-entrypoint.sh
   opc  373144  373089  node /usr/local/bin/n8n
   ```
   → PID 373144 (el otro "nativo" reportado) pertenece a `n8n-unified`, hostPid 373089.
4. `cat /proc/373144/cgroup` → `0::/system.slice/docker-a6c5df6d6ff13c99e2806fd25431a95f0c08d39db4ee1bec6e40ad834b36e3bb.scope` (cgroup docker, no host systemd)
   `sudo ls -l /proc/373144/ns/pid` → `pid:[4026534282]` vs `n8n-unified` hostPid 373089 `pid:[4026534282]` (mismo namespace).
   Tras el `down`, PID 2044933 desapareció de `ps aux` (legacy muerto), PID 373144 permaneció (canónico) — validación cruzada perfecta.
5. `ROLLBACK.md` ya corregía: `/etc/systemd/system/n8n.service` **disabled/inactive**, docker-run legacy inactivo en `/srv/apps/n8n`.

**Acción:** Documentado, NO se ejecutó `rm /usr/local/bin/n8n`, `systemctl stop n8n`, `pkill n8n`, ni purga. Si en el futuro aparece un `n8n start` manual (`sudo -u opc n8n start`), documentar y crear servicio systemd/tmux ad-hoc.

---

## 4. Post-check + validación funcional (FASE 12 parcial)

### docker ps --format "{{.Names}} ({{.Status}})" | sort (24 activos)
```
duartec-email-store (Up 33s healthy)
duartec-local-whisper (Up 9 days healthy)
duartec-media-wrapper (Up 25h healthy)
duartec-ollama (Up 12h)
duartec-parts-caddy (Up 3 days)
duartec-parts-db-api (Up 2 weeks healthy)
duartec-parts-mail-relay (Up 3 days)
duartec-parts-mariadb (Up 7 days healthy)
insforge-deno-1 (Up 2 weeks healthy)
insforge-insforge-1 (Up 2 weeks)
insforge-postgres-1 (Up 2 weeks healthy)
insforge-postgrest-1 (Up 2 weeks healthy)
n8n-runners (Up 2 weeks)             ← canónico duartec-voice-ai, 5680/tcp interno
n8n-unified (Up 3 days)              ← canónico, 5678/tcp interno
+ 10× openclaw-sbx-workspace-* (Up 27-40h)
```

- `docker ps | grep n8n-unified` → **Up 3 days 5678/tcp** (running=true, started 2026-09-03T01:39:38Z)
- `docker inspect n8n-unified --format '{{.State.Status}}'` → `running`

### ss -lntup
- `ss | grep 5678` → **VACÍO** ✅ (cierre de 0.0.0.0:5678 es el objetivo de seguridad — conseguido)
- `ss | grep 5680` → **VACÍO en host** (nota: `n8n-runners` expone `5680/tcp` solo en red bridge `duartec-voice-ai_duartec-net`, no en host — esperado. Ni el runner canónico ni el legacy exponían 5680 al host.)
- Puertos restantes OK en ss: 19080/2019 (caddy), 3306 (mariadb interna), 11434 (ollama no en ss porque solo docker), 7130-7131, etc.

### Valida n8n canónico
- `docker exec n8n-unified wget -qO- http://localhost:5678/` → **200** `<!DOCTYPE html> n8n.io - Workflow Automation` (resto `cmVzdA==`, sentry `release=n8n@2.37.x`), `wget exit:0`
- `docker logs n8n-unified --tail 40 | grep` → `Pruning old insights data`, `401 unauthorized` esporádico, `AxiosError: Request failed with status code 401` (tráfico workflows, no crítico), sin crash. Últimos logs no muestran pérdida de servicio tras el down.
- Canónico es `n8n-unified` (duartec-voice-ai, 33wf, 73exec/7d, sqlite 37.7M) — intacto, no tocado.

### systemctl / journal
- `systemctl --failed` → **1 unidad falla**: `postfix@-.service` (failed, falta /etc/postfix/main.cf — preexistente, no relacionado con esta tanda; periódica `fatal: open /etc/postfix/main.cf: No such file or directory` cada minuto)
- `journalctl -p err --since "5 min ago"` → `networkctl: Interface "veth*" / "br-0c533ab473f9" not found.` (remoción red n8n_default — esperable tras down, ruido networkd), resto postfix descrito.

### docker stats --no-stream
```
n8n-unified 286.6MiB / 23.41GiB 0.07%   ← estable
duartec-ollama 49MiB, mariadb 153MiB, media-wrapper 604MiB/2GiB es el top
n8n-runners 18.72MiB (canónico)
```

### ps después
- `ps aux | grep n8n` → solo `opc 373144 node /usr/local/bin/n8n` (n8n-unified). 2044933 gone — confirmación legacy retirado.

---

## 5. Reporte final

### Qué se retiró
- Proyecto compose `n8n` (5 contenedores): `n8n-n8n-1` (ace03195c465, 0wf, 0.0.0.0:5678), `n8n-runners-1` (5680/tcp), `n8n-sandbox-api-1` (healthy), `n8n-sandbox-runner-1-1` (dind privileged), `n8n-searxng-1`. Red `n8n_default` (172.20.0.0/16, br-0c533ab473f9) eliminada. `docker compose -p n8n down` sin `--volumes`.

### Qué NO se tocó (cuarentena 14d)
- Volúmenes: `n8n_n8n-data`, `n8n_sandbox-tls` preservados (tars en `~/infra-audit/backups-2026-09-06/cuarentena-*.tgz`), volumen canónico `duartec-voice-ai_n8n_data_unified` intacto.
- Imágenes: NO `docker rmi` (candidatas anotadas arriba).
- Todo `duartec-voice-ai` (n8n-unified, n8n-runners, caddy, ollama, mariadb, etc.) y openclaw/insforge.
- Binario `/usr/local/bin/n8n` inexistente en host — no purgado (falso positivo explicado).

### Validación
- `docker ps` 24 activos (29−5) ✅, `n8n-unified` Up 3d ✅, `ss 0.0.0.0:5678` VACÍO (cierre seguridad) ✅, `ss 5680` vacío host pero 5680/tcp interno ok (n8n-runners) ✅, `wget localhost:5678` dentro de n8n-unified 200 ✅, `docker logs` sin crash ✅, `systemctl --failed` solo postfix preexistente ⚠️, `journalctl` solo ruido veth/br post-down.

### Rollback
Apunta a `~/infra-audit/backups-2026-09-06/ROLLBACK.md` §1:
```bash
docker compose -f ~/n8n/compose.yml up -d
# o desde backup:
docker compose -f ~/infra-audit/backups-2026-09-06/compose/n8n-compose.yml --env-file ~/infra-audit/backups-2026-09-06/compose/n8n-legacy.env up -d
# fallback:
docker start n8n-n8n-1 n8n-runners-1 n8n-sandbox-api-1 n8n-sandbox-runner-1-1 n8n-searxng-1
# restaurar volúmenes si daño:
docker volume create n8n_n8n-data && docker run --rm -v n8n_n8n-data:/data -v ~/infra-audit/backups-2026-09-06:/backup ubuntu tar xzf /backup/cuarentena-n8n-data.tgz -C /data
```

### Próximo riesgo
- **Bajo para esta tanda.** 5678 cerrado al exterior ✅. Queda decidir destino volúmenes cuarentena tras 14d (`docker volume rm n8n_n8n-data n8n_sandbox-tls`) y `docker rmi ace03195c465` + imágenes runners/sandbox/searxng si no se revierte.
- **Medio fuera de scope:** `postfix@-.service` failed persistente (sin main.cf), no crítico pero spam journal; y `systemd/networkctl` veth efímeros tras down (normal).
- **No tocar en Tanda 2** sin revisión: `duartec-voice-ai_n8n_data_unified` (52M tar validado) y caddy host.

---
*Generado 2026-09-06T02:16Z — subagente Tanda 1 — 1 comando: `docker compose -p n8n down`.*
