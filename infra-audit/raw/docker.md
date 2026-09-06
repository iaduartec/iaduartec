# Auditoría Docker — Host kiri-vnic (Oracle Cloud ARM64, Ubuntu 24.04)

**Fecha:** 2026-09-06 · **Modo:** SOLO LECTURA (ningún cambio realizado) · **Método:** docker ps/inspect/logs/ls/sqlite3(ro)/ss/systemctl cat/tailscale serve status
**Nota de secretos:** todos los valores de env sensibles (passwords, tokens, API keys, hashes) fueron redactados; solo se listan nombres de claves.

---

## 1. Inventario general

### 1.1 docker ps -a (29 contenedores, TODOS activos, 0 parados)

| Contenedor                                                 | Imagen                                                      | Estado               | Puertos                    |
| ---------------------------------------------------------- | ----------------------------------------------------------- | -------------------- | -------------------------- |
| openclaw-sbx-workspace-978141… (y 9 más con IDs distintos) | openclaw-sandbox:bookworm-slim                              | Up 27–40 h           | — (red: none)              |
| n8n-unified                                                | docker.n8n.io/n8nio/n8n:latest                              | Up 3 days            | 5678/tcp (solo interno)    |
| duartec-parts-caddy                                        | caddy:2.8.4-alpine                                          | Up 3 days            | 127.0.0.1:19080→80         |
| duartec-media-wrapper                                      | duartec-voice-ai-media (build)                              | Up 25 h (healthy)    | 127.0.0.1:5682, 5999, 6080 |
| duartec-parts-mail-relay                                   | duartec-voice-ai-mail-relay (build)                         | Up 3 days            | 8080/tcp interno           |
| duartec-local-whisper                                      | duartec-voice-ai-whisper (build)                            | Up 9 days (healthy)  | 5681/tcp interno           |
| n8n-runners-1                                              | ghcr.io/n8n-io/runners:2.35.7                               | Up 13 days           | 5680/tcp interno           |
| n8n-sandbox-runner-1-1                                     | ghcr.io/n8n-io/n8n-sandbox-service-runner-dind:latest       | Up 13 days           | 2375-2376, 8080 internos   |
| n8n-n8n-1                                                  | docker.io/n8nio/n8n:2.35.7 → **ID ace03195c465 (dangling)** | Up 13 days           | **0.0.0.0:5678→5678**      |
| n8n-sandbox-api-1                                          | ghcr.io/n8n-io/n8n-sandbox-service-api:latest               | Up 13 days (healthy) | 8080, 9090 internos        |
| n8n-searxng-1                                              | ghcr.io/searxng/searxng:latest                              | Up 13 days           | 8080/tcp interno           |
| insforge-postgrest-1                                       | postgrest/postgrest:v12.2.12                                | Up 2 weeks (healthy) | 127.0.0.1:3002→3000        |
| insforge-insforge-1                                        | local/insforge-oss:v1.5.0-redacted                          | Up 2 weeks           | 127.0.0.1:7130-7131        |
| insforge-deno-1                                            | ghcr.io/insforge/deno-runtime:latest                        | Up 2 weeks (healthy) | 7133/tcp interno           |
| insforge-postgres-1                                        | ghcr.io/insforge/postgres-all:latest                        | Up 2 weeks (healthy) | 5432/tcp interno           |
| duartec-parts-mariadb                                      | mariadb:11.4                                                | Up 7 days (healthy)  | 3306/tcp interno           |
| duartec-parts-db-api                                       | duartec-voice-ai-db-api (build)                             | Up 2 weeks (healthy) | 8080/tcp interno           |
| n8n-runners                                                | n8nio/runners:latest                                        | Up 2 weeks           | 5680/tcp interno           |
| duartec-email-store                                        | node:24-bookworm-slim                                       | Up <1 min (healthy)  | 5679/tcp interno           |
| duartec-ollama                                             | ollama/ollama:latest                                        | Up 11 h              | 11434/tcp interno          |

### 1.2 docker compose ls

| Proyecto         | Estado      | Config                                        |
| ---------------- | ----------- | --------------------------------------------- |
| duartec-voice-ai | running(10) | /home/ubuntu/duartec-infra/docker-compose.yml |
| insforge         | running(4)  | /home/ubuntu/apps/insforge/docker-compose.yml |
| n8n              | running(5)  | /home/ubuntu/n8n/compose.yml                  |

Compose files SIN proyecto activo: `/srv/apps/web-duartec/compose/compose.yaml` (conflicto puerto 3000 con systemd), `/srv/apps/api-service/compose/compose.yaml` (corre como systemd api-stub), `/srv/ai/openclaw-lite/compose/compose.yaml`, `/home/ubuntu/ocmonitor-share/docker-compose.yml` (imagen `ocmonitor` no existe).

### 1.3 docker images (20 tagged + 1 dangling, 13.77 GB)

Todas las imágenes están en uso por ≥1 contenedor (docker system df: TOTAL 20, ACTIVE 20). No hay imágenes huérfanas. 1 imagen dangling: `ace03195c465` (n8n 2.35.7, 1.48 GB, tag eliminado) — en uso por n8n-n8n-1.

### 1.4 docker volume ls (13)

| Volumen                           | Montado en                                    | Tamaño                                        |
| --------------------------------- | --------------------------------------------- | --------------------------------------------- |
| c4518f07… (anónimo)               | n8n-sandbox-runner-1-1:/var/lib/docker (dind) | **894M**                                      |
| duartec-voice-ai_mariadb_data     | duartec-parts-mariadb:/var/lib/mysql          | **843M**                                      |
| duartec-voice-ai_n8n_data_unified | n8n-unified:/home/node/.n8n                   | **130M** (incl. 3 backups sqlite legacy ≈36M) |
| insforge_postgres-data            | insforge-postgres-1                           | 91M                                           |
| insforge_deno_cache               | insforge-deno-1:/deno-dir                     | 16M                                           |
| duartec-voice-ai_caddy_logs       | duartec-parts-caddy                           | 14M                                           |
| n8n_n8n-data                      | n8n-n8n-1:/home/node/.n8n                     | 5.5M (DB muerta)                              |
| n8n_sandbox-tls                   | sandbox-api + sandbox-runner                  | menor                                         |
| duartec-voice-ai_caddy_data       | duartec-parts-caddy:/data                     | 24K                                           |
| insforge_storage-data             | insforge-insforge-1:/insforge-storage         | **8K (vacío)**                                |
| insforge_insforge-logs            | insforge-insforge-1                           | menor                                         |
| 5efaa7f8… (anónimo)               | n8n-searxng-1:/etc/searxng                    | 8K                                            |
| f35819ff… (anónimo)               | n8n-searxng-1:/var/cache/searxng              | 8K                                            |

### 1.5 Redes (6)

`bridge`, `host`, `none` (default) + `duartec-voice-ai_duartec-net` (10 servicios), `insforge_insforge-network` (4), `n8n_default` (5).

### 1.6 docker system df

Images 20/13.77GB · Containers 29/190MB · Volumes 13/1.94GB · Build cache 0.

### 1.7 docker stats (top RAM)

| Contenedor                    | RAM                              | CPU   |
| ----------------------------- | -------------------------------- | ----- |
| duartec-media-wrapper         | 606MiB (límite 2Gi)              | 3.45% |
| n8n-unified                   | 287MiB                           | 0.03% |
| n8n-n8n-1                     | 241MiB                           | 0.07% |
| duartec-email-store           | 161MiB                           | 0.01% |
| duartec-parts-mariadb         | 154MiB                           | 0.01% |
| n8n-sandbox-runner-1-1 (dind) | 144MiB                           | 0.06% |
| insforge-insforge-1           | 58MiB                            | —     |
| duartec-parts-caddy           | 56MiB                            | —     |
| duartec-ollama                | 49MiB (modelo descargado de RAM) | —     |
| 10× openclaw-sbx-workspace    | ~0.5MiB c/u                      | 0%    |

Suma de contenedores ≈ 2.05 GiB de 23.4 GiB (los ~7G de `free` incluyen page cache del host).

---

## 2. Inspección por contenedor (labels, mounts, health, restart, creado)

| Contenedor                 | Proyecto compose               | Restart                      | Health  | Creado (UTC)                        | Mounts fuente                                                                              |
| -------------------------- | ------------------------------ | ---------------------------- | ------- | ----------------------------------- | ------------------------------------------------------------------------------------------ |
| n8n-unified                | duartec-voice-ai (svc n8n)     | unless-stopped               | —       | 2026-09-03 01:39                    | vol n8n_data_unified:/home/node/.n8n; binds: ~/.nvm, duartec-infra, DUARTEC                |
| duartec-parts-caddy        | duartec-voice-ai (caddy)       | unless-stopped               | —       | 2026-09-02 23:53                    | vols caddy_data, caddy_logs; bind duartec-infra/caddy→/etc/caddy; dashboard→/srv-dashboard |
| duartec-media-wrapper      | duartec-voice-ai (media)       | unless-stopped               | healthy | 2026-09-02 23:53 (reiniciado 09-05) | binds: ~/.config/mission-bridge-chromium, yt-cookies.txt                                   |
| duartec-parts-mail-relay   | duartec-voice-ai (mail-relay)  | unless-stopped               | —       | 2026-09-02 23:53                    | —                                                                                          |
| duartec-local-whisper      | duartec-voice-ai (whisper)     | unless-stopped               | healthy | 2026-08-27 19:48                    | bind whisper_cache→/cache/huggingface                                                      |
| duartec-parts-mariadb      | duartec-voice-ai (mariadb)     | unless-stopped (RC=1)        | healthy | 2026-07-19 06:22                    | vol mariadb_data                                                                           |
| duartec-parts-db-api       | duartec-voice-ai (db-api)      | unless-stopped (RC=6)        | healthy | 2026-07-18 22:42                    | binds: db-api→/app, DUARTEC, portfolio.json                                                |
| duartec-ollama             | duartec-voice-ai (ollama)      | unless-stopped (RC=1)        | —       | 2026-06-20 23:53                    | bind **~/.ollama→/root/.ollama**                                                           |
| duartec-email-store        | duartec-voice-ai (email-store) | unless-stopped (**RC=2603**) | healthy | 2026-07-10 10:04                    | binds: package.json/lock, email_store_mariadb.js, DUARTEC                                  |
| n8n-runners                | duartec-voice-ai (n8n-runners) | unless-stopped               | —       | 2026-07-10 14:21                    | —                                                                                          |
| n8n-n8n-1                  | n8n (svc n8n)                  | no                           | —       | 2026-08-23 02:28                    | vol n8n_n8n-data:/home/node/.n8n                                                           |
| n8n-runners-1              | n8n (runners)                  | no                           | —       | 2026-08-23 02:28                    | —                                                                                          |
| n8n-sandbox-api-1          | n8n (sandbox-api)              | no                           | healthy | 2026-08-23 02:28                    | vol n8n_sandbox-tls                                                                        |
| n8n-sandbox-runner-1-1     | n8n (sandbox-runner-1)         | no                           | —       | 2026-08-23 02:28                    | vol dind /var/lib/docker + n8n_sandbox-tls                                                 |
| n8n-searxng-1              | n8n (searxng)                  | no                           | —       | 2026-08-23 02:27                    | 2 vols anónimos + bind searxng-settings.yml                                                |
| insforge-postgres-1        | insforge (postgres)            | unless-stopped               | healthy | 2026-08-23 00:27                    | vol postgres-data                                                                          |
| insforge-postgrest-1       | insforge (postgrest)           | unless-stopped               | healthy | 2026-08-23 00:28                    | —                                                                                          |
| insforge-insforge-1        | insforge (insforge)            | unless-stopped               | —       | 2026-08-23 00:28                    | vols storage-data, insforge-logs                                                           |
| insforge-deno-1            | insforge (deno)                | unless-stopped               | healthy | 2026-08-23 00:27                    | vol deno_cache                                                                             |
| openclaw-sbx-workspace-×10 | — (docker run efímero)         | no                           | —       | 2026-09-04 10:10–22:51              | binds tmp/openclaw-setup-inference-*, workspaces skills; red **none**                      |

---

## 3. Compose files activos

### 3.1 /home/ubuntu/duartec-infra/docker-compose.yml — proyecto duartec-voice-ai (10 servicios)

| Servicio          | Imagen                            | Puertos                  | Volúmenes                                          | depends_on |
| ----------------- | --------------------------------- | ------------------------ | -------------------------------------------------- | ---------- |
| mariadb           | mariadb:11.4                      | interno 3306             | mariadb_data                                       | —          |
| email-store       | node:24-bookworm-slim             | interno 5679             | package.json/lock, email_store_mariadb.js, DUARTEC | mariadb    |
| whisper           | build duartec-voice-ai-whisper    | interno 5681             | whisper_cache                                      | —          |
| media             | build duartec-voice-ai-media      | 127.0.0.1:5682/5999/6080 | mission-bridge-chromium, yt-cookies                | —          |
| n8n (n8n-unified) | docker.n8n.io/n8nio/n8n:latest    | interno 5678             | n8n_data_unified, binds DUARTEC/duartec-infra/.nvm | —          |
| n8n-runners       | n8nio/runners:latest              | interno 5680             | —                                                  | n8n        |
| caddy             | caddy:2.8.4-alpine                | **127.0.0.1:19080:80**   | caddy_data/logs, caddy→/etc/caddy, dashboard       | —          |
| db-api            | build duartec-voice-ai-db-api     | interno 8080             | db-api, DUARTEC, portfolio.json                    | mariadb    |
| ollama            | ollama/ollama:latest              | interno 11434            | **bind ~/.ollama**                                 | —          |
| mail-relay        | build duartec-voice-ai-mail-relay | interno 8080             | —                                                  | —          |

Red: duartec-net. El compose inyecta el .env completo a TODOS los servicios (por eso cada contenedor ve todas las claves del .env — mala segregación pero funcional).

### 3.2 /home/ubuntu/n8n/compose.yml — proyecto n8n (5 running + 1 init)

| Servicio                                  | Imagen                                    | Rol                                              |
| ----------------------------------------- | ----------------------------------------- | ------------------------------------------------ |
| n8n (n8n-n8n-1)                           | docker.io/n8nio/n8n:${N8N_VERSION}=2.35.7 | 0.0.0.0:5678→5678; vol n8n-data                  |
| runners (n8n-runners-1)                   | ghcr.io/n8n-io/runners:2.35.7             | broker http://n8n:5679                           |
| sandbox-api (n8n-sandbox-api-1)           | n8n-sandbox-service-api:latest            | API de sandboxes AI (8080) + gRPC 9090 TLS       |
| sandbox-runner-1 (n8n-sandbox-runner-1-1) | n8n-sandbox-service-runner-dind:latest    | Docker-in-Docker, gTLS, registro con sandbox-api |
| searxng (n8n-searxng-1)                   | searxng:latest                            | buscador AI, settings bind                       |
| sandbox-certs                             | (init one-shot)                           | genera TLS, ya no existe como contenedor         |

### 3.3 /home/ubuntu/apps/insforge/docker-compose.yml — proyecto insforge (4)

postgres (postgres-all) → postgrest (v12.2.12, 127.0.0.1:3002) y deno (deno-runtime) → insforge (local/insforge-oss v1.5.0-redacted, 127.0.0.1:7130-7131). Red interna propia. Env keys: JWT_SECRET, ENCRYPTION_KEY, OPENROUTER_API_KEY, STRIPE_*, VERCEL_TOKEN, OAuth clients (GOOGLE/GITHUB/MICROSOFT/DISCORD/LINKEDIN/X/APPLE), DATABASE_URL/DIRECT_URL/PGRST_DB_URI (valores no mostrados).

---

## 4. VEREDICTO n8n

**Canónico: `n8n-unified`** (proyecto duartec-voice-ai). Evidencia:

| Métrica             | n8n-unified                                                                                | n8n-n8n-1                                             |
| ------------------- | ------------------------------------------------------------------------------------------ | ----------------------------------------------------- |
| Imagen              | n8n:latest (pull 2026-09-03), env N8N_VERSION=2.35.7                                       | n8n:2.35.7 **dangling** (ace03195c465)                |
| DB                  | SQLite `duartec-voice-ai_n8n_data_unified`                                                 | SQLite `n8n_n8n-data`                                 |
| Tamaño datos        | 130M (sqlite 37.7MB + wal 4.1MB)                                                           | 5.5M (sqlite 1.5MB + wal 4.1MB)                       |
| Última escritura DB | **2026-09-05 11:04** (wal)                                                                 | 2026-08-25 18:28 (wal)                                |
| Workflows           | **33 (20 activos)**                                                                        | **0**                                                 |
| Ejecuciones 7 días  | **73**                                                                                     | 0 (max = NULL)                                        |
| Última ejecución    | 2026-09-05 03:15                                                                           | nunca                                                 |
| Logs recientes      | errores de request + pruning (activo)                                                      | solo healthcheck + 1 "unknown webhook"                |
| Editor              | https://n8n.tail4b3cf6.ts.net/ (tailscale serve → 19080 → docker caddy → n8n-unified:5678) | publica **0.0.0.0:5678** (sin reverse proxy dedicado) |
| Runners             | N8N_RUNNERS_MODE=external, broker 5679, consumido por n8n-runners                          | runners-1 conectado pero sin tareas                   |

**Runners:**

- `n8n-runners` (duartec-voice-ai, n8nio/runners:latest): broker `http://n8n:5679` → resuelve a n8n-unified. Logs con 358 líneas, reconexiones activas Sep 2–3 (cuando se recreó unified). → **runner del canónico, en uso.**
- `n8n-runners-1` (proyecto n8n, runners:2.35.7): broker `http://n8n:5679` → n8n-n8n-1. Solo **7 líneas de log desde 2026-08-23**, atascado en "Waiting for task offer to be accepted" → **nunca ejecutó una tarea** (n8n-1 no tiene workflows).
- `n8n-sandbox-runner-1-1` (dind): ejecuta contenedores sandbox efímeros para el feature AI de n8n; registrado con sandbox-api vía gRPC mTLS. Actividad real: sandboxes creados 09-03 01:29, detenidos/borrados por idle 09-03/09-04.
- `n8n-sandbox-api-1`: API/gRPC de sandboxes para `N8N_INSTANCE_AI_SANDBOX_*`. Esa API solo es alcanzable desde la red `n8n_default`.
- **n8n-unified TAMBIÉN lleva las env N8N_INSTANCE_AI_SANDBOX\_*/N8N_INSTANCE_AI_SEARXNG_URL apuntando a `sandbox-api:8080`/`searxng:8080`, pero vive en `duartec-net` — los nombres no resuelven (redes distintas).** Esos endpoints son inalcanzables para unified: config heredada muerta.

**Conclusión:** stack "n8n" completo (n8n-n8n-1 + runners-1 + sandbox-api + sandbox-runner + searxng) es un **duplicado/legacy sin workflows**. Su única actividad reciente es la infra del sandbox (Sep 3–4), que además el canónico no puede alcanzar por red. El searxng sin requests en 48h+ solo servía a ese stack.

---

## 5. VEREDICTO Caddy

**Quién bindea 80/443:** `ss -lntp`:

- **Host caddy (systemd, PID 2600105)**: `10.0.0.229:80`, `10.0.0.229:443`, `*:8090` (restaurante). Config `/etc/caddy/Caddyfile` ≡ `~/duartec-infra/Caddyfile-host` (md5 idénticos). **Es el edge público.**
- **tailscaled (PID 1329)**: `100.103.134.102:443` + `[fd7a:…]:443` → `tailscale serve` con 29 rutas en 5 hosts.
- **Docker caddy (duartec-parts-caddy)**: solo `127.0.0.1:19080→80` (auto_https off). **Es el proxy interno tailnet.** NO publica 443.

**Mapa dominio→upstream:**

| Entrada                         | Ruta                                                                                      | Upstream                                               |
| ------------------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| Edge público (host caddy)       | /portfolio*, /summary*, /login*, /hub*, /ai-agents*… (36 handles)                         | 127.0.0.1:3001 (portfolio Next.js)                     |
| Edge público                    | /duartec*, /_next/*, fallback                                                             | 127.0.0.1:3000 (web-duartec Next.js)                   |
| Edge público                    | /canvas*                                                                                  | 127.0.0.1:8020 (python canvas)                         |
| Edge público                    | /espacio*, /restaurante*                                                                  | estático /srv/apps/espacio, /srv/apps/restaurante/dist |
| :8090 (host caddy)              | /*                                                                                        | estático restaurante                                   |
| tailscale serve kiri-vnic       | /                                                                                         | 10.0.0.229:80 (host caddy)                             |
| tailscale serve kiri-vnic       | /novnc, /dashboard, /formulario, /partes, /hub-v2, /api/n8n                               | **127.0.0.1:19080 (docker caddy)**                     |
| tailscale serve kiri-vnic       | /media, /assets, /openclaw, /favicon*, /**openclaw**                                      | 127.0.0.1:5800 (openclaw gateway host)                 |
| tailscale serve kiri-vnic       | /canvas                                                                                   | 127.0.0.1:8020                                         |
| tailscale serve kiri-vnic:8443  | /                                                                                         | 127.0.0.1:8082 — **PUERTO MUERTO (no listena)**        |
| tailscale serve n8n.tail…       | /                                                                                         | 127.0.0.1:19080 → docker caddy → n8n-unified:5678      |
| tailscale serve openclaw.tail…  | /                                                                                         | 127.0.0.1:5800                                         |
| tailscale serve openwebui.tail… | /                                                                                         | 127.0.0.1:8082 — **PUERTO MUERTO**                     |
| tailscale serve kiri-vnic:9450  | /                                                                                         | 127.0.0.1:8090 (restaurante, caddy)                    |
| docker caddy (19080)            | /webhook*, /webhook-test* (gated X-Duartec-Webhook-Secret), /api*, /rest*, host n8n.tail… | n8n-unified:5678                                       |
| docker caddy                    | /whisper (gated Tailscale-User-Login)                                                     | whisper:5681                                           |
| docker caddy                    | /data (gated)                                                                             | db-api:8080 (+ X-Duartec-Secret header_up)             |
| docker caddy                    | /mail                                                                                     | mail-relay:8080                                        |
| docker caddy                    | /novnc (gated)                                                                            | media:6080                                             |
| docker caddy                    | /dashboard, /formulario, /partes, /hub, /hub-v2                                           | file_server /srv-dashboard                             |

**Duplicación:** NO hay dos Caddys sirviendo el mismo host:80/443 (roles distintos: edge público vs proxy interno). PERO hay **3 capas** para el tráfico tailnet de n8n/dashboard (tailscaled → docker caddy → upstream), y el docker caddy duplica rutas estáticas (/dashboard, /formulario, /partes, /hub-v2) que tailscale serve podría servir directo. Rutas muertas: openwebui y :8443→8082. En `/etc/caddy` hay **~25 backups Caddyfile.bak** (2 de 2022/feb-2026).

---

## 6. VEREDICTO bases de datos

| DB                      | Contenedor            | Versión/imagen                       | Vol/datos | Consumidores (evidencia)                                                                                                                                                                            | Estado                   |
| ----------------------- | --------------------- | ------------------------------------ | --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| MariaDB `duartec_parts` | duartec-parts-mariadb | mariadb:11.4                         | 843M      | **db-api** (DB_HOST=mariadb; 160 req reales/48h, p.ej. GET /archive/search cada 31 min desde n8n), **email-store** (email_store_mariadb.js; "Connected to MariaDB"), workflows n8n (envs MARIADB_*) | **ACTIVA**               |
| PostgreSQL (insforge)   | insforge-postgres-1   | ghcr.io/insforge/postgres-all:latest | 91M       | **insforge** (7130/7131; tráfico real de usuario 100.112.222.48 el 09-05 20:39), **postgrest** (127.0.0.1:3002), **deno**                                                                           | **ACTIVA**               |
| SQLite n8n unified      | (dentro n8n-unified)  | n8n 2.35.7                           | 37.7M+wal | n8n-unified                                                                                                                                                                                         | ACTIVA                   |
| SQLite n8n-1            | (dentro n8n-n8n-1)    | n8n 2.35.7                           | 1.5M+wal  | n8n-n8n-1                                                                                                                                                                                           | **MUERTA** (0 workflows) |

- `insforge_storage-data` = 8K → storage de insforge sin ficheros (uso marginal).
- Redundancia interna: dentro del volumen unified hay `database-corrupted-backup.sqlite` (6.9M), `database-recovered.sqlite` (6.9M), `database.sqlite.v19.bak` (22M) — backups legacy May–Jun en volumen vivo.
- No hay DBs sin consumidores.

---

## 7. VEREDICTO Ollama

- **Única instalación efectiva: el contenedor `duartec-ollama`** (ollama/ollama:latest, 4.16GB imagen). `docker exec duartec-ollama ollama list` → **solo `qwen3:1.7b` (1.4 GB, modificado hace 12 h)** — coincide con el modelo canónico esperado.
- **Host:** `which -a ollama` → no existe binario en PATH; `ollama.service` existe pero **disabled** (no activo); sin procesos ollama fuera de docker (el "ollama serve" de ps es el del contenedor, UID root mapeado del contenedor).
- **Storage compartido:** `~/.ollama` (1.3G, contiene models/ + id_ed25519) está montado EN el contenedor → un solo almacenamiento, sin duplicación de modelos. El unit systemd residual deshabilitado es lo único redundante.
- **Inconsistencia de config (con evidencia):** `OLLAMA_MODEL=llama3.2:latest` en unified/mail-relay/media-wrapper/email-store; `LOCAL_AI_MODEL=qwen2.5:3-instruct` y `TRIAGE_AI_MODEL=qwen2.5:3b-instruct` en db-api — **ninguno de esos modelos existe** (solo qwen3:1.7b). Esas rutas AI fallan o caen a fallback.

---

## 8. Otros componentes

| Componente                        | Qué es                                                                 | Consumidor                                                              | Edad/creado           | Actividad reciente                                                                                                                                                 |
| --------------------------------- | ---------------------------------------------------------------------- | ----------------------------------------------------------------------- | --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| searxng (n8n-searxng-1)           | meta-buscador para feature AI de n8n                                   | solo red n8n_default (unified NO puede alcanzarlo)                      | 2026-08-23            | **0 requests en 48h**; errores de engines (wikidata 403) al arrancar                                                                                               |
| whisper (duartec-local-whisper)   | STT local modelo `tiny`                                                | teórico: docker caddy /whisper                                          | 2026-08-27            | **0 POSTs desde su arranque**; solo healthchecks. La transcripción real usa OpenAI (TRANSCRIBE_MODEL=gpt-4o-mini-transcribe)                                       |
| media-wrapper                     | chromium + x11vnc + noVNC + API media (5682) para yt-dlp               | Mission Bridge (host) vía 127.0.0.1:5682; /novnc y /media vía tailscale | 2026-09-02 (recreado) | 606MB RAM, 3.45% CPU; solo /health en logs recientes                                                                                                               |
| Mission Bridge                    | systemd python server (/home/ubuntu/mission-bridge)                    | cliente de media-wrapper                                                | —                     | activo (servicio running)                                                                                                                                          |
| mail-relay                        | relay IMAP/SMTP (imap/smtp.serviciodecorreo.es) interno 8080           | docker caddy /mail                                                      | 2026-09-02            | **0 líneas de log** — sin evidencia de uso                                                                                                                         |
| email-store                       | store de emails en MariaDB, puerto interno 5679                        | docker caddy? workflows n8n                                             | 2026-07-10            | **CRASH-LOOP: RC=2603, ~5min/ciclo**; causa: ImapFlow ETIMEOUT (IMAP TLS) → unhandled 'error' → Node exit → restart. Cada ciclo re-ejecuta `npm ci` (188 paquetes) |
| postgrest (insforge)              | API REST sobre postgres                                                | insforge stack                                                          | 2026-08-23            | healthy, activo                                                                                                                                                    |
| deno (insforge)                   | runtime edge functions                                                 | insforge stack                                                          | 2026-08-23            | healthy, cache 16M                                                                                                                                                 |
| insforge (insforge-insforge-1)    | backend OSS v1.5.0 (auth/API 7130, realtime 7131)                      | usuario tailnet 100.112.222.48                                          | 2026-08-23            | **tráfico real 09-05 20:39** (GET /, /stats, sockets)                                                                                                              |
| portfolio (portfolio.service)     | Next.js prod 127.0.0.1:3001 (/srv/apps/portfolio)                      | host caddy (36 rutas)                                                   | —                     | activo; portfolio-mtm.service = oneshot daily (inactive entre corridas = normal)                                                                                   |
| web-duartec (web-duartec.service) | Next.js prod 127.0.0.1:3000 (/srv/apps/web-duartec, build .next 09-03) | host caddy /duartec*                                                    | —                     | activo + **GitHub Actions self-hosted runner** (actions.runner.iaduartec-Web_Duartec.kiri-vnic)                                                                    |
| api-stub (api-stub.service)       | node /srv/apps/api-service/server.js 127.0.0.1:8080                    | —                                                                       | —                     | activo (stub JSON)                                                                                                                                                 |
| openclaw                          | gateway host CLI port 5800 + 10 sandboxes efímeros                     | n8n workflows (OPENCLAW_WS_URL=ws://172.17.0.1:5800)                    | sandboxes 2026-09-04  | gateway activo; **10 sandboxes idle** (red none, 0.5MB RAM), ~/.openclaw = 7.0G                                                                                    |
| Tailscale                         | tailscaled + serve (29 rutas, 5 hosts)                                 | entrada tailnet de todo                                                 | —                     | activo; 2 rutas → 8082 muerto                                                                                                                                      |
| ocmonitor-share                   | repo con compose (imagen `ocmonitor` inexistente)                      | —                                                                       | —                     | stack NO desplegado; `unified-monitoring-agent` = Oracle Cloud, no relacionado                                                                                     |

---

## 9. Imágenes huérfanas / dangling

- **Dangling (1):** `ace03195c465` — n8n 2.35.7 (1.48 GB). EN USO por n8n-n8n-1 (el tag `docker.io/n8nio/n8n:2.35.7` ya no existe). Se liberará al retirar el stack n8n.
- **Huérfanas (sin contenedor): 0** — docker system df: 20 imágenes, todas ACTIVE.
- Imágenes ligadas solo al stack legacy n8n: n8n 2.35.7 dangling (1.48G), runners:2.35.7 (448M), sandbox-api (44M), sandbox-dind (382M), searxng (255M) ≈ **2.6 GB recuperables** al retirar el stack.

---

## 10. Duplicados / desactualizados / defectos (CON EVIDENCIA)

1. **Stack n8n completo duplicado y muerto**: n8n-n8n-1 (0 workflows, DB sin escritura desde 2026-08-25 18:28, imagen dangling, RC logs solo health) + n8n-runners-1 (7 líneas log, nunca ejecutó tarea) + sandbox-api/dind (última actividad 09-04, inalcanzable desde el n8n canónico) + searxng (0 requests 48h).
2. **Dos sets de runners n8n** (n8n-runners→unified activo; n8n-runners-1→n8n-1 muerto).
3. **n8n-unified con imagen `:latest`** (pulled 09-03) aunque N8N_VERSION pin 2.35.7 → drift de versión descontrolado en el canónico.
4. **email-store en crash-loop**: RC=2603 desde 2026-07-10; ciclo ~5min10s (boots 01:34:14 → 01:39:24 → 01:44:35 → 01:49:47); causa ImapFlow ETIMEOUT sin handler; además `npm ci` en cada arranque.
5. **Whisper sin uso**: 0 POSTs desde 2026-08-27; consume imagen 521MB + whisper_cache.
6. **10 sandboxes openclaw idle** (creados 09-04, red none, sin puertos) + ~/.openclaw 7.0G.
7. **~25 Caddyfile.bak en /etc/caddy** (incl. 2 de 2022 y feb-2026) + backups de compose/.env en duartec-infra (.bak 20260630, .bak 20260710, rollback 20260823, backup-before-security 20260902).
8. **Backups sqlite legacy dentro del volumen n8n unified** (36M: v19.bak 22M Jun 6, corrupted-backup/recovered 6.9M May 31) + `yt-dlp` binario y `yt-cookies.txt` (Jun 6) dentro del volumen.
9. **Volumen dind 894M** (docker-in-docker del sandbox runner) — crece con cada uso del sandbox.
10. **Rutas tailscale muertas**: openwebui.tail…→8082 y kiri-vnic:8443→8082 (8082 NO listena).
11. **N8N_MCP_URL=http://100.103.134.102:5680/mcp-server/http** en unified/db-api/media-wrapper/mail-relay/email-store — puerto 5680 NO listena (endpoint MCP muerto).
12. **Modelos ollama inexistentes en configs**: llama3.2:latest, qwen2.5:3-instruct, qwen2.5:3b-instruct (solo existe qwen3:1.7b).
13. **OPENCLAW_URL=127.0.0.1:18889** en envs — puerto no listena (gateway real en 5800).
14. **Compose files no activos**: /srv/apps/web-duartec (port 3000 ocupado por systemd), /srv/apps/api-service (corre por systemd), /srv/ai/openclaw-lite, ocmonitor-share (imagen inexistente).
15. **.env duplicado a todos los servicios** del proyecto duartec-voice-ai (cada contenedor ve TODAS las claves incl. TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, N8N_ENCRYPTION_KEY…).
16. **n8n-n8n-1 publica 0.0.0.0:5678** (editor/API con N8N_BASIC_AUTH_ACTIVE=false) — riesgo de exposición pública mitigado solo por firewall OCI; se elimina al retirar el stack.

---

## 11. Counts finales

| Métrica                        | Valor                                                                                                                                        |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| Contenedores activos / parados | **29 / 0** (10 openclaw efímeros + 19 de 3 proyectos compose)                                                                                |
| Proyectos compose              | 3 (duartec-voice-ai 10, insforge 4, n8n 5)                                                                                                   |
| Volúmenes                      | 13 (1.94 GB: dind 894M, mariadb 843M, n8n-unified 130M, postgres 91M)                                                                        |
| Redes                          | 6 (bridge/host/none + 3 de proyecto)                                                                                                         |
| Imágenes                       | 20 tagged + 1 dangling (en uso); 13.77 GB                                                                                                    |
| RAM top                        | media-wrapper 606M · n8n-unified 287M · n8n-n8n-1 241M · email-store 161M · mariadb 154M · dind 144M · caddy 56M · insforge 58M · ollama 49M |
| RAM contenedores               | ≈ 2.05 GiB de 23.4 GiB (resto page cache del host)                                                                                           |
| Disco host                     | 87G/194G usados                                                                                                                              |
