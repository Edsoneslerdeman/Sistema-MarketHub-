"""
MarketHub - Servidor de Aplicación Web
Servidor web Flask moderno para minimercados con Punto de Venta (POS),
gestión de inventario, kardex, historial de ventas, reportes analíticos y roles.
"""
from __future__ import annotations
import os
import sys
import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify, Response
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from modules.database import inicializar_bd, get_connection
from modules import usuarios as usr
from modules import inventario as inv
from modules import ventas as ven
from modules import pagos as pag
from modules import reportes as rep

app = Flask(__name__)
app.secret_key = os.environ.get("MARKETHUB_SECRET_KEY", "markethub-clave-secreta-pos-2026")


# ==========================================
# Decoradores de Autenticación y Permisos
# ==========================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "usuario" not in session:
            flash("Debe iniciar sesión para acceder al sistema.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def roles_required(*roles_permitidos):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "usuario" not in session:
                return redirect(url_for("login"))
            rol_actual = session["usuario"].get("rol")
            if rol_actual not in roles_permitidos:
                flash(f"Acceso denegado: Su rol '{rol_actual}' no tiene permiso para esta sección.", "error")
                return redirect(url_for("index"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ==========================================
# Autenticación y Sesión
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "").strip()

        res = usr.verificar_credenciales(usuario, password)
        if res["ok"]:
            u = res["usuario"]
            session["usuario"] = {
                "id": u.id,
                "nombre": u.nombre,
                "usuario": u.usuario,
                "rol": u.rol
            }
            # Sincronizar sesión interna
            usr.establecer_sesion(u)
            flash(f"¡Bienvenido, {u.nombre}!", "success")

            if u.rol == "cajero":
                return redirect(url_for("vista_pos"))
            elif u.rol == "almacenero":
                return redirect(url_for("vista_inventario"))
            else:
                return redirect(url_for("vista_pos"))
        else:
            flash(res["error"], "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    usr.cerrar_sesion()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    rol = session.get("usuario", {}).get("rol")
    if rol == "almacenero":
        return redirect(url_for("vista_inventario"))
    return redirect(url_for("vista_pos"))


# ==========================================
# Terminal Punto de Venta (POS)
# ==========================================

@app.route("/pos")
@login_required
@roles_required("admin", "cajero")
def vista_pos():
    categorias = inv.listar_categorias()
    return render_template("pos.html", categorias=categorias)


@app.route("/api/productos")
@login_required
def api_productos():
    """Retorna productos activos en formato JSON para el catálogo POS."""
    busqueda = request.args.get("q", "").strip()
    categoria_id = request.args.get("categoria_id", type=int)
    productos = inv.listar_productos(solo_activos=True, busqueda=busqueda or None, categoria_id=categoria_id)
    return jsonify(productos)


@app.route("/api/pos/cobrar", methods=["POST"])
@login_required
@roles_required("admin", "cajero")
def api_pos_cobrar():
    """Procesa la venta atómica y retorna el cambio y comprobante térmico."""
    data = request.get_json() or {}
    items = data.get("items", [])
    metodo_pago = data.get("metodo_pago", "efectivo")
    monto_recibido = data.get("monto_recibido")
    cliente_nit = data.get("cliente_nit", "").strip()
    cliente_nombre = data.get("cliente_nombre", "").strip()

    if not items:
        return jsonify({"ok": False, "error": "El carrito está vacío."}), 400

    # Gestionar cliente opcional
    cliente_id = None
    if cliente_nit:
        conn = get_connection()
        row = conn.execute("SELECT id FROM clientes WHERE nit_ci = ?", (cliente_nit,)).fetchone()
        if row:
            cliente_id = row["id"]
        else:
            cur = conn.execute(
                "INSERT INTO clientes (razon_social, nit_ci) VALUES (?, ?)",
                (cliente_nombre or "Cliente " + cliente_nit, cliente_nit)
            )
            conn.commit()
            cliente_id = cur.lastrowid
        conn.close()

    # Construir carrito temporal
    carrito = ven.Carrito()
    for it in items:
        prod_id = it.get("producto_id")
        cant = it.get("cantidad", 1)
        res_add = carrito.agregar(prod_id, cant)
        if not res_add["ok"]:
            return jsonify({"ok": False, "error": res_add["error"]}), 400

    # Registrar venta con transacción atómica
    usuario_id = session["usuario"]["id"]
    res_venta = ven.registrar_venta(
        carrito=carrito,
        metodo_pago=metodo_pago,
        monto_recibido=monto_recibido,
        cliente_id=cliente_id,
        usuario_id=usuario_id
    )

    if res_venta["ok"]:
        ticket_texto = ven.generar_ticket_texto(res_venta["venta_id"])
        res_venta["ticket"] = ticket_texto
        return jsonify(res_venta)
    else:
        return jsonify(res_venta), 400


@app.route("/api/pos/pausar", methods=["POST"])
@login_required
def api_pos_pausar():
    """Pone la venta actual en espera."""
    data = request.get_json() or {}
    etiqueta = data.get("etiqueta", "Venta en espera")
    items = data.get("items", [])

    carrito = ven.Carrito()
    for it in items:
        carrito.agregar(it["producto_id"], it["cantidad"])

    res = ven.pausar_venta(carrito, etiqueta, usuario_id=session["usuario"]["id"])
    return jsonify(res)


@app.route("/api/pos/pausadas")
@login_required
def api_pos_pausadas():
    """Lista las ventas en espera."""
    return jsonify(ven.listar_ventas_pausadas())


@app.route("/api/pos/recuperar/<int:espera_id>", methods=["POST"])
@login_required
def api_pos_recuperar(espera_id: int):
    """Restaura una venta en espera."""
    carrito = ven.Carrito()
    res = ven.recuperar_venta_pausada(espera_id, carrito)
    if res["ok"]:
        return jsonify({"ok": True, "items": carrito.mostrar()})
    return jsonify(res), 400


# ==========================================
# Gestión de Inventario
# ==========================================

@app.route("/inventario")
@login_required
@roles_required("admin", "almacenero")
def vista_inventario():
    productos = inv.listar_productos(solo_activos=True)
    categorias = inv.listar_categorias()
    stats = rep.reporte_inventario()
    return render_template("inventario.html", productos=productos, categorias=categorias, stats=stats)


@app.route("/inventario/guardar", methods=["POST"])
@login_required
@roles_required("admin", "almacenero")
def guardar_producto_web():
    prod_id = request.form.get("producto_id")
    nombre = request.form.get("nombre", "").strip()
    codigo = request.form.get("codigo", "").strip()
    precio = request.form.get("precio", 0)
    stock_minimo = request.form.get("stock_minimo", 5)
    categoria_id = request.form.get("categoria_id") or None
    if categoria_id:
        categoria_id = int(categoria_id)

    usuario_id = session["usuario"]["id"]

    if prod_id:
        res = inv.editar_producto(
            producto_id=int(prod_id),
            nombre=nombre,
            codigo=codigo,
            precio=precio,
            stock_minimo=stock_minimo,
            categoria_id=categoria_id,
            usuario_id=usuario_id
        )
    else:
        stock_inicial = request.form.get("stock_inicial", 0)
        res = inv.agregar_producto(
            nombre=nombre,
            codigo=codigo,
            precio=precio,
            stock_inicial=int(stock_inicial),
            stock_minimo=int(stock_minimo),
            categoria_id=categoria_id,
            usuario_id=usuario_id
        )

    if res["ok"]:
        flash(res["mensaje"], "success")
    else:
        flash(res["error"], "error")

    return redirect(url_for("vista_inventario"))


@app.route("/inventario/entrada", methods=["POST"])
@login_required
@roles_required("admin", "almacenero")
def entrada_stock_web():
    prod_id = int(request.form.get("producto_id"))
    cantidad = int(request.form.get("cantidad", 0))
    motivo = request.form.get("motivo", "Compra / Reposición")
    usuario_id = session["usuario"]["id"]

    res = inv.entrada_stock(prod_id, cantidad, motivo=motivo, usuario_id=usuario_id)
    if res["ok"]:
        flash(res["mensaje"], "success")
    else:
        flash(res["error"], "error")

    return redirect(url_for("vista_inventario"))


@app.route("/inventario/eliminar/<int:prod_id>", methods=["POST"])
@login_required
@roles_required("admin", "almacenero")
def eliminar_producto_web(prod_id: int):
    usuario_id = session["usuario"]["id"]
    res = inv.eliminar_producto(prod_id, usuario_id=usuario_id)
    if res["ok"]:
        flash(res["mensaje"], "success")
    else:
        flash(res["error"], "error")
    return redirect(url_for("vista_inventario"))


@app.route("/api/kardex")
@login_required
def api_kardex():
    prod_id = request.args.get("producto_id", type=int)
    movs = inv.historial_movimientos(producto_id=prod_id, limite=60)
    return jsonify(movs)


# ==========================================
# Historial de Ventas
# ==========================================

@app.route("/ventas")
@login_required
@roles_required("admin", "cajero")
def vista_ventas():
    hoy = datetime.date.today().isoformat()
    hace_mes = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()

    fecha_inicio = request.args.get("fecha_inicio", hace_mes)
    fecha_fin = request.args.get("fecha_fin", hoy)

    # Si es cajero, puede ver todas o solo las suyas
    rol = session["usuario"]["rol"]
    uid_filtro = session["usuario"]["id"] if rol == "cajero" else None

    ventas = ven.listar_ventas(fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, usuario_id=uid_filtro)
    return render_template(
        "ventas.html",
        ventas=ventas,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin
    )


@app.route("/api/ventas/<int:venta_id>")
@login_required
def api_venta_detalle(venta_id: int):
    venta = ven.obtener_venta(venta_id)
    if not venta:
        return jsonify({"ok": False, "error": "Venta no encontrada."}), 404
    return jsonify(venta)


@app.route("/api/ventas/<int:venta_id>/ticket")
@login_required
def api_venta_ticket(venta_id: int):
    ticket_str = ven.generar_ticket_texto(venta_id)
    return jsonify({"ticket": ticket_str})


@app.route("/ventas/anular/<int:venta_id>", methods=["POST"])
@login_required
@roles_required("admin")
def anular_venta_web(venta_id: int):
    usuario_id = session["usuario"]["id"]
    res = ven.anular_venta(venta_id, usuario_id=usuario_id, motivo="Anulada por administrador")
    if res["ok"]:
        flash(res["mensaje"], "success")
    else:
        flash(res["error"], "error")
    return redirect(url_for("vista_ventas"))


# ==========================================
# Reportes y Cierre de Caja
# ==========================================

@app.route("/reportes")
@login_required
@roles_required("admin")
def vista_reportes():
    hoy = datetime.date.today().isoformat()
    hace_siete = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()

    fecha_inicio = request.args.get("fecha_inicio", hace_siete)
    fecha_fin = request.args.get("fecha_fin", hoy)

    datos_ventas = rep.reporte_ventas(fecha_inicio, fecha_fin)
    top_prod = rep.reporte_top_productos(fecha_inicio, fecha_fin, limite=10)["top_productos"]
    cierre_hoy = ven.cierre_caja()

    return render_template(
        "reportes.html",
        datos_ventas=datos_ventas,
        top_productos=top_prod,
        cierre_hoy=cierre_hoy,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin
    )


# ==========================================
# Gestión de Personal / Usuarios
# ==========================================

@app.route("/usuarios")
@login_required
@roles_required("admin")
def vista_usuarios():
    usuarios = usr.listar_usuarios()
    return render_template("usuarios.html", usuarios=usuarios)


@app.route("/usuarios/guardar", methods=["POST"])
@login_required
@roles_required("admin")
def guardar_usuario_web():
    user_id = request.form.get("usuario_id")
    nombre = request.form.get("nombre", "").strip()
    usuario = request.form.get("usuario", "").strip()
    password = request.form.get("password", "").strip()
    rol = request.form.get("rol", "cajero")

    if user_id:
        res = usr.editar_usuario(int(user_id), nombre, usuario, rol, password or None)
    else:
        res = usr.registrar_usuario(nombre, usuario, password, rol)

    if res["ok"]:
        flash(res["mensaje"], "success")
    else:
        flash(res["error"], "error")
    return redirect(url_for("vista_usuarios"))


@app.route("/usuarios/estado/<int:user_id>", methods=["POST"])
@login_required
@roles_required("admin")
def cambiar_estado_usuario_web(user_id: int):
    if user_id == session["usuario"]["id"]:
        flash("No puedes desactivar tu propia cuenta activa.", "error")
        return redirect(url_for("vista_usuarios"))

    activo = request.form.get("activo") == "1"
    res = usr.cambiar_estado_usuario(user_id, activo)
    flash(res["mensaje"], "success")
    return redirect(url_for("vista_usuarios"))


# ==========================================
# Exportación de Datos a CSV
# ==========================================

@app.route("/exportar/ventas")
@login_required
def exportar_ventas():
    hoy = datetime.date.today().isoformat()
    hace_mes = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
    fi = request.args.get("fecha_inicio", hace_mes)
    ff = request.args.get("fecha_fin", hoy)

    csv_data = rep.exportar_ventas_csv(fi, ff)
    filename = f"markethub_ventas_{fi}_al_{ff}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )


@app.route("/exportar/inventario")
@login_required
def exportar_inventario():
    csv_data = rep.exportar_inventario_csv()
    hoy = datetime.date.today().isoformat()
    filename = f"markethub_inventario_{hoy}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )


# ==========================================
# Inicialización y Ejecución
# ==========================================

if __name__ == "__main__":
    inicializar_bd()
    print("\n" + "=" * 60)
    print(" 🚀 MARKETHUB — SISTEMA WEB INICIADO CON ÉXITO")
    print("=" * 60)
    print(" Acceda al sistema desde su navegador web en:")
    print(" 👉 http://127.0.0.1:5000")
    print("=" * 60)
    print(" Cuentas de acceso:")
    print("  - Administrador:  admin   / admin123")
    print("  - Cajero:         cajero  / cajero123")
    print("  - Almacenero:     almacen / almacen123")
    print("=" * 60 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
