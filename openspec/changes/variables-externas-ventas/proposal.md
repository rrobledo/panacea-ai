## Why

Hoy el analista explica las ventas solo con datos internos (fecha, sucursal, producto, cliente). En las Sierras de Córdoba gran parte de la variación diaria viene de afuera: clima, feriados y fines de semana largos, temporada turística, eventos locales (Oktoberfest, temporada teatral) y días de cobro. Sin esas variables el agente no puede separar "vendimos menos porque llovió el fin de semana largo" de una caída real, y las proyecciones ignoran los próximos feriados y el pronóstico.

Fuente: artifact "Variables externas para analizar ventas · Sierras de Córdoba" (14/11/2026), https://claude.ai/artifact/d5161b21-8b30-40a0-b88c-9a57ae44656e

## What Changes

- Nuevo catálogo `config/lugares_venta.yaml` que asocia cada `lugar_venta_id` (0 Dietética, 1 Villa Allende, 2 Carlos Paz, 3 Córdoba, 4 Villa General Belgrano) con localidad, coordenadas y perfil turístico.
- Nuevo calendario `config/calendario_externo.yaml` con lo que ninguna API trae: días no laborables y puentes turísticos, temporadas (verano, vacaciones de invierno de Córdoba, Semana Santa), eventos locales por localidad (Oktoberfest, Chocolate Alpino, Masa Vienesa, temporada teatral de Carlos Paz) y aguinaldo.
- Nuevas herramientas de datos en `agent/tools/externas.py`, compartidas por el servidor MCP `ventas-db` (Claude Code) y la app web:
  - `ventas_con_contexto`: serie diaria de ventas, tickets y unidades por lugar de venta, enriquecida con clima histórico (Open-Meteo), feriados nacionales (Nager.Date), fin de semana largo, víspera de feriado, día de cobro, temporada y eventos.
  - `impacto_variables`: efecto en % de cada variable sobre la venta diaria, controlando por día de la semana y lugar, con cantidad de días observados para juzgar la confiabilidad.
  - `contexto_proximos_dias`: pronóstico del clima a 14 días, próximos feriados y eventos por lugar, para estimar demanda y planificar dotación y stock.
- Clientes HTTP de Open-Meteo y Nager.Date (gratuitos, sin API key) con caché y tolerancia a fallas: si la API no responde, la herramienta devuelve las variables de calendario y avisa qué faltó.
- `.mcp.json`: se agrega el servidor `open-meteo` (versión fijada) para consultas de clima ad hoc desde Claude Code.
- Se actualizan `config/perfiles/ventas.yaml` (herramientas habilitadas), `prompts/ventas.md` y `CLAUDE.md` (reglas para usar y comunicar estas variables: hechos vs. hipótesis, mínimo de días observados, VGB con pocas semanas de historia).
- Fuera de alcance de esta etapa: TomTom (tránsito), PredictHQ y Fever (eventos), AccuWeather/Xweather y series macro (BCRA/INDEC). Requieren claves o son pagos; quedan documentados como fase 2.

## Capabilities

### New Capabilities
- `external-sales-variables`: catálogo de lugares de venta geolocalizados, calendario externo, obtención de clima y feriados, y las herramientas que cruzan esas variables con las ventas (serie enriquecida, impacto por variable y contexto de los próximos días).

### Modified Capabilities
<!-- No hay specs archivadas en openspec/specs/. El registro de herramientas y el perfil de ventas cambian por configuración, sin cambiar requisitos existentes. -->

## Impact

- **Código**: nuevo `agent/tools/externas.py` y `agent/externas/` (clientes Open-Meteo y Nager.Date, carga del calendario); `agent/tools/registro.py` registra las 3 herramientas; `mcp_server/server.py` las expone sin cambios de estructura; tests nuevos con respuestas HTTP simuladas.
- **Configuración**: `config/lugares_venta.yaml`, `config/calendario_externo.yaml`, `config/perfiles/ventas.yaml`, `.mcp.json`, `prompts/ventas.md`, `CLAUDE.md`.
- **Dependencias**: `httpx` en Python (cliente HTTP con timeout). Node: `open-meteo-mcp-server@2.5.6` vía `npx`, solo para Claude Code.
- **Red**: salida HTTPS desde Vercel y desde la máquina local a `archive-api.open-meteo.com`, `api.open-meteo.com` y `date.nager.at`. No se envían datos de ventas ni de clientes: solo coordenadas, fechas y el código de país.
- **Licencias**: Open-Meteo es gratuito para uso no comercial; para uso comercial hay que evaluar el plan pago o el autoalojamiento (ver design).
- **Costos**: sin costo de API en esta etapa; más tokens por turno cuando el agente trae la serie enriquecida (se acota agregando por día y limitando el rango).
