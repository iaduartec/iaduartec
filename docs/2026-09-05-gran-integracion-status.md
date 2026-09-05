# Estado de la gran integración — Mission Alpha

**Fecha de verificación:** 2026-09-05
**Estado:** operativo en investigación y Canvas; promoción de inversión aún bloqueada por diseño.

## Resumen ejecutivo

La integración técnica entre repositorios, runtime y superficies públicas está conectada y sincronizada. Canvas entrega datos reales autenticados, Hub V2 construye con assets locales, Trading mantiene el gate de operador y modo paper, y los punteros del repositorio raíz no tienen referencias `-dirty`.

Esto no equivale todavía a una política de inversión desplegable: Shadow continúa en dry-run, no hay autorización live y la evidencia OOS/promoción sigue sometida a sus gates.

## Matriz de integración

| Superficie | Estado actual | Evidencia | Pendiente |
|---|---|---|---|
| Mission Bridge / Canvas | Operativo | servicio activo; `/health` 200; `portfolio.json` 200 con 259 ideas; sentimiento 200 con 6 señales, 32 mercados, 6 narrativas y 5 divergencias | resolver avisos de proveedores 429 si se necesita ampliar análisis de fondo |
| Routing Tailscale/Caddy | Operativo | `:9449` tailnet-only → Caddy → Canvas; APIs autenticadas 200 | mantener la ruta declarativa en reinicios |
| Hub V2 | Integrado en `main` | `pnpm check` y `pnpm build` pasan; fuentes locales; rama y remoto sincronizados | corregir solo los avisos de formato preexistentes si se decide una limpieza estética |
| Duartec Infra | Sincronizado | `codex-verify.sh full` funcional; `npm audit` local: 0 vulnerabilidades | confirmar el refresco de alertas remotas de Dependabot |
| Trading | Operativo con guardrails | 60 tests pasan, 8 skips opcionales; operador fail-closed; `trading.env` no trackeado | auditoría externa de credenciales históricas; no live trading |
| Portfolio / Lab | Integrado como fuente de investigación | `main` sincronizado y policy gates preservados | paridad final con runtime y promoción solo tras evidencia OOS/Shadow |
| Site Mission Alpha Connections | Publicada | versión 3 desplegada y HTTP 200 | mantenerla como resumen, no como fuente de estado operativo |

## Repositorios sincronizados

- raíz `/home/ubuntu`: `main` sincronizado con `origin/main`.
- `mission-bridge`: `main` sincronizado con `origin/main`.
- `duartec-infra`: `main` sincronizado con `origin/main`.
- `apps/duartec-hub`: `main` sincronizado con `origin/main`.
- `portfolio-repo`: `main` sincronizado con `origin/main`.
- `projects/trading`: `main` limpio; el repositorio no tiene upstream configurado en este checkout.
- `sites/mission-alpha-connections`: `main` sincronizado con su remote de Sites.

Nota de estructura: el checkout raíz conserva referencias Git tipo `gitlink` para varios repositorios, pero no tiene `.gitmodules`; por eso `git submodule status` no es un verificador válido aquí. La paridad de esos punteros se comprobó directamente con `git ls-files -s` y contra los HEAD de cada checkout.

## Guardrails que siguen activos

- Sin órdenes Alpaca Live.
- Runtime de Trading en paper/dry-run.
- Canvas y APIs protegidos por identidad; sin identidad, respuesta fail-closed.
- Ingesta rechaza evidencia ausente, no verificada o sin provenance.
- No se ha reescrito historial ni se han mostrado secretos.

## Pendientes reales

1. Auditar credenciales históricas desde GitHub/proveedores. Secret Scanning no está disponible en el plan actual del repositorio privado, por lo que no se inventa una rotación ni se reescribe el historial sin un secreto confirmado.
2. Confirmar si las alertas moderadas que GitHub mostró durante el push de infraestructura ya están obsoletas; la auditoría local actual devuelve cero vulnerabilidades.
3. Acumular evidencia prospectiva OOS/Shadow suficiente para una eventual promoción. Esta es una decisión cuantitativa, no un problema de sincronización técnica.

## Limpieza aplicada

- Eliminadas ramas locales fusionadas de Trading sin worktree activo.
- Movido el backup de `trading.env` fuera del repositorio a `/home/ubuntu/.quarantine/trading-env-backup-20260905T000000Z`, conservado con modo `600`.
- Conservados los worktrees activos y los rollbacks de infraestructura que aún tienen valor de recuperación.
