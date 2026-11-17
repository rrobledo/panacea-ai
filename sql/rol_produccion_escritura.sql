-- Rol de escritura del perfil produccion: solo puede cambiar el plan diario de la programación.
-- Lo usa únicamente la herramienta cambiar_programacion, después de que el usuario confirma en el chat.
-- Ejecutar como administrador. Cambiá la contraseña y reemplazá "panacea" por el nombre de tu base.
-- Después cargá DB_URL_PRODUCCION_ESCRITURA (en Vercel y en .env.local) con este usuario y el host -pooler.
--
-- No puede insertar ni borrar filas, ni tocar prod, fecha o producto: solo UPDATE de la columna plan.
-- Cada cambio queda en app.auditoria_sql con el usuario, la conversación y los valores anterior y nuevo.

CREATE ROLE agente_produccion_rw LOGIN PASSWORD 'CAMBIAR_ESTA_CLAVE';
GRANT CONNECT ON DATABASE panacea TO agente_produccion_rw;
GRANT USAGE ON SCHEMA public TO agente_produccion_rw;
GRANT SELECT (id, producto_id, fecha, plan) ON public.costos_programacion TO agente_produccion_rw;
GRANT UPDATE (plan) ON public.costos_programacion TO agente_produccion_rw;
ALTER ROLE agente_produccion_rw SET statement_timeout = '30s';
