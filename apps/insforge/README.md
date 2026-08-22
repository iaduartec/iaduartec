# InsForge trading backend

Migraciones y configuración mínima del backend InsForge usado por las integraciones de trading. El directorio no contiene exports de datos ni secretos; las credenciales se leen desde `.insforge/project.json` o el gestor de secretos local.

## Migraciones

```bash
npx -y @insforge/cli db migrations list
npx -y @insforge/cli db migrations up
```

La migración inicial crea `trading_trades` y `position_ots`. La migración de ownership añade `owner_id` y reemplaza las políticas globales por predicados `auth.uid()`. Las filas sin propietario quedan inaccesibles hasta que un proceso confiable las asigne explícitamente.

## Seguridad

- No hardcodes claves, tokens, cookies ni URLs privadas.
- Toda escritura debe usar el SDK/CLI de InsForge y pasar por RLS.
- Las políticas deben aislar usuario o tenant; `USING (true)` no es una política de aislamiento.
- Prueba SELECT, INSERT, UPDATE y DELETE con dos identidades antes de desplegar.

## Verificación

Revisa los SQL con el validador del proyecto y consulta el estado del despliegue antes de aplicar cambios. No importes datos gestionados ni secretos desde backups locales.
