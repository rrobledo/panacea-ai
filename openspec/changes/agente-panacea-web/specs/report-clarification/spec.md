## ADDED Requirements

### Requirement: Herramienta solicitar_aclaraciones
El sistema SHALL ofrecer la herramienta `solicitar_aclaraciones` con esquema estricto que recibe un `brief` (título, objetivo, período, secciones, métricas, audiencia) y una lista de hasta 6 `preguntas`, cada una con `id`, `texto`, `tipo` (`opcion`, `multiple`, `texto`, `fecha`), `opciones` y una opción `recomendada`.

#### Scenario: Sin preguntas
- **WHEN** el agente llama a la herramienta con `preguntas` vacía y un brief completo
- **THEN** el usuario igual ve el brief y debe aprobarlo antes de la generación

### Requirement: Pausa del turno en aclaraciones
Cuando el modelo llame a `solicitar_aclaraciones`, el backend SHALL cortar el loop, guardar el `tool_use` pendiente, emitir el evento `aclaraciones` y cerrar el turno. La conversación SHALL quedar en estado de espera hasta que llegue `POST /api/clarify`.

#### Scenario: Tarjeta de preguntas
- **WHEN** llega el evento `aclaraciones`
- **THEN** el chat muestra una tarjeta con las preguntas, la opción recomendada preseleccionada, el resumen "Voy a generar" y los botones "Aprobar y generar" y "Ajustar"

#### Scenario: Mensaje nuevo con aclaración pendiente
- **WHEN** el usuario escribe un mensaje libre mientras hay una aclaración pendiente
- **THEN** el mensaje se envía como respuesta de ajuste del `tool_use` pendiente, sin dejarlo huérfano

### Requirement: Aprobar o ajustar el brief
`POST /api/clarify` SHALL recibir las respuestas y la decisión. Si el usuario aprueba, el backend SHALL guardar el brief aprobado con un `brief_id` ligado a la conversación y devolverlo al modelo dentro del `tool_result`. Si el usuario ajusta, el `tool_result` SHALL contener los cambios pedidos y ningún `brief_id`.

#### Scenario: Aprobación
- **WHEN** el usuario responde y pulsa "Aprobar y generar"
- **THEN** el modelo recibe las respuestas y un `brief_id` válido y el turno continúa

#### Scenario: Ajuste
- **WHEN** el usuario pulsa "Ajustar" con un comentario
- **THEN** el modelo recibe el comentario sin `brief_id` y debe volver a llamar a `solicitar_aclaraciones`

### Requirement: Generación bloqueada sin brief aprobado
`generar_artifact` SHALL rechazar la llamada con un error explicativo si el `brief_id` no existe, no está aprobado o pertenece a otra conversación.

#### Scenario: Intento sin brief
- **WHEN** el modelo llama a `generar_artifact` sin haber pasado por aclaraciones
- **THEN** la herramienta devuelve error indicando que primero debe llamar a `solicitar_aclaraciones` y no se crea ningún artifact

#### Scenario: Brief de otra conversación
- **WHEN** el modelo usa un `brief_id` aprobado en otra conversación
- **THEN** la herramienta devuelve error y no se crea ningún artifact
