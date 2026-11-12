## ADDED Requirements

### Requirement: Auditoría de SQL
El sistema SHALL registrar en `app.auditoria_sql` cada consulta ejecutada o rechazada con usuario, perfil, conversación, herramienta, SQL, parámetros, duración, filas devueltas y error si lo hubo.

#### Scenario: Consulta rechazada
- **WHEN** `sql_guard` rechaza una consulta
- **THEN** queda un registro con el SQL, el motivo del rechazo y el usuario

### Requirement: Auditoría de tokens
El sistema SHALL registrar por cada llamada al modelo los tokens de entrada, salida, lectura y escritura de caché, el modelo y el costo estimado, asociados a usuario, perfil y conversación.

#### Scenario: Turno con varias llamadas
- **WHEN** un turno hace cuatro llamadas a la Messages API
- **THEN** quedan cuatro registros de uso y el turno muestra el total

### Requirement: Presupuesto por turno
El backend SHALL cortar el loop cuando un turno supere `presupuesto_tokens_por_turno` del perfil, pidiendo una respuesta final sin herramientas e informando al usuario. Cuentan los tokens nuevos del turno (entrada sin caché, escritura de caché y salida); las lecturas de caché no cuentan, porque cada vuelta relee el historial completo a 1/20 del precio de entrada.

#### Scenario: Presupuesto superado
- **WHEN** el acumulado de tokens nuevos del turno supera 200 000 en el perfil `ventas` y el modelo pide otra herramienta
- **THEN** no se ejecutan más herramientas y el usuario ve un aviso de límite alcanzado

### Requirement: Tope mensual por usuario
El sistema SHALL rechazar nuevos turnos de un usuario que superó su tope mensual de costo configurado, con un mensaje claro, hasta el mes siguiente o hasta que un administrador lo amplíe.

#### Scenario: Tope alcanzado
- **WHEN** un usuario con tope de US$50 ya consumió US$50 en el mes
- **THEN** `POST /api/chat` responde 429 con el motivo y no invoca al modelo

### Requirement: Tablero de uso
Los administradores SHALL ver un tablero con consumo de tokens, costo estimado y cantidad de consultas por usuario y por perfil en el mes en curso y los anteriores.

#### Scenario: Usuario no administrador
- **WHEN** un usuario sin `admin: true` abre el tablero de uso
- **THEN** recibe 403
