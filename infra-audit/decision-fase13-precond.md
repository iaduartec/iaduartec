# FASE 13 — Precondiciones de Purga (NO BORRAR) — 2026-09-06

**Verificación:** `date -u` = 2026-09-06T03:33:48Z (real) | Simulado 2026-09-13 (~7d post-cuarentena)
**TIMESTAMP.txt:** `2026-09-06T02:15:06+00:00` — `Backup completed by subagente FASE 10`
**NO se ejecutó ningún `rm`/`prune`/`volume rm`/`rmi`.**

## 1) Cuarentena

| Tar                                                                   | Tamaño   | Fecha            | Estado   |
| --------------------------------------------------------------------- | -------- | ---------------- | -------- |
| cuarentena-n8n-data.tgz                                               | 427K     | 2026-09-06 02:14 | vigent   |
| cuarentena-n8n-unified.tgz                                            | 52M      | 2026-09-06 02:14 | vigent   |
| cuarentena-mariadb-data.tgz                                           | 29M      | 2026-09-06 02:14 | vigent   |
| +6 tgz más (ocmonitor, openclaw x2, virtual-tier x2, sandbox-tls 13K) | 13K–196M | 2026-09-06       | vigentes |
| .bak (crontab, services)                                              | <7KB     | 2026-09-06       | vigentes |

- **Vencimiento 14d:** 2026-09-20 — **restantes: 13d (real) / 7d (simulado 2026-09-13)** — total 13d desde creado.
- **Vencimiento 30d:** 2026-10-06 — **restantes: 29d (real) / 23d (simulado)** — total 29d.
- **Conclusión:** Cuarentena **NO vencida**. `tar tzf` OK (n8n-data, mariadb). No purgar.

## 2) Volumen `n8n_n8n-data`

- `docker volume ls` → **existe** (`local n8n_n8n-data`, creado 2026-08-23, labels `project=n8n/volume=n8n-data`).
- `docker volume inspect` Mountpoint `/var/lib/docker/volumes/n8n_n8n-data/_data` — `du -sh` **5.5M**.
- `docker ps -a --filter volume=n8n_n8n-data` → **vacío**. `docker inspect $(docker ps -aq) | grep n8n_n8n-data` → vacío.
- Activo en uso: `duartec-voice-ai_n8n_data_unified` (105M) por contenedor `n8n-unified` (n8n:2.37.7).
- **En uso?: NO.** Volumen huérfano, candidato a purga **solo tras** vencimiento + rollback descartado.

## 3) Imagen `ace03195c465` (n8n custom 1.48G)

- `docker images -a --filter dangling=true` → `<untagged> ace03195c465 1.48GB` **existe** (dangling).
- `docker image inspect` → Created 2026-08-21, RepoDigest `n8n@sha256:166d7e...`, history `N8N_VERSION=2.35.7`.
- `docker ps -a --filter ancestor=ace03195c465` → vacío. `docker inspect` todos → sin refs.
- `grep -r ace03195c465 ~/duartec-infra ~/n8n` → sin hallazgos. Imágenes activas: `n8n:1.114.3`, `n8n:2.37.7/latest`.
- `docker system df` → Images 14.85GB reclaimable 11.17GB (75%), Volumes 780MB reclaimable (40%).
- **Dependencias?: NO.** Reclaimable pero **no borrar** hasta confirmar que 2.37.7 suple 2.35.7 sin rollback.

## 4) Tars vencidos

- `find ~/infra-audit -name "*.tgz" -o -name "*.tar" | xargs ls -lh` → 9× `.tgz`, 0× `.tar`.
- Todos con mtime 2026-09-06 02:14–03:11 (full-iso verificado). Cero vencidos.
- **Vencidos?: NO.** `.tar` pendientes mencionados no existen como `.tar` sueltos; son `.tgz` vigentes.

## 5) Decisión

**ESPERAR — NO PURGAR HOY.** Precondiciones no cumplidas: cuarentena <14d (faltan 13d reales). Volumen e imagen son reclaimable pero el rollback aún es posible.

## 6) Checklist para purga futura (post 2026-09-20 / 2026-10-06)

- [ ] Confirmar rollback innecesario (n8n-unified 2.37.7 estable ≥14d, n8n-data_unified OK).
- [ ] Re-validar `tar tzf` + checksum de los 3 tgz críticos.
- [ ] `docker volume rm n8n_n8n-data` solo si `docker ps -a --filter volume=` sigue vacío.
- [ ] `docker rmi ace03195c465` solo si `docker ps -a --filter ancestor=` vacío y `grep -r` negativo.
- [ ] `docker system df` post-purga para auditar reclaimable.
- [ ] Borrar `.tgz` solo tras 30d (2026-10-06) o 14d con aprobación explícita y backup externo verificado.
