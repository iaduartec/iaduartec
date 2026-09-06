# G4 — duartec-static-sites :19180 reubicación (B, frágil)

**Host:** kiri-vnic — 14 contenedores, whisper cuarentena, api-stub disabled, tailscale 8082 off, crons limpios  
**Fecha ejecución:** 2026-09-06T03:13 UTC  
**Estado final:** ✅ REUBICADO — frágil eliminado, servicio vigente y validado

---

## 1. Pre-check

### systemd --user status (antes)
```
● duartec-static-sites.service - Duartec static sites bridge for Espacio and Restaurante
     Loaded: loaded (/home/ubuntu/.config/systemd/user/duartec-static-sites.service; enabled; preset: enabled)
     Active: active (running) since Sun 2026-08-23 00:43:31 UTC; 2 weeks 0 days ago
   Main PID: 1874350 (MainThread)
     CGroup: .../duartec-static-sites.service
             └─1874350 /home/ubuntu/.nvm/versions/node/v24.10.0/bin/node /home/ubuntu/output/playwright/hub-link-audit/static-sites-server.mjs
```

### systemctl --user cat (antes)
```
[Unit]
Description=Duartec static sites bridge for Espacio and Restaurante
After=network.target

[Service]
Type=simple
ExecStart=/home/ubuntu/.nvm/versions/node/v24.10.0/bin/node /home/ubuntu/output/playwright/hub-link-audit/static-sites-server.mjs
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
```
- **Sin WorkingDirectory** → default `/home/ubuntu` (frágil, implícito `!` del análisis previo).
- **Node binario obsoleto:** `v24.10.0` ya no existe en disco (actual es `v24.20.0` en `/home/ubuntu/.nvm/versions/node/v24.20.0/bin/node` y `/usr/bin/node v24.20.0`). El servicio seguía corriendo solo porque el PID era previo a la actualización de Node.

### static-sites-server.mjs — head 80
```js
import { createReadStream, statSync } from 'node:fs';
import { createServer } from 'node:http';
import { extname, join, normalize, relative } from 'node:path';

const host = '100.103.134.102';
const port = 19180;
const roots = {
  '/espacio': '/srv/apps/espacio',
  '/restaurante': '/srv/apps/restaurante/dist',
};
// ... contentTypes, resolveFile(prefix), anti-traversal via relative(), createServer(GET/HEAD only)
// server.listen(port, host, () => console.log(`Static sites server listening on http://${host}:${port}`));
```
- **Cero dependencia de `~/output/playwright/...`** fuera de su propia ubicación. Roots son `/srv/apps/...` ya existentes.
- No importa artefactos playwright, no hardcode de rutas `~/output`.

### Filesystem
```
~/output/playwright/hub-link-audit/:
  total 1.9M
  -rw-rw-r-- 1.9M hub-v2-fixed.png
  -rw-rw-r-- 2.5K static-sites-server.mjs

/srv/apps/espacio: 444K (index.html, reservas.html, assets/, backend/, node_modules/...)
/srv/apps/restaurante/dist: 216K (_astro/, 404.html, index.html, menu/, reservas/, ...)

ss -lntup | grep 19180:
  tcp LISTEN 0 511 100.103.134.102:19180 0.0.0.0:* users:(("MainThread",pid=1874350,fd=21))

curl:
  http://127.0.0.1:19180/espacio/ → 000 (esperado: bind solo a tailscale IP)
  http://100.103.134.102:19180/espacio/ → 200 (<!DOCTYPE html> El Santuario...)
  http://100.103.134.102:19180/restaurante/ → 200
```

### Veredicto pre-check
Confirma investigación previa: **VIGENTE PERO FRÁGIL** — funciona, pero `ExecStart` apunta a ruta volátil `~/output/playwright/...` y binario NVM efímero. Reubicación segura.

---

## 2. Decisión

**→ REUBICAR (seguro).**

Criterio tarea:
- Si static file server sirve desde `/srv/apps/...` y no depende de playwright output → reubicar moviendo `.mjs` a `/srv/apps/static-sites/server.mjs` y actualizando unit.
- Si tuviera hardcode `~/output/playwright/...` o artefactos → NO mover, solo documentar.

Análisis: archivo es puro `node:http` static server, sin deps `~/output`. **Apto para reubicación inmediata.**

### Backups previos (ejecutados)
```bash
mkdir -p ~/infra-audit/backups-2026-09-06
cp -a ~/output/playwright/hub-link-audit/static-sites-server.mjs ~/infra-audit/backups-2026-09-06/static-sites-server.mjs.bak
systemctl --user cat duartec-static-sites > ~/infra-audit/backups-2026-09-06/duartec-static-sites.unit.bak
```
- `static-sites-server.mjs.bak`: 2.5K ✔
- `duartec-static-sites.unit.bak`: 377 bytes ✔

### Acciones de reubicación (ejecutadas)
```bash
sudo mkdir -p /srv/apps/static-sites && sudo chown ubuntu:ubuntu /srv/apps/static-sites
cp -a ~/output/playwright/hub-link-audit/static-sites-server.mjs /srv/apps/static-sites/server.mjs

# Nuevo unit ~/.config/systemd/user/duartec-static-sites.service:
[Unit]
Description=Duartec static sites bridge for Espacio and Restaurante
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/node /srv/apps/static-sites/server.mjs
WorkingDirectory=/srv/apps/static-sites
Restart=always
RestartSec=3

[Install]
WantedBy=default.target

systemctl --user daemon-reload
systemctl --user restart duartec-static-sites
```
Cambios clave:
- `ExecStart` de `/home/ubuntu/.nvm/.../v24.10.0/bin/node ~/output/...` → `/usr/bin/node /srv/apps/static-sites/server.mjs` (estable, sistema; `v24.20.0` disponible)
- `WorkingDirectory=/srv/apps/static-sites` explícito (elimina fragilidad `!/home/ubuntu` / default home)
- Ubicación nueva `/srv/apps/static-sites` consistente con `/srv/apps/espacio` y `/srv/apps/restaurante` (previo plan `/srv/apps`).

---

## 3. Validación (post-reubicación 2026-09-06T03:13:37 UTC)

```
systemctl --user is-active duartec-static-sites
  → active

systemctl --user status duartec-static-sites
  ● active (running) since Sun 2026-09-06 03:13:37 UTC; 2s ago
    Main PID: 4011639 (MainThread)
    └─4011639 /usr/bin/node /srv/apps/static-sites/server.mjs
    Started duartec-static-sites.service
    Static sites server listening on http://100.103.134.102:19180

ss -lntup | grep 19180
  tcp LISTEN 0 511 100.103.134.102:19180 0.0.0.0:* users:(("MainThread",pid=4011639,fd=21))

curl -s -o /dev/null -w "%{http_code}" http://100.103.134.102:19180/espacio/     → 200
curl -s http://100.103.134.102:19180/espacio/ | head -5                          → <!DOCTYPE html> El Santuario...
curl -s -o /dev/null -w "%{http_code}" http://100.103.134.102:19180/restaurante/ → 200
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:19180/espacio/            → 000 (correcto, bind tailscale-only)
```

✅ Sin regresión. PID nuevo con binario `/usr/bin/node` y path estable.

---

## 4. Rollback

Si el nuevo path falla (p.ej. permisos `/srv/apps/static-sites`):

```bash
# Restaurar fuentes
cp -a ~/infra-audit/backups-2026-09-06/static-sites-server.mjs.bak ~/output/playwright/hub-link-audit/static-sites-server.mjs
cp ~/infra-audit/backups-2026-09-06/duartec-static-sites.unit.bak ~/.config/systemd/user/duartec-static-sites.service
# O si el backup unit no existe: restaurar manual con ExecStart nvm viejo (ajustar a v24.20.0 si hace falta):
# ExecStart=/home/ubuntu/.nvm/versions/node/v24.20.0/bin/node /home/ubuntu/output/playwright/hub-link-audit/static-sites-server.mjs
systemctl --user daemon-reload
systemctl --user restart duartec-static-sites
systemctl --user status duartec-static-sites
ss -lntup | grep 19180
curl -s -o /dev/null -w "%{http_code}" http://100.103.134.102:19180/espacio/
```

Nota: el archivo original `~/output/playwright/hub-link-audit/static-sites-server.mjs` se **conservó** (solo `cp -a`, no `mv`), por lo que rollback es trivial. El backup en `~/infra-audit/backups-2026-09-06/` garantiza reversión aunque se borre `~/output`.

---

## 5. Estado final y recomendaciones

- **Frágil eliminado:** ya no depende de `~/output/playwright` ni de ruta NVM volátil.
- **Próximos pasos opcionales:** limpieza de `~/output/playwright/hub-link-audit/static-sites-server.mjs` cuando se considere estable (no urgente; mantener 1–2 semanas). Considerar añadir `Restart=always` ya presente y monitorizar con `systemctl --user is-active` en validación final global.
- **No tocado:** trading, CNMV, portfolio-mtm, whisper, mail-relay, tailscale (8082), crons — según scope G4.

