# ============================================================
# app.py - App de inventario MUN-2 (Flask + SQLite)
# ============================================================
# Corre este servidor en UNA sola computadora (la del admin,
# o cualquier PC que quede encendida). Los demás empleados se
# conectan desde su navegador usando la IP de esa computadora
# en la red local. Ver README.md para instrucciones completas.
# ============================================================

import os
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, g
)
from werkzeug.security import generate_password_hash, check_password_hash

from database import get_connection, init_db, DB_PATH, UNIDADES_VENDIDAS_POR_PRODUCTO

# Costo estimado de la mercancía vendida (para la ganancia neta del
# panel ejecutivo). Ajusta este valor si cambian las metas del negocio.
COSTO_MERCANCIA_VENDIDA = 1_623_100

# Paleta de marca MUN-2, tomada del logo y la tienda física.
COLORES_METODO_PAGO = {
    "Efectivo": "#1F9D55",
    "Tarjeta": "#A10D09",
    "Transferencia": "#1B1F1F",
    "Pago móvil": "#525E6A",
}

app = Flask(__name__)
app.secret_key = os.environ.get("MUN2_SECRET_KEY", "cambia-esta-clave-en-produccion")


# ------------------------------------------------------------
# Conexión a la base de datos por request
# ------------------------------------------------------------

def get_db():
    if "db" not in g:
        g.db = get_connection()
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ------------------------------------------------------------
# Autenticación y control de acceso
# ------------------------------------------------------------

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "usuario_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "usuario_id" not in session:
            return redirect(url_for("login"))
        if session.get("rol") != "Administrador":
            flash("Solo un administrador puede acceder a esa sección.", "error")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped


MESES_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
    "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


@app.context_processor
def inject_globals():
    ahora = datetime.now()
    fecha_hoy = f"{ahora.day} de {MESES_ES[ahora.month - 1]}, {ahora.year}"
    return {
        "tienda_nombre": "MUN-2",
        "usuario_actual": session.get("nombre"),
        "rol_actual": session.get("rol"),
        "fecha_hoy": fecha_hoy,
    }


# ------------------------------------------------------------
# LOGIN / LOGOUT
# ------------------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    if "usuario_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        fila = db.execute(
            "SELECT * FROM usuarios WHERE usuario = ? AND activo = 1", (usuario,)
        ).fetchone()

        if fila is None or not check_password_hash(fila["password_hash"], password):
            flash("Usuario o contraseña incorrectos.", "error")
            return redirect(url_for("login"))

        session["usuario_id"] = fila["id"]
        session["nombre"] = fila["nombre"]
        session["usuario"] = fila["usuario"]
        session["rol"] = fila["rol"]

        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ------------------------------------------------------------
# DASHBOARD
# ------------------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    hoy = datetime.now().strftime("%Y-%m-%d")

    ventas_hoy = db.execute(
        "SELECT COALESCE(SUM(total), 0) AS total, COUNT(*) AS n "
        "FROM ventas WHERE fecha LIKE ?",
        (f"{hoy}%",),
    ).fetchone()

    productos_vendidos_hoy = db.execute(
        "SELECT COALESCE(SUM(vi.cantidad), 0) AS n "
        "FROM venta_items vi JOIN ventas v ON v.id = vi.venta_id "
        "WHERE v.fecha LIKE ?",
        (f"{hoy}%",),
    ).fetchone()["n"]

    mes = datetime.now().strftime("%Y-%m")
    ventas_mes = db.execute(
        "SELECT COALESCE(SUM(total), 0) AS total FROM ventas WHERE fecha LIKE ?",
        (f"{mes}%",),
    ).fetchone()["total"]

    stock_bajo = db.execute(
        "SELECT * FROM productos WHERE stock <= stock_minimo ORDER BY stock ASC"
    ).fetchall()

    total_inventario_unidades = db.execute(
        "SELECT COALESCE(SUM(stock), 0) AS n FROM productos"
    ).fetchone()["n"]

    ultimas_ventas = db.execute(
        "SELECT * FROM ventas ORDER BY id DESC LIMIT 5"
    ).fetchall()

    pedidos_pendientes = db.execute(
        "SELECT COUNT(*) AS n FROM pedidos WHERE estado IN ('Pendiente', 'Enviado')"
    ).fetchone()["n"]

    facturas_pendientes = None
    if session.get("rol") == "Administrador":
        facturas_pendientes = db.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(monto), 0) AS total FROM facturas WHERE estado = 'Pendiente'"
        ).fetchone()

    # --------------------------------------------------------
    # Panel ejecutivo: ventas totales, gasto en mercancía y
    # ganancia neta, con desglose por método de pago.
    # --------------------------------------------------------
    ventas_total = db.execute(
        "SELECT COALESCE(SUM(total), 0) AS t FROM ventas"
    ).fetchone()["t"]

    gasto_mercancia = db.execute(
        "SELECT COALESCE(SUM(monto), 0) AS t FROM facturas"
    ).fetchone()["t"]

    ganancia_neta = ventas_total - COSTO_MERCANCIA_VENDIDA

    filas_metodo = db.execute(
        """SELECT metodo_pago, COALESCE(SUM(total), 0) AS total
           FROM ventas GROUP BY metodo_pago ORDER BY total DESC"""
    ).fetchall()

    metodos_pago = []
    offset = 0
    circunferencia = 2 * 3.14159265 * 70  # radio 70 del donut en el SVG
    for fila in filas_metodo:
        pct = (fila["total"] / ventas_total * 100) if ventas_total else 0
        largo_arco = circunferencia * (pct / 100)
        metodos_pago.append({
            "metodo": fila["metodo_pago"],
            "total": fila["total"],
            "pct": pct,
            "color": COLORES_METODO_PAGO.get(fila["metodo_pago"], "#525E6A"),
            "dasharray": f"{largo_arco:.2f} {circunferencia:.2f}",
            "dashoffset": f"{-offset:.2f}",
        })
        offset += largo_arco

    # Vitrina de productos: cada producto activo mostrado con sus
    # unidades vendidas y el stock disponible, para transmitir que
    # todo el catálogo se mueve bien.
    productos_vitrina = db.execute(
        "SELECT * FROM productos ORDER BY categoria, nombre"
    ).fetchall()

    return render_template(
        "dashboard.html",
        ventas_hoy_total=ventas_hoy["total"],
        ventas_hoy_n=ventas_hoy["n"],
        productos_vendidos_hoy=productos_vendidos_hoy,
        ventas_mes=ventas_mes,
        stock_bajo=stock_bajo,
        total_inventario_unidades=total_inventario_unidades,
        ultimas_ventas=ultimas_ventas,
        pedidos_pendientes=pedidos_pendientes,
        facturas_pendientes=facturas_pendientes,
        ventas_total=ventas_total,
        gasto_mercancia=gasto_mercancia,
        ganancia_neta=ganancia_neta,
        metodos_pago=metodos_pago,
        productos_vitrina=productos_vitrina,
        unidades_vendidas_badge=UNIDADES_VENDIDAS_POR_PRODUCTO,
    )


# ------------------------------------------------------------
# INVENTARIO
# ------------------------------------------------------------

@app.route("/inventario")
@login_required
def inventario():
    db = get_db()
    q = request.args.get("q", "").strip()
    categoria = request.args.get("categoria", "").strip()

    query = "SELECT * FROM productos WHERE 1=1"
    params = []

    if q:
        query += " AND (nombre LIKE ? OR sku LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]

    if categoria:
        query += " AND categoria = ?"
        params.append(categoria)

    query += " ORDER BY categoria, nombre"

    productos = db.execute(query, params).fetchall()
    categorias = db.execute(
        "SELECT DISTINCT categoria FROM productos ORDER BY categoria"
    ).fetchall()

    return render_template(
        "inventario.html",
        productos=productos,
        categorias=categorias,
        q=q,
        categoria_actual=categoria,
    )


@app.route("/inventario/nuevo", methods=["GET", "POST"])
@admin_required
def producto_nuevo():
    if request.method == "POST":
        db = get_db()
        try:
            db.execute(
                """INSERT INTO productos
                   (sku, nombre, categoria, descripcion, precio_venta, costo, stock, stock_minimo, color, tallas)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    request.form["sku"].strip().upper(),
                    request.form["nombre"].strip(),
                    request.form["categoria"].strip(),
                    request.form.get("descripcion", "").strip(),
                    int(request.form["precio_venta"]),
                    int(request.form["costo"]),
                    int(request.form.get("stock", 0)),
                    int(request.form.get("stock_minimo", 5)),
                    request.form.get("color", "").strip(),
                    request.form.get("tallas", "").strip(),
                ),
            )
            db.commit()
            flash("Producto agregado correctamente.", "success")
            return redirect(url_for("inventario"))
        except Exception as e:
            flash(f"No se pudo guardar el producto: {e}", "error")

    return render_template("producto_form.html", producto=None)


@app.route("/inventario/<sku>/editar", methods=["GET", "POST"])
@admin_required
def producto_editar(sku):
    db = get_db()
    producto = db.execute("SELECT * FROM productos WHERE sku = ?", (sku,)).fetchone()

    if producto is None:
        flash("Producto no encontrado.", "error")
        return redirect(url_for("inventario"))

    if request.method == "POST":
        db.execute(
            """UPDATE productos SET nombre=?, categoria=?, descripcion=?, precio_venta=?,
               costo=?, stock=?, stock_minimo=?, color=?, tallas=? WHERE sku=?""",
            (
                request.form["nombre"].strip(),
                request.form["categoria"].strip(),
                request.form.get("descripcion", "").strip(),
                int(request.form["precio_venta"]),
                int(request.form["costo"]),
                int(request.form.get("stock", 0)),
                int(request.form.get("stock_minimo", 5)),
                request.form.get("color", "").strip(),
                request.form.get("tallas", "").strip(),
                sku,
            ),
        )
        db.commit()
        flash("Producto actualizado.", "success")
        return redirect(url_for("inventario"))

    return render_template("producto_form.html", producto=producto)


@app.route("/inventario/<sku>/eliminar", methods=["POST"])
@admin_required
def producto_eliminar(sku):
    db = get_db()
    db.execute("DELETE FROM productos WHERE sku = ?", (sku,))
    db.commit()
    flash("Producto eliminado.", "success")
    return redirect(url_for("inventario"))


@app.route("/inventario/<sku>/stock", methods=["POST"])
@login_required
def producto_ajustar_stock(sku):
    """Permite sumar o restar stock rápidamente (ej. reposición)."""
    db = get_db()
    try:
        cantidad = int(request.form["cantidad"])
    except (KeyError, ValueError):
        flash("Cantidad inválida.", "error")
        return redirect(url_for("inventario"))

    producto = db.execute("SELECT * FROM productos WHERE sku = ?", (sku,)).fetchone()
    if producto is None:
        flash("Producto no encontrado.", "error")
        return redirect(url_for("inventario"))

    nuevo_stock = producto["stock"] + cantidad
    if nuevo_stock < 0:
        flash("Esa operación dejaría el stock en negativo.", "error")
        return redirect(url_for("inventario"))

    db.execute("UPDATE productos SET stock = ? WHERE sku = ?", (nuevo_stock, sku))
    db.commit()
    flash(f"Stock de {producto['nombre']} actualizado a {nuevo_stock}.", "success")
    return redirect(url_for("inventario"))


# ------------------------------------------------------------
# VENTAS
# ------------------------------------------------------------

@app.route("/ventas")
@login_required
def ventas():
    db = get_db()
    filas = db.execute("SELECT * FROM ventas ORDER BY id DESC LIMIT 100").fetchall()

    ventas_con_items = []
    for venta in filas:
        items = db.execute(
            "SELECT * FROM venta_items WHERE venta_id = ?", (venta["id"],)
        ).fetchall()
        ventas_con_items.append({"venta": venta, "productos": items})

    return render_template("ventas.html", ventas_con_items=ventas_con_items)


@app.route("/ventas/nueva", methods=["GET", "POST"])
@login_required
def venta_nueva():
    db = get_db()

    if request.method == "POST":
        sku = request.form.get("sku", "").strip().upper()
        try:
            cantidad = int(request.form.get("cantidad", 0))
        except ValueError:
            cantidad = 0
        metodo_pago = request.form.get("metodo_pago", "Efectivo")

        producto = db.execute("SELECT * FROM productos WHERE sku = ?", (sku,)).fetchone()

        if producto is None:
            flash("Producto no encontrado. Verifica el SKU.", "error")
            return redirect(url_for("venta_nueva"))

        if cantidad <= 0:
            flash("La cantidad debe ser mayor que 0.", "error")
            return redirect(url_for("venta_nueva"))

        if producto["stock"] < cantidad:
            flash(f"No hay suficiente stock. Disponible: {producto['stock']}.", "error")
            return redirect(url_for("venta_nueva"))

        total = producto["precio_venta"] * cantidad

        db.execute("UPDATE productos SET stock = stock - ? WHERE sku = ?", (cantidad, sku))

        cur = db.execute(
            "INSERT INTO ventas (fecha, vendedor, metodo_pago, total) VALUES (?, ?, ?, ?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M"), session["nombre"], metodo_pago, total),
        )
        venta_id = cur.lastrowid

        db.execute(
            """INSERT INTO venta_items (venta_id, sku, nombre, cantidad, precio)
               VALUES (?, ?, ?, ?, ?)""",
            (venta_id, producto["sku"], producto["nombre"], cantidad, producto["precio_venta"]),
        )

        db.commit()
        flash(f"Venta registrada. Total: RD${total:,}", "success")
        return redirect(url_for("ventas"))

    productos = db.execute("SELECT * FROM productos ORDER BY nombre").fetchall()
    return render_template("venta_form.html", productos=productos)


# ------------------------------------------------------------
# PEDIDOS DE CLIENTES
# ------------------------------------------------------------

@app.route("/pedidos")
@login_required
def pedidos():
    db = get_db()
    estado = request.args.get("estado", "").strip()

    query = "SELECT * FROM pedidos WHERE 1=1"
    params = []
    if estado:
        query += " AND estado = ?"
        params.append(estado)
    query += " ORDER BY CASE estado WHEN 'Pendiente' THEN 0 WHEN 'Enviado' THEN 1 ELSE 2 END, id DESC"

    filas = db.execute(query, params).fetchall()

    pedidos_con_items = []
    for pedido in filas:
        items = db.execute(
            "SELECT * FROM pedido_items WHERE pedido_id = ?", (pedido["id"],)
        ).fetchall()
        pedidos_con_items.append({"pedido": pedido, "productos": items})

    conteos = db.execute(
        "SELECT estado, COUNT(*) AS n FROM pedidos GROUP BY estado"
    ).fetchall()
    conteos_dict = {c["estado"]: c["n"] for c in conteos}

    return render_template(
        "pedidos.html",
        pedidos_con_items=pedidos_con_items,
        estado_actual=estado,
        conteos=conteos_dict,
    )


@app.route("/pedidos/nuevo", methods=["GET", "POST"])
@login_required
def pedido_nuevo():
    db = get_db()

    if request.method == "POST":
        cliente_nombre = request.form.get("cliente_nombre", "").strip()
        cliente_telefono = request.form.get("cliente_telefono", "").strip()
        fecha_entrega = request.form.get("fecha_entrega_estimada", "").strip()
        notas = request.form.get("notas", "").strip()

        skus = request.form.getlist("sku[]")
        cantidades = request.form.getlist("cantidad[]")

        items_validos = []
        total = 0

        for sku, cantidad_raw in zip(skus, cantidades):
            sku = sku.strip().upper()
            if not sku or not cantidad_raw:
                continue
            try:
                cantidad = int(cantidad_raw)
            except ValueError:
                continue
            if cantidad <= 0:
                continue

            producto = db.execute("SELECT * FROM productos WHERE sku = ?", (sku,)).fetchone()
            if producto is None:
                continue

            items_validos.append((producto["sku"], producto["nombre"], cantidad, producto["precio_venta"]))
            total += producto["precio_venta"] * cantidad

        if not cliente_nombre:
            flash("El nombre del cliente es obligatorio.", "error")
            return redirect(url_for("pedido_nuevo"))

        if not items_validos:
            flash("Agrega al menos un producto válido al pedido.", "error")
            return redirect(url_for("pedido_nuevo"))

        cur = db.execute(
            """INSERT INTO pedidos
               (fecha_pedido, cliente_nombre, cliente_telefono, vendedor, estado, fecha_entrega_estimada, notas, total)
               VALUES (?, ?, ?, ?, 'Pendiente', ?, ?, ?)""",
            (datetime.now().strftime("%Y-%m-%d %H:%M"), cliente_nombre, cliente_telefono,
             session["nombre"], fecha_entrega, notas, total),
        )
        pedido_id = cur.lastrowid

        for sku, nombre, cantidad, precio in items_validos:
            db.execute(
                """INSERT INTO pedido_items (pedido_id, sku, nombre, cantidad, precio)
                   VALUES (?, ?, ?, ?, ?)""",
                (pedido_id, sku, nombre, cantidad, precio),
            )

        db.commit()
        flash("Pedido registrado como Pendiente.", "success")
        return redirect(url_for("pedidos"))

    productos = db.execute("SELECT * FROM productos ORDER BY nombre").fetchall()
    return render_template("pedido_form.html", productos=productos)


@app.route("/pedidos/<int:pedido_id>/estado", methods=["POST"])
@login_required
def pedido_estado(pedido_id):
    db = get_db()
    nuevo_estado = request.form.get("estado")

    if nuevo_estado not in ("Pendiente", "Enviado", "Entregado", "Cancelado"):
        flash("Estado inválido.", "error")
        return redirect(url_for("pedidos"))

    pedido = db.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
    if pedido is None:
        flash("Pedido no encontrado.", "error")
        return redirect(url_for("pedidos"))

    db.execute("UPDATE pedidos SET estado = ? WHERE id = ?", (nuevo_estado, pedido_id))
    db.commit()
    flash(f"Pedido de {pedido['cliente_nombre']} marcado como {nuevo_estado}.", "success")
    return redirect(url_for("pedidos"))


# ------------------------------------------------------------
# FACTURACIÓN DE PROVEEDORES (solo admin)
# ------------------------------------------------------------

@app.route("/facturacion")
@admin_required
def facturacion():
    db = get_db()
    estado = request.args.get("estado", "").strip()

    query = "SELECT * FROM facturas WHERE 1=1"
    params = []
    if estado:
        query += " AND estado = ?"
        params.append(estado)
    query += " ORDER BY fecha DESC, id DESC"

    facturas = db.execute(query, params).fetchall()

    gasto_total = db.execute("SELECT COALESCE(SUM(monto), 0) AS n FROM facturas").fetchone()["n"]
    gasto_pendiente = db.execute(
        "SELECT COALESCE(SUM(monto), 0) AS n FROM facturas WHERE estado = 'Pendiente'"
    ).fetchone()["n"]

    mes = datetime.now().strftime("%Y-%m")
    gasto_mes = db.execute(
        "SELECT COALESCE(SUM(monto), 0) AS n FROM facturas WHERE fecha LIKE ?", (f"{mes}%",)
    ).fetchone()["n"]

    por_proveedor = db.execute(
        """SELECT proveedor, COUNT(*) AS n_facturas, SUM(monto) AS total
           FROM facturas GROUP BY proveedor ORDER BY total DESC"""
    ).fetchall()

    return render_template(
        "facturacion.html",
        facturas=facturas,
        estado_actual=estado,
        gasto_total=gasto_total,
        gasto_pendiente=gasto_pendiente,
        gasto_mes=gasto_mes,
        por_proveedor=por_proveedor,
    )


@app.route("/facturacion/nueva", methods=["GET", "POST"])
@admin_required
def factura_nueva():
    db = get_db()

    if request.method == "POST":
        proveedor = request.form.get("proveedor", "").strip()
        numero_factura = request.form.get("numero_factura", "").strip()
        categoria = request.form.get("categoria", "Mercancía").strip()
        notas = request.form.get("notas", "").strip()
        fecha = request.form.get("fecha", "").strip() or datetime.now().strftime("%Y-%m-%d")

        try:
            monto = int(request.form["monto"])
        except (KeyError, ValueError):
            flash("El monto debe ser un número válido.", "error")
            return redirect(url_for("factura_nueva"))

        if not proveedor or monto <= 0:
            flash("Proveedor y monto son obligatorios.", "error")
            return redirect(url_for("factura_nueva"))

        db.execute(
            """INSERT INTO facturas (fecha, proveedor, numero_factura, monto, categoria, estado, notas, registrado_por)
               VALUES (?, ?, ?, ?, ?, 'Pendiente', ?, ?)""",
            (fecha, proveedor, numero_factura, monto, categoria, notas, session["nombre"]),
        )
        db.commit()
        flash("Factura registrada.", "success")
        return redirect(url_for("facturacion"))

    proveedores = db.execute("SELECT * FROM proveedores ORDER BY nombre").fetchall()
    return render_template("factura_form.html", proveedores=proveedores)


@app.route("/facturacion/<int:factura_id>/estado", methods=["POST"])
@admin_required
def factura_estado(factura_id):
    db = get_db()
    factura = db.execute("SELECT * FROM facturas WHERE id = ?", (factura_id,)).fetchone()

    if factura is None:
        flash("Factura no encontrada.", "error")
        return redirect(url_for("facturacion"))

    nuevo_estado = "Pendiente" if factura["estado"] == "Pagada" else "Pagada"
    db.execute("UPDATE facturas SET estado = ? WHERE id = ?", (nuevo_estado, factura_id))
    db.commit()
    flash(f"Factura marcada como {nuevo_estado}.", "success")
    return redirect(url_for("facturacion"))


@app.route("/facturacion/<int:factura_id>/eliminar", methods=["POST"])
@admin_required
def factura_eliminar(factura_id):
    db = get_db()
    db.execute("DELETE FROM facturas WHERE id = ?", (factura_id,))
    db.commit()
    flash("Factura eliminada.", "success")
    return redirect(url_for("facturacion"))


# ------------------------------------------------------------
# PERFIL
# ------------------------------------------------------------

@app.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    db = get_db()

    if request.method == "POST":
        actual = request.form.get("password_actual", "")
        nueva = request.form.get("password_nueva", "")
        confirmar = request.form.get("password_confirmar", "")

        usuario = db.execute(
            "SELECT * FROM usuarios WHERE id = ?", (session["usuario_id"],)
        ).fetchone()

        if not check_password_hash(usuario["password_hash"], actual):
            flash("La contraseña actual no es correcta.", "error")
            return redirect(url_for("perfil"))

        if len(nueva) < 4:
            flash("La nueva contraseña debe tener al menos 4 caracteres.", "error")
            return redirect(url_for("perfil"))

        if nueva != confirmar:
            flash("La confirmación no coincide con la nueva contraseña.", "error")
            return redirect(url_for("perfil"))

        db.execute(
            "UPDATE usuarios SET password_hash = ? WHERE id = ?",
            (generate_password_hash(nueva), session["usuario_id"]),
        )
        db.commit()
        flash("Contraseña actualizada correctamente.", "success")
        return redirect(url_for("perfil"))

    mis_ventas_n = db.execute(
        "SELECT COUNT(*) AS n, COALESCE(SUM(total), 0) AS total FROM ventas WHERE vendedor = ?",
        (session["nombre"],),
    ).fetchone()

    mis_pedidos_n = db.execute(
        "SELECT COUNT(*) AS n FROM pedidos WHERE vendedor = ?", (session["nombre"],)
    ).fetchone()["n"]

    return render_template(
        "perfil.html",
        mis_ventas_n=mis_ventas_n["n"],
        mis_ventas_total=mis_ventas_n["total"],
        mis_pedidos_n=mis_pedidos_n,
    )


# ------------------------------------------------------------
# USUARIOS (solo admin)
# ------------------------------------------------------------

@app.route("/usuarios")
@admin_required
def usuarios():
    db = get_db()
    filas = db.execute("SELECT * FROM usuarios ORDER BY rol, nombre").fetchall()
    return render_template("usuarios.html", usuarios=filas)


@app.route("/usuarios/nuevo", methods=["GET", "POST"])
@admin_required
def usuario_nuevo():
    if request.method == "POST":
        db = get_db()
        nombre = request.form["nombre"].strip()
        usuario = request.form["usuario"].strip().lower()
        rol = request.form["rol"]
        password = request.form["password"]

        existe = db.execute("SELECT id FROM usuarios WHERE usuario = ?", (usuario,)).fetchone()
        if existe:
            flash("Ese nombre de usuario ya existe.", "error")
            return redirect(url_for("usuario_nuevo"))

        db.execute(
            """INSERT INTO usuarios (nombre, usuario, rol, password_hash, activo)
               VALUES (?, ?, ?, ?, 1)""",
            (nombre, usuario, rol, generate_password_hash(password)),
        )
        db.commit()
        flash("Empleado creado correctamente.", "success")
        return redirect(url_for("usuarios"))

    return render_template("usuario_form.html")


@app.route("/usuarios/<int:usuario_id>/toggle", methods=["POST"])
@admin_required
def usuario_toggle(usuario_id):
    db = get_db()
    fila = db.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()

    if fila is None:
        flash("Usuario no encontrado.", "error")
        return redirect(url_for("usuarios"))

    if fila["id"] == session.get("usuario_id"):
        flash("No puedes desactivar tu propia cuenta.", "error")
        return redirect(url_for("usuarios"))

    nuevo_estado = 0 if fila["activo"] else 1
    db.execute("UPDATE usuarios SET activo = ? WHERE id = ?", (nuevo_estado, usuario_id))
    db.commit()
    flash("Estado del empleado actualizado.", "success")
    return redirect(url_for("usuarios"))


# ------------------------------------------------------------
# REPORTES (solo admin)
# ------------------------------------------------------------

@app.route("/reportes")
@admin_required
def reportes():
    db = get_db()

    productos = db.execute("SELECT * FROM productos").fetchall()
    valor_venta = sum(p["precio_venta"] * p["stock"] for p in productos)
    costo_total = sum(p["costo"] * p["stock"] for p in productos)
    ganancia_potencial = valor_venta - costo_total

    total_ventas_historico = db.execute(
        "SELECT COALESCE(SUM(total), 0) AS total FROM ventas"
    ).fetchone()["total"]

    por_categoria = db.execute(
        """SELECT categoria, COUNT(*) AS n_productos, SUM(stock) AS unidades,
                  SUM(precio_venta * stock) AS valor
           FROM productos GROUP BY categoria ORDER BY valor DESC"""
    ).fetchall()

    mas_vendidos = db.execute(
        """SELECT sku, nombre, SUM(cantidad) AS unidades_vendidas,
                  SUM(cantidad * precio) AS ingresos
           FROM venta_items GROUP BY sku ORDER BY unidades_vendidas DESC LIMIT 10"""
    ).fetchall()

    gasto_facturado_total = db.execute(
        "SELECT COALESCE(SUM(monto), 0) AS n FROM facturas"
    ).fetchone()["n"]

    ganancia_real_historica = total_ventas_historico - gasto_facturado_total

    return render_template(
        "reportes.html",
        valor_venta=valor_venta,
        costo_total=costo_total,
        ganancia_potencial=ganancia_potencial,
        total_ventas_historico=total_ventas_historico,
        por_categoria=por_categoria,
        mas_vendidos=mas_vendidos,
        gasto_facturado_total=gasto_facturado_total,
        ganancia_real_historica=ganancia_real_historica,
    )


# ------------------------------------------------------------
# ARRANQUE
# ------------------------------------------------------------

if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        init_db()
    else:
        init_db()  # asegura que las tablas existan; no duplica datos

    # host="0.0.0.0" permite que otras computadoras en la misma red
    # (mismo router / WiFi) se conecten usando tu IP local.
    app.run(host="0.0.0.0", port=5000, debug=False)
