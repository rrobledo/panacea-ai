# Plan comercial Panacea: seguimiento semanal

El plan parte del reporte de estrategia del 16/10/2026 (`reportes/reporte_estrategia_2026-10-16.html`,
https://claude.ai/artifact/KdZFGe3gNSGdj1XSWkCS2J). Tiene 9 estrategias, 27 acciones y 19 indicadores, y dura
13 semanas: del domingo 25/10/2026 al sábado 23/01/2027. El plan se armó el 24/10; las semanas van de domingo a sábado (la clave 2026-W44 es del 25/10 al 31/10).

## Carpetas

```
plan_ventas/
├── plan/
│   ├── plan.json               ← EL PLAN: estrategias, acciones con semana objetivo, indicadores con base y meta
│   ├── clientes_objetivo.json  ← mayoristas inactivos al 15/10 (se crea solo en la primera corrida)
│   └── artifacts.json          ← links publicados (general y de cada semana)
├── semanas/
│   └── 2026-W45/               ← una carpeta por semana del plan (domingo a sábado)
│       ├── kpis.json           ← automático: indicadores calculados desde la base
│       ├── avances.json        ← manual: estado de acciones, KPI manuales, hechos, decisiones
│       └── reporte_semana_2026-W45.html
├── seguimiento_general.html    ← página general del plan
└── scripts/
    ├── kpis_semana.py          ← consulta la base (solo lectura) y escribe kpis.json
    ├── generar.py              ← arma las páginas HTML desde los JSON (no usa la base)
    └── plantilla_*.html, estilo.css, comun.js
```

## Métricas por sucursal y base post aumento

- `scripts/historico.py` arma la serie semanal por sucursal desde julio (`datos/historico.json`) y la base previa al plan (`plan/bases.json`: semanas posteriores al último aumento y anteriores al inicio del plan). También genera la proyección de tickets.
- El ticket promedio, las unidades por ticket, el % de un solo producto y el % de café se comparan contra esa base. Así se mide con los mismos precios.
- El "ticket a precios constantes" divide el ticket por un índice de precios de mostrador y se compara contra 2025.
- **Cuando haya un aumento de precios:** actualizar `ultimo_aumento` y `semanas_base` en `plan.json` (2 a 4 semanas posteriores al aumento) y volver a correr `historico.py`.
- **Reporte para el equipo de ventas:** `python3 plan_ventas/scripts/generar.py --equipo` lo escribe en `reportes/`. Los textos (resumen, comentarios por sucursal, estrategias) están en `datos/notas_equipo.json`.

## Rutina de cada lunes

1. **Datos de ventas** (`DATABASE_URL` está en `.claude/settings.local.json`). Correr `historico.py` y después:
   `.venv/bin/python plan_ventas/scripts/kpis_semana.py` calcula la última semana completa.
   Para una semana puntual, agregá el argumento, por ejemplo `2026-W45`.
2. **Avances** en `semanas/<semana>/avances.json`:
   - `acciones`: el estado de cada acción (`pendiente`, `en_curso`, `hecha`, `bloqueada` o `descartada`) y una nota opcional. Cada semana nueva copia los estados de la anterior.
   - `kpis_manuales`: `pct_sobrante` (% de sobrante de los 5 productos foco), `dias_produccion_cargada` (0 a 7) y `tickets_con_pack`.
   - `hechos`, `decisiones` y `proxima_semana`: listas de texto libre.
   - Para crear la plantilla sin conexión a la base: `python3 plan_ventas/scripts/generar.py --nueva 2026-W46`.
3. **Páginas**: `python3 plan_ventas/scripts/generar.py` regenera el reporte de cada semana y el general.
4. **Publicar**: pedile a Claude "publicá el seguimiento de la semana X".
   - El reporte semanal se publica como artifact nuevo.
   - El general se actualiza en el mismo link.
   - Los links quedan guardados en `plan/artifacts.json`.

## Cómo se evalúa cada indicador

- **interanual**: variación contra la misma semana de 2025 (fechas −364 días).
- **valor**: el número de la semana, por ejemplo el % de tickets con un solo producto.
- **acumulado**: total desde el inicio del plan, por ejemplo los mayoristas reactivados.

Estados posibles:
- **En meta**: alcanzó el objetivo.
- **Mejora**: está mejor que la base, pero sin llegar a la meta.
- **Sin mejora**: está igual o peor que la base.
- **Referencia**: el indicador no tiene meta.

Para cambiar metas, responsables o acciones, editá `plan/plan.json` y regenerá las páginas. Los
responsables figuran como "A definir".
