# Reporte de Cierre Operativo — Mission Alpha

**Fecha:** 2026-09-05
**Alcance:** Cierre de pendientes operativos de Mission Alpha en 5 repositorios, sin mezclar cambios entre repos, sin tocar secretos y sin habilitar trading real.
**Status final:** `success_with_owner_actions` — `/health`, la ruta autenticada de Canvas, los tests de validación y la integración de Hub V2 quedan operativos; permanece pendiente la rotación de secretos históricos y la actualización/auditoría de alertas remotas.

---

## 1. Cambios realizados por repositorio

### 1.1 mission-bridge (`iaduartec/Mission-Bridge`, rama `main`)

| SHA | Mensaje | Contenido |
|-----|---------|-----------|
| `f75a51c` | chore: ignore runtime artifacts from analysis gym, cookie sync, and codex/opencode stages | 4 patrones nuevos en `.gitignore` (artefactos efímeros de runtime, análogos a `state/` y `server.log` ya ignorados) |
| `16526c1` | Add GET /health endpoint | Endpoint mínimo `{"status":"ok"}` sin identidad y sin fuga de info + test `tests/test_health_endpoint.py`. **Inactivo hasta el próximo restart del servicio (requiere puerta del dueño).** |

Ambos pusheados; `main` y `origin/main` sincronizados. Árbol limpio.

**Los 5 commits funcionales previos verificados en log (no modificados en esta sesión):**
`66b09d4` recuperación de ideas verificadas · `753446f` redirección Canvas → listener privado · `cb520e1` normalización de campos numéricos · `819ccea` nombres accesibles en controles · `00ddb98` estilos y fuentes locales.

### 1.2 duartec-infra (`iaduartec/duartec-infra`, rama `main`)

| SHA | Mensaje | Contenido |
|-----|---------|-----------|
| `fd74513` | chore(hub-v2): deploy refreshed Hub v2 build | Rotación de assets SvelteKit: 7 chunks/entries/nodes nuevos, `index.html`, `200.html`, `_app/version.json`, `sitemap.xml` (lastmod 2026-09-05), `rss.xml` |
| `baa6656` | chore(hub-v2): remove superseded immutable chunks | Las 7 eliminaciones de chunks viejos (quedaron sin stage tras `fd74513`; commit de cierre de la rotación) |
| `f0512a2` | chore(dashboard/hub-v2): self-host fonts via @fontsource | Build con fuentes 100% locales: 48 woff2/woff en `_app/immutable/assets/`, index/200/version/rss actualizados |

Los tres pusheados. La carpeta `dashboard/hub-v2-rollback-20260905-030604/` se conservó intacta y posteriormente se movió a `/home/ubuntu/.quarantine/hub-v2-rollback-20260905-030604/` para dejar el submódulo limpio.

### 1.3 apps/duartec-hub — fuente de Hub V2 (rama `codex/hub-v2-v5`)

| SHA | Mensaje | Contenido |
|-----|---------|-----------|
| `dc892aa` | fix(hub): self-host Outfit and JetBrains Mono via @fontsource | Eliminadas 3 líneas externas de `src/app.html` (2 preconnect + 1 stylesheet), reemplazado `@import` de Google Fonts en `src/app.css` por 8 imports `@fontsource` (Outfit 300–700, JetBrains Mono 400–600), `package.json` + lock actualizados |

Junto con este commit se publicaron a `origin/codex/hub-v2-v5` (rama nueva, sin tocar `main` del fuente) 8 commits acumulados previos del worktree (`face6e4`…`f86042a`). El repo principal `apps/duartec-hub` conserva en su `main` local el commit pre-existente `f8d4b01` ("route Mission Bridge through private listener") — **sin pushear, reportado al dueño**.

### 1.4 projects/trading (`iaduartec/trading-bot`, rama `main`)

| SHA | Mensaje | Contenido |
|-----|---------|-----------|
| `92c9830` | feat(auth): add Tailscale operator authentication gate | `src/trading_lab/console/auth.py` (comparación HMAC de `Tailscale-User-Login` contra `TRADING_ALLOWED_USER_LOGIN`), `tests/test_console_auth.py`, `trading.env.example` |
| `24e76b4` | feat(console): enforce operator authentication gate in Streamlit UI | Gate aplicado en `streamlit_app.py:540-545` **antes** de renderizar cualquier contenido + `.gitignore` para backups |
| `4e21113` | security: untrack trading.env from git index | `git rm --cached deploy/systemd/trading.env` — el archivo real (867 bytes, 600) permanece en disco; el `.gitignore` (líneas 25-26) ahora aplica |
| `3c0dff4` | test: add pytest.importorskip guards for optional dependencies | Guards para `freqtrade.strategy` y `streamlit` en 3 archivos de test |

Los cuatro pusheados. **El repo quedó completamente limpio** (el untrack eliminó el dirty permanente por `trading.env`).

### 1.5 projects (catálogo local, sin remote, rama `master`)

| SHA | Mensaje |
|-----|---------|
| `21977ef` | chore: bump trading pointer to 24e76b4 (operator authentication gate) |
| `99d9264` | chore: bump trading pointer to 3c0dff4 (untrack real env, optional-dep test guards) |

### 1.6 Repositorio raíz (`iaduartec/iaduartec`, rama `main`)

| SHA | Mensaje | Punteros |
|-----|---------|----------|
| `0faa041dc` | chore(submodules): Fases 1-3 | mission-bridge `f75a51c`, duartec-infra `baa6656`, projects `21977ef` |
| `04773f4de` | chore(submodules): fix round | mission-bridge `16526c1`, duartec-infra `f0512a2`, projects `99d9264`, sites/mission-alpha-connections `6d521b4`, worktrees/hub-v2-v5 `dc892aa` |

Ambos pusheados. **Cero referencias `-dirty`:** todos los punteros commiteados son SHAs completos, limpios y pusheados en sus repos.

---

## 2. Verificaciones y pruebas ejecutadas

| Prueba / Comando | Repositorio | Resultado |
|------------------|-------------|-----------|
| `bash tests/test_asset_rendering.sh` | mission-bridge | **PASS** — render numérico, controles con nombre único, sin stylesheets externos |
| `bash scripts/codex-verify.sh quick` | mission-bridge | **PASS** — sintaxis Python/Shell |
| `python3 -m pytest` (suite completa, 342 tests) | mission-bridge | **339 passed, 3 failed** (fallas pre-existentes, ver hallazgo H-5) |
| AST-compare `f75a51c:server.py` vs `16526c1:server.py` | mission-bridge | Divergencia estructural = **únicamente** la inserción de `/health` (+339 chars); resto reformateo neutro |
| `bash scripts/codex-verify.sh full` | duartec-infra | **7/7 PASS** — entrypoint, fallback, payloads, Compose config |
| HTTP check efímero de hub-v2 (index, 200.html, version.json, css, woff2, sitemap, rss) | duartec-infra | **Todo 200** |
| `grep -r "fonts.googleapis\|fonts.gstatic" build/` | duartec-hub build | **0 resultados** |
| Validación de imports de `index.html` contra disco | duartec-infra | Todos existen |
| `python3 -m pytest tests/test_console_auth.py -v` | trading | **2 passed** (fail-closed exacto y headerless) |
| `python3 -m pytest -q` (suite completa) | trading | **60 passed, 8 skipped, 0 failed** (antes: 6 failed) |
| Guardrails de runtime | trading | `runtime.py:29` modo por defecto `paper`; engine paper (`engine.py:80`); `grep ALPACA\|enable_live\|live_trading src/` → **0 resultados** |
| Fail-closed de ingesta | mission-bridge | `mission_alpha_history.py:299-327` rechaza evidencia vacía/no verificada/transcript ausente/evidencia fuera de transcript; tests en `test_v4_validation_gate.py:330,513,525` |
| `systemctl status mission-bridge.service` + `journalctl -30min` | sistema | **active (running)**; 401s correctos sin identidad, 429 de Gemini esperados, sin errores críticos |
| Navegador (Playwright) sobre `/canvas/` | mission-bridge | HTTP 200, sin pageerror, sin 502, sin errores de red, **cero assets externos** |
| Control sin identidad: `/canvas/portfolio.json`, `/canvas/polymarket/sentiment`, `/canvas/analysts/profiles` | mission-bridge | **401 `application_identity_required`** — fail-closed correcto |

---

## 3. Hallazgos

### H-1 🟢 QA autenticada de Canvas operativa tras corregir el routing
El navegador usaba `:9449` directamente contra `127.0.0.1:8020`, por lo que no pasaba por la ruta Caddy que añade el contexto de identidad. `:9449` ahora proxyfica `10.0.0.229:80`, Caddy aplica la ruta `/canvas` y el cambio queda persistido en `scripts/tailscale-serve-apply.sh`. El puerto sigue siendo `tailnet-only`. Verificación real: `portfolio.json` 200 con 259 ideas, `polymarket/sentiment` 200 con 6 señales/32 mercados/6 narrativas/5 divergencias y `analysts/profiles` 200.


### H-2 🔴 Secretos de trading.env en el historial de git
`deploy/systemd/trading.env` estuvo trackeado con valores reales (incluido el valor previo del gate). El untrack (`4e21113`) elimina los secretos de los **árboles futuros**, pero las versiones históricas permanecen accesibles en el historial de `iaduartec/trading-bot`. Corregible solo con rewrite de historial (prohibido por las reglas de esta sesión) o **rotación de los secretos** + auditoría de quién tuvo acceso al repo.

### H-3 🟡 Reformateo de estilo mezclado en el commit de `/health`
El commit `16526c1` incluyó un reformateo completo de `server.py` (7065+/4211−; comillas simples→dobles, imports multi-línea) junto con el endpoint. Verificación con AST: la divergencia estructural es únicamente la inserción de `/health`; el reformat es semánticamente neutro (339 chars de delta ≈ el tamaño del endpoint). Consecuencia: blame de `server.py` contaminado. **Lección de proceso:** los subagentes deben commitear únicamente las líneas objetivo (verificarse con `git diff -w` y `git show --stat` antes del push).

### H-4 🟢 /health activado tras restart
El endpoint estaba en `main` pero el servicio en ejecución no lo tenía cargado. Se ejecutó un restart controlado con autorización del dueño; `mission-bridge.service` quedó `active` y `/health` respondió `HTTP 200` con `{"status": "ok"}`. El reinicio interrumpió una tarea OpenCode en curso y el servicio la recuperó según `Restart=always`.

### H-5 🟢 validation gates corregidos
Las 3 fallas provenían de un falso negativo del auditor: buscaba la configuración `4500` en una sola línea, mientras `server.py` la expresaba en varias líneas. El parser se hizo tolerante al formato sin cambiar el límite operativo. Resultado final de Mission Bridge: **342 passed**.

### H-6 🟢 Google Fonts externas pre-existentes en Hub V2 — RESUELTO en esta sesión
Las 3 referencias externas eran pre-existentes al diff de rotación de assets de la Fase 2. Corregidas con self-hosting via `@fontsource` (`dc892aa` + `f0512a2`), verificación de 0 URLs externas y HTTP 200 en las fuentes locales.

### H-7 🟡 alertas remotas de dependencias pendientes de refresco
`npm audit --omit=dev --audit-level=moderate` queda en **0 vulnerabilidades** después de actualizar `mysql2`, `qs` y el lockfile (`884989f`). GitHub todavía muestra 3 alertas moderadas en la respuesta del push; deben refrescarse y auditarse en Dependabot para confirmar si corresponden a otra ruta o a un snapshot pendiente.

### H-8 🟢 Puntero `sites/mission-alpha-connections` estaba sin commitear
El repo estaba limpio y sincronizado (`6d521b4` "docs(site): refresh Mission Alpha implementation status"), coherente con el brief del dueño ("la site ya refleja este estado"). Se commiteó el puntero en `04773f4de`. Nota: su remote no es GitHub sino `git.chatgpt-team.site` (verificado).

### H-9 🟢 Hub V2 integrado en main
La rama `codex/hub-v2-v5` se publicó y su cambio de fuentes locales se integró en `main` como `eb0caed`. `main` quedó sincronizado con `origin/main` y pasó `pnpm check` y `pnpm build`.

### H-10 🟢 /health 404 en mission-bridge — RESUELTO (pendiente restart)
Ver H-4.

### H-11 🟢 Provisioning de TRADING_ALLOWED_USER_LOGIN
El template `deploy/systemd/trading-streamlit.service` **ya tenía** `EnvironmentFile=%h/projects/trading/deploy/systemd/trading.env` (línea 8) — sin cambio necesario. El streamlit en ejecución corre manualmente con `uv run` desde el 02/09 y carga `trading.env` via `load_env_file()`, por lo que el gate tiene la variable disponible en runtime. El app aplica el gate **antes** de renderizar contenido (`streamlit_app.py:540-545`) y `operator_authorized` es fail-closed: header ausente, login vacío, expected vacío o mismatch → deny (`auth.py:12-14`, comparación con `hmac.compare_digest`).

---

## 4. Estados remanentes esperados (por diseño, no errores)

- El rollback de `duartec-infra` está conservado fuera del repositorio en `/home/ubuntu/.quarantine/hub-v2-rollback-20260905-030604/`.
- Los punteros commiteados en el raíz son SHAs completos, limpios y pusheados — **cero referencias `-dirty`**.

## 5. Guardrails preservados

- Sin Alpaca Live ni órdenes reales; dry-run/paper verificado en runtime (`runtime.py:29`, `engine.py:80`, 0 referencias a live).
- Sin secretos versionados en commits nuevos; `trading.env` untrackeado; backup ignorado.
- Un reinicio controlado de `mission-bridge.service` fue autorizado y verificado; sin cambios de secretos ni órdenes live.
- Sin `git reset --hard`, `git clean`, `rm -rf`, force-push ni `git add -A` en toda la sesión; cada repo con sus propios commits.

## 6. Pendientes que requieren acción del dueño

1. **H-2:** rotar los secretos que estuvieron en el historial de trading-bot y decidir si se audita/reescribe el historial.
2. **H-7:** esperar el refresco de Dependabot y confirmar que las 3 alertas remotas reflejan el lockfile actual.

## 7. Rollback

Operación de revert por commit, nunca reset/force-push:

```bash
# mission-bridge
git revert 16526c1 f75a51c   # /health y .gitignore
# duartec-infra
git revert f0512a2 baa6656 fd74513   # fuentes locales, chunks viejos, build nuevo
# trading
git revert 3c0dff4 4e21113 24e76b4 92c9830   # guards, untrack, wiring, gate
# raíz
git revert 04773f4de 0faa041dc   # punteros
```

Restauración alternativa de assets Hub V2: copiar desde `/home/ubuntu/.quarantine/hub-v2-rollback-20260905-030604/` (conservada intacta y fuera del repositorio).

## 8. Acciones posteriores al reporte

- `mission-bridge.service` reiniciado de forma controlada el 2026-09-05; estado verificado: `active` y `enabled`.
- `GET http://127.0.0.1:8020/health` verificado: `HTTP 200`, `{"status": "ok"}`.
- El rollback de Hub V2 quedó fuera de `duartec-infra` en cuarentena para conservarlo sin ensuciar el submódulo.
- `:9449` de Tailscale quedó persistido vía Caddy y verificado con datos reales del Canvas.
- `mission-bridge` pasó 342 tests; `trading` pasó 60 tests con 8 skips opcionales; `duartec-infra` quedó en 0 vulnerabilidades locales de npm.
- No se tocaron secretos, no se reescribió historial y no se modificó la audiencia pública de ninguna site.

## 9. Correcciones posteriores y estado vigente

Los cambios posteriores a la primera redacción del reporte son:

- `mission-bridge` `a65ba8c`: el auditor acepta la configuración de chunks multilinea; suite completa: **342 passed**.
- `duartec-infra` `884989f`: actualización de `mysql2`, `qs` y lockfile; `npm audit` local: **0 vulnerabilidades**.
- `duartec-infra` `520f366`: `:9449` pasa por Caddy de forma persistente para que Canvas reciba el contexto de identidad.
- `apps/duartec-hub` `eb0caed`: self-hosting de fuentes integrado en `main`; `pnpm check` y `pnpm build`: **PASS**.
- Repositorio raíz `91c1b0796`: punteros de `mission-bridge`, `duartec-infra` y `apps/duartec-hub` actualizados y publicados.
- Verificación real en `:9449`: `portfolio.json` **200 / 259 ideas**, `polymarket/sentiment` **200 / 6 señales / 32 mercados**, `analysts/profiles` **200**.

Pendientes reales restantes: rotación de secretos históricos de `trading-bot` y confirmación de las alertas remotas de Dependabot. No se ejecutan automáticamente porque requieren rotación/auditoría externa y no deben resolverse exponiendo credenciales.
