## 1. Configuración

- [x] 1.1 Crear `config/lugares_venta.yaml` con los ids 0–4 (coordenadas de Villa Allende, Carlos Paz, Córdoba y Villa General Belgrano; Dietética sin coordenadas hasta confirmar)
- [x] 1.2 Crear `config/calendario_externo.yaml` con no laborables y puentes 2024–2027, temporadas, vacaciones de invierno de Córdoba, aguinaldo y eventos locales (Oktoberfest, Chocolate Alpino, Masa Vienesa, temporada teatral de Carlos Paz), con estado `confirmado`/`a_confirmar`
- [x] 1.3 Modelos Pydantic y carga validada de ambos YAML en `agent/externas/config.py`, con errores que nombran archivo y campo
- [x] 1.4 Agregar `httpx` a `requirements.txt` y `OPEN_METEO_API_KEY` opcional a `.env.example` (con clave se usan los hosts comerciales customer-*)

## 2. Fuentes externas

- [x] 2.1 Cliente Nager.Date (`agent/externas/feriados.py`): feriados AR por año, timeout de 8 s, un reintento, caché por año
- [x] 2.2 Cliente Open-Meteo (`agent/externas/clima.py`): histórico diario (archivo) y pronóstico a 14 días, con caché por (lugar, año) y de 1 h para el pronóstico, y clave opcional
- [x] 2.3 Módulo de calendario (`agent/externas/calendario.py`): feriado, no laborable, fin de semana largo, víspera, día de cobro, aguinaldo, temporada y eventos por lugar
- [x] 2.4 Tests de las fuentes con respuestas HTTP simuladas, incluido el caso de falla y timeout

## 3. Herramientas

- [x] 3.1 `ventas_con_contexto` en `agent/tools/externas.py`: serie diaria por lugar (SQL agregado), relleno de días sin ventas, join con calendario y clima, límite de 400 días, `avisos` y `fuentes`
- [x] 3.2 `impacto_variables`: índice sobre mediana móvil de 28 días, efecto por mediana controlando por día de la semana, `dias_con`, `dias_sin`, `confiable`, filtro opcional por temporada
- [x] 3.3 `contexto_proximos_dias`: pronóstico, calendario y venta de referencia de los últimos 8 días equivalentes, máximo 14 días
- [x] 3.4 Registrar las 3 herramientas en `agent/tools/registro.py` y verificar que `mcp_server/server.py` las exponga
- [x] 3.5 Tests de las herramientas con base simulada (`tests/fakes.py`): fin de semana largo del 21–23/11/2026, Oktoberfest solo en VGB, lugar sin coordenadas, fuente caída, rango excedido

## 4. Perfil, prompts y Claude Code

- [x] 4.1 Agregar las 3 herramientas a `config/perfiles/ventas.yaml` y verificar con `tests/test_profiles.py`
- [x] 4.2 Actualizar `prompts/ventas.md` y `CLAUDE.md`: cuándo usar cada herramienta, asociación vs. causa, mínimo de 8 días, citar `dias_con` y período en las estrategias
- [x] 4.3 Agregar `open-meteo` (`npx -y open-meteo-mcp-server@2.5.6`) a `.mcp.json` y a `enabledMcpjsonServers`
- [x] 4.4 Agregar a `evals/preguntas.yaml` dos preguntas: efecto de la lluvia en Villa Allende y demanda del próximo fin de semana largo en Carlos Paz

## 5. Verificación

- [x] 5.1 Correr `pytest` completo
- [x] 5.2 Prueba real desde Claude Code: `impacto_variables` para Carlos Paz (últimos 24 meses) y `contexto_proximos_dias` para todos los lugares; validar a mano 3 días contra Open-Meteo y el calendario oficial
- [ ] 5.3 Prueba en la app web local con el perfil de ventas
- [x] 5.4 Documentar en `README.md` las fuentes, el tráfico de red saliente y las variables de fase 2 (TomTom, PredictHQ, Fever, macro)
