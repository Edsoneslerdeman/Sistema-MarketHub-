"""
MarketHub - Módulo de Pagos (RF-04)
Procesa pagos en efectivo, QR (simulado) y tarjeta.
Calcula cambio y registra cada transacción.
"""
from __future__ import annotations
from typing import Optional
from modules.database import get_connection


METODOS_VALIDOS = ("efectivo", "qr", "tarjeta")


def procesar_pago(venta_id: int, metodo: str, monto: float,
                  referencia: Optional[str] = None) -> dict:
    """
    Registra el pago de una venta.
    - efectivo : monto = dinero entregado por el cliente
    - qr       : monto = total exacto, referencia = código de transacción
    - tarjeta  : monto = total exacto, referencia = últimos 4 dígitos
    """
    if metodo not in METODOS_VALIDOS:
        return {"ok": False, "error": f"Método inválido. Use: {METODOS_VALIDOS}"}

    conn = get_connection()
    venta = conn.execute(
        "SELECT total FROM ventas WHERE id = ?", (venta_id,)
    ).fetchone()

    if venta is None:
        conn.close()
        return {"ok": False, "error": "Venta no encontrada."}

    total = venta["total"]

    if monto < total:
        conn.close()
        return {
            "ok": False,
            "error": f"Monto insuficiente. Total: Bs.{total:.2f}, recibido: Bs.{monto:.2f}"
        }

    cambio = round(monto - total, 2) if metodo == "efectivo" else 0.0

    # Registrar en tabla pagos
    conn.execute(
        """INSERT INTO pagos (venta_id, metodo, monto, referencia, estado)
           VALUES (?, ?, ?, ?, 'aprobado')""",
        (venta_id, metodo, monto, referencia)
    )
    # Actualizar cambio en venta
    conn.execute(
        "UPDATE ventas SET monto_pago = ?, cambio = ? WHERE id = ?",
        (monto, cambio, venta_id)
    )
    conn.commit()
    conn.close()

    resultado = {
        "ok": True,
        "venta_id": venta_id,
        "metodo": metodo,
        "total": total,
        "monto_recibido": monto,
        "cambio": cambio,
        "referencia": referencia,
    }

    # Mensaje según método
    if metodo == "efectivo":
        resultado["mensaje"] = f"Pago en efectivo. Cambio: Bs.{cambio:.2f}"
    elif metodo == "qr":
        resultado["mensaje"] = f"Pago QR aprobado. Ref: {referencia or 'N/A'}"
    elif metodo == "tarjeta":
        resultado["mensaje"] = f"Tarjeta aprobada. Ref: {referencia or 'N/A'}"

    return resultado


def obtener_pago(venta_id: int) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM pagos WHERE venta_id = ? ORDER BY fecha DESC LIMIT 1", (venta_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def listar_pagos(fecha_inicio: Optional[str] = None,
                 fecha_fin: Optional[str] = None) -> list[dict]:
    conn = get_connection()
    query = "SELECT * FROM pagos WHERE 1=1"
    params = []
    if fecha_inicio:
        query += " AND fecha >= ?"
        params.append(fecha_inicio)
    if fecha_fin:
        query += " AND fecha <= ?"
        params.append(fecha_fin)
    query += " ORDER BY fecha DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def resumen_pagos_dia(fecha: Optional[str] = None) -> dict:
    """Totales por método de pago para un día dado (por defecto hoy)."""
    conn = get_connection()
    if fecha is None:
        fecha = conn.execute("SELECT date('now','localtime')").fetchone()[0]

    rows = conn.execute("""
        SELECT metodo, COUNT(*) as cantidad, SUM(monto) as total
        FROM pagos
        WHERE date(fecha) = ? AND estado = 'aprobado'
        GROUP BY metodo
    """, (fecha,)).fetchall()
    conn.close()

    resumen = {m: {"cantidad": 0, "total": 0.0} for m in METODOS_VALIDOS}
    for r in rows:
        resumen[r["metodo"]] = {
            "cantidad": r["cantidad"],
            "total": round(r["total"], 2)
        }
    total_general = sum(v["total"] for v in resumen.values())
    return {"fecha": fecha, "por_metodo": resumen, "total_general": round(total_general, 2)}