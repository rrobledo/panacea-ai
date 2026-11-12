## ADDED Requirements

### Requirement: Chat con streaming
El sistema SHALL ofrecer un chat web donde el usuario elige un perfil, escribe un mensaje y recibe la respuesta del agente por SSE desde `POST /api/chat`, con eventos para texto parcial, inicio y fin de cada herramienta (nombre, argumentos resumidos y duración), aclaraciones, artifact creado, error y fin de turno.

#### Scenario: Pasos visibles
- **WHEN** el agente llama a `perfil_datos` y luego a `resumen_ventas`
- **THEN** el chat muestra cada paso con su nombre y duración mientras ocurre, antes del texto final

#### Scenario: Error de herramienta
- **WHEN** una herramienta devuelve error
- **THEN** el error se envía al modelo como `tool_result` con `is_error` y el turno continúa

### Requirement: Loop de agente propio
El backend SHALL implementar el loop con el SDK `anthropic` y la Messages API en streaming: enviar mensajes y herramientas del perfil, ejecutar cada `tool_use`, devolver los `tool_result` y repetir hasta `end_turn`, hasta una pausa por aclaraciones o hasta alcanzar `max_herramientas_por_turno`.

#### Scenario: Tope de herramientas
- **WHEN** un turno alcanza `max_herramientas_por_turno`
- **THEN** el backend deja de ejecutar herramientas, pide al modelo una respuesta final sin herramientas y avisa al usuario que se alcanzó el límite

### Requirement: Historial solo por agregado
El historial de mensajes de una conversación SHALL crecer únicamente agregando al final; el backend MUST NOT reescribir ni reordenar mensajes previos, incluidos los bloques de razonamiento devueltos por el modelo.

#### Scenario: Reanudar tras aclaraciones
- **WHEN** el usuario responde una tarjeta de aclaraciones
- **THEN** las respuestas se agregan como `tool_result` del `tool_use` pendiente y el resto del historial se envía sin cambios

### Requirement: Un turno a la vez por conversación
El backend SHALL rechazar con 409 un pedido sobre una conversación que tiene un turno en curso. Un turno en curso sin avance durante más de 5 minutos SHALL considerarse cortado y poder retomarse.

#### Scenario: Doble envío
- **WHEN** el usuario envía un mensaje mientras el agente todavía responde el anterior en la misma conversación
- **THEN** el segundo pedido recibe 409 y el historial no se modifica

#### Scenario: Turno abandonado
- **WHEN** un turno quedó en curso por un corte y pasaron más de 5 minutos sin avance
- **THEN** un nuevo pedido puede tomar el turno y retomarlo

### Requirement: Conversaciones persistidas y reanudables
Cada conversación SHALL guardarse en el esquema `app` con su perfil, autor y mensajes, y el estado del loop SHALL guardarse después de cada herramienta, de modo que una función interrumpida pueda retomarse sin repetir herramientas ya ejecutadas.

#### Scenario: Volver a una conversación
- **WHEN** el usuario abre `/chat/{id}` de una conversación anterior
- **THEN** ve todos los mensajes y pasos previos y puede continuar escribiendo

#### Scenario: Función cortada
- **WHEN** la función de Vercel se corta en medio de un turno después de ejecutar dos herramientas
- **THEN** al reintentar el turno se reutilizan los dos resultados guardados y el loop continúa desde ahí

#### Scenario: Conversación ajena
- **WHEN** un usuario pide `/chat/{id}` de una conversación de otro usuario que no es administrador
- **THEN** recibe 404
