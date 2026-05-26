"""
MarketHub - Interfaz de Línea de Comandos (CLI)
Sistema de Gestión para Minimercado MarketHub
Universidad Simón I. Patiño — Ingeniería en Sistemas
Estudiante: Edson Jesús Rodríguez Terrazas
"""
import sys
import os

# Asegurar que los módulos sean encontrados
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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


# Helpers de presentación 
def titulo(texto: str):
    if RICH:
        console.print(Panel(f"[bold cyan]{texto}[/]", expand=False))
    else:
        print(f"\n{'='*50}\n  {texto}\n{'='*50}")


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


# Demo completo del sistema 

def demo():
    titulo("MARKETHUB — Demo del Sistema de Gestión")

    # 1. Base de datos
    print("\n[1] Inicializando base de datos...")
    inicializar_bd()
    ok("Base de datos lista.")

    # 2. Usuarios
    print("\n[2] Registrando usuarios...")
    res = usr.registrar_usuario("Edson Rodríguez", "edson", "admin123", "admin")
    ok(res["mensaje"]) if res["ok"] else error(res["error"])

    res = usr.registrar_usuario("María López", "maria", "cajero123", "cajero")
    ok(res["mensaje"]) if res["ok"] else error(res["error"])

    # 3. Iniciar sesión como admin
    print("\n[3] Iniciando sesión como administrador...")
    res = usr.iniciar_sesion("edson", "admin123")
    if res["ok"]:
        ok(f"Sesión iniciada: {res['usuario'].nombre} ({res['usuario'].rol})")
    else:
        error(res["error"])
        return

    # 4. Categorías y productos
    print("\n[4] Creando categorías y productos...")
    inv.agregar_categoria("Abarrotes")
    inv.agregar_categoria("Lácteos")
    inv.agregar_categoria("Bebidas")
    inv.agregar_categoria("Limpieza")

    productos_demo = [
        ("Arroz Doña María 1kg",  "ARR-001", 12.50, 100, 10, 1),
        ("Azúcar Blanca 1kg",     "AZU-001",  8.00,  80, 10, 1),
        ("Aceite Fino 1L",        "ACE-001", 18.00,  50,  5, 1),
        ("Leche PIL 1L",          "LEC-001",  7.50,  60, 15, 2),
        ("Queso Boliviano 250g",  "QUE-001", 22.00,  30,  5, 2),
        ("Agua Vital 600ml",      "AGU-001",  3.50, 120, 20, 3),
        ("Refresco Cola 2L",      "REF-001", 10.00,  40, 10, 3),
        ("Detergente Ariel 500g", "DET-001", 15.00,  35,  5, 4),
    ]

    for nombre, cod, precio, stock, stock_min, cat in productos_demo:
        res = inv.agregar_producto(nombre, cod, precio, stock, stock_min, cat)
        ok(res["mensaje"]) if res["ok"] else error(res.get("error", ""))

    # 5. Listar productos
    print("\n[5] Productos registrados:")
    prods = inv.listar_productos()
    tabla_dict(prods, ["id", "nombre", "codigo", "precio", "stock", "stock_minimo", "categoria"])

    # 6. Primera venta — efectivo
    print("\n[6] Procesando venta en efectivo...")
    carrito = ven.Carrito()
    carrito.agregar("ARR-001", 2)
    carrito.agregar("LEC-001", 3)
    carrito.agregar("AGU-001", 4)

    print("  Carrito:")
    tabla_dict(carrito.mostrar(), ["nombre", "cantidad", "precio_unit", "subtotal"])
    print(f"  Total: Bs.{carrito.total:.2f}")

    res = ven.registrar_venta(carrito, "efectivo", monto_recibido=100.0)
    ok(res["mensaje"]) if res["ok"] else error(res["error"])

    # 7. Segunda venta — QR
    print("\n[7] Procesando venta con QR...")
    carrito.agregar("QUE-001", 1)
    carrito.agregar("DET-001", 2)
    res = ven.registrar_venta(carrito, "qr")
    ok(res["mensaje"]) if res["ok"] else error(res["error"])

    # 8. Tercera venta — tarjeta
    print("\n[8] Procesando venta con tarjeta...")
    carrito.agregar("REF-001", 2)
    carrito.agregar("ACE-001", 1)
    res = ven.registrar_venta(carrito, "tarjeta")
    ok(res["mensaje"]) if res["ok"] else error(res["error"])

    # 9. Alertas de bajo stock
    print("\n[9] Alertas de bajo stock:")
    alertas = inv.alertas_bajo_stock()
    if alertas:
        tabla_dict(alertas, ["nombre", "codigo", "stock", "stock_minimo"])
    else:
        ok("Todos los productos tienen stock suficiente.")

    # 10. Cierre de caja
    print("\n[10] Cierre de caja del día:")
    cierre = ven.cierre_caja()
    if RICH:
        console.print(Panel(
            f"Fecha: [cyan]{cierre['fecha']}[/]\n"
            f"Total ventas: [yellow]{cierre['total_ventas']}[/]\n"
            f"Ingresos: [bold green]Bs.{cierre['ingresos_totales']:.2f}[/]",
            title="Cierre de Caja", expand=False
        ))
    else:
        print(f"  Fecha:          {cierre['fecha']}")
        print(f"  Total ventas:   {cierre['total_ventas']}")
        print(f"  Ingresos:       Bs.{cierre['ingresos_totales']:.2f}")

    print("  Por método de pago:")
    tabla_dict(cierre["por_metodo_pago"], ["metodo_pago", "n", "t"])
    print("  Top productos:")
    tabla_dict(cierre["top_5_productos"], ["nombre", "uds", "ingreso"])

    # 11. Dashboard ejecutivo
    print("\n[11] Dashboard ejecutivo:")
    dash = rep.dashboard_hoy()
    if dash["ok"]:
        ok(f"Ventas hoy: {dash['ventas_hoy']} | Ingresos: Bs.{dash['ingresos_hoy']:.2f} | Alertas stock: {dash['alertas_stock']}")

    # 12. Reporte analítico
    print("\n[12] Reporte de ventas (período):")
    hoy = __import__("datetime").date.today().isoformat()
    reporte = rep.reporte_ventas(hoy, hoy)
    if reporte["ok"]:
        r = reporte["resumen"]
        ok(f"Transacciones: {r['total_transacciones']} | "
           f"Ingresos: Bs.{r['ingresos_brutos']:.2f} | "
           f"Ticket prom.: Bs.{r['ticket_promedio']:.2f}")

    # 13. Reporte inventario
    print("\n[13] Reporte de inventario:")
    ri = rep.reporte_inventario()
    if ri["ok"]:
        ok(f"Productos activos: {ri['total_productos_activos']} | "
           f"Valor inventario: Bs.{ri['valor_inventario_bs']:.2f}")

    # 14. Listar usuarios
    print("\n[14] Usuarios del sistema:")
    tabla_dict(usr.listar_usuarios(), ["id", "nombre", "usuario", "rol", "activo", "creado_en"])

    # 15. Historial de movimientos
    print("\n[15] Últimos movimientos de inventario:")
    tabla_dict(
        inv.historial_movimientos(limite=8),
        ["fecha", "producto", "tipo", "cantidad", "motivo", "operador"]
    )

    titulo("Demo completado exitosamente ✓")


if __name__ == "__main__":
    demo()