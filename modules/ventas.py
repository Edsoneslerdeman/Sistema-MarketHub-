"""
MarketHub - Módulo de Ventas
Gestiona el carrito de compras, transacciones atómicas de venta,
ventas en espera (pausadas), anulación con devolución de stock y cierre de caja.
"""
from __future__ import annotations
import json
import sqlite3
from dataclasses import dataclass, field
from typing import Optional

from modules.database import get_connection
from modules import inventario as inv
from modules import pagos as pag
from modules import usuarios as usr


# ==========================================
# Carrito de Compras en Memoria
# ==========================================

@dataclass
class ItemCarrito:
    producto_id: int
    nombre: str
    codigo: str
    cantidad: int
    precio_unit: float

    @property
    def subtotal(self) -> float:
        return round(self.cantidad * self.precio_unit, 2)


@dataclass
class Carrito:
    items: list[ItemCarrito] = field(default_factory=list)

    def agregar(self, codigo_o_id: str | int, cantidad: int = 1) -> dict:
        """Agrega o incrementa un producto en el carrito validando el stock disponible."""
        try:
            cantidad = int(cantidad)
        except (ValueError, TypeError):
            return {"ok": False, "error": "Cantidad inválida."}

        if cantidad <= 0:
            return {"ok": False, "error": "La cantidad debe ser mayor a 0."}

        producto = inv.buscar_producto(codigo_o_id)
        if producto is None:
            return {"ok": False, "error": f"Producto con código '{codigo_o_id}' no encontrado o inactivo."}

        # Validar existencia previa en el carrito
        for item in self.items:
            if item.producto_id == producto["id"]:
                nueva_cantidad = item.cantidad + cantidad
                if nueva_cantidad > producto["stock"]:
                    return {
                        "ok": False,
                        "error": f"Stock insuficiente para '{producto['nombre']}'. Disponible: {producto['stock']}, en carrito: {item.cantidad}."
                    }
                item.cantidad = nueva_cantidad
                return {"ok": True, "mensaje": f"'{producto['nombre']}' actualizado a {nueva_cantidad} uds."}

        # Producto nuevo en carrito
        if cantidad > producto["stock"]:
            return {
                "ok": False,
                "error": f"Stock insuficiente. Disponible: {producto['stock']} uds."
            }

        self.items.append(ItemCarrito(
            producto_id=producto["id"],
            nombre=producto["nombre"],
            codigo=producto["codigo"],
            cantidad=cantidad,
            precio_unit=producto["precio"]
        ))
        return {"ok": True, "mensaje": f"'{producto['nombre']}' agregado al carrito."}

    def actualizar_cantidad(self, producto_id: int, nueva_cantidad: int) -> dict:
        """Actualiza directamente la cantidad de un ítem en el carrito."""
        if nueva_cantidad <= 0:
            return self.quitar(producto_id)

        producto = inv.buscar_producto(producto_id)
        if not producto or producto["stock"] < nueva_cantidad:
            return {"ok": False, "error": "No hay stock suficiente para esa cantidad."}

        for item in self.items:
            if item.producto_id == producto_id:
                item.cantidad = nueva_cantidad
                return {"ok": True, "mensaje": "Cantidad actualizada."}

        return {"ok": False, "error": "Producto no encontrado en el carrito."}

    def quitar(self, producto_id: int) -> dict:
        """Quita un producto del carrito."""
        longitud_inicial = len(self.items)
        self.items = [item for item in self.items if item.producto_id != producto_id]
        if len(self.items) < longitud_inicial:
            return {"ok": True, "mensaje": "Producto retirado del carrito."}
        return {"ok": False, "error": "El producto no estaba en el carrito."}

    def limpiar(self) -> None:
        """Vacía el carrito."""
        self.items.clear()

    @property
    def total(self) -> float:
        """Calcula el total general redondeado a 2 decimales."""
        return round(sum(i.subtotal for i in self.items), 2)

    def mostrar(self) -> list[dict]:
        """Retorna una lista de diccionarios con el detalle de ítems."""
        return [
            {
                "producto_id": i.producto_id,
                "nombre": i.nombre,
                "codigo": i.codigo,
                "cantidad": i.cantidad,
                "precio_unit": i.precio_unit,
                "subtotal": i.subtotal,
            }
            for i in self.items
        ]

    def serializar(self) -> str:
        """Convierte los ítems a JSON para guardar ventas en espera."""
        return json.dumps(self.mostrar())

    def deserializar(self, datos_json: str) -> None:
        """Restaura ítems a partir de JSON."""
        self.limpiar()
        items_data = json.loads(datos_json)
        for d in items_data:
            self.items.append(ItemCarrito(
                producto_id=d["producto_id"],
                nombre=d["nombre"],
                codigo=d.get("codigo", ""),
                cantidad=d["cantidad"],
                precio_unit=d["precio_unit"]
            ))


# ==========================================
# Registro Atómico de Ventas
# ==========================================

def registrar_venta(carrito: Carrito, metodo_pago: str,
                    monto_recibido: Optional[float] = None,
                    cliente_id: Optional[int] = None,
                    usuario_id: Optional[int] = None,
                    notas: Optional[str] = None,
                    referencia: Optional[str] = None) -> dict:
    """
    Ejecuta una venta completa en una ÚNICA transacción SQLite atómica (ACID):
    1. Valida permisos y carrito.
    2. Inserta la cabecera en 'ventas'.
    3. Inserta ítems en 'detalle_ventas'.
    4. Descuenta el inventario y genera movimientos en el kardex.
    5. Procesa y registra el pago exacto y cálculo de cambio.
    6. Confirma (commit) o revierte todo (rollback) ante cualquier error.
    """
    if not carrito.items:
        return {"ok": False, "error": "El carrito está vacío. Agregue productos antes de cobrar."}

    total = carrito.total
    if total <= 0:
        return {"ok": False, "error": "El total de la venta debe ser mayor a 0."}

    # Determinar operador
    uid = usuario_id or (usr.sesion().id if usr.sesion() else None)
    if uid is None:
        return {"ok": False, "error": "No hay un cajero o usuario autenticado para registrar la venta."}

    # Validar monto recibido
    if monto_recibido is None or metodo_pago != "efectivo":
        monto_recibido = total
    else:
        try:
            monto_recibido = round(float(monto_recibido), 2)
        except (ValueError, TypeError):
            return {"ok": False, "error": "El monto recibido es inválido."}

    if metodo_pago == "efectivo" and monto_recibido < total:
        return {
            "ok": False,
            "error": f"Monto recibido insuficiente (Bs. {monto_recibido:.2f}). El total es Bs. {total:.2f}."
        }

    conn = get_connection()
    try:
        # Iniciar transacción
        cursor = conn.cursor()

        # 1. Cabecera de venta
        cursor.execute(
            """INSERT INTO ventas (usuario_id, cliente_id, total, metodo_pago, monto_pago, cambio, notas)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (uid, cliente_id, total, metodo_pago, monto_recibido, 0.0, notas)
        )
        venta_id = cursor.lastrowid

        # 2. Insertar detalles y descontar stock atómicamente
        for item in carrito.items:
            cursor.execute(
                """INSERT INTO detalle_ventas (venta_id, producto_id, cantidad, precio_unit, subtotal)
                   VALUES (?, ?, ?, ?, ?)""",
                (venta_id, item.producto_id, item.cantidad, item.precio_unit, item.subtotal)
            )
            # Descontar stock con verificación directa
            descuento_exitoso = inv._descontar_stock(
                conn, item.producto_id, item.cantidad,
                motivo=f"Venta #{venta_id}", usuario_id=uid
            )
            if not descuento_exitoso:
                conn.rollback()
                return {
                    "ok": False,
                    "error": f"Stock insuficiente en tiempo real para '{item.nombre}'. Transacción cancelada."
                }

        # 3. Registrar el pago en la misma transacción
        res_pago = pag.registrar_pago_transaccion(
            conn, venta_id, metodo_pago, total, monto_recibido, referencia
        )
        if not res_pago["ok"]:
            conn.rollback()
            return res_pago

        # Si todo fue exitoso, commit total
        conn.commit()

        # Limpiar carrito
        carrito.limpiar()

        cambio_final = res_pago["cambio"]
        return {
            "ok": True,
            "venta_id": venta_id,
            "total": total,
            "monto_recibido": monto_recibido,
            "cambio": cambio_final,
            "metodo": metodo_pago,
            "mensaje": f"Venta #{venta_id} procesada exitosamente. Cambio: Bs. {cambio_final:.2f}"
        }
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": f"Error al procesar la venta: {e}"}
    finally:
        conn.close()


# ==========================================
# Ventas en Espera (Pausar / Reanudar)
# ==========================================

def pausar_venta(carrito: Carrito, etiqueta: str = "Cliente en espera",
                 usuario_id: Optional[int] = None) -> dict:
    """Pausa la venta actual para atender a otro cliente."""
    if not carrito.items:
        return {"ok": False, "error": "El carrito está vacío."}

    uid = usuario_id or (usr.sesion().id if usr.sesion() else 1)
    conn = get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO ventas_en_espera (usuario_id, etiqueta, datos_json, total)
               VALUES (?, ?, ?, ?)""",
            (uid, etiqueta.strip(), carrito.serializar(), carrito.total)
        )
        conn.commit()
        espera_id = cursor.lastrowid
        carrito.limpiar()
        return {"ok": True, "id": espera_id, "mensaje": f"Venta '{etiqueta}' puesta en espera."}
    finally:
        conn.close()


def recuperar_venta_pausada(espera_id: int, carrito_destino: Carrito) -> dict:
    """Restaura una venta en espera al carrito activo y la elimina de espera."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM ventas_en_espera WHERE id = ?", (espera_id,)).fetchone()
        if not row:
            return {"ok": False, "error": "Venta en espera no encontrada."}

        carrito_destino.deserializar(row["datos_json"])
        conn.execute("DELETE FROM ventas_en_espera WHERE id = ?", (espera_id,))
        conn.commit()
        return {"ok": True, "mensaje": f"Venta '{row['etiqueta']}' restaurada al carrito."}
    finally:
        conn.close()


def listar_ventas_pausadas() -> list[dict]:
    """Lista las ventas en espera activas."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT e.id, e.etiqueta, e.total, e.fecha, u.nombre AS cajero
        FROM ventas_en_espera e
        JOIN usuarios u ON e.usuario_id = u.id
        ORDER BY e.fecha DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ==========================================
# Consultas y Anulación
# ==========================================

def obtener_venta(venta_id: int) -> Optional[dict]:
    """Retorna información completa de una venta y sus ítems individuales."""
    conn = get_connection()
    venta = conn.execute("""
        SELECT v.*, u.nombre AS cajero, c.razon_social AS cliente_nombre, c.nit_ci AS cliente_nit
        FROM ventas v
        JOIN usuarios u ON v.usuario_id = u.id
        LEFT JOIN clientes c ON v.cliente_id = c.id
        WHERE v.id = ?
    """, (venta_id,)).fetchone()

    if not venta:
        conn.close()
        return None

    detalle = conn.execute("""
        SELECT d.*, p.nombre AS producto, p.codigo
        FROM detalle_ventas d
        JOIN productos p ON d.producto_id = p.id
        WHERE d.venta_id = ?
    """, (venta_id,)).fetchall()
    conn.close()

    return {**dict(venta), "detalle": [dict(r) for r in detalle]}


def listar_ventas(fecha_inicio: Optional[str] = None, fecha_fin: Optional[str] = None,
                  limite: int = 100, usuario_id: Optional[int] = None) -> list[dict]:
    """Lista ventas registradas con filtrado de fechas y cajero."""
    conn = get_connection()
    query = """
        SELECT v.id, v.fecha, v.total, v.metodo_pago, v.monto_pago, v.cambio, v.estado,
               u.nombre AS cajero,
               COALESCE(c.razon_social, 'Cliente General') AS cliente
        FROM ventas v
        JOIN usuarios u ON v.usuario_id = u.id
        LEFT JOIN clientes c ON v.cliente_id = c.id
        WHERE 1=1
    """
    params = []
    if fecha_inicio:
        query += " AND date(v.fecha) >= ?"
        params.append(fecha_inicio)
    if fecha_fin:
        query += " AND date(v.fecha) <= ?"
        params.append(fecha_fin)
    if usuario_id:
        query += " AND v.usuario_id = ?"
        params.append(usuario_id)

    query += " ORDER BY v.fecha DESC, v.id DESC LIMIT ?"
    params.append(limite)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def anular_venta(venta_id: int, usuario_id: Optional[int] = None,
                 motivo: str = "Devolución del cliente") -> dict:
    """Anula una venta y devuelve el stock al inventario de forma atómica."""
    conn = get_connection()
    try:
        venta = conn.execute("SELECT estado FROM ventas WHERE id = ?", (venta_id,)).fetchone()
        if not venta:
            return {"ok": False, "error": "Venta no encontrada."}
        if venta["estado"] == "anulada":
            return {"ok": False, "error": "Esta venta ya fue anulada anteriormente."}

        # Obtener ítems para retornar stock
        detalles = conn.execute(
            "SELECT producto_id, cantidad FROM detalle_ventas WHERE venta_id = ?", (venta_id,)
        ).fetchall()

        uid = usuario_id or (usr.sesion().id if usr.sesion() else None)

        for d in detalles:
            conn.execute(
                "UPDATE productos SET stock = stock + ? WHERE id = ?",
                (d["cantidad"], d["producto_id"])
            )
            inv._registrar_movimiento(
                conn, d["producto_id"], "entrada", d["cantidad"],
                motivo=f"Anulación Venta #{venta_id}: {motivo}", usuario_id=uid
            )

        conn.execute("UPDATE ventas SET estado = 'anulada' WHERE id = ?", (venta_id,))
        conn.commit()
        return {"ok": True, "mensaje": f"Venta #{venta_id} anulada y stock devuelto."}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


# ==========================================
# Cierre de Caja
# ==========================================

def cierre_caja(fecha: Optional[str] = None) -> dict:
    """Genera el resumen de cierre diario con cifras exactas verificadas."""
    conn = get_connection()
    if fecha is None:
        fecha = conn.execute("SELECT date('now', 'localtime')").fetchone()[0]

    total_ventas = conn.execute("""
        SELECT COUNT(*) AS total_transacciones,
               COALESCE(SUM(total), 0) AS total_ingresos
        FROM ventas
        WHERE date(fecha) = ? AND estado = 'completada'
    """, (fecha,)).fetchone()

    por_metodo = conn.execute("""
        SELECT metodo_pago, COUNT(*) AS cantidad, COALESCE(SUM(total), 0) AS subtotal
        FROM ventas
        WHERE date(fecha) = ? AND estado = 'completada'
        GROUP BY metodo_pago
    """, (fecha,)).fetchall()

    top_productos = conn.execute("""
        SELECT p.nombre, SUM(d.cantidad) AS unidades, ROUND(SUM(d.subtotal), 2) AS ingreso
        FROM detalle_ventas d
        JOIN ventas v ON d.venta_id = v.id
        JOIN productos p ON d.producto_id = p.id
        WHERE date(v.fecha) = ? AND v.estado = 'completada'
        GROUP BY p.nombre
        ORDER BY ingreso DESC
        LIMIT 5
    """, (fecha,)).fetchall()

    conn.close()
    return {
        "fecha": fecha,
        "total_ventas": total_ventas["total_transacciones"] or 0,
        "ingresos_totales": round(float(total_ventas["total_ingresos"] or 0), 2),
        "por_metodo_pago": [dict(r) for r in por_metodo],
        "top_5_productos": [dict(r) for r in top_productos],
    }


# ==========================================
# Generador de Ticket Térmico (58mm / 80mm)
# ==========================================

def generar_ticket_texto(venta_id: int) -> str:
    """Genera el texto de un ticket de compra listo para imprimir."""
    venta = obtener_venta(venta_id)
    if not venta:
        return "Venta no encontrada."

    ancho = 36
    linea = "=" * ancho
    linea_corta = "-" * ancho

    t = []
    t.append("         MARKETHUB MINIMERCADO         ")
    t.append("     SISTEMA DE GESTION INTEGRAL      ")
    t.append(linea)
    t.append(f"Ticket #{venta['id']:06d}     Fecha: {venta['fecha'][:10]}")
    t.append(f"Hora: {venta['fecha'][11:19]}      Cajero: {venta['cajero']}")
    cliente = venta.get("cliente_nombre") or "Cliente General"
    nit = venta.get("cliente_nit") or "0"
    t.append(f"Cliente: {cliente}")
    t.append(f"NIT/CI:  {nit}")
    t.append(linea_corta)
    t.append("CANT  DESCRIPCION            SUBTOTAL")
    t.append(linea_corta)

    for d in venta["detalle"]:
        nom = d["producto"][:18]
        t.append(f"{d['cantidad']:<4}  {nom:<20} Bs.{d['subtotal']:>6.2f}")

    t.append(linea_corta)
    t.append(f"TOTAL:                      Bs.{venta['total']:>6.2f}")
    t.append(f"METODO DE PAGO:             {venta['metodo_pago'].upper():>9}")
    t.append(f"MONTO RECIBIDO:             Bs.{venta['monto_pago']:>6.2f}")
    t.append(f"CAMBIO ENTREGADO:           Bs.{venta['cambio']:>6.2f}")
    t.append(linea)
    t.append("     ¡GRACIAS POR SU PREFERENCIA!     ")
    t.append("         CONSERVE SU TICKET           ")
    return "\n".join(t)
