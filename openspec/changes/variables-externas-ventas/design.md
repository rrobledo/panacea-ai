## Context

El analista de ventas corre por dos canales que comparten el mismo registro de herramientas (`agent/tools/registro.py`): el servidor MCP local `ventas-db` (Claude Code) y la app web (FastAPI + loop propio sobre la Messages API, desplegada como función Python en Vercel). Las herramientas son funciones Python que reciben un `ContextoPerfil` y devuelven JSON.

El artifact de referencia propone un catálogo de MCP externos: Open-Meteo y Nager.Date (gratis, sin clave), TomTom Maps y Traffic Analytics, PredictHQ, Fever, AccuWeather y Xweather (con clave, pagos o conectores de la cuenta de Claude).

Estado de los datos (consulta del 14/11/2026 a `panacea_sales_v2`):

| id | lugar_venta | desde | ventas ARS | tickets |
|---|---|---|---|---|
| 2 | Carlos Paz | 27/03/2024 | 472,8 M | 47.950 |
| 1 | Villa Allende | 21/09/2022 | 298,5 M | 42.089 |
| 0 | Dietetica | 22/09/2022 | 262,6 M | 4.066 |
| 3 | Cordoba | 17/10/2025 (hasta 18/03/2026) | 47,4 M | 3.373 |
| 4 | Villa General Belgrano | 25/09/2026 | 12,6 M | 906 |

Verificaciones hechas al redactar este diseño:
- `open-meteo-mcp-server` 2.5.6 existe en npm y expone `weather_archive`, `weather_forecast` y otras 15 herramientas.
- La URL `https://gateway.pipeworx.io/nager-holidays/mcp` del artifact ya no existe. El reemplazo (`/holidays/mcp`) es un agregador de terceros que mezcla las herramientas de feriados con más de 40 herramientas ajenas (Polymarket, memoria, etc.).
- `https://date.nager.at/api/v3/PublicHolidays/2026/AR` responde sin clave.

## Goals / Non-Goals

**Goals:**
- Que el agente, en ambos canales, pueda cruzar ventas diarias con clima, feriados, fines de semana largos, cobro, temporada y eventos locales.
- Medir el efecto de cada variable por lugar de venta, con indicación de confiabilidad.
- Anticipar los próximos 14 días (pronóstico + calendario) para dotación, stock y promociones.
- No sacar datos de ventas ni de clientes del sistema.

**Non-Goals:**
- Tránsito (TomTom), eventos comerciales (PredictHQ, Fever), AccuWeather/Xweather y series macro: requieren claves o contratos. Fase 2.
- Un modelo econométrico completo (regresión multivariada, estacionalidad con Prophet). El impacto se mide con comparaciones controladas simples y se presenta como orientativo.
- Persistir el clima en la base: por ahora, caché en memoria.

## Decisions

### 1. Herramientas nativas en Python en lugar de conectar los MCP externos al agente
Se implementan clientes HTTP de Open-Meteo y Nager.Date dentro de `agent/externas/` y se exponen como herramientas del registro compartido.

- Alternativa A: sumar servidores MCP a `.mcp.json`. Solo sirve en Claude Code; la app web en Vercel no puede lanzar procesos `npx`.
- Alternativa B: usar el conector MCP de la Messages API (`mcp_servers`). Solo acepta servidores remotos; Open-Meteo es stdio y el único remoto de feriados es el agregador Pipeworx, que mete ruido en el contexto y es un tercero no auditado.
- Ventaja decisiva: el join con las ventas se hace en el servidor. Si el modelo trajera el clima por un lado y las ventas por otro, tendría que cruzar cientos de filas en el contexto: más tokens y más errores.

Además se agrega `open-meteo` (versión fijada 2.5.6) a `.mcp.json` para preguntas puntuales de clima en Claude Code. No es parte del flujo de análisis.

### 2. Configuración en YAML para lo que ninguna API trae
- `config/lugares_venta.yaml`: id → nombre, localidad, lat/lon, `perfil` (residencial | turistico | eventos | online). La "Dietetica" (id 0) no tiene ubicación conocida: queda sin coordenadas hasta confirmarlo (ver Open Questions).
- `config/calendario_externo.yaml`: días no laborables y puentes turísticos (ej. 07/12/2026), temporadas (verano 15/12–15/03, vacaciones de invierno de Córdoba por año, Semana Santa), eventos con `lugares: [4]`, `desde`, `hasta`, `estado`, y aguinaldo. Se precarga con las fechas del artifact para 2024–2027 y con las ediciones pasadas de los eventos que haya en la historia de ventas (Oktoberfest 2024, 2025 y 2026, temporadas teatrales).
- Se valida con Pydantic al cargar, igual que los perfiles.

### 3. Variables derivadas en Python, no en SQL
La consulta SQL devuelve solo la serie diaria agregada por lugar (`GROUP BY operation_date, lugar_venta_id`), con los filtros del perfil y `excluir_clientes` opcional. Las variables externas se agregan en Python sobre esa serie. Así el `sql_guard` no cambia y no hace falta crear tablas.

Definiciones:
- `dia_cobro`: primeros 5 días hábiles del mes.
- `aguinaldo`: del 15 al 30/06 y del 15 al 31/12.
- `calor_extremo`: máxima ≥ 33 °C; `frio`: máxima ≤ 12 °C; `dia_lluvioso`: lluvia ≥ 1 mm.
- `fin_de_semana_largo`: bloque de 3 o más días seguidos no laborables (fin de semana + feriados + no laborables).

### 4. Cálculo del impacto
Para cada lugar, se normaliza la métrica diaria dividiéndola por su mediana móvil centrada de 28 días. Esto neutraliza la inflación y la tendencia, que en ARS son fuertes. Se usa la mediana y no la media porque, con la media, los propios días con la variable bajan la base: en la prueba con lluvia que reduce la venta a la mitad, la media daba −42% en vez de −50%. Para cada variable binaria V:

`efecto_pct = mediana(índice | V, mismo día de semana) / mediana(índice | no V, mismo día de semana) − 1`, ponderado por la cantidad de días con V de cada día de la semana.

Se usa la mediana para que un día atípico no domine. Se informa `dias_con` y `dias_sin`, y `confiable = dias_con ≥ 8`. Se descarta la regresión múltiple por ahora: con 2 a 4 años de historia y variables correlacionadas (temporada y feriados), los coeficientes serían inestables y difíciles de explicar al usuario.

### 5. Caché y tolerancia a fallas
- `httpx` con timeout de 8 s y un reintento.
- Caché `functools.lru_cache` por (lugar, año) para el clima histórico y por año para los feriados. El pronóstico se cachea 1 h.
- Un rango de varios años es una sola llamada por lugar a la API de archivo (que acepta rangos largos), así que el costo de red está acotado.
- Si una fuente falla, la herramienta devuelve igual lo demás con `avisos`. Nunca lanza una excepción hacia el loop.

### 6. Formato de respuesta
Igual que las demás herramientas: JSON con `columnas`, `filas`, `total_filas` y `truncado`, más `avisos` (lista) y `fuentes` (Open-Meteo, Nager.Date, calendario propio con fecha de actualización).

## Risks / Trade-offs

- [Licencia de Open-Meteo: gratis solo para uso no comercial] → Para el análisis interno de Panacea el volumen es mínimo, pero hay que decidir si se contrata el plan comercial (API key con el mismo formato) o se autoaloja. El cliente acepta una `OPEN_METEO_API_KEY` opcional y una URL base configurable desde el inicio.
- [El calendario YAML se desactualiza (eventos de 2027 "a confirmar")] → Estado por entrada, avisos visibles y una tarea de mantenimiento: revisar el archivo cada trimestre.
- [Pocos datos en VGB y Córdoba] → Marcado `insuficiente` y aviso explícito; el prompt prohíbe sacar conclusiones con menos de 8 días con la variable.
- [Confusión entre variables (los fines de semana largos caen en temporada)] → Se informa como asociación; `impacto_variables` acepta filtrar por temporada para comparar dentro de un mismo período.
- [Latencia en Vercel por llamadas externas] → Caché, una llamada por lugar y timeout corto; en el peor caso la herramienta responde sin clima en ~8 s.
- [Salida de red desde la función] → Solo coordenadas y fechas; ningún dato de ventas. Se documenta en el README.

## Migration Plan

1. Agregar `httpx` a `requirements.txt` y los YAML nuevos.
2. Implementar y testear con respuestas HTTP simuladas.
3. Registrar las herramientas y habilitarlas en `config/perfiles/ventas.yaml`.
4. Desplegar. Rollback: quitar las 3 herramientas del perfil (la app deja de ofrecerlas sin redeploy de código si se revierte el YAML).

## Open Questions

- ¿Dónde está la "Dietetica" (id 0)? ¿Es un local físico (y en qué localidad) o un canal online o mayorista? Con 4.066 tickets y 262 M ARS, el ticket promedio es ~10 veces el de los locales, lo que sugiere venta mayorista.
- ¿La sucursal Córdoba (id 3) cerró en marzo de 2026? Si es así, se usa solo para el análisis histórico.
- ¿El uso de Panacea cuenta como comercial para Open-Meteo? Define si hace falta el plan pago.
- ¿Querés sumar en fase 2 TomTom (tránsito en los accesos de Villa Allende y Carlos Paz) o PredictHQ (eventos)? Ambos requieren cuenta y clave.
