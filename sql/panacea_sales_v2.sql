-- Estructura original de la tabla (solo para crear una base de pruebas)
CREATE TABLE IF NOT EXISTS public.panacea_sales_v2 (
	document_id int8 NULL, category_id int4 NULL, category varchar(50) NULL,
	ref_id int4 NULL, product_id int4 NULL, product varchar(100) NULL,
	lugar_venta_id int4 NULL, lugar_venta varchar(50) NULL,
	customer_id int4 NULL, customer varchar(50) NULL,
	operation_date date NULL, operation_hour int2 NULL, operation_year int2 NULL,
	operation_month int2 NULL, week_of_year varchar(10) NULL, week_of_month int2 NULL,
	day_of_week int2 NULL, day_of_week_text varchar(20) NULL,
	count float8 NULL, subtotal float8 NULL
);
CREATE INDEX IF NOT EXISTS panacea_sales_v2_operation_date_idx ON public.panacea_sales_v2 USING btree (operation_date);
CREATE INDEX IF NOT EXISTS panacea_sales_v2_operation_year_idx ON public.panacea_sales_v2 USING btree (operation_year, operation_month, product_id);
