"""
MarketHub - Módulo de Reportes Analíticos (RF-07)
Genera reportes de ventas, inventario y pagos con indicadores clave.
Tiempo de respuesta objetivo: ≤ 2 seg (validado en testing).
"""
from __future__ import annotations
from typing import Optional
from modules.database import get_connection
from modules import usuarios as usr


def _check_permiso() -> Optional[dict]:
    if not usr.requiere_permiso("reportes"):
        return {"ok": False, "error": "Solo el administrador puede ver reportes."}
    return None


# ── Reporte de ventas ─────────────────────────────────────────────────────────

def reporte_ventas(fecha_inicio: str, fecha_fin: str) -> dict:
    """
    Retorna ventas totales, promedio diario, mejor día y distribución
    por método de pago para el rango de fechas indicado.
    """
    err = _check_permiso()
    if err:
        return err

    conn = get_connection()

    resumen = conn.execute("""
        SELECT
            COUNT(*)            AS total_transacciones,
            SUM(total)          AS ingresos_brutos,
            AVG(total)          AS ticket_promedio,
            MIN(total)          AS venta_minima,
            MAX(total)          AS venta_maxima
        FROM ventas
        WHERE date(fecha) BETWEEN ? AND ?
    """, (fecha_inicio, fecha_fin)).fetchone()

    por_dia = conn.execute("""
        SELECT date(fecha) AS dia, COUNT(*) AS n, ROUND(SUM(total),2) AS total
        FROM ventas
        WHERE date(fecha) BETWEEN ? AND ?
        GROUP BY dia
        ORDER BY dia
    """, (fecha_inicio, fecha_fin)).fetchall()

    por_metodo = conn.execute("""
        SELECT metodo_pago, COUNT(*) AS n, ROUND(SUM(total),2) AS total
        FROM ventas
        WHERE date(fecha) BETWEEN ? AND ?
        GROUP BY metodo_pago
    """, (fecha_inicio, fecha_fin)).fetchall()

    mejor_dia = max(por_dia, key=lambda r: r["total"], default=None)

    conn.close()
    return {
        "ok": True,
        "periodo": {"inicio": fecha_inicio, "fin": fecha_fin},
        "resumen": {
            "total_transacciones": resumen["total_transacciones"] or 0,
            "ingresos_brutos": round(resumen["ingresos_brutos"] or 0, 2),
            "ticket_promedio": round(resumen["ticket_promedio"] or 0, 2),
            "venta_minima": round(resumen["venta_minima"] or 0, 2),
            "venta_maxima": round(resumen["venta_maxima"] or 0, 2),
        },
        "por_dia": [dict(r) for r in por_dia],
        "por_metodo_pago": [dict(r) for r in por_metodo],
        "mejor_dia": dict(mejor_dia) if mejor_dia else None,
    }


# ── Reporte de productos más vendidos ────────────────────────────────────────

def reporte_top_productos(fecha_inicio: str, fecha_fin: str, limite: int = 10) -> dict:
    err = _check_permiso()
    if err:
        return err

    conn = get_connection()
    rows = conn.execute("""
        SELECT
            p.nombre,
            p.codigo,
            SUM(d.cantidad)   AS unidades_vendidas,
            ROUND(SUM(d.subtotal), 2) AS ingresos
        FROM detalle_ventas d
        JOIN ventas v ON d.venta_id = v.id
        JOIN productos p ON d.producto_id = p.id
        WHERE date(v.fecha) BETWEEN ? AND ?
        GROUP BY p.id
        ORDER BY unidades_vendidas DESC
        LIMIT ?
    """, (fecha_inicio, fecha_fin, limite)).fetchall()
    conn.close()
    return {"ok": True, "top_productos": [dict(r) for r in rows]}


# ── Reporte de inventario ─────────────────────────────────────────────────────

def reporte_inventario() -> dict:
    err = _check_permiso()
    if err:
        return err

    conn = get_connection()

    total_productos = conn.execute(
        "SELECT COUNT(*) AS n FROM productos WHERE activo = 1"
    ).fetchone()["n"]

    valor_total = conn.execute(
        "SELECT ROUND(SUM(precio * stock),2) AS v FROM productos WHERE activo = 1"
    ).fetchone()["v"] or 0.0

    bajo_stock = conn.execute("""
        SELECT nombre, codigo, stock, stock_minimo
        FROM productos
        WHERE activo = 1 AND stock <= stock_minimo
        ORDER BY stock ASC
    """).fetchall()

    sin_stock = conn.execute(
        "SELECT nombre, codigo FROM productos WHERE activo = 1 AND stock = 0"
    ).fetchall()

    por_categoria = conn.execute("""
        SELECT c.nombre AS categoria, COUNT(*) AS productos, SUM(p.stock) AS unidades
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id
        WHERE p.activo = 1
        GROUP BY c.nombre
        ORDER BY unidades DESC
    """).fetchall()

    conn.close()
    return {
        "ok": True,
        "total_productos_activos": total_productos,
        "valor_inventario_bs": valor_total,
        "bajo_stock": [dict(r) for r in bajo_stock],
        "sin_stock": [dict(r) for r in sin_stock],
        "por_categoria": [dict(r) for r in por_categoria],
    }


# ── Reporte de rendimiento por cajero ────────────────────────────────────────

def reporte_cajeros(fecha_inicio: str, fecha_fin: str) -> dict:
    err = _check_permiso()
    if err:
        return err

    conn = get_connection()
    rows = conn.execute("""
        SELECT
            u.nombre AS cajero,
            u.usuario,
            COUNT(v.id)            AS ventas_realizadas,
            ROUND(SUM(v.total), 2) AS total_facturado,
            ROUND(AVG(v.total), 2) AS ticket_promedio
        FROM ventas v
        JOIN usuarios u ON v.usuario_id = u.id
        WHERE date(v.fecha) BETWEEN ? AND ?
        GROUP BY u.id
        ORDER BY total_facturado DESC
    """, (fecha_inicio, fecha_fin)).fetchall()
    conn.close()
    return {"ok": True, "rendimiento_cajeros": [dict(r) for r in rows]}


#  Dashboard ejecutivo 

def dashboard_hoy() -> dict:
    """Resumen ejecutivo del día actual para la pantalla principal."""
    err = _check_permiso()
    if err:
        return err

    conn = get_connection()
    hoy = conn.execute("SELECT date('now','localtime')").fetchone()[0]

    ventas_hoy = conn.execute(
        "SELECT COUNT(*) AS n, ROUND(SUM(total),2) AS t FROM ventas WHERE date(fecha) = ?", (hoy,)
    ).fetchone()

    productos_bajo_stock = conn.execute(
        "SELECT COUNT(*) AS n FROM productos WHERE activo=1 AND stock <= stock_minimo"
    ).fetchone()["n"]

    ultima_venta = conn.execute(
        "SELECT fecha, total FROM ventas ORDER BY fecha DESC LIMIT 1"
    ).fetchone()

    conn.close()
    return {
        "ok": True,
        "fecha": hoy,
        "ventas_hoy": ventas_hoy["n"] or 0,
        "ingresos_hoy": ventas_hoy["t"] or 0.0,
        "alertas_stock": productos_bajo_stock,
        "ultima_venta": dict(ultima_venta) if ultima_venta else None,
    }