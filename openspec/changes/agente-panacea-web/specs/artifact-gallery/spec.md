## ADDED Requirements

### Requirement: Galería de reportes
La ruta `/artifacts` SHALL listar los artifacts visibles para el usuario con título, tipo, perfil, autor, versión actual y fecha, ordenados por fecha de actualización descendente, con vista previa.

#### Scenario: Listado
- **WHEN** un usuario con perfil `ventas` abre `/artifacts`
- **THEN** ve los artifacts del perfil `ventas`, el más reciente primero

### Requirement: Búsqueda y filtros
La galería SHALL permitir buscar por título y filtrar por perfil, autor, tipo y rango de fechas, combinando filtros.

#### Scenario: Filtros combinados
- **WHEN** el usuario filtra por tipo `reporte` y fechas del 01/10/2026 al 31/10/2026
- **THEN** solo ve reportes actualizados en ese rango

### Requirement: Visibilidad por perfil
Un usuario SHALL ver los artifacts de los perfiles que tiene asignados; un administrador SHALL ver todos. Ningún usuario MUST ver artifacts de perfiles que no tiene.

#### Scenario: Perfil ajeno
- **WHEN** un usuario con solo `produccion` pide `/artifacts/{id}` de un reporte de `ventas`
- **THEN** recibe 404

#### Scenario: Administrador
- **WHEN** un administrador abre la galería
- **THEN** ve artifacts de todos los perfiles y puede filtrar por cualquiera

### Requirement: Reportes fijados
Un usuario SHALL poder fijar un artifact para su perfil; los fijados SHALL aparecer primero en la galería y en el panel "Reportes recientes" del chat.

#### Scenario: Fijar
- **WHEN** un usuario fija "Estrategia comercial 2026"
- **THEN** aparece arriba en la galería para todos los usuarios del perfil `ventas`

### Requirement: Recientes en el chat
El chat SHALL mostrar un panel lateral con los reportes recientes del perfil seleccionado y un enlace a la galería.

#### Scenario: Cambio de perfil
- **WHEN** el usuario cambia el selector de perfil de `ventas` a `produccion`
- **THEN** el panel muestra los reportes recientes de `produccion`
