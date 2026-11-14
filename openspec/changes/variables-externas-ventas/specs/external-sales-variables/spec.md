## ADDED Requirements

### Requirement: Catálogo de lugares de venta geolocalizados
El sistema SHALL cargar `config/lugares_venta.yaml`, que asocia cada `lugar_venta_id` con nombre, localidad, latitud, longitud, zona horaria y perfil (residencial, turístico, etc.). Las herramientas de variables externas MUST resolver la ubicación de un lugar de venta solo desde este catálogo.

#### Scenario: Lugar de venta catalogado
- **WHEN** una herramienta recibe `lugar_venta_id = 2`
- **THEN** usa las coordenadas de Villa Carlos Paz (-31.4241, -64.4978) para consultar el clima

#### Scenario: Lugar de venta sin catalogar
- **WHEN** las ventas incluyen un `lugar_venta_id` que no está en el catálogo
- **THEN** la herramienta devuelve sus ventas con las variables de calendario, deja las de clima vacías e informa en `avisos` que ese lugar no tiene ubicación

#### Scenario: Catálogo inválido
- **WHEN** `config/lugares_venta.yaml` tiene coordenadas fuera de rango o ids repetidos
- **THEN** la carga de configuración falla al iniciar con un mensaje que indica el archivo y el campo

### Requirement: Calendario externo configurable
El sistema SHALL cargar `config/calendario_externo.yaml` con días no laborables y puentes, temporadas, eventos locales (con fecha de inicio, fin y lugares a los que aplican) y fechas de aguinaldo. Cada entrada MUST tener un estado `confirmado` o `a_confirmar`.

#### Scenario: Evento local acotado a una localidad
- **WHEN** se arma la serie del 9 al 12 de octubre de 2026
- **THEN** los días de Villa General Belgrano tienen `evento = "Oktoberfest"` y los de Villa Allende no tienen evento

#### Scenario: Fecha a confirmar
- **WHEN** una variable proviene de una entrada con estado `a_confirmar`
- **THEN** la herramienta la incluye y la lista en `avisos` como fecha no confirmada

### Requirement: Feriados nacionales
El sistema SHALL obtener los feriados nacionales de Argentina desde Nager.Date por año y combinarlos con los días no laborables del calendario externo. A partir de ellos MUST calcular para cada fecha: `feriado`, `no_laborable`, `fin_de_semana_largo` (bloque de 3 o más días sin actividad laboral que incluye sábado y domingo) y `vispera_feriado`.

#### Scenario: Fin de semana largo
- **WHEN** el lunes 23/11/2026 es feriado
- **THEN** el sábado 21, el domingo 22 y el lunes 23 tienen `fin_de_semana_largo = true` y el viernes 20 tiene `vispera_feriado = true`

#### Scenario: Nager.Date no responde
- **WHEN** la API de Nager.Date falla o supera el timeout
- **THEN** la herramienta usa solo el calendario externo, marca `feriado` como desconocido (null) para ese año e informa la falla en `avisos`

### Requirement: Clima histórico y pronóstico
El sistema SHALL obtener de Open-Meteo, por lugar de venta y día, la temperatura máxima y mínima, la lluvia en mm y el código de clima: el histórico desde la API de archivo y los próximos 14 días desde la API de pronóstico. Las respuestas MUST guardarse en caché por lugar y rango para no repetir llamadas dentro de un mismo proceso. Solo se envían coordenadas y fechas: ningún dato de ventas ni de clientes sale del sistema.

#### Scenario: Día lluvioso
- **WHEN** el 15/03/2026 llovieron 12 mm en Villa Allende
- **THEN** la fila de ese día y lugar tiene `lluvia_mm = 12` y `dia_lluvioso = true` (umbral: 1 mm o más)

#### Scenario: Clima no disponible
- **WHEN** Open-Meteo falla para un lugar
- **THEN** las columnas de clima de ese lugar quedan en null, el resto de la serie se devuelve igual y `avisos` lo informa

### Requirement: Serie de ventas enriquecida
La herramienta `ventas_con_contexto(desde, hasta, lugar_venta_id?)` SHALL devolver una fila por día y lugar de venta con ventas (SUM(subtotal)), tickets (COUNT DISTINCT document_id) y unidades (SUM(count)), más las variables de calendario, cobro, temporada, eventos y clima. El rango MUST limitarse a 400 días por llamada y la respuesta MUST respetar `max_filas` del perfil, indicando si se truncó.

#### Scenario: Consulta de un trimestre
- **WHEN** se pide del 01/08/2026 al 31/10/2026 para Carlos Paz
- **THEN** se devuelven 92 filas con ventas, tickets, unidades y todas las variables externas

#### Scenario: Rango demasiado largo
- **WHEN** se pide un rango de más de 400 días
- **THEN** la herramienta responde con un error que pide acotar el rango o usar `impacto_variables`

#### Scenario: Día sin ventas
- **WHEN** un lugar no registró ventas en una fecha del rango posterior a su primera venta
- **THEN** la fila aparece con ventas, tickets y unidades en 0

### Requirement: Impacto de cada variable
La herramienta `impacto_variables(desde, hasta, lugar_venta_id?, metrica)` SHALL estimar, para cada variable binaria (lluvia, calor extremo, feriado, fin de semana largo, víspera, día de cobro, temporada, evento), el efecto en % sobre la métrica (ventas, tickets o unidades) frente a días comparables sin la variable, en el mismo lugar y día de la semana. Cada efecto MUST incluir la cantidad de días con y sin la variable, y se MUST marcar como `insuficiente` cuando haya menos de 8 días con la variable.

#### Scenario: Ranking de variables
- **WHEN** se pide el impacto en ventas de Carlos Paz para los últimos 24 meses
- **THEN** se devuelve un ranking por efecto absoluto con `efecto_pct`, `dias_con`, `dias_sin` y `confiable`

#### Scenario: Poca historia
- **WHEN** se pide el impacto para Villa General Belgrano, que vende desde el 25/09/2026
- **THEN** la mayoría de las variables salen como `insuficiente` y `avisos` indica que la historia es menor a un año

#### Scenario: Ventas en ARS con inflación
- **WHEN** el rango supera 3 meses y la métrica es ventas
- **THEN** el efecto se calcula sobre la venta diaria dividida por la mediana móvil de 28 días del mismo lugar, para que la inflación no sesgue la comparación, y la respuesta lo aclara en `metodo`

### Requirement: Contexto de los próximos días
La herramienta `contexto_proximos_dias(dias, lugar_venta_id?)` SHALL devolver, para cada lugar y cada día de hoy a `dias` (máximo 14), el pronóstico del clima, si es feriado, fin de semana largo o víspera, si es día de cobro, la temporada y los eventos. MUST incluir también la venta promedio de los últimos 8 días equivalentes (mismo lugar y día de la semana) como referencia.

#### Scenario: Próximo fin de semana largo
- **WHEN** el 14/11/2026 se piden 14 días para Carlos Paz
- **THEN** los días 21, 22 y 23/11 aparecen como fin de semana largo, con su pronóstico y la venta de referencia

### Requirement: Disponibilidad en ambos canales
Las tres herramientas SHALL estar registradas en el registro compartido, de modo que las expongan tanto el servidor MCP `ventas-db` como la app web, y solo se ofrecen al modelo en los perfiles que las listan en `herramientas`.

#### Scenario: Perfil de ventas
- **WHEN** un usuario con perfil `ventas` abre una conversación
- **THEN** el modelo recibe `ventas_con_contexto`, `impacto_variables` y `contexto_proximos_dias` entre sus herramientas

#### Scenario: Claude Code
- **WHEN** se inicia Claude Code en el repo con `ventas-db` habilitado
- **THEN** las tres herramientas aparecen como `mcp__ventas-db__*`

### Requirement: Uso responsable por el agente
El prompt del perfil de ventas SHALL indicar que los efectos de variables externas son asociaciones, no causas probadas; que deben presentarse como HIPÓTESIS salvo que tengan suficientes días observados; y que todo efecto citado en una estrategia debe ir con `dias_con` y el período analizado.

#### Scenario: Recomendación basada en clima
- **WHEN** el agente recomienda reforzar delivery los días de lluvia
- **THEN** cita el efecto medido, los días observados y el período, y marca la recomendación como hipótesis si el efecto no es confiable
