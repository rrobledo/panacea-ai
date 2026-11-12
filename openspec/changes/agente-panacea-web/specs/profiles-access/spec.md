## ADDED Requirements

### Requirement: Perfiles definidos en YAML
El sistema SHALL cargar los perfiles desde `config/perfiles/*.yaml` y validarlos al iniciar. Cada perfil MUST definir `id`, `nombre`, `modelo`, `prompt`, `base_datos.credencial_env`, `base_datos.tablas` y `herramientas`, y MAY definir `esfuerzo`, `reglas` y `limites`. Agregar un perfil MUST NOT requerir cambios de código.

#### Scenario: Perfil inválido
- **WHEN** un YAML de perfil omite `base_datos.tablas` o lista una herramienta inexistente
- **THEN** el backend no arranca y registra un error que nombra el archivo y el campo

#### Scenario: Perfil nuevo
- **WHEN** se agrega `config/perfiles/compras.yaml` con su prompt y su variable de credencial
- **THEN** el perfil aparece disponible para los usuarios asignados sin modificar código

### Requirement: Autenticación y asignación de perfiles
El sistema SHALL exigir sesión iniciada (Auth.js) para toda ruta salvo la de login y SHALL asignar a cada usuario los perfiles listados para su email en `config/usuarios.yaml`. Un email que no figure MUST NOT acceder a la aplicación.

#### Scenario: Usuario no registrado
- **WHEN** inicia sesión un email que no está en `usuarios.yaml`
- **THEN** ve un mensaje de acceso denegado y no puede llamar a ninguna ruta `/api/*`

#### Scenario: Perfil no asignado
- **WHEN** un usuario con perfiles `[produccion]` envía un mensaje indicando el perfil `ventas`
- **THEN** el backend responde 403 y no invoca al modelo

### Requirement: Aplicación del perfil en cada pedido
En cada turno el backend SHALL armar el system prompt con el prompt del perfil y los diccionarios de sus tablas, SHALL enviar al modelo solo las herramientas listadas en el perfil y SHALL ejecutar toda consulta con la credencial indicada en `credencial_env`.

#### Scenario: Herramienta no listada
- **WHEN** el perfil `produccion` no lista `clientes_inactivos`
- **THEN** esa herramienta no se incluye en la definición enviada a Claude y una llamada a ella devuelve error

#### Scenario: Doble barrera de permisos
- **WHEN** un SQL pasa la validación de código pero toca una tabla sin `GRANT` para el rol del perfil
- **THEN** Postgres rechaza la consulta y la herramienta devuelve el error sin exponer la credencial

### Requirement: Reglas de negocio del perfil
Las herramientas de análisis de clientes SHALL aplicar automáticamente la exclusión de los IDs de clientes definidos en `reglas.excluir_clientes_en_analisis` del perfil, sumados a los que pida el agente. Los clientes genéricos de Panacea son las ventas de mostrador de cada sucursal (IDs 999 Carlos Paz, 0 Villa Allende, 888 Córdoba, 777 Villa General Belgrano), no un "Consumidor final".

#### Scenario: Mostrador excluido
- **WHEN** el perfil `ventas`, con `excluir_clientes_en_analisis: [999, 0, 888, 777]`, invoca `clientes_inactivos` sin `excluir_clientes`
- **THEN** el resultado no incluye ninguno de esos cuatro clientes

#### Scenario: Exclusión adicional
- **WHEN** el agente pide `excluir_clientes: [250]`
- **THEN** se excluyen el 250 y los cuatro clientes genéricos
