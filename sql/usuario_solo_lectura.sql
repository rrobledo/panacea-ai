-- Ejecutar como administrador en la base real. Cambiá la contraseña.
CREATE ROLE agente_ventas LOGIN PASSWORD 'CAMBIAR_ESTA_CLAVE';
GRANT CONNECT ON DATABASE panacea TO agente_ventas;   -- reemplazá "panacea" por el nombre de tu base
GRANT USAGE ON SCHEMA public TO agente_ventas;
GRANT SELECT ON public.panacea_sales_v2 TO agente_ventas;
ALTER ROLE agente_ventas SET default_transaction_read_only = on;
ALTER ROLE agente_ventas SET statement_timeout = '60s';

-- Opcional, acelera las herramientas de clientes y de canasta:
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS panacea_sales_v2_customer_idx ON public.panacea_sales_v2 (customer_id, operation_date);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS panacea_sales_v2_document_idx ON public.panacea_sales_v2 (document_id);
