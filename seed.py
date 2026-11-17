"""
MarketHub - Script de Inicialización y Datos Iniciales (Seeder)
Crea las tablas y carga datos de prueba iniciales de forma segura.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.database import inicializar_bd, get_connection
from modules import usuarios as usr
from modules import inventario as inv


def poblar_datos(reiniciar: bool = False):
    if reiniciar:
        print("[*] Reiniciando base de datos...")
        conn = get_connection()
        for t in ["detalle_ventas", "movimientos_inventario", "pagos", "ventas",
                  "ventas_en_espera", "arqueos_caja", "productos", "categorias", "clientes", "usuarios"]:
            conn.execute(f"DROP TABLE IF EXISTS {t}")
        conn.commit()
        conn.close()

    print("[*] Verificando tablas del sistema...")
    inicializar_bd()

    # 1. Usuarios del sistema
    print("[*] Configurando usuarios por defecto...")
    usuarios_iniciales = [
        ("Administrador General", "admin", "admin123", "admin"),
        ("Cajero Principal", "cajero", "cajero123", "cajero"),
        ("Almacenero de Bodega", "almacen", "almacen123", "almacenero"),
    ]

    for nom, user, pwd, rol in usuarios_iniciales:
        res = usr.registrar_usuario(nom, user, pwd, rol)
        if res["ok"]:
            print(f"  [+] Usuario creado: {user} ({rol})")
        else:
            print(f"  [.] Usuario {user}: {res['error']}")

    # 2. Categorías
    print("[*] Configurando categorías...")
    cats = ["Abarrotes", "Lácteos y Quesos", "Bebidas y Refrescos", "Limpieza y Hogar", "Snacks y Golosinas"]
    cat_ids = {}
    for c in cats:
        res = inv.agregar_categoria(c)
        if res["ok"]:
            cat_ids[c] = res["id"]

    # Obtener IDs actuales de categorías
    for c in inv.listar_categorias():
        cat_ids[c["nombre"]] = c["id"]

    # 3. Productos iniciales
    print("[*] Verificando productos de demostración...")
    prods_existentes = inv.listar_productos()
    if not prods_existentes:
        productos_demo = [
            ("Arroz Doña María 1kg",  "ARR-001", 12.50, 80, 10, cat_ids.get("Abarrotes")),
            ("Azúcar Blanca 1kg",     "AZU-001",  8.00, 60, 10, cat_ids.get("Abarrotes")),
            ("Aceite Fino 1L",        "ACE-001", 18.00, 45,  8, cat_ids.get("Abarrotes")),
            ("Fideo Corbatita 400g",  "FID-001",  6.50, 70, 15, cat_ids.get("Abarrotes")),
            ("Leche PIL Entera 1L",   "LEC-001",  7.50, 50, 15, cat_ids.get("Lácteos y Quesos")),
            ("Queso Chaqueño 500g",   "QUE-001", 24.00, 25,  5, cat_ids.get("Lácteos y Quesos")),
            ("Yogur Frutilla 1L",     "YOG-001", 14.00, 30,  6, cat_ids.get("Lácteos y Quesos")),
            ("Agua Vital 600ml",      "AGU-001",  3.50, 100, 20, cat_ids.get("Bebidas y Refrescos")),
            ("Coca Cola 2L",          "REF-001", 12.00, 40, 10, cat_ids.get("Bebidas y Refrescos")),
            ("Jugo Del Valle 1L",     "JUG-001",  9.00, 35,  8, cat_ids.get("Bebidas y Refrescos")),
            ("Detergente Ariel 500g", "DET-001", 15.00, 30,  5, cat_ids.get("Limpieza y Hogar")),
            ("Lavavajillas Ola 500ml","LAV-001",  8.50, 28,  6, cat_ids.get("Limpieza y Hogar")),
            ("Galletas Mabel's 120g", "GAL-001",  4.50, 90, 20, cat_ids.get("Snacks y Golosinas")),
        ]

        for nom, cod, precio, stock, stock_min, cat in productos_demo:
            res = inv.agregar_producto(nom, cod, precio, stock, stock_min, cat)
            if res["ok"]:
                print(f"  [+] Producto creado: {nom} ({cod})")
    else:
        print(f"  [i] Ya existen {len(prods_existentes)} productos en el catálogo.")

    # 4. Cliente genérico
    conn = get_connection()
    cli = conn.execute("SELECT id FROM clientes WHERE nit_ci = '0'").fetchone()
    if not cli:
        conn.execute(
            "INSERT INTO clientes (razon_social, nit_ci, telefono) VALUES ('Sin Nombre / Cliente General', '0', '')"
        )
        conn.commit()
        print("  [+] Cliente General (NIT 0) registrado.")
    conn.close()

    print("\n[OK] Datos inicializados correctamente.")
    print("Usuarios disponibles:")
    print("  - Admin:       admin    / admin123")
    print("  - Cajero:      cajero   / cajero123")
    print("  - Almacenero:  almacen  / almacen123")


if __name__ == "__main__":
    reiniciar_flag = "--reset" in sys.argv
    poblar_datos(reiniciar=reiniciar_flag)
