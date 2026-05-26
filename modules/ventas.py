"""
MarketHub - Módulo de Ventas (RF-02, RF-08)
Gestiona el carrito de compras, registro de ventas y cierre de caja.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from modules.database import get_connection
from modules import inventario as inv
from modules import pagos as pag
from modules import usuarios as usr


#  Carrito de compras (en memoria) 

@dataclass
class ItemCarrito:
    producto_id: int
    nombre: str
    cantidad: int
    precio_unit: float

    @property
    def subtotal(self) -> float:
        return round(self.cantidad * self.precio_unit, 2)


@dataclass
class Carrito:
    items: list[ItemCarrito] = field(default_factory=list)

    def agregar(self, codigo: str, cantidad: int = 1) -> dict:
        """Agrega un producto al carrito por su código de barras."""
        producto = inv.buscar_producto(codigo)
        if producto is None:
            return {"ok": False, "error": f"Producto '{codigo}' no encontrado."}
        if producto["stock"] < cantidad:
            return {
                "ok": False,
                "error": f"Stock insuficiente. Disponible: {producto['stock']} uds."
            }
        # Si ya existe en el carrito, sumar
        for item in self.items:
            if item.producto_id == producto["id"]:
                nuevo_total = item.cantidad + cantidad
                if nuevo_total > producto["stock"]:
                    return {"ok": False, "error": "No hay suficiente stock."}
                item.cantidad = nuevo_total
                return {"ok": True, "mensaje": f"'{producto['nombre']}' actualizado ({nuevo_total} uds.)"}

        self.items.append(ItemCarrito(
            producto_id=producto["id"],
            nombre=producto["nombre"],
            cantidad=cantidad,
            precio_unit=producto["precio"]
        ))
        return {"ok": True, "mensaje": f"'{producto['nombre']}' agregado al carrito."}

    def quitar(self, producto_id: int) -> dict:
        antes = len(self.items)
        self.items = [i for i in self.items if i.producto_id != producto_id]
        if len(self.items) < antes:
            return {"ok": True, "mensaje": "Producto retirado del carrito."}
        return {"ok": False, "error": "Producto no estaba en el carrito."}

    def limpiar(self):
        self.items.clear()

    @property
    def total(self) -> float:
        return round(sum(i.subtotal for i in self.items), 2)

    def mostrar(self) -> list[dict]:
        return [
            {
                "producto_id": i.producto_id,
                "nombre": i.nombre,
                "cantidad": i.cantidad,
                "precio_unit": i.precio_unit,
                "subtotal": i.subtotal,
            }
            for i in self.items
        ]


# Registro de ventas 

def registrar_venta(carrito: Carrito, metodo_pago: str,
                    monto_recibido: Optional[float] = None) -> dict:
    """
    Persiste la venta, descuenta stock y registra el pago.
    Retorna el resultado completo con cambio si aplica.
    """
    if not usr.requiere_permiso("ventas"):
        return {"ok": False, "error": "Sin permiso para registrar ventas."}
    if not carrito.items:
        return {"ok": False, "error": "El carrito está vacío."}

    total = carrito.total
    if monto_recibido is None:
        monto_recibido = total  # QR / tarjeta = monto exacto

    if monto_recibido < total and metodo_pago == "efectivo":
        return {"ok": False, "error": f"Monto insuficiente. Total: Bs.{total:.2f}"}

    conn = get_connection()
    try:
        # 1. Insertar cabecera de venta
        usuario_id = usr.sesion().id
        cursor = conn.execute(
            """INSERT INTO ventas (usuario_id, total, metodo_pago)
               VALUES (?, ?, ?)""",
            (usuario_id, total, metodo_pago)
        )
        venta_id = cursor.lastrowid

        # 2. Insertar detalle y descontar stock
        for item in carrito.items:
            conn.execute(
                """INSERT INTO detalle_ventas
                   (venta_id, producto_id, cantidad, precio_unit, subtotal)
                   VALUES (?, ?, ?, ?, ?)""",
                (venta_id, item.producto_id, item.cantidad,
                 item.precio_unit, item.subtotal)
            )
            ok = inv._descontar_stock(conn, item.producto_id, item.cantidad, "Venta")
            if not ok:
                conn.rollback()
                conn.close()
                return {"ok": False, "error": f"Stock insuficiente para '{item.nombre}'."}

        conn.commit()
        conn.close()

        # 3. Procesar pago
        res_pago = pag.procesar_pago(venta_id, metodo_pago, monto_recibido)
        if not res_pago["ok"]:
            return res_pago

        carrito.limpiar()
        return {
            "ok": True,
            "venta_id": venta_id,
            "total": total,
            "cambio": res_pago.get("cambio", 0),
            "metodo": metodo_pago,
            "mensaje": f"Venta #{venta_id} registrada. {res_pago['mensaje']}",
        }
    except Exception as e:
        conn.rollback()
        conn.close()
        return {"ok": False, "error": str(e)}


def obtener_venta(venta_id: int) -> Optional[dict]:
    conn = get_connection()
    venta = conn.execute("SELECT * FROM ventas WHERE id = ?", (venta_id,)).fetchone()
    if venta is None:
        conn.close()
        return None
    detalle = conn.execute(
        """SELECT d.*, p.nombre AS producto
           FROM detalle_ventas d
           JOIN productos p ON d.producto_id = p.id
           WHERE d.venta_id = ?""",
        (venta_id,)
    ).fetchall()
    conn.close()
    return {**dict(venta), "detalle": [dict(r) for r in detalle]}


def listar_ventas(fecha_inicio: Optional[str] = None,
                  fecha_fin: Optional[str] = None,
                  limite: int = 100) -> list[dict]:
    conn = get_connection()
    query = """
        SELECT v.*, u.nombre AS cajero
        FROM ventas v
        JOIN usuarios u ON v.usuario_id = u.id
        WHERE 1=1
    """
    params = []
    if fecha_inicio:
        query += " AND date(v.fecha) >= ?"
        params.append(fecha_inicio)
    if fecha_fin:
        query += " AND date(v.fecha) <= ?"
        params.append(fecha_fin)
    query += " ORDER BY v.fecha DESC LIMIT ?"
    params.append(limite)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


#  Cierre de caja (RF-08) 

def cierre_caja(fecha: Optional[str] = None) -> dict:
    """Genera el resumen de cierre de caja para una fecha (por defecto hoy)."""
    conn = get_connection()
    if fecha is None:
        fecha = conn.execute("SELECT date('now','localtime')").fetchone()[0]

    total_ventas = conn.execute(
        "SELECT COUNT(*) as n, SUM(total) as t FROM ventas WHERE date(fecha) = ?", (fecha,)
    ).fetchone()

    por_metodo = conn.execute("""
        SELECT metodo_pago, COUNT(*) as n, SUM(total) as t
        FROM ventas WHERE date(fecha) = ?
        GROUP BY metodo_pago
    """, (fecha,)).fetchall()

    top_productos = conn.execute("""
        SELECT p.nombre, SUM(d.cantidad) as uds, SUM(d.subtotal) as ingreso
        FROM detalle_ventas d
        JOIN ventas v ON d.venta_id = v.id
        JOIN productos p ON d.producto_id = p.id
        WHERE date(v.fecha) = ?
        GROUP BY p.nombre
        ORDER BY ingreso DESC
        LIMIT 5
    """, (fecha,)).fetchall()

    conn.close()
    return {
        "fecha": fecha,
        "total_ventas": total_ventas["n"] or 0,
        "ingresos_totales": round(total_ventas["t"] or 0, 2),
        "por_metodo_pago": [dict(r) for r in por_metodo],
        "top_5_productos": [dict(r) for r in top_productos],
    }