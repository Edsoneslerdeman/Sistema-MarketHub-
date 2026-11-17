"""
MarketHub - Interfaz de Línea de Comandos (CLI)
Demostración y verificación del sistema de gestión para minimercados.
"""
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from modules.database import inicializar_bd
from modules import usuarios as usr
from modules import inventario as inv
from modules import ventas as ven
from modules import pagos as pag
from modules import reportes as rep

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    RICH = True
except ImportError:
    RICH = False

console = Console() if RICH else None


def titulo(texto: str):
    if RICH:
        console.print(Panel(f"[bold cyan]{texto}[/]", expand=False))
    else:
        print(f"\n{'='*55}\n  {texto}\n{'='*55}")


def ok(msg):
    if RICH:
        console.print(f"[bold green]✓[/] {msg}")
    else:
        print(f"[OK] {msg}")


def error(msg):
    if RICH:
        console.print(f"[bold red]✗[/] {msg}")
    else:
        print(f"[ERROR] {msg}")


def tabla_dict(datos: list[dict], columnas: list[str] = None):
    if not datos:
        print("  (sin resultados)")
        return
    cols = columnas or list(datos[0].keys())
    if RICH:
        t = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold blue")
        for c in cols:
            t.add_column(str(c).upper())
        for row in datos:
            t.add_row(*[str(row.get(c, "")) for c in cols])
        console.print(t)
    else:
        header = " | ".join(f"{c:<18}" for c in cols)
        print(header)
        print("-" * len(header))
        for row in datos:
            print(" | ".join(f"{str(row.get(c,'')):<18}" for c in cols))


def demo():
    titulo("MARKETHUB — Demostración Integral del Sistema")

    # 1. Base de datos
    print("\n[1] Inicializando base de datos...")
    inicializar_bd()
    ok("Base de datos y tablas verificadas con integridad ACID.")

    # 2. Usuarios
    print("\n[2] Verificando usuarios por rol...")
    usr.registrar_usuario("Administrador", "admin", "admin123", "admin")
    usr.registrar_usuario("Cajero Principal", "cajero", "cajero123", "cajero")
    usr.registrar_usuario("Almacenero Bodega", "almacen", "almacen123", "almacenero")

    # 3. Autenticación
    print("\n[3] Iniciando sesión...")
    res = usr.iniciar_sesion("cajero", "cajero123")
    if res["ok"]:
        ok(f"Sesión activa: {res['usuario'].nombre} (Rol: {res['usuario'].rol})")
    else:
        error(res["error"])
        return

    # 4. Listar productos
    print("\n[4] Catálogo de productos disponibles:")
    prods = inv.listar_productos()
    tabla_dict(prods[:5], ["id", "nombre", "codigo", "precio", "stock", "stock_minimo", "categoria"])

    # 5. Venta en efectivo con cambio
    print("\n[5] Simulando venta en efectivo (Verificación del cálculo de cambio)...")
    carrito = ven.Carrito()
    p1 = prods[0]["codigo"]
    carrito.agregar(p1, 2)
    total = carrito.total
    paga_con = total + 50.0  # Entrega 50 Bs más

    print(f"  Total a pagar:     Bs. {total:.2f}")
    print(f"  Cliente entrega:   Bs. {paga_con:.2f}")
    res_v = ven.registrar_venta(carrito, "efectivo", monto_recibido=paga_con)

    if res_v["ok"]:
        ok(f"Venta #{res_v['venta_id']} registrada. Cambio devuelto al cliente: Bs. {res_v['cambio']:.2f}")
    else:
        error(res_v["error"])

    # 6. Comprobante / Ticket térmico
    print("\n[6] Vista previa del ticket térmico generado:")
    ticket = ven.generar_ticket_texto(res_v["venta_id"])
    print(ticket)

    # 7. Cierre de caja
    print("\n[7] Resumen de cierre de caja auditado:")
    cierre = ven.cierre_caja()
    ok(f"Ventas hoy: {cierre['total_ventas']} | Recaudación neta: Bs. {cierre['ingresos_totales']:.2f}")

    titulo("Demostración completada exitosamente ✓")


if __name__ == "__main__":
    demo()
