"""
MarketHub - Módulo de Base de Datos
Gestiona la conexión SQLite y la creación de tablas del sistema.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "markethub.db")


def get_connection() -> sqlite3.Connection:
    """Retorna una conexión a la base de datos con row_factory activado."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def inicializar_bd() -> None:
    """Crea todas las tablas del sistema si no existen."""
    conn = get_connection()
    cursor = conn.cursor()

    # Tabla: usuarios 
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre      TEXT    NOT NULL,
            usuario     TEXT    NOT NULL UNIQUE,
            password    TEXT    NOT NULL,
            rol         TEXT    NOT NULL CHECK(rol IN ('admin','cajero','almacenero')),
            activo      INTEGER NOT NULL DEFAULT 1,
            creado_en   TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    #  Tabla: categorias 
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categorias (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre  TEXT    NOT NULL UNIQUE
        )
    """)

    # Tabla: productos 
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
            creado_en    TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # Tabla: ventas 
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id   INTEGER NOT NULL REFERENCES usuarios(id),
            total        REAL    NOT NULL,
            metodo_pago  TEXT    NOT NULL CHECK(metodo_pago IN ('efectivo','qr','tarjeta')),
            monto_pago   REAL,
            cambio       REAL    DEFAULT 0,
            estado       TEXT    NOT NULL DEFAULT 'completada',
            fecha        TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    #  Tabla: detalle_ventas 
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detalle_ventas (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_id    INTEGER NOT NULL REFERENCES ventas(id),
            producto_id INTEGER NOT NULL REFERENCES productos(id),
            cantidad    INTEGER NOT NULL CHECK(cantidad > 0),
            precio_unit REAL    NOT NULL,
            subtotal    REAL    NOT NULL
        )
    """)

    # Tabla: movimientos_inventario 
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimientos_inventario (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER NOT NULL REFERENCES productos(id),
            tipo        TEXT    NOT NULL CHECK(tipo IN ('entrada','salida','ajuste')),
            cantidad    INTEGER NOT NULL,
            motivo      TEXT,
            usuario_id  INTEGER REFERENCES usuarios(id),
            fecha       TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # Tabla: pagos 
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pagos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_id    INTEGER NOT NULL REFERENCES ventas(id),
            metodo      TEXT    NOT NULL,
            monto       REAL    NOT NULL,
            referencia  TEXT,
            estado      TEXT    NOT NULL DEFAULT 'aprobado',
            fecha       TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    conn.commit()
    conn.close()
    print(f"[BD] Base de datos inicializada en: {DB_PATH}")