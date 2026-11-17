"""
MarketHub - Módulo de Reportes Analíticos
Provee métricas de negocio, estadísticas de ventas, control de inventario y exportación a CSV.
"""
from __future__ import annotations
import csv
import io
from typing import Optional
from modules.database import get_connection


def reporte_ventas(fecha_inicio: str, fecha_fin: str) -> dict:
    """
    Retorna métricas consolidadas de ventas para un período dado.
    Calcula transacciones, ingresos netos, ticket promedio y desglose diario.
    """
    conn = get_connection()

    resumen = conn.execute("""
        SELECT
            COUNT(*)                        AS total_transacciones,
            COALESCE(SUM(total), 0)         AS ingresos_brutos,
            COALESCE(AVG(total), 0)         AS ticket_promedio,
            COALESCE(MIN(total), 0)         AS venta_minima,
            COALESCE(MAX(total), 0)         AS venta_maxima
        FROM ventas
        WHERE date(fecha) BETWEEN ? AND ? AND estado = 'completada'
    """, (fecha_inicio, fecha_fin)).fetchone()

    por_dia = conn.execute("""
        SELECT date(fecha) AS dia, COUNT(*) AS n, ROUND(SUM(total), 2) AS total
        FROM ventas
        WHERE date(fecha) BETWEEN ? AND ? AND estado = 'completada'
        GROUP BY dia
        ORDER BY dia ASC
    """, (fecha_inicio, fecha_fin)).fetchall()

    por_metodo = conn.execute("""
        SELECT metodo_pago, COUNT(*) AS n, ROUND(SUM(total), 2) AS total
        FROM ventas
        WHERE date(fecha) BETWEEN ? AND ? AND estado = 'completada'
        GROUP BY metodo_pago
    """, (fecha_inicio, fecha_fin)).fetchall()

    dias_list = [dict(r) for r in por_dia]
    mejor_dia = max(dias_list, key=lambda r: r["total"], default=None)

    conn.close()
    return {
        "ok": True,
        "periodo": {"inicio": fecha_inicio, "fin": fecha_fin},
        "resumen": {
            "total_transacciones": resumen["total_transacciones"] or 0,
            "ingresos_brutos": round(float(resumen["ingresos_brutos"] or 0), 2),
            "ticket_promedio": round(float(resumen["ticket_promedio"] or 0), 2),
            "venta_minima": round(float(resumen["venta_minima"] or 0), 2),
            "venta_maxima": round(float(resumen["venta_maxima"] or 0), 2),
        },
        "por_dia": dias_list,
        "por_metodo_pago": [dict(r) for r in por_metodo],
        "mejor_dia": mejor_dia,
    }


def reporte_top_productos(fecha_inicio: str, fecha_fin: str, limite: int = 10) -> dict:
    """Retorna los productos más vendidos en unidades e ingresos dentro del período."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT
            p.nombre,
            p.codigo,
            COALESCE(SUM(d.cantidad), 0)       AS unidades_vendidas,
            ROUND(COALESCE(SUM(d.subtotal), 0), 2) AS ingresos
        FROM detalle_ventas d
        JOIN ventas v ON d.venta_id = v.id
        JOIN productos p ON d.producto_id = p.id
        WHERE date(v.fecha) BETWEEN ? AND ? AND v.estado = 'completada'
        GROUP BY p.id
        ORDER BY unidades_vendidas DESC
        LIMIT ?
    """, (fecha_inicio, fecha_fin, limite)).fetchall()
    conn.close()
    return {"ok": True, "top_productos": [dict(r) for r in rows]}


def reporte_inventario() -> dict:
    """Analiza la composición del stock, valuación en dinero y alertas de reposición."""
    conn = get_connection()

    total_productos = conn.execute(
        "SELECT COUNT(*) AS n FROM productos WHERE activo = 1"
    ).fetchone()["n"]

    valor_total = conn.execute(
        "SELECT COALESCE(ROUND(SUM(precio * stock), 2), 0) AS v FROM productos WHERE activo = 1"
    ).fetchone()["v"] or 0.0

    bajo_stock = conn.execute("""
        SELECT nombre, codigo, stock, stock_minimo, precio
        FROM productos
        WHERE activo = 1 AND stock <= stock_minimo
        ORDER BY stock ASC
    """).fetchall()

    sin_stock = conn.execute("""
        SELECT nombre, codigo, stock_minimo, precio
        FROM productos
        WHERE activo = 1 AND stock = 0
    """).fetchall()

    por_categoria = conn.execute("""
        SELECT COALESCE(c.nombre, 'Sin Categoría') AS categoria,
               COUNT(p.id) AS productos,
               COALESCE(SUM(p.stock), 0) AS unidades,
               COALESCE(ROUND(SUM(p.precio * p.stock), 2), 0) AS valor
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id
        WHERE p.activo = 1
        GROUP BY c.id
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


def reporte_cajeros(fecha_inicio: str, fecha_fin: str) -> dict:
    """Rendimiento y volumen facturado por cada cajero o usuario."""
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
        WHERE date(v.fecha) BETWEEN ? AND ? AND v.estado = 'completada'
        GROUP BY u.id
        ORDER BY total_facturado DESC
    """, (fecha_inicio, fecha_fin)).fetchall()
    conn.close()
    return {"ok": True, "rendimiento_cajeros": [dict(r) for r in rows]}


def dashboard_hoy() -> dict:
    """Métricas operativas del día actual para la pantalla principal."""
    conn = get_connection()
    hoy = conn.execute("SELECT date('now', 'localtime')").fetchone()[0]

    ventas_hoy = conn.execute("""
        SELECT COUNT(*) AS n, COALESCE(ROUND(SUM(total), 2), 0) AS t
        FROM ventas
        WHERE date(fecha) = ? AND estado = 'completada'
    """, (hoy,)).fetchone()

    productos_bajo_stock = conn.execute("""
        SELECT COUNT(*) AS n FROM productos WHERE activo = 1 AND stock <= stock_minimo
    """).fetchone()["n"]

    ultima_venta = conn.execute("""
        SELECT v.id, v.fecha, v.total, u.nombre AS cajero
        FROM ventas v
        JOIN usuarios u ON v.usuario_id = u.id
        WHERE v.estado = 'completada'
        ORDER BY v.fecha DESC, v.id DESC LIMIT 1
    """).fetchone()

    conn.close()
    return {
        "ok": True,
        "fecha": hoy,
        "ventas_hoy": ventas_hoy["n"] or 0,
        "ingresos_hoy": float(ventas_hoy["t"] or 0.0),
        "alertas_stock": productos_bajo_stock,
        "ultima_venta": dict(ultima_venta) if ultima_venta else None,
    }


# ==========================================
# Exportación de Datos a CSV
# ==========================================

def exportar_ventas_csv(fecha_inicio: str, fecha_fin: str) -> str:
    """Genera un archivo CSV con el historial de ventas del período."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT v.id, v.fecha, u.nombre AS cajero,
               COALESCE(c.razon_social, 'Cliente General') AS cliente,
               v.metodo_pago, v.total, v.monto_pago AS monto_recibido,
               v.cambio, v.estado
        FROM ventas v
        JOIN usuarios u ON v.usuario_id = u.id
        LEFT JOIN clientes c ON v.cliente_id = c.id
        WHERE date(v.fecha) BETWEEN ? AND ?
        ORDER BY v.fecha DESC
    """, (fecha_inicio, fecha_fin)).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Venta ID", "Fecha y Hora", "Cajero", "Cliente",
        "Metodo Pago", "Total (Bs)", "Monto Recibido (Bs)", "Cambio (Bs)", "Estado"
    ])
    for r in rows:
        writer.writerow([
            r["id"], r["fecha"], r["cajero"], r["cliente"],
            r["metodo_pago"].upper(), f"{r['total']:.2f}",
            f"{r['monto_recibido']:.2f}", f"{r['cambio']:.2f}", r["estado"].upper()
        ])

    return output.getvalue()


def exportar_inventario_csv() -> str:
    """Genera un archivo CSV con el catálogo e inventario valorizado."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT p.id, p.codigo, p.nombre, COALESCE(c.nombre, 'Sin Categoria') AS categoria,
               p.precio, p.stock, p.stock_minimo,
               ROUND(p.precio * p.stock, 2) AS valor_stock,
               CASE WHEN p.stock <= p.stock_minimo THEN 'SI' ELSE 'NO' END AS bajo_stock
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id
        WHERE p.activo = 1
        ORDER BY p.nombre ASC
    """).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Codigo", "Producto", "Categoria",
        "Precio (Bs)", "Stock Actual", "Stock Minimo", "Valorizacion (Bs)", "Alerta Reposicion"
    ])
    for r in rows:
        writer.writerow([
            r["id"], r["codigo"], r["nombre"], r["categoria"],
            f"{r['precio']:.2f}", r["stock"], r["stock_minimo"],
            f"{r['valor_stock']:.2f}", r["bajo_stock"]
        ])

    return output.getvalue()
