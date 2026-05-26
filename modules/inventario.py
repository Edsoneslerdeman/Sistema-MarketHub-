"""
MarketHub - Módulo de Inventario (RF-03, RF-01)
Gestiona productos, stock en tiempo real y movimientos de almacén.
"""
from __future__ import annotations
from typing import Optional
from modules.database import get_connection
from modules import usuarios as usr


# Productos

def agregar_producto(nombre: str, codigo: str, precio: float,
                     stock_inicial: int = 0, stock_minimo: int = 5,
                     categoria_id: Optional[int] = None) -> dict:
    if not usr.requiere_permiso("inventario"):
        return {"ok": False, "error": "Sin permiso para gestionar inventario."}
    if precio < 0:
        return {"ok": False, "error": "El precio no puede ser negativo."}

    try:
        conn = get_connection()
        cursor = conn.execute(
            """INSERT INTO productos (nombre, codigo, precio, stock, stock_minimo, categoria_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (nombre, codigo, precio, stock_inicial, stock_minimo, categoria_id)
        )
        prod_id = cursor.lastrowid
        if stock_inicial > 0:
            _registrar_movimiento(conn, prod_id, "entrada", stock_inicial, "Stock inicial")
        conn.commit()
        return {"ok": True, "id": prod_id, "mensaje": f"Producto '{nombre}' registrado."}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def listar_productos(solo_activos: bool = True, con_bajo_stock: bool = False) -> list[dict]:
    conn = get_connection()
    query = """
        SELECT p.*, c.nombre AS categoria
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id
        WHERE 1=1
    """
    params = []
    if solo_activos:
        query += " AND p.activo = 1"
    if con_bajo_stock:
        query += " AND p.stock <= p.stock_minimo"
    query += " ORDER BY p.nombre"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def buscar_producto(codigo: str) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM productos WHERE codigo = ? AND activo = 1", (codigo,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def actualizar_precio(producto_id: int, nuevo_precio: float) -> dict:
    if not usr.requiere_permiso("inventario"):
        return {"ok": False, "error": "Sin permiso."}
    if nuevo_precio < 0:
        return {"ok": False, "error": "Precio inválido."}
    conn = get_connection()
    conn.execute("UPDATE productos SET precio = ? WHERE id = ?", (nuevo_precio, producto_id))
    conn.commit()
    conn.close()
    return {"ok": True, "mensaje": "Precio actualizado."}


def ajustar_stock(producto_id: int, cantidad: int, motivo: str = "Ajuste manual") -> dict:
    """Ajusta el stock directamente (inventario físico vs sistema)."""
    if not usr.requiere_permiso("inventario"):
        return {"ok": False, "error": "Sin permiso."}

    conn = get_connection()
    row = conn.execute("SELECT stock FROM productos WHERE id = ?", (producto_id,)).fetchone()
    if row is None:
        conn.close()
        return {"ok": False, "error": "Producto no encontrado."}

    diferencia = cantidad - row["stock"]
    tipo = "ajuste"
    conn.execute("UPDATE productos SET stock = ? WHERE id = ?", (cantidad, producto_id))
    usuario_id = usr.sesion().id if usr.sesion() else None
    _registrar_movimiento(conn, producto_id, tipo, diferencia, motivo, usuario_id)
    conn.commit()
    conn.close()
    return {"ok": True, "mensaje": f"Stock ajustado a {cantidad} unidades."}


def entrada_stock(producto_id: int, cantidad: int, motivo: str = "Compra/reposición") -> dict:
    """Registra una entrada de mercadería."""
    if not usr.requiere_permiso("inventario"):
        return {"ok": False, "error": "Sin permiso."}
    if cantidad <= 0:
        return {"ok": False, "error": "La cantidad debe ser mayor a 0."}

    conn = get_connection()
    conn.execute(
        "UPDATE productos SET stock = stock + ? WHERE id = ?", (cantidad, producto_id)
    )
    usuario_id = usr.sesion().id if usr.sesion() else None
    _registrar_movimiento(conn, producto_id, "entrada", cantidad, motivo, usuario_id)
    conn.commit()
    conn.close()
    return {"ok": True, "mensaje": f"{cantidad} unidades ingresadas al stock."}


def _descontar_stock(conn, producto_id: int, cantidad: int, motivo: str = "Venta") -> bool:
    """Descuenta stock durante una venta (uso interno)."""
    row = conn.execute(
        "SELECT stock FROM productos WHERE id = ? AND activo = 1", (producto_id,)
    ).fetchone()
    if row is None or row["stock"] < cantidad:
        return False
    conn.execute(
        "UPDATE productos SET stock = stock - ? WHERE id = ?", (cantidad, producto_id)
    )
    usuario_id = usr.sesion().id if usr.sesion() else None
    _registrar_movimiento(conn, producto_id, "salida", cantidad, motivo, usuario_id)
    return True


def _registrar_movimiento(conn, producto_id: int, tipo: str,
                           cantidad: int, motivo: str = "", usuario_id=None):
    conn.execute(
        """INSERT INTO movimientos_inventario (producto_id, tipo, cantidad, motivo, usuario_id)
           VALUES (?, ?, ?, ?, ?)""",
        (producto_id, tipo, cantidad, motivo, usuario_id)
    )


def historial_movimientos(producto_id: Optional[int] = None, limite: int = 50) -> list[dict]:
    conn = get_connection()
    query = """
        SELECT m.*, p.nombre AS producto, u.usuario AS operador
        FROM movimientos_inventario m
        JOIN productos p ON m.producto_id = p.id
        LEFT JOIN usuarios u ON m.usuario_id = u.id
    """
    params = []
    if producto_id:
        query += " WHERE m.producto_id = ?"
        params.append(producto_id)
    query += " ORDER BY m.fecha DESC LIMIT ?"
    params.append(limite)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def alertas_bajo_stock() -> list[dict]:
    """Retorna productos cuyo stock es igual o menor al stock mínimo."""
    return listar_productos(con_bajo_stock=True)


# Categorías 

def agregar_categoria(nombre: str) -> dict:
    try:
        conn = get_connection()
        conn.execute("INSERT INTO categorias (nombre) VALUES (?)", (nombre,))
        conn.commit()
        return {"ok": True, "mensaje": f"Categoría '{nombre}' creada."}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def listar_categorias() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM categorias ORDER BY nombre").fetchall()
    conn.close()
    return [dict(r) for r in rows]