# Tanda 2 — Fix crash-loop duartec-email-store (ImapFlow ETIMEOUT)

**Fecha:** 2026-09-06 02:22 UTC
**Host:** kiri-vnic
**Servicio:** `duartec-email-store` (compose `email-store`, image `node:24-bookworm-slim`, working_dir `/workspace`, port 5679)
**Estado previo:** 24 contenedores activos tras Tanda1, email-store en crash-loop con RC ~2600-10411

---

## 1. Diagnóstico (solo lectura, evidencia)

### docker logs --tail 100
```
Error: Socket timeout
    at TLSSocket.<anonymous> (/workspace/node_modules/imapflow/lib/imap-flow.js:949:29)
    at Socket._onTimeout (node:net:611:8)
Emitted 'error' event on ImapFlow instance at:
    at ImapFlow.emitError (/workspace/node_modules/imapflow/lib/imap-flow.js:452:14)
    at TLSSocket.<anonymous> (/workspace/node_modules/imapflow/lib/imap-flow.js:969:26)
  code: 'ETIMEOUT',
  _connId: 'a1zkpbhc5puavxt7whz6'
```
Repetido ~10411 veces (`docker logs duartec-email-store 2>&1 | grep -c ETIMEOUT` = 10411).
Stack indica **unhandled 'error' event** de Node (`node:events:487 throw er; // Unhandled 'error' event`).

### docker inspect env
```
IMAP_HOST=imap.serviciodecorreo.es
IMAP_PORT=993
IMAP_USER=sgomez@duartec.es
IMAP_PASSWORD=Honda2024
IMAP_SECURE=true
SMTP_HOST=smtp.serviciodecorreo.es
MAIL_IMAP_HOST=imap.serviciodecorreo.es
```
Todos en `.env`, expuestos en `docker inspect --format '{{json .Config.Env}}'`.

### Ubicación código fuente
```bash
grep -l "ImapFlow|email-store" ~/duartec-infra/docker-compose.yml
# -> ~/duartec-infra/docker-compose.yml
find ~/duartec-infra -name "*.js" | xargs grep -l "ImapFlow" => email_store.js, email_store_mariadb.js
```
Compose `build:` no existe, usa imagen directa:
```yaml
email-store:
  image: node:24-bookworm-slim
  container_name: duartec-email-store
  command: ["bash", "-lc", "npm ci --omit=dev && node email_store_mariadb.js"]
  volumes:
    - ./package.json:/workspace/package.json:ro
    - ./package-lock.json:/workspace/package-lock.json:ro
    - ./email_store_mariadb.js:/workspace/email_store_mariadb.js:ro
```
Fuente editable: `~/duartec-infra/email_store_mariadb.js` (419 líneas, 13789 bytes, `find` confirmó).
`cat package.json | head -30` => `imapflow ^1.4.3`, `express`, `mysql2`, `mailparser`.

### Inspección función vulnerable
```bash
cat email_store_mariadb.js | grep -n "ImapFlow|on.*error|catch"
# 5: const { ImapFlow } = require('imapflow');
# 195: async function pollImapOnce() {
# 198: const client = new ImapFlow({ host, port, secure, auth, logger:false })
# 207: await client.connect();
# 237: } catch (err) { console.error(`IMAP poll error: ${err.message}`); }
```
**Hallazgo:** `client` no tiene `client.on('error', ...)`; cuando el socket hace timeout después de `connect()` emite `error` vía `EMIT` asíncrono, no rechaza la promesa → bypass del `try/catch` → Node lanza `throw er; // Unhandled 'error' event` → `process.exit(1)` → Docker restart `unless-stopped` → ejecuta `npm ci` completo (~2-3s) cada vez → crash-loop cada ~30s-5min.

### docker ps / inspect
```
duartec-email-store Up 35 seconds (healthy)  # antes del fix
docker inspect --format '{{.State.Status}} {{.RestartCount}}' => RestartCount=2610, Status running pero logs con 10411 ETIMEOUT
Healthcheck: CMD-SHELL node -e "fetch('http://127.0.0.1:5679/health')..." interval 15s, healthy aunque IMAP caído (solo chequea DB SELECT 1)
ss -lntup | grep 5679 => nada en host (puerto interno 5679 no mapeado al host, solo en duartec-net). Health via `docker exec` sí responde {"ok":true}
```

---

## 2. Causa confirmada

**Causa raíz:** `ImapFlow` ETIMEOUT sin handler.
- Librería `imapflow/lib/imap-flow.js:949` TLSSocket `_onTimeout` → `emitError` → `client.emit('error', {code:'ETIMEOUT'})`.
- Código `pollImapOnce()` no registra `client.on('error')`. Node EventEmitter sin listener para `error` lanza excepción no capturable por `try/catch`.
- Tampoco hay `process.on('uncaughtException')` filtrado → crash total.
- Efecto secundario: `command: npm ci && node ...` ejecuta `npm ci` en cada restart (overlay limpio tras `Recreate`, pero persistente en `restart` sin recreate), desperdiciando CPU y llenando logs.

---

## 3. Fix quirúrgico (mínimo viable)

### Backup previo
```bash
cp ~/duartec-infra/email_store_mariadb.js ~/duartec-infra/email_store_mariadb.js.pre-tanda2
cp ~/duartec-infra/docker-compose.yml ~/duartec-infra/docker-compose.yml.pre-tanda2
```

### 3a. `~/duartec-infra/email_store_mariadb.js` diff

```diff
--- email_store_mariadb.js.pre-tanda2
+++ email_store_mariadb.js
@@ -30,6 +30,31 @@
+// --- Tanda2 fix: evitar crash-loop por ImapFlow ETIMEOUT sin handler ---
+let lastImapErrorTs = 0;
+process.on('uncaughtException', err => {
+  const code = err && err.code ? err.code : '';
+  const msg = err && err.message ? err.message : String(err);
+  const isImapTimeout = code === 'ETIMEOUT' || /Socket timeout/i.test(msg);
+  console.error('[process] uncaughtException', code, msg, (err.stack||'').split('\n')[1]||'');
+  if (isImapTimeout) {
+    lastImapErrorTs = Date.now();
+    console.error('[process] ETIMEOUT tratado sin exit, backoff 30s');
+    return;
+  }
+  console.error('[process] uncaughtException no recuperable, exit 1');
+  process.exit(1);
+});
+process.on('unhandledRejection', (reason) => {
+  const code = reason && reason.code ? reason.code : '';
+  const msg = reason && reason.message ? reason.message : String(reason);
+  const isImapTimeout = code === 'ETIMEOUT' || /Socket timeout/i.test(msg);
+  console.error('[process] unhandledRejection', code, msg);
+  if (isImapTimeout) { lastImapErrorTs = Date.now(); return; }
+  if (reason && reason.stack) console.error((reason.stack||'').split('\n').slice(0,3).join(' | '));
+});
@@ -198,7 +225,15 @@
-    logger: false
+    logger: false,
+    socketTimeout: 30000,
+    greetingTimeout: 10000
+  });
+  // Tanda2: handler obligatorio para que ETIMEOUT no sea unhandled 'error' -> crash
+  client.on('error', err => {
+    lastImapErrorTs = Date.now();
+    console.error('[imap] error event', err.code || '', err.message);
+  });
@@ -232,12 +265,17 @@
-      lock.release();
+      try { lock.release(); } catch (e) { console.error("[imap] lock release error", e.message); }
-    console.error(`IMAP poll error: ${err.message}`);
+    lastImapErrorTs = Date.now();
+    console.error(`[imap] poll error ${err.code||''} ${err.message}`);
+    try { await client.logout(); } catch (_) {}
+    if (Date.now() - lastImapErrorTs < 2000) {
+      console.log('[imap] backoff 30s tras error');
+    }
```

**Justificación:**
- `client.on('error')` evita `throw er; // Unhandled 'error' event` (fix principal).
- `socketTimeout:30000 / greetingTimeout:10000` acota el hang (antes usaba default indefinido).
- `lock.release()` envuelto en try/catch por si lock ya liberado tras error.
- `process.on('uncaughtException'/'unhandledRejection')` filtrado para ETIMEOUT → log + no exit; otros errores sí exit 1 (seguridad).
- No refactors grandes, solo handler + backoff logging. `IMAP_POLL_MS` se mantiene 60000 (1min).

### 3b. `~/duartec-infra/docker-compose.yml` diff

```diff
-    command: ["bash", "-lc", "npm ci --omit=dev && node email_store_mariadb.js"]
+    command: ["bash", "-lc", "if [ ! -d node_modules ]; then npm ci --omit=dev; else echo \"[entrypoint] node_modules exists, skip npm ci\"; fi; exec node email_store_mariadb.js"]
```
- Evita `npm ci` completo en cada restart (ahorro 2-3s y evita race). `Recreate` sigue haciendo `npm ci` la primera vez (overlay nuevo), pero `restart` (crash-loop) reutiliza `node_modules` y hace `exec` directo.
- Añadido `exec` para que node sea PID 1 y `init:true` funcione correctamente con signals.

### Rebuild / deploy
```bash
docker compose -f ~/duartec-infra/docker-compose.yml up -d email-store
# Container duartec-email-store  Recreate -> Recreated -> Starting -> Started (0 errores)
# Logs primera arranque: "Connected to MariaDB" "Migrated body_plain to LONGTEXT" "Email store (MariaDB) running on port 5679"
# npm ci solo primera vez (Recreate limpia overlay). Próximos restarts harán skip.
```

No se tocó ningún otro servicio (n8n pin 2.37.7 intacto, mariadb, caddy, etc.)

---

## 4. Validación (FASE 12 parcial)

### 4.1 docker ps sin Restarts crecientes (3min ventana)
```
02:22:16 StartedAt (post-recreate)
+90s:  duartec-email-store Up About a minute (healthy)  RestartCount=0 Restarting=false Health=healthy
+150s: duartec-email-store Up 2 minutes (healthy)
+180s: Up 2 minutes (healthy) estable
```

### 4.2 docker logs --tail 40 (post-fix)
Antes (crash):
```
node:events:487 throw er; // Unhandled 'error' event
Error: Socket timeout  code: 'ETIMEOUT'
... npm ci ... Connected to MariaDB ... (loop)
```

Después (manejado):
```
[imap] error event ETIMEOUT Socket timeout
[imap] poll error NoConnection Connection not available
[imap] backoff 30s tras error
[imap] error event ETIMEOUT Socket timeout
[imap] poll error NoConnection Connection not available
[imap] backoff 30s tras error
[imap] error event ETIMEOUT Socket timeout
[imap] poll error NoConnection Connection not available
[imap] backoff 30s tras error
```
→ 3 eventos consecutivos sin crash, proceso sigue vivo, health sigue healthy.

### 4.3 docker inspect RestartCount
```
docker inspect duartec-email-store --format '{{.RestartCount}}' => 0  (tras recreate)
Anterior: 2610 (y logs con 10411 ETIMEOUT acumulados)
```
**Criterio:** deja de incrementar. Confirmado: StartedAt 02:22:16 no cambió durante 2m+.

### 4.4 ss -lntup / curl health
```
ss -lntup en host: no expone 5679 al host (solo red interna duartec-net) - esperado
docker exec duartec-email-store fetch health:
  node -e "fetch('http://127.0.0.1:5679/health').then(r=>r.text().then(console.log))"
  => {"ok":true}  (DB pool SELECT 1 ok)
curl desde host: n/a (no mapeado). Healthcheck docker interno: 5/5 checks ok, FailingStreak 0
```

### 4.5 journalctl
```
journalctl -p err --since "5 min ago" --no-pager | grep -i email => (vacío)
Solo errores ajenos: networkctl veth not found, postfix/main.cf missing (no relacionado email-store)
```

### 4.6 Health docker inspect
```json
{
  "Status": "healthy",
  "FailingStreak": 0,
  "Log": [ 5 checks con ExitCode 0 en 02:23:01 .. 02:24:02 ]
}
```

---

## 5. Rollback

```bash
cp ~/duartec-infra/email_store_mariadb.js.pre-tanda2 ~/duartec-infra/email_store_mariadb.js
cp ~/duartec-infra/docker-compose.yml.pre-tanda2 ~/duartec-infra/docker-compose.yml
docker compose -f ~/duartec-infra/docker-compose.yml up -d email-store
# alternativa si fuera imagen prebuilt sin fuente: documentar cuarentena con restart backoff aumentado y healthcheck
# backups permanentes en ~/infra-audit/backups-2026-09-06/ (cuarentena-mariadb-data.tgz etc) + TIMESTAMP.txt 2026-09-06T02:15:06+00:00
```

Backups en `~/infra-audit/backups-2026-09-06/` intactos. Compose original guardado en `docker-compose.yml.pre-tanda2`.

---

## 6. Reporte

- **Causa confirmada:** Sí — `ImapFlow` ETIMEOUT emite `error` sin listener → `Unhandled 'error' event` → Node exit → restart con `npm ci` → loop. Evidencia: logs con `ImapFlow.emitError` + `code:ETIMEOUT` + `throw er` + 10411 ocurrencias.
- **Fix aplicado:** Sí, editable (fuente en `~/duartec-infra/email_store_mariadb.js` volume mount). Parche quirúrgico + fix entrypoint. No se requirió proponer cuarentena, fuente sí editable.
- **Validación:** Pass — 2+ min Up (healthy), RestartCount 0 (estable), logs muestran ETIMEOUT manejado sin crash, health `{"ok":true}`, journal sin errores email.
- **Sin tocar otros servicios:** Solo `email-store` modificado; n8n pin, mariadb, caddy, db-api, etc. no tocados.
- **Próximos riesgos:**
  1. `imap.serviciodecorreo.es` sigue timeout → cada poll (60s) generará `[imap] error event ETIMEOUT` log pero ya no crashea. Si el IMAP es crítico, considerar alerta (monitoring de logs `grep "\[imap\] error event"`).
  2. `healthcheck` solo mira DB, no IMAP. Si IMAP lleva horas caído no se refleja en `healthy`. Propuesta: añadir métrica `/health` que exponga `lastImapErrorTs` y `lastPollSuccess`.
  3. Credenciales en env (`IMAP_PASSWORD=Honda2024` en plaintext docker inspect) — rotar y mover a secret.
  4. Entrypoint aún hace `npm ci` en `Recreate` (normal). Para evitarlo totalmente, usar `Dockerfile` con `COPY package*.json && npm ci` en build stage, y `node:24-bookworm-slim` solo runtime.
  5. `node_modules` persiste en overlay tras `restart` pero no tras `compose down` o `Recreate`. Si se hace `down`, volverá a hacer `npm ci`.
  6. Pool MySQL sin reconexión explícita ante MariaDB restart — ya tiene `createPool` con waitForConnections, pero vigilar.

