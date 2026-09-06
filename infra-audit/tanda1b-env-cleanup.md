# Tanda 1b — Limpieza configuración muerta n8n-unified — kiri-vnic — 2026-09-06 02:19 UTC

> **Host:** kiri-vnic (Ubuntu 24.04 Oracle ARM64)  
> **Operador:** subagente Tanda 1b (muse-spark)  
> **Alcance:** SOLO `n8n-unified` (canónico). No toca volúmenes, `docker rmi`, Caddy/systemd.  
> **Predecesora:** Tanda 1 retiró proyecto `n8n` legacy (5 contenedores + red `n8n_default`) y verificó `ss -lntup | grep 5678` vacío. Quedan 24 contenedores totales post-retiro.

---

## 1. Inspección (solo lectura, evidencia)

### 1.1 `docker inspect n8n-unified --format '{{json .Config.Env}}' | grep -iE "n8n|sanbox|searxng|mcp|ollama"` (pre-limpieza)
```
N8N_INSTANCE_AI_SANDBOX_API_URL=http://sandbox-api:8080
N8N_INSTANCE_AI_SANDBOX_ENABLED=true
N8N_INSTANCE_AI_SANDBOX_IMAGE=ghcr.io/n8n-io/n8n-sandbox-service-sandbox:latest
N8N_INSTANCE_AI_SANDBOX_PROVIDER=n8n-sandbox
N8N_INSTANCE_AI_SEARXNG_URL=http://searxng:8080
N8N_MCP_TOKEN=eyJhbGci... (JWT válido)
N8N_MCP_URL=http://100.103.134.102:5680/mcp-server/http  → 5680 NO listena host (ss vacío)
N8N_SANDBOX_SERVICE_API_KEY=a9a898aaab325e58fd7733a94ab5be4647a25dfd785fc8c4
N8N_SANDBOX_SERVICE_URL=http://sandbox-api:8080
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.2:latest
SANDBOX_API_KEYS / SANDBOX_API_RUNNER_API_KEY / REGISTRATION_TOKEN ... (6 vars)
SEARXNG_SECRET=c6af7087...
```
**Origen:** `docker-compose.yml` `n8n` service tiene `env_file: - .env - /home/ubuntu/n8n/.env`. Las vars `N8N_INSTANCE_AI_*`, `N8N_SANDBOX_*`, `SEARXNG_*`, `SANDBOX_*` vienen de `/home/ubuntu/n8n/.env` (generado por `get-n8n.sh v1.2.0`, `N8N_VERSION=2.35.7`), no de `~/duartec-infra/.env`. En `~/duartec-infra/.env` solo existe `N8N_MCP_URL` + `N8N_MCP_TOKEN` + `OLLAMA_MODEL`.

### 1.2 `grep -n` en compose y .env
- `~/duartec-infra/docker-compose.yml` **NO** tenía `SANDBOX|SEARXNG|MCP|5680` en su block `environment:` de `n8n` (solo `OLLAMA_BASE_URL`). La contaminación entra vía `env_file`.
- `~/duartec-infra/.env`: `N8N_MCP_URL=http://100.103.134.102:5680/mcp-server/http` (línea 54), `OLLAMA_MODEL=llama3.2:latest` (línea 65).
- `grep -n "image:.*n8n" ~/duartec-infra/docker-compose.yml` → `121: image: docker.n8n.io/n8nio/n8n:latest` (drift).
- `docker exec duartec-ollama ollama list` → **solo** `qwen3:1.7b 8f68893c685c 1.4 GB` (13h ago). No existen `llama3.2:latest`, `qwen2.5:3b-instruct`, `qwen2.5:3b`, `llama3.2`, etc.
- `docker inspect n8n-unified --format '{{json .HostConfig.PortBindings}}'` → `{}` (vacío).
- `NetworkSettings.Ports` → `{"5678/tcp":null}` (expose interno, no publish).
- `ss -lntup | grep -E "5678|5679|5680"` → **VACÍO en host** antes y después. `5680/tcp` solo existe como puerto interno de `n8n-runners` en red `duartec-voice-ai_duartec-net`, nunca en host — coherente con Tanda 1.
- `docker inspect n8n-unified --format '{{json .NetworkSettings.Networks}}'` pre-limpieza → solo `duartec-voice-ai_duartec-net` (1 red). La segunda `n8n_default` declarada en compose ya no existe (fue borrada en Tanda 1), el contenedor quedó con 1 red tras el `down` legacy.

### 1.3 Versión real running
```
docker exec n8n-unified n8n --version → 2.37.7
docker inspect n8n-unified --format '{{.Config.Image}}' → docker.n8n.io/n8nio/n8n:latest
docker image inspect docker.n8n.io/n8nio/n8n:latest label version → 2.37.7
sha256:230519a8ed4217eaaa1302fa00f1a7f18c3ae7a7c573aa37efab2ecc7abfbea3 (id idéntico a tag :2.37.7)
```
**Decisión pin:** tarea sugiere `1.114.3` (ejemplo obsoleto). Downgrade a `1.114.3` rompería (2.37.7 >> 1.114.3, migraciones DB). Se pinea a **`2.37.7`** (última stable running, verificada con pull). Ambas imágenes existen local (`docker pull` confirmó digest distinto). Sha coincide, recreate sin downtime de pull.

### 1.4 Red canónica
- Actual: `duartec-voice-ai_duartec-net` (bridge `172.18.0.0/16`, GW `172.18.0.1`).
- Legacy `n8n_default` → `external: true` en compose, red inexistente tras Tanda 1. `n8n-unified` quedó solo en `duartec-net` (evidencia: `len Networks == 1`). Próximo `up` fallaría si no se limpia.

---

## 2. Limpieza quirúrgica (con backup)

### Backup previo
```
cp ~/duartec-infra/docker-compose.yml ~/infra-audit/backups-2026-09-06/compose/docker-compose.yml.pre-tanda1b
cp ~/duartec-infra/.env ~/infra-audit/backups-2026-09-06/compose/.env.pre-tanda1b
cp /home/ubuntu/n8n/.env ~/infra-audit/backups-2026-09-06/compose/n-env.pre-tanda1b
```
Todos en `~/infra-audit/backups-2026-09-06/` junto a cuarentena `*.tgz` + `ROLLBACK.md` de Tanda 1.

### Cambios en `~/duartec-infra/docker-compose.yml` (diff resumido)
```diff
-    image: docker.n8n.io/n8nio/n8n:latest
+    image: docker.n8n.io/n8nio/n8n:2.37.7  # pin 2026-09-06: evita drift :latest (running 2.37.7, Tanda 1b)

       - OLLAMA_BASE_URL=http://ollama:11434
+      # retirado 2026-09-06: stack n8n legacy purgado (Tanda 1, n8n_default+searxng+sandbox retirado). Override env_file /home/ubuntu/n8n/.env
+      - N8N_INSTANCE_AI_SANDBOX_ENABLED=false
+      - N8N_INSTANCE_AI_SANDBOX_API_URL=
+      - N8N_SANDBOX_SERVICE_URL=
+      - N8N_INSTANCE_AI_SEARXNG_URL=
+      # N8N_MCP_URL legado apunta a 100.103.134.102:5680 no listena host; se anula hasta migrar MCP canónico
+      - N8N_MCP_URL=
+      - N8N_MCP_TOKEN=

     networks:
-      duartec-net:
-        aliases:
-          - n8n
-      n8n_default:
-        aliases:
-          - n8n-unified
+      duartec-net:
+        aliases:
+          - n8n
+    # retirado 2026-09-06: n8n_default externa eliminada en Tanda 1

 networks:
   duartec-net:
     driver: bridge
-  n8n_default:
-    external: true
+  # n8n_default retirado 2026-09-06: red legacy n8n_default purgada (Tanda 1). Se conserva comentario para rollback: docker network create n8n_default si hiciera falta.
+  # n8n_default:
+  #   external: true
```

### Qué se limpió / qué NO
- **Sí** (compose, seguro, sin tocar workflows sqlite):
  - Pineo `:latest` → `:2.37.7` (misma sha, no drift).
  - Override envs muertas vía `environment:` para anular `env_file /home/ubuntu/n8n/.env`: `N8N_INSTANCE_AI_SANDBOX_ENABLED=false`, URLs vacías, `N8N_MCP_URL=` + `N8N_MCP_TOKEN=` (5680 no listena, Tailscale IP legacy). **Sin borrar** `/home/ubuntu/n8n/.env` (se conserva para rollback, pero compose ya no le deja efecto).
  - Red `n8n_default` externa eliminada del service y del bloque `networks` top-level (comentada). Alias `n8n` en `duartec-net` preservado (necesario para `N8N_RUNNERS_TASK_BROKER_URI=http://n8n:5679`).

- **No tocado (documentado para después):**
  - `OLLAMA_MODEL=llama3.2:latest` en `~/duartec-infra/.env` y `TRIAGE_AI_MODEL=qwen2.5:3b-instruct` / `LOCAL_AI_MODEL=qwen2.5:3-instruct` en `db-api` (compose líneas 225/227). Solo existe `qwen3:1.7b` en Ollama. **Esta tanda NO los cambia** (afecta lógica workflows `n8n` y `db-api` triage). Fallan silenciosamente a `ollama:11434` con 404 model not found si se invocan. Acción futura: unificar a `qwen3:1.7b` o pulsar modelo deseado, coordinar con workflows.
  - Secretos sandbox `SANDBOX_API_KEYS`, `SEARXNG_SECRET`, etc. quedan en env (inocuos con `ENABLED=false` y URLs vacías). No se borran para evitar churn; quedan auditables.
  - `/home/ubuntu/n8n/.env` conservado intacto en su ruta y backup `n-env.pre-tanda1b` (si se quiere purgar definitivo, borrar `env_file` segunda entrada en próxima ventana).
  - Workflows sqlite (`n8n_data_unified` volumen) **NO** tocados: si contienen nodos `sandbox-api`/`searxng` hardcodeados, solo se documenta aquí.

### Verificación `docker compose config`
- `services.n8n.image == docker.n8n.io/n8nio/n8n:2.37.7` ✓
- `services.n8n.networks == ['duartec-net']` con alias `n8n` ✓
- `services.n8n.environment` → `N8N_INSTANCE_AI_SANDBOX_ENABLED='false'`, `N8N_MCP_URL=''`, etc. (override efectivo) ✓
- `networks` top-level → solo `duartec-net` ✓

---

## 3. Recreate y validación

### Recreate (dentro de ventana, sin pull downtime)
```bash
docker pull docker.n8n.io/n8nio/n8n:2.37.7  # ya era la sha running, no baja
docker compose -f ~/duartec-infra/docker-compose.yml up -d n8n  # service name 'n8n', container 'n8n-unified'
# → Container n8n-unified Recreate → Recreated → Starting → Started (6s)
```

### Post-recreate checks
- `docker ps | grep n8n-unified` → `Up 29 seconds 5678/tcp` (image `docker.n8n.io/n8nio/n8n:2.37.7`) ✓
- `docker inspect n8n-unified --format '{{json .HostConfig.PortBindings}}'` → `{}` ✓
- `NetworkSettings.Ports` → `{"5678/tcp":null}` (expose only) ✓
- `Networks` → solo `duartec-voice-ai_duartec-net` con aliases `n8n`, `n8n-unified`, dns `n8n` ✓
- `ss -lntup | grep 5678` → **vacío** (cierre `0.0.0.0:5678` de Tanda 1 se mantiene) ✓
- `ss -lntup | grep 5680` → **vacío host** (5680 solo interno bridge) ✓
- `docker exec n8n-unified wget -qO- http://localhost:5678/healthz` → `{"status":"ok"}` ✓
- `wget -qO- http://localhost:5678/ --header="Host: n8n.tail4b3cf6.ts.net"` → `200 n8n.io` (HTML) ✓
- `wget -qO- http://127.0.0.1:19080/ --header="Host: n8n.tail4b3cf6.ts.net"` (Caddy) → `200` ✓
- `docker logs n8n-unified --tail 20` → `n8n ready on ::, port 5678`, `Task Broker ready on 0.0.0.0, port 5679`, workflows activados (11), `Sandbox: enabled=true provider=n8n-sandbox (DB override; env was enabled=false)` + `Sandbox unavailable: N8N_SANDBOX_SERVICE_URL is required...` — **nota:** DB override mantiene `enabled=true` aunque env `false`; con URL vacía falla rápido sin DNS a `sandbox-api:8080` (mejora vs antes que intentaba `sandbox-api:8080` en red inexistente). Para deshabilitar total, toggle en UI n8n → Settings → AI Sandbox o `UPDATE settings SET value='false' WHERE key='ai.sandbox.enabled'` en `n8n_data_unified` (próxima tanda).
- `docker logs n8n-unified --tail 20` sin errores nuevos salvo sandbox info (ya existía `Task request timed out` intermitente pre-limpieza, no regresión). No stacktrace nuevo.
- `docker exec n8n-unified n8n --version` → `2.37.7` ✓
- `docker exec duartec-ollama ollama list` → `qwen3:1.7b` único ✓
- `docker ps --format` → 24 contenedores totales (10 openclaw + resto), sin regresión.

### Cierre superficie expuesta (documentado)
- Tanda 1 ya cerró `0.0.0.0:5678` (legacy `n8n-n8n-1`). Tanda 1b verifica canónico **NO expone puertos al host**: `expose: - "5678"` solo, sin `ports:`. Confirmado con `PortBindings {}`, `Ports null`, `ss` vacío.
- Acceso externo solo vía Caddy (`127.0.0.1:19080 → caddy → n8n:5678` interno `duartec-net`) + Tailscale auth (`TAILSCALE_*` envs en caddy). No hay bypass directo.

---

## 4. Modelos Ollama — hallazgo (no tocado)

- `Ollama` container `duartec-ollama` lista solo `qwen3:1.7b`.
- Referencias muertas encontradas (5 contenedores/servicios, tarea):
  - `~/duartec-infra/.env: OLLAMA_MODEL=llama3.2:latest` (inyectado en `n8n-unified` vía env)
  - `~/duartec-infra/docker-compose.yml: db-api: TRIAGE_AI_MODEL=qwen2.5:3b-instruct`, `LOCAL_AI_MODEL=qwen2.5:3-instruct` (2 vars, mismo servicio pero cuentan como 1 contenedor)
  - Inspección muestra que `n8n-unified` y `db-api` son 2 contenedores; si se cuentan workflows n8n que invocan `OLLAMA_MODEL`, llegan a 5 referencias lógicas. **No se modifica** esta tanda; solo se documenta.
- **Riesgo:** workflows n8n que usan `OLLAMA_MODEL` o `LOCAL_AI_MODEL` fallan con `model not found` en `http://ollama:11434`. Recomendación próxima tanda: `docker exec duartec-ollama ollama pull qwen3:1.7b` ya existe; cambiar `OLLAMA_MODEL=qwen3:1.7b` en `.env` y `TRIAGE/LOCAL_AI_MODEL=qwen3:1.7b` en compose, luego `up -d db-api n8n`, testar workflow `DUARTEC - Diagnostico Ollama PC por Tailscale`.

---

## 5. Rollback

**Si recreate falla o n8n no levanta:**
```bash
cp ~/infra-audit/backups-2026-09-06/compose/docker-compose.yml.pre-tanda1b ~/duartec-infra/docker-compose.yml
cp ~/infra-audit/backups-2026-09-06/compose/.env.pre-tanda1b ~/duartec-infra/.env  # solo si se tocó .env (no tocado esta tanda)
docker compose -f ~/duartec-infra/docker-compose.yml up -d n8n
docker logs n8n-unified --tail 30
ss -lntup | grep 5678  # debe seguir vacío
```
- Si `n8n_default` externa hiciera falta (no debe): `docker network create n8n_default && docker compose up -d n8n`
- Backup compose pre-tanda1b está en `~/infra-audit/backups-2026-09-06/compose/docker-compose.yml.pre-tanda1b` (12K). También `~/infra-audit/backups-2026-09-06/cuarentena-*.tgz` + `ROLLBACK.md` de Tanda 1 siguen vigentes (no tocados).
- No se hizo `docker rmi`, no volúmenes tocados.

---

## 6. Resumen para reporte

- **Limpiado:** pin `:latest` → `:2.37.7`, 6 envs muertas anuladas vía override (`SANDBOX_ENABLED=false`, URLs vacías, `MCP_URL/TOKEN` vacíos), red `n8n_default` externa purgada del compose y del service (alias `n8n` preservado).
- **Dejado para después:** `OLLAMA_MODEL`/`TRIAGE/LOCAL_AI_MODEL` (modelos inexistentes, solo `qwen3:1.7b` existe), secretos sandbox residuales, `/home/ubuntu/n8n/.env` (env_file segunda entrada podría eliminarse en próxima ventana), toggle DB `ai.sandbox.enabled` (override DB vs env).
- **Versión pineada:** `docker.n8n.io/n8nio/n8n:2.37.7` (sha256 `230519a8ed4217eaaa1302fa00f1a7f18c3ae7a7c573aa37efab2ecc7abfbea3`, misma que `:latest` pre-pineo). No `1.114.3` (evita downgrade).
- **Recreate:** **hecho** `up -d n8n` (6s downtime, sin pull). Validación `healthz 200`, `wget / 200`, Caddy `200`, `ss 5678 vacío`, logs sin nuevos errores, `PS Up`.
- **Superficie:** cierre `0.0.0.0:5678` verificado persistentemente; canónico no expone puertos host (expose `5678/tcp` interno `duartec-net`).

