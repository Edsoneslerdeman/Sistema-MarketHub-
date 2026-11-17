"""
MarketHub - Módulo de Inventario
Gestiona catálogo de productos, control de stock, categorías y kardex de movimientos.
"""
from __future__ import annotations
import sqlite3
from typing import Optional
from modules.database import get_connection
from modules import usuarios as usr


# ==========================================
# Gestión de Productos
# ==========================================

def agregar_producto(nombre: str, codigo: str, precio: float,
                      stock_inicial: int = 0, stock_minimo: int = 5,
                      categoria_id: Optional[int] = None,
                      usuario_id: Optional[int] = None) -> dict:
    """Registra un nuevo producto y su entrada inicial en el kardex."""
    nombre = nombre.strip()
    codigo = codigo.strip().upper()

    if not nombre or not codigo:
        return {"ok": False, "error": "El nombre y el código de producto son obligatorios."}

    try:
        precio = round(float(precio), 2)
        stock_inicial = int(stock_inicial)
        stock_minimo = int(stock_minimo)
    except (ValueError, TypeError):
        return {"ok": False, "error": "Valores numéricos inválidos para precio o stock."}

    if precio < 0:
        return {"ok": False, "error": "El precio no puede ser negativo."}
    if stock_inicial < 0 or stock_minimo < 0:
        return {"ok": False, "error": "El stock no puede ser negativo."}

    conn = get_connection()
    try:
        # Verificar si existe un producto inactivo con el mismo código
        row_inactivo = conn.execute(
            "SELECT id, activo FROM productos WHERE codigo = ?", (codigo,)
        ).fetchone()

        if row_inactivo:
            if row_inactivo["activo"] == 0:
                # Reactivar y actualizar
                conn.execute(
                    """UPDATE productos
                       SET nombre = ?, precio = ?, stock = ?, stock_minimo = ?,
                           categoria_id = ?, activo = 1
                       WHERE id = ?""",
                    (nombre, precio, stock_inicial, stock_minimo, categoria_id, row_inactivo["id"])
                )
                prod_id = row_inactivo["id"]
            else:
                return {"ok": False, "error": f"Ya existe un producto activo con el código '{codigo}'."}
        else:
            cursor = conn.execute(
                """INSERT INTO productos (nombre, codigo, precio, stock, stock_minimo, categoria_id)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (nombre, codigo, precio, stock_inicial, stock_minimo, categoria_id)
            )
            prod_id = cursor.lastrowid

        # Registrar movimiento en kardex si tiene stock inicial
        if stock_inicial > 0:
            uid = usuario_id or (usr.sesion().id if usr.sesion() else None)
            _registrar_movimiento(conn, prod_id, "entrada", stock_inicial, "Inventario inicial", uid)

        conn.commit()
        return {"ok": True, "id": prod_id, "mensaje": f"Producto '{nombre}' registrado con éxito."}
    except sqlite3.IntegrityError as e:
        return {"ok": False, "error": f"Error de duplicidad o clave foránea: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def editar_producto(producto_id: int, nombre: str, codigo: str, precio: float,
                    stock_minimo: int = 5, categoria_id: Optional[int] = None,
                    usuario_id: Optional[int] = None) -> dict:
    """Modifica los datos de un producto sin alterar directamente el stock (usa ajuste para stock)."""
    nombre = nombre.strip()
    codigo = codigo.strip().upper()

    if not nombre or not codigo:
        return {"ok": False, "error": "Nombre y código son obligatorios."}

    try:
        precio = round(float(precio), 2)
        stock_minimo = int(stock_minimo)
    except (ValueError, TypeError):
        return {"ok": False, "error": "Valores numéricos inválidos."}

    if precio < 0 or stock_minimo < 0:
        return {"ok": False, "error": "El precio y stock mínimo no pueden ser negativos."}

    conn = get_connection()
    try:
        # Verificar que el código no pertenezca a otro producto
        duplicado = conn.execute(
            "SELECT id FROM productos WHERE codigo = ? AND id != ?", (codigo, producto_id)
        ).fetchone()
        if duplicado:
            return {"ok": False, "error": f"El código '{codigo}' ya está asignado a otro producto."}

        conn.execute(
            """UPDATE productos
               SET nombre = ?, codigo = ?, precio = ?, stock_minimo = ?, categoria_id = ?
               WHERE id = ?""",
            (nombre, codigo, precio, stock_minimo, categoria_id, producto_id)
        )
        conn.commit()
        return {"ok": True, "mensaje": f"Producto '{nombre}' actualizado."}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def listar_productos(solo_activos: bool = True, con_bajo_stock: bool = False,
                     busqueda: Optional[str] = None, categoria_id: Optional[int] = None) -> list[dict]:
    """Lista productos con filtros combinables de búsqueda y stock."""
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
    if categoria_id:
        query += " AND p.categoria_id = ?"
        params.append(categoria_id)
    if busqueda:
        query += " AND (p.nombre LIKE ? OR p.codigo LIKE ?)"
        patron = f"%{busqueda.strip()}%"
        params.extend([patron, patron])

    query += " ORDER BY p.nombre ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def buscar_producto(codigo_o_id: str | int) -> Optional[dict]:
    """Busca un producto por código exacto o ID."""
    conn = get_connection()
    if isinstance(codigo_o_id, int) or (isinstance(codigo_o_id, str) and codigo_o_id.isdigit()):
        row = conn.execute(
            """SELECT p.*, c.nombre AS categoria
               FROM productos p
               LEFT JOIN categorias c ON p.categoria_id = c.id
               WHERE p.id = ? AND p.activo = 1""",
            (int(codigo_o_id),)
        ).fetchone()
        if row:
            conn.close()
            return dict(row)

    row = conn.execute(
        """SELECT p.*, c.nombre AS categoria
           FROM productos p
           LEFT JOIN categorias c ON p.categoria_id = c.id
           WHERE UPPER(p.codigo) = ? AND p.activo = 1""",
        (str(codigo_o_id).strip().upper(),)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def buscar_productos_coincidencia(termino: str, limite: int = 15) -> list[dict]:
    """Búsqueda rápida por nombre o código para autocompletado en el POS."""
    termino = termino.strip()
    if not termino:
        return listar_productos(limite=limite)

    conn = get_connection()
    patron = f"%{termino}%"
    rows = conn.execute(
        """SELECT p.id, p.nombre, p.codigo, p.precio, p.stock, p.stock_minimo, c.nombre AS categoria
           FROM productos p
           LEFT JOIN categorias c ON p.categoria_id = c.id
           WHERE p.activo = 1 AND (p.nombre LIKE ? OR p.codigo LIKE ?)
           ORDER BY p.nombre ASC LIMIT ?""",
        (patron, patron, limite)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def ajustar_stock(producto_id: int, cantidad_nueva: int, motivo: str = "Ajuste manual",
                  usuario_id: Optional[int] = None) -> dict:
    """Ajusta el inventario físico y registra la diferencia en el kardex."""
    try:
        cantidad_nueva = int(cantidad_nueva)
    except (ValueError, TypeError):
        return {"ok": False, "error": "La cantidad debe ser un número entero."}

    if cantidad_nueva < 0:
        return {"ok": False, "error": "El stock no puede ser negativo."}

    conn = get_connection()
    try:
        row = conn.execute("SELECT stock, nombre FROM productos WHERE id = ?", (producto_id,)).fetchone()
        if not row:
            return {"ok": False, "error": "Producto no encontrado."}

        stock_anterior = row["stock"]
        diferencia = cantidad_nueva - stock_anterior
        uid = usuario_id or (usr.sesion().id if usr.sesion() else None)

        conn.execute("UPDATE productos SET stock = ? WHERE id = ?", (cantidad_nueva, producto_id))
        _registrar_movimiento(conn, producto_id, "ajuste", diferencia, motivo, uid)
        conn.commit()
        return {
            "ok": True,
            "mensaje": f"Stock de '{row['nombre']}' ajustado de {stock_anterior} a {cantidad_nueva} unidades."
        }
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def entrada_stock(producto_id: int, cantidad: int, motivo: str = "Compra/reposición",
                  usuario_id: Optional[int] = None) -> dict:
    """Registra la llegada de mercadería y suma al stock existente."""
    try:
        cantidad = int(cantidad)
    except (ValueError, TypeError):
        return {"ok": False, "error": "La cantidad debe ser un número entero."}

    if cantidad <= 0:
        return {"ok": False, "error": "La cantidad a ingresar debe ser mayor a 0."}

    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE productos SET stock = stock + ? WHERE id = ? AND activo = 1",
            (cantidad, producto_id)
        )
        if cursor.rowcount == 0:
            return {"ok": False, "error": "Producto no encontrado o inactivo."}

        uid = usuario_id or (usr.sesion().id if usr.sesion() else None)
        _registrar_movimiento(conn, producto_id, "entrada", cantidad, motivo, uid)
        conn.commit()
        return {"ok": True, "mensaje": f"Se ingresaron {cantidad} unidades al stock."}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def eliminar_producto(producto_id: int, usuario_id: Optional[int] = None) -> dict:
    """Desactiva un producto (soft-delete) para mantener la integridad histórica."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT nombre FROM productos WHERE id = ?", (producto_id,)).fetchone()
        if not row:
            return {"ok": False, "error": "Producto no encontrado."}

        conn.execute("UPDATE productos SET activo = 0 WHERE id = ?", (producto_id,))
        uid = usuario_id or (usr.sesion().id if usr.sesion() else None)
        _registrar_movimiento(conn, producto_id, "ajuste", 0, "Producto desactivado del catálogo", uid)
        conn.commit()
        return {"ok": True, "mensaje": f"Producto '{row['nombre']}' eliminado del catálogo."}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


# ==========================================
# Funciones Internas y Kardex
# ==========================================

def _descontar_stock(conn: sqlite3.Connection, producto_id: int, cantidad: int,
                     motivo: str = "Venta", usuario_id: Optional[int] = None) -> bool:
    """
    Descuenta stock de forma atómica dentro de una transacción ya abierta.
    Verifica que el stock no baje de cero con condición WHERE stock >= cantidad.
    """
    cursor = conn.execute(
        "UPDATE productos SET stock = stock - ? WHERE id = ? AND activo = 1 AND stock >= ?",
        (cantidad, producto_id, cantidad)
    )
    if cursor.rowcount == 0:
        return False

    _registrar_movimiento(conn, producto_id, "salida", cantidad, motivo, usuario_id)
    return True


def _registrar_movimiento(conn: sqlite3.Connection, producto_id: int, tipo: str,
                          cantidad: int, motivo: str = "", usuario_id: Optional[int] = None) -> None:
    """Inserta una fila en el kardex de movimientos."""
    conn.execute(
        """INSERT INTO movimientos_inventario (producto_id, tipo, cantidad, motivo, usuario_id)
           VALUES (?, ?, ?, ?, ?)""",
        (producto_id, tipo, cantidad, motivo, usuario_id)
    )


def historial_movimientos(producto_id: Optional[int] = None, limite: int = 50) -> list[dict]:
    """Retorna los últimos movimientos registrados en el kardex."""
    conn = get_connection()
    query = """
        SELECT m.id, m.fecha, m.tipo, m.cantidad, m.motivo,
               p.nombre AS producto, p.codigo,
               COALESCE(u.nombre, 'Sistema') AS operador
        FROM movimientos_inventario m
        JOIN productos p ON m.producto_id = p.id
        LEFT JOIN usuarios u ON m.usuario_id = u.id
    """
    params = []
    if producto_id:
        query += " WHERE m.producto_id = ?"
        params.append(producto_id)
    query += " ORDER BY m.fecha DESC, m.id DESC LIMIT ?"
    params.append(limite)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def alertas_bajo_stock() -> list[dict]:
    """Retorna productos cuyo stock es igual o inferior al stock mínimo."""
    return listar_productos(con_bajo_stock=True)


# ==========================================
# Categorías
# ==========================================

def agregar_categoria(nombre: str) -> dict:
    """Crea una nueva categoría."""
    nombre = nombre.strip().title()
    if not nombre:
        return {"ok": False, "error": "El nombre de la categoría es obligatorio."}

    conn = get_connection()
    try:
        cursor = conn.execute("INSERT INTO categorias (nombre) VALUES (?)", (nombre,))
        conn.commit()
        return {"ok": True, "id": cursor.lastrowid, "mensaje": f"Categoría '{nombre}' creada."}
    except sqlite3.IntegrityError:
        return {"ok": False, "error": f"La categoría '{nombre}' ya existe."}
    finally:
        conn.close()


def listar_categorias() -> list[dict]:
    """Retorna todas las categorías con la cantidad de productos asociados."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT c.id, c.nombre, COUNT(p.id) AS total_productos
        FROM categorias c
        LEFT JOIN productos p ON c.id = p.categoria_id AND p.activo = 1
        GROUP BY c.id
        ORDER BY c.nombre ASC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def eliminar_categoria(categoria_id: int) -> dict:
    """Elimina una categoría desasociando los productos existentes."""
    conn = get_connection()
    try:
        conn.execute("UPDATE productos SET categoria_id = NULL WHERE categoria_id = ?", (categoria_id,))
        conn.execute("DELETE FROM categorias WHERE id = ?", (categoria_id,))
        conn.commit()
        return {"ok": True, "mensaje": "Categoría eliminada."}
    finally:
        conn.close()
