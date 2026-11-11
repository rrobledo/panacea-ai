"""
Carga datos simulados en una base Postgres de PRUEBA con la misma estructura que panacea_sales_v2.
NO lo ejecutes contra producción: borra el contenido de la tabla.
Uso: DATABASE_URL=postgresql+psycopg2://usuario:clave@localhost:5432/pruebas python data/crear_demo_postgres.py
"""
import os, random
from datetime import date, timedelta
from pathlib import Path
from sqlalchemy import create_engine, text

url = os.environ["DATABASE_URL"]
if input(f"Esto BORRA public.panacea_sales_v2 en {url.split('@')[-1]}. Escribí 'si' para seguir: ") != "si":
    raise SystemExit("Cancelado.")

random.seed(7)
eng = create_engine(url)
dias = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
categorias = {1: "Medicamentos", 2: "Dermocosmética", 3: "Perfumería", 4: "Higiene", 5: "Bebés"}
productos = [  # (product_id, category_id, nombre, precio)
    (101, 1, "Ibuprofeno 400 x20", 3200), (102, 1, "Paracetamol 500 x16", 2100), (103, 1, "Antigripal x10", 4500),
    (104, 1, "Vitamina C x30", 6800), (201, 2, "Protector solar FPS50", 18500), (202, 2, "Crema hidratante", 14200),
    (203, 2, "Serum facial", 22900), (301, 3, "Perfume 100ml", 48000), (302, 3, "Desodorante", 3900),
    (401, 4, "Shampoo 400ml", 5600), (402, 4, "Pasta dental", 2800), (403, 4, "Jabón líquido", 3100),
    (501, 5, "Pañales x50", 21000), (502, 5, "Toallitas húmedas", 4300),
]
pesos = [9, 10, 6, 4, 3, 3, 2, 1, 6, 6, 8, 5, 3, 4]
lugares = [(1, "Sucursal Centro"), (2, "Sucursal Norte"), (3, "Tienda Online"), (4, "Sucursal Sur")]
clientes = [(0, "Consumidor final")] + [(i, f"Cliente {i:04d}") for i in range(1, 801)]
estacion = {1: .85, 2: .8, 3: .95, 4: 1, 5: 1.15, 6: 1.25, 7: 1.3, 8: 1.1, 9: 1, 10: 1, 11: 1.05, 12: 1.35}

filas, doc = [], 500000
inicio = date(2024, 1, 1)
for d in range((date(2026, 9, 30) - inicio).days + 1):
    f = inicio + timedelta(days=d)
    for _ in range(int(random.randint(25, 45) * estacion[f.month] * (1 + d / 2000))):
        doc += 1
        lid, lugar = random.choices(lugares, weights=[5, 3, 2, 2])[0]
        cid, cli = clientes[0] if random.random() < .45 else random.choice(clientes[1:])
        hora = random.choices(range(8, 22), weights=[2, 4, 6, 7, 6, 4, 4, 5, 6, 7, 6, 4, 2, 1])[0]
        dow = (f.weekday() + 1) % 7  # 0 = domingo
        for pid, cat, nom, precio in random.sample(random.choices(productos, weights=pesos, k=6), random.randint(1, 4)):
            cant = float(random.choice([1, 1, 1, 2, 2, 3]))
            filas.append(dict(document_id=doc, category_id=cat, category=categorias[cat], ref_id=pid * 10,
                product_id=pid, product=nom, lugar_venta_id=lid, lugar_venta=lugar, customer_id=cid, customer=cli,
                operation_date=f, operation_hour=hora, operation_year=f.year, operation_month=f.month,
                week_of_year=f"{f.isocalendar()[0]}-{f.isocalendar()[1]:02d}", week_of_month=(f.day - 1) // 7 + 1,
                day_of_week=dow, day_of_week_text=dias[dow], count=cant,
                subtotal=round(precio * cant * random.choice([1, 1, 1, .9, .85]), 2)))

cols = ", ".join(filas[0]); vals = ", ".join(f":{c}" for c in filas[0])
with eng.begin() as con:
    con.execute(text(Path(__file__).parent.parent.joinpath("sql/panacea_sales_v2.sql").read_text()))
    con.execute(text("TRUNCATE public.panacea_sales_v2"))
    con.execute(text(f"INSERT INTO public.panacea_sales_v2 ({cols}) VALUES ({vals})"), filas)
    con.execute(text("ANALYZE public.panacea_sales_v2"))
print(f"Listo: {len(filas)} líneas de venta en {doc - 500000} tickets.")
