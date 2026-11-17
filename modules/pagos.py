"""
MarketHub - Módulo de Pagos
Gestiona validación de pagos (efectivo, QR y tarjeta), cálculo riguroso de cambio
y registro contable sin distorsión de ingresos.
"""
from __future__ import annotations
import sqlite3
from typing import Optional
from modules.database import get_connection

METODOS_VALIDOS = ("efectivo", "qr", "tarjeta")


def calcular_cambio(total: float, monto_recibido: float, metodo: str) -> float:
    """Calcula el cambio exacto para efectivo, o 0.0 para medios electrónicos."""
    if metodo != "efectivo":
        return 0.0
    return max(0.0, round(monto_recibido - total, 2))


def registrar_pago_transaccion(conn: sqlite3.Connection, venta_id: int, metodo: str,
                               total: float, monto_recibido: float,
                               referencia: Optional[str] = None) -> dict:
    """
    Registra el pago DENTRO de una transacción SQLite existente (garantiza atomicidad ACID).
    - 'monto' almacena el valor neto cobrado (total).
    - 'monto_recibido' almacena el dinero entregado por el cliente.
    - 'cambio' almacena la diferencia devuelta.
    """
    if metodo not in METODOS_VALIDOS:
        return {"ok": False, "error": f"Método inválido '{metodo}'. Opciones: {METODOS_VALIDOS}"}

    total = round(float(total), 2)
    monto_recibido = round(float(monto_recibido), 2)

    # Validaciones según método
    if metodo == "efectivo":
        if monto_recibido < total:
            return {
                "ok": False,
                "error": f"Monto insuficiente. Total a pagar: Bs. {total:.2f}, Entregado: Bs. {monto_recibido:.2f}"
            }
        cambio = round(monto_recibido - total, 2)
    else:
        # En QR y Tarjeta el cobro es por el monto exacto
        monto_recibido = total
        cambio = 0.0

    # 1. Insertar en tabla pagos
    cursor = conn.execute(
        """INSERT INTO pagos (venta_id, metodo, monto, monto_recibido, cambio, referencia, estado)
           VALUES (?, ?, ?, ?, ?, ?, 'aprobado')""",
        (venta_id, metodo, total, monto_recibido, cambio, referencia)
    )
    pago_id = cursor.lastrowid

    # 2. Actualizar monto_pago y cambio en la cabecera de venta
    conn.execute(
        """UPDATE ventas
           SET monto_pago = ?, cambio = ?
           WHERE id = ?""",
        (monto_recibido, cambio, venta_id)
    )

    msg = f"Pago en efectivo completado. Cambio a entregar: Bs. {cambio:.2f}" if metodo == "efectivo" \
        else f"Pago con {metodo.upper()} aprobado exitosamente."

    return {
        "ok": True,
        "pago_id": pago_id,
        "venta_id": venta_id,
        "metodo": metodo,
        "total": total,
        "monto_recibido": monto_recibido,
        "cambio": cambio,
        "referencia": referencia,
        "mensaje": msg
    }


def procesar_pago(venta_id: int, metodo: str, monto_recibido: float,
                  referencia: Optional[str] = None) -> dict:
    """Procesa el pago de forma independiente abriendo su propia conexión (para compatibilidad)."""
    conn = get_connection()
    try:
        venta = conn.execute("SELECT total FROM ventas WHERE id = ?", (venta_id,)).fetchone()
        if not venta:
            return {"ok": False, "error": "Venta no encontrada."}

        res = registrar_pago_transaccion(conn, venta_id, metodo, venta["total"], monto_recibido, referencia)
        if res["ok"]:
            conn.commit()
        else:
            conn.rollback()
        return res
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def obtener_pago(venta_id: int) -> Optional[dict]:
    """Retorna el registro de pago asociado a una venta."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM pagos WHERE venta_id = ? ORDER BY id DESC LIMIT 1", (venta_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def listar_pagos(fecha_inicio: Optional[str] = None, fecha_fin: Optional[str] = None,
                 limite: int = 100) -> list[dict]:
    """Lista pagos con información cruzada de la venta."""
    conn = get_connection()
    query = """
        SELECT pg.id, pg.venta_id, pg.metodo, pg.monto, pg.monto_recibido, pg.cambio,
               pg.referencia, pg.estado, pg.fecha,
               v.total AS venta_total, u.nombre AS cajero
        FROM pagos pg
        JOIN ventas v ON pg.venta_id = v.id
        JOIN usuarios u ON v.usuario_id = u.id
        WHERE 1=1
    """
    params = []
    if fecha_inicio:
        query += " AND date(pg.fecha) >= ?"
        params.append(fecha_inicio)
    if fecha_fin:
        query += " AND date(pg.fecha) <= ?"
        params.append(fecha_fin)

    query += " ORDER BY pg.fecha DESC, pg.id DESC LIMIT ?"
    params.append(limite)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def resumen_pagos_dia(fecha: Optional[str] = None) -> dict:
    """
    Retorna el resumen de ingresos reales por método de pago.
    Utiliza el monto neto de la venta (no el dinero entregado por el cliente).
    """
    conn = get_connection()
    if fecha is None:
        fecha = conn.execute("SELECT date('now', 'localtime')").fetchone()[0]

    rows = conn.execute("""
        SELECT metodo, COUNT(*) AS cantidad, COALESCE(SUM(monto), 0) AS total_recaudado
        FROM pagos
        WHERE date(fecha) = ? AND estado = 'aprobado'
        GROUP BY metodo
    """, (fecha,)).fetchall()
    conn.close()

    resumen = {m: {"cantidad": 0, "total": 0.0} for m in METODOS_VALIDOS}
    for r in rows:
        metodo = r["metodo"]
        if metodo in resumen:
            resumen[metodo] = {
                "cantidad": r["cantidad"],
                "total": round(float(r["total_recaudado"]), 2)
            }

    total_general = sum(v["total"] for v in resumen.values())
    return {
        "fecha": fecha,
        "por_metodo": resumen,
        "total_general": round(total_general, 2)
    }
