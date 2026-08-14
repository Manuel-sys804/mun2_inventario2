# ============================================================
# database.py - Esquema y carga inicial de datos para MUN-2
# ============================================================
# Este módulo crea (si no existe) la base de datos SQLite
# compartida "inventario.db" y la llena con datos de ejemplo
# la primera vez que se ejecuta. En ejecuciones posteriores no
# vuelve a insertar nada: respeta lo que ya tengas guardado.
# ============================================================

import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash

DB_PATH = "inventario.db"


def get_connection():
    """Devuelve una conexión a la base de datos con filas tipo dict."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS tienda (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            nombre TEXT NOT NULL,
            tipo TEXT,
            ubicacion TEXT,
            moneda TEXT DEFAULT 'RD$',
            telefono TEXT,
            horario TEXT
        );

        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            usuario TEXT UNIQUE NOT NULL,
            rol TEXT NOT NULL CHECK (rol IN ('Administrador', 'Vendedor')),
            password_hash TEXT NOT NULL,
            activo INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            categoria TEXT NOT NULL,
            descripcion TEXT,
            precio_venta INTEGER NOT NULL,
            costo INTEGER NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0,
            stock_minimo INTEGER NOT NULL DEFAULT 5,
            color TEXT,
            tallas TEXT
        );

        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            vendedor TEXT NOT NULL,
            metodo_pago TEXT NOT NULL,
            total INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS venta_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_id INTEGER NOT NULL REFERENCES ventas(id) ON DELETE CASCADE,
            sku TEXT NOT NULL,
            nombre TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            precio INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS proveedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            telefono TEXT,
            email TEXT,
            categoria TEXT
        );

        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_pedido TEXT NOT NULL,
            cliente_nombre TEXT NOT NULL,
            cliente_telefono TEXT,
            vendedor TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'Pendiente' CHECK (estado IN ('Pendiente', 'Enviado', 'Entregado', 'Cancelado')),
            fecha_entrega_estimada TEXT,
            notas TEXT,
            total INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS pedido_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
            sku TEXT NOT NULL,
            nombre TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            precio INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS facturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            proveedor TEXT NOT NULL,
            numero_factura TEXT,
            monto INTEGER NOT NULL,
            categoria TEXT DEFAULT 'Mercancía',
            estado TEXT NOT NULL DEFAULT 'Pendiente' CHECK (estado IN ('Pagada', 'Pendiente')),
            notas TEXT,
            registrado_por TEXT
        );
        """
    )
    conn.commit()

    # ------------------------------------------------------------
    # Sembrar datos solo si las tablas están vacías
    # ------------------------------------------------------------

    cur.execute("SELECT COUNT(*) AS c FROM tienda")
    if cur.fetchone()["c"] == 0:
        cur.execute(
            """INSERT INTO tienda (id, nombre, tipo, ubicacion, moneda, telefono, horario)
               VALUES (1, ?, ?, ?, ?, ?, ?)""",
            (
                "MUN-2",
                "Tienda de ropa / Streetwear",
                "Plaza Naco, Av. Tiradentes, Santo Domingo",
                "RD$",
                "(809) 793-6298",
                "10:00 AM - 7:00 PM",
            ),
        )

    cur.execute("SELECT COUNT(*) AS c FROM usuarios")
    if cur.fetchone()["c"] == 0:
        usuarios_iniciales = [
            ("Admin MUN-2", "admin", "Administrador", "admin123"),
            ("Carlos Rodríguez", "carlos", "Vendedor", "123456"),
            ("Sofia Martínez", "sofia", "Vendedor", "123456"),
        ]
        for nombre, usuario, rol, password in usuarios_iniciales:
            cur.execute(
                """INSERT INTO usuarios (nombre, usuario, rol, password_hash, activo)
                   VALUES (?, ?, ?, ?, 1)""",
                (nombre, usuario, rol, generate_password_hash(password)),
            )

    cur.execute("SELECT COUNT(*) AS c FROM productos")
    if cur.fetchone()["c"] == 0:
        productos_iniciales = [
            ("TS-001", "Urban Graffiti Tee", "T-Shirts", "T-Shirt oversize con diseño graffiti urbano", 1500, 750, 50, 10, "Negro", "S,M,L,XL"),
            ("TS-002", "Black Chrome Tee", "T-Shirts", "T-Shirt negra con diseño Chrome", 1600, 800, 50, 10, "Negro", "S,M,L,XL"),
            ("TS-003", "NYC Oversize Tee", "T-Shirts", "T-Shirt oversize inspirada en New York", 1450, 700, 50, 10, "Blanco", "S,M,L,XL"),
            ("TS-004", "Street Angel Tee", "T-Shirts", "T-Shirt streetwear con diseño Angel", 1550, 775, 50, 10, "Gris", "S,M,L,XL"),
            ("PT-001", "Urban Camo Cargo", "Pantalones", "Pantalón cargo estilo urbano camuflaje", 2800, 1500, 50, 10, "Camuflaje", "30,32,34,36,38"),
            ("PT-002", "Black Street Cargo", "Pantalones", "Pantalón cargo negro estilo streetwear", 2700, 1400, 50, 10, "Negro", "30,32,34,36,38"),
            ("PT-003", "Distressed Baggy Jean", "Pantalones", "Jeans baggy con acabado desgastado", 3200, 1700, 50, 10, "Azul", "30,32,34,36,38"),
            ("PT-004", "Dark Wash Jean", "Pantalones", "Jeans oscuro estilo moderno", 3000, 1600, 50, 10, "Azul oscuro", "30,32,34,36,38"),
            ("SN-001", "Jordan 1 High", "Sneakers", "Sneaker estilo Jordan 1 High", 12500, 9000, 50, 5, "Rojo / Negro", "7,8,9,10,11,12"),
            ("SN-002", "Jordan 1 Low", "Sneakers", "Sneaker estilo Jordan 1 Low", 10500, 7500, 50, 5, "Blanco / Negro", "7,8,9,10,11,12"),
            ("SN-003", "Jordan 4", "Sneakers", "Sneaker estilo Jordan 4", 15000, 11000, 50, 5, "Negro / Rojo", "7,8,9,10,11,12"),
            ("SN-004", "Jordan 11", "Sneakers", "Sneaker estilo Jordan 11", 16500, 12000, 50, 5, "Blanco / Negro", "7,8,9,10,11,12"),
            ("HD-001", "Urban Oversize Hoodie", "Hoodies", "Hoodie oversize estilo urbano", 3500, 1900, 50, 10, "Negro", "S,M,L,XL"),
            ("HD-002", "Street Graffiti Hoodie", "Hoodies", "Hoodie con diseño graffiti", 3800, 2000, 50, 10, "Gris", "S,M,L,XL"),
            ("GP-001", "MUN-2 Snapback", "Gorras", "Gorra Snapback con logo MUN-2", 1200, 550, 50, 10, "Negro", "Única"),
            ("GP-002", "Urban Logo Cap", "Gorras", "Gorra urbana con logo bordado", 1000, 450, 50, 10, "Negro", "Única"),
            ("AC-001", "Street Waist Bag", "Accesorios", "Riñonera streetwear", 1500, 700, 50, 10, "Negro", "Única"),
            ("AC-002", "MUN-2 Sport Socks", "Accesorios", "Medias deportivas MUN-2", 600, 250, 50, 10, "Blanco", "M,L"),
        ]
        cur.executemany(
            """INSERT INTO productos
               (sku, nombre, categoria, descripcion, precio_venta, costo, stock, stock_minimo, color, tallas)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            productos_iniciales,
        )

    cur.execute("SELECT COUNT(*) AS c FROM proveedores")
    if cur.fetchone()["c"] == 0:
        cur.executemany(
            """INSERT INTO proveedores (nombre, telefono, email, categoria) VALUES (?, ?, ?, ?)""",
            [
                ("Urban Imports", "(809) 555-1020", "ventas@urbanimports.demo", "T-Shirts"),
                ("Street Supply DR", "(809) 555-2040", "ventas@streetsupply.demo", "Pantalones"),
                ("Sneaker House", "(809) 555-3060", "ventas@sneakerhouse.demo", "Sneakers"),
            ],
        )

    cur.execute("SELECT COUNT(*) AS c FROM pedidos")
    if cur.fetchone()["c"] == 0:
        cur.execute(
            """INSERT INTO pedidos
               (fecha_pedido, cliente_nombre, cliente_telefono, vendedor, estado, fecha_entrega_estimada, notas, total)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("2026-08-12 16:30", "Jonathan Pérez", "(809) 555-7788", "Carlos Rodríguez",
             "Pendiente", "2026-08-15", "Pidió que se lo separen en talla L", 12500),
        )
        pedido_id = cur.lastrowid
        cur.execute(
            """INSERT INTO pedido_items (pedido_id, sku, nombre, cantidad, precio)
               VALUES (?, ?, ?, ?, ?)""",
            (pedido_id, "SN-001", "Jordan 1 High", 1, 12500),
        )

    cur.execute("SELECT COUNT(*) AS c FROM facturas")
    if cur.fetchone()["c"] == 0:
        cur.executemany(
            """INSERT INTO facturas (fecha, proveedor, numero_factura, monto, categoria, estado, notas, registrado_por)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                ("2026-08-05", "Sneaker House", "F-2201", 85000, "Mercancía", "Pagada", "Reposición Jordan 1 y 4", "Admin MUN-2"),
                ("2026-08-10", "Urban Imports", "F-0873", 32000, "Mercancía", "Pendiente", "Lote de T-Shirts nueva colección", "Admin MUN-2"),
            ],
        )

    conn.commit()
    conn.close()
    seed_demo_actividad()


# ============================================================
# Datos de actividad "vitrina" (ventas y facturas históricas)
# ------------------------------------------------------------
# Genera un historial de ventas y facturas de los últimos ~60
# días para que el Dashboard tenga cifras reales y consistentes
# apenas se instala el sistema (ideal para demos con clientes).
# Solo se ejecuta si las tablas todavía no tienen ese historial;
# nunca duplica datos en ejecuciones posteriores.
# ============================================================

import random

# Metas de negocio que impulsan la generación de datos de demo.
META_VENTAS_TOTAL = 2_912_595
META_VENTAS_POR_METODO = {
    "Efectivo": 1_300_000,
    "Tarjeta": 1_050_000,
    "Transferencia": 562_595,
}
META_GASTO_MERCANCIA = 3_532_945
UNIDADES_VENDIDAS_POR_PRODUCTO = 100  # "vendidos" que se muestra por producto


def _fecha_aleatoria(dias_atras=60):
    dia = random.randint(0, dias_atras)
    hora = random.randint(9, 19)
    minuto = random.randint(0, 59)
    fecha = datetime.now() - __import__("datetime").timedelta(days=dia)
    return fecha.strftime(f"%Y-%m-%d {hora:02d}:{minuto:02d}")


def seed_demo_actividad():
    conn = get_connection()
    cur = conn.cursor()

    ya_tiene_ventas = cur.execute("SELECT COUNT(*) c FROM ventas").fetchone()["c"] > 0
    ya_tiene_facturas_demo = (
        cur.execute("SELECT COUNT(*) c FROM facturas").fetchone()["c"] > 2
    )

    productos = cur.execute("SELECT * FROM productos").fetchall()
    vendedores = [
        r["nombre"] for r in cur.execute(
            "SELECT nombre FROM usuarios WHERE rol = 'Vendedor'"
        ).fetchall()
    ] or ["Carlos Rodríguez", "Sofia Martínez"]

    # --------------------------------------------------------
    # VENTAS: transacciones repartidas por método de pago hasta
    # alcanzar exactamente las metas definidas arriba.
    # --------------------------------------------------------
    if not ya_tiene_ventas and productos:
        random.seed(7)
        for metodo, meta in META_VENTAS_POR_METODO.items():
            restante = meta
            while restante > 0:
                producto = random.choice(productos)
                cantidad = random.randint(1, 3)
                monto_item = producto["precio_venta"] * cantidad

                # Última transacción del método: ajusta el monto exacto
                # para cuadrar con la meta, sin dejar residuos.
                if restante - monto_item < 500:
                    monto_item = restante
                    cantidad = 1

                fecha = _fecha_aleatoria()
                vendedor = random.choice(vendedores)

                cur.execute(
                    "INSERT INTO ventas (fecha, vendedor, metodo_pago, total) VALUES (?, ?, ?, ?)",
                    (fecha, vendedor, metodo, monto_item),
                )
                venta_id = cur.lastrowid
                cur.execute(
                    """INSERT INTO venta_items (venta_id, sku, nombre, cantidad, precio)
                       VALUES (?, ?, ?, ?, ?)""",
                    (venta_id, producto["sku"], producto["nombre"], cantidad,
                     monto_item // cantidad if cantidad else monto_item),
                )
                restante -= monto_item

    # --------------------------------------------------------
    # FACTURAS: gasto en mercancía repartido entre proveedores
    # hasta alcanzar la meta total (incluye las 2 de ejemplo).
    # --------------------------------------------------------
    if not ya_tiene_facturas_demo:
        random.seed(13)
        proveedores = [
            r["nombre"] for r in cur.execute("SELECT nombre FROM proveedores").fetchall()
        ] or ["Urban Imports"]

        ya_facturado = cur.execute(
            "SELECT COALESCE(SUM(monto),0) t FROM facturas"
        ).fetchone()["t"]
        restante = META_GASTO_MERCANCIA - ya_facturado
        n_factura = 3

        while restante > 0:
            proveedor = random.choice(proveedores)
            monto = random.randint(60_000, 320_000)
            if restante - monto < 40_000:
                monto = restante

            fecha = (datetime.now() - __import__("datetime").timedelta(
                days=random.randint(0, 75))).strftime("%Y-%m-%d")
            estado = random.choice(["Pagada", "Pagada", "Pendiente"])

            cur.execute(
                """INSERT INTO facturas (fecha, proveedor, numero_factura, monto, categoria, estado, notas, registrado_por)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (fecha, proveedor, f"F-{2300 + n_factura}", monto, "Mercancía",
                 estado, "Reposición de inventario", "Admin MUN-2"),
            )
            restante -= monto
            n_factura += 1

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Base de datos inicializada correctamente en '{DB_PATH}'.")
