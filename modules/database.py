"""
MarketHub - Módulo de Base de Datos
Gestiona la conexión SQLite y el esquema relacional del sistema.
"""
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "markethub.db")


def get_connection(db_file: str = None) -> sqlite3.Connection:
    """Retorna una conexión a SQLite con foreign keys y row_factory activados."""
    target_path = db_file or DB_PATH
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def inicializar_bd(db_file: str = None) -> None:
    """Crea todas las tablas del sistema con restricciones de integridad."""
    conn = get_connection(db_file)
    cursor = conn.cursor()

    # 1. Tabla: usuarios (Soporta admin, cajero y almacenero)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre      TEXT    NOT NULL,
            usuario     TEXT    NOT NULL UNIQUE,
            password    TEXT    NOT NULL,
            rol         TEXT    NOT NULL CHECK(rol IN ('admin', 'cajero', 'almacenero')),
            activo      INTEGER NOT NULL DEFAULT 1,
            creado_en   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # 2. Tabla: categorias
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categorias (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre  TEXT    NOT NULL UNIQUE
        )
    """)

    # 3. Tabla: clientes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            razon_social TEXT    NOT NULL,
            nit_ci       TEXT    NOT NULL UNIQUE,
            telefono     TEXT,
            direccion    TEXT,
            creado_en    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # 4. Tabla: productos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre       TEXT    NOT NULL,
            codigo       TEXT    NOT NULL UNIQUE,
            precio       REAL    NOT NULL CHECK(precio >= 0),
            stock        INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
            stock_minimo INTEGER NOT NULL DEFAULT 5,
            categoria_id INTEGER REFERENCES categorias(id),
            activo       INTEGER NOT NULL DEFAULT 1,
            creado_en    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # 5. Tabla: ventas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id   INTEGER NOT NULL REFERENCES usuarios(id),
            cliente_id   INTEGER REFERENCES clientes(id),
            total        REAL    NOT NULL CHECK(total >= 0),
            metodo_pago  TEXT    NOT NULL CHECK(metodo_pago IN ('efectivo', 'qr', 'tarjeta')),
            monto_pago   REAL    NOT NULL DEFAULT 0,
            cambio       REAL    NOT NULL DEFAULT 0,
            estado       TEXT    NOT NULL DEFAULT 'completada' CHECK(estado IN ('completada', 'anulada')),
            notas        TEXT,
            fecha        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # 6. Tabla: detalle_ventas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detalle_ventas (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_id    INTEGER NOT NULL REFERENCES ventas(id) ON DELETE CASCADE,
            producto_id INTEGER NOT NULL REFERENCES productos(id),
            cantidad    INTEGER NOT NULL CHECK(cantidad > 0),
            precio_unit REAL    NOT NULL CHECK(precio_unit >= 0),
            subtotal    REAL    NOT NULL CHECK(subtotal >= 0)
        )
    """)

    # 7. Tabla: movimientos_inventario (Kardex)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimientos_inventario (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER NOT NULL REFERENCES productos(id),
            tipo        TEXT    NOT NULL CHECK(tipo IN ('entrada', 'salida', 'ajuste')),
            cantidad    INTEGER NOT NULL,
            motivo      TEXT,
            usuario_id  INTEGER REFERENCES usuarios(id),
            fecha       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # 8. Tabla: pagos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pagos (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_id       INTEGER NOT NULL REFERENCES ventas(id) ON DELETE CASCADE,
            metodo         TEXT    NOT NULL CHECK(metodo IN ('efectivo', 'qr', 'tarjeta')),
            monto          REAL    NOT NULL CHECK(monto >= 0),
            monto_recibido REAL    NOT NULL CHECK(monto_recibido >= 0),
            cambio         REAL    NOT NULL DEFAULT 0 CHECK(cambio >= 0),
            referencia     TEXT,
            estado         TEXT    NOT NULL DEFAULT 'aprobado',
            fecha          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # 9. Tabla: arqueos_caja (Control de caja)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS arqueos_caja (
            id                     INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id             INTEGER NOT NULL REFERENCES usuarios(id),
            fecha_apertura         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
            saldo_inicial          REAL    NOT NULL DEFAULT 0,
            fecha_cierre           TEXT,
            total_ventas_sistema   REAL    DEFAULT 0,
            total_efectivo_sistema REAL    DEFAULT 0,
            total_efectivo_real    REAL,
            diferencia             REAL    DEFAULT 0,
            estado                 TEXT    NOT NULL DEFAULT 'abierta' CHECK(estado IN ('abierta', 'cerrada')),
            observaciones          TEXT
        )
    """)

    # 10. Tabla: ventas_en_espera (Parked carts)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ventas_en_espera (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id  INTEGER NOT NULL REFERENCES usuarios(id),
            etiqueta    TEXT    NOT NULL,
            datos_json  TEXT    NOT NULL,
            total       REAL    NOT NULL DEFAULT 0,
            fecha       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    inicializar_bd()
    print(f"Base de datos inicializada correctamente en: {DB_PATH}")
