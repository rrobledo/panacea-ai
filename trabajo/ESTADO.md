# Estado del trabajo – guardado el 29/10/2026

## Qué se hizo (sesión del 16/10/2026)

| Entregable | Archivo local | Link publicado |
|---|---|---|
| Reporte de estrategia comercial (ventas, mapa semanal top 20, canasta sin Dietética, desperdicio) | `reportes/reporte_estrategia_2026-10-16.html` | https://claude.ai/artifact/KdZFGe3gNSGdj1XSWkCS2J (sigue publicado) |
| Programación de producción de noviembre (plantilla semanal, calendario, envíos VGB) | `reportes/reporte_programacion-noviembre_2026-10-16.html` | Ya no está publicada (se borró o se perdió el acceso) |
| Presentación al equipo de ventas (15 diapositivas) | `trabajo/presentaciones/ventas/project/` | Ya no está publicada |
| Presentación al equipo de producción (14 diapositivas) | `trabajo/presentaciones/produccion/project/` | Ya no está publicada |

Las presentaciones están en el formato del tipo "Slides" de claude.ai: `deck.json` y una diapositiva HTML por archivo en `slides/`. Para republicarlas hay que crear un deck nuevo desde el tipo Slides y subir esos archivos.

## Pendientes

1. **Título de la portada de ventas.** El usuario pidió hacerlo más impactante. Propuestas con datos reales:
   - Opción 2, recomendada: "Facturamos 45% más, pero vendemos lo mismo", con el subtítulo "Vamos por más tickets y más productos por ticket".
   - Alternativas: "Un producto más por ticket: de $6.060 a $10.424" o "Que entren más. Que lleven más."
   - Falta que el usuario elija una.
2. **Republicar.** Decidir si vuelven a publicarse las presentaciones y la programación. Si se republica la programación, actualizar el link de la diapositiva `plan` de la presentación de producción.
3. **Confirmaciones pendientes del usuario:**
   - Precio a granel. El usuario informó Chipa $2.800, Francés $1.800 y Criollos $2.000 por 100 g, pero la caja cobra unos $9.000 a $12.000 por kg.
   - Si el Pan de Pancho se usa en la cocina sin registrarse como venta.
   - Si el feriado del 20/11 pasa al lunes 23/11.
   - Por qué no hay ventas de Villa General Belgrano después del 05/10. Revisar que el sistema de caja de ese local cargue en la base.
4. **Opcional.** Valuar el desperdicio a costo de insumos con `costos_costos` y `costos_insumos`, en lugar de a precio de venta.

## Cifras clave

- **Año, 1/1 al 15/10, 2026 contra 2025:**
  - Ventas $399,4 M (+45,7%) y unidades 121.948 (+4,1%).
  - Tickets 27.566 (+14,0%) y ticket promedio $14.487 (+27,8%).
  - Precio por unidad +40%.
- **Tercer trimestre:** unidades 0% y tickets −3,5%. Villa Allende tuvo −293 tickets (−9,8%).
- **Mayoristas:** Dulce Miga (≈ $1,46 M por mes) no compra desde el 17/06, y hay 4 clientes más con más de 90 días sin comprar.
- **Mostrador:**
  - El 40% de los tickets lleva un solo producto ($6.060); los de dos productos promedian $10.424.
  - El café aparece en el 7,9% de los tickets.
- **Desperdicio:** entre $3,0 M y $9,8 M por mes a precio de venta, sobre ≈ $39,7 M producidos por mes.
- **Plan de noviembre con margen 0,5:**
  - Producción planificada ≈ $48,4 M por mes.
  - Sobrante esperado $5,3 M y venta perdida por faltantes $2,7 M.

## Carpetas

- `trabajo/scripts/`: scripts de análisis.
  - `merma2.py`: producción contra ventas, con los mapeos manuales y la conversión de paquetes.
  - `plan.py`: genera `plan_items.json`.
  - `run*.js`: pruebas de humo de los reportes.
  - Los scripts acceden a la base importando `mcp_server/server.py` en modo solo lectura.
- `trabajo/datos/`: resultados intermedios en JSON (merma, plan, ventas semanales).

## Notas técnicas

- `mcp_server/server.py` convierte `postgres://` en `postgresql+psycopg2://`.
- `.mcp.json` usa el Python del entorno virtual del proyecto. Si `ventas-db` no conecta, ejecutar `/mcp`.

## Plan comercial con seguimiento semanal (creado el 31/10/2026)

- Carpeta: `plan_ventas/`. La rutina de cada lunes está en `plan_ventas/README.md`.
- Página general: https://claude.ai/artifact/KreYKSVH7GwbekvN68WhYJ. Se actualiza en el mismo link.
- El plan va del 02/11/2026 al 31/01/2027: 13 semanas, 9 estrategias, 27 acciones y 19 indicadores.
- **Pendiente:** correr `kpis_semana.py`, que requiere `DATABASE_URL`. Por eso el SQL todavía no se probó contra la base real. Además faltan los responsables de cada estrategia.
- 31/10/2026: la conexión quedó configurada en `.claude/settings.local.json` (env, archivo en .gitignore).
- Reporte de la línea base, semana 2026-W44: https://claude.ai/artifact/VLm3QrRS5xb8FD7qBP4ywH
- La comparación interanual usa solo sucursales comparables. Córdoba operó del 17/10/2025 al 18/03/2026 y Villa General Belgrano abrió el 25/09/2026.
- Pendiente: decidir si se recalibran las metas de E3 y E4, que ya se cumplían antes de empezar, y revisar la lista de 10 mayoristas objetivo.
- 02/11/2026: el ticket promedio se compara contra la base post aumento (28/09; semanas W40, W41 y W43). Se agregaron el ticket a precios constantes (índice de precios) y las métricas por sucursal (`historico.py`).
- Reporte para el equipo de ventas: https://claude.ai/artifact/LxLuxP9fqAYnNPB3xGLB8q (`reportes/reporte_equipo-ventas_2026-11-02.html`).
- Pendientes: confirmar si cambió la carga de tickets en Carlos Paz desde el 07/09 y averiguar por qué cayeron los tickets de Villa General Belgrano.

## 02/11/2026 — Corrección de calendario
- El plan se armó el 24/10/2026 y se ejecuta desde el domingo 25/10. Las semanas del plan van de domingo a sábado (clave ISO del lunes siguiente: 2026-W44 = 25/10 al 31/10). Fin: 23/01/2027. Las acciones se corrieron una semana.
- Base previa al plan: semanas W40, W41 y W43 (27/09–10/10 y 18/10–24/10); W42 (11–17/10) excluida por atípica.
- Informe de la primera semana: reporte del equipo (LxLuxP9fqAYnNPB3xGLB8q, v2), semana W44 (VLm3QrRS5xb8FD7qBP4ywH, v4) y general (KreYKSVH7GwbekvN68WhYJ, v5).
- Pendiente: cargar el estado real de las acciones de la primera semana en semanas/2026-W44/avances.json.
