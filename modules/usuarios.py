"""
MarketHub - Módulo de Usuarios (RF-05, RF-06)
Gestiona registro, autenticación y control de acceso por roles.
"""
from __future__ import annotations
import bcrypt
from dataclasses import dataclass, field
from typing import Optional
from modules.database import get_connection


# Roles y permisos 
PERMISOS = {
    "admin":  {"ventas", "inventario", "pagos", "usuarios", "reportes"},
    "cajero": {"ventas", "pagos"},
}


@dataclass
class Usuario:
    id: int
    nombre: str
    usuario: str
    rol: str
    activo: bool


# Sesión activa (simple, sin tokens) 
_sesion_actual: Optional[Usuario] = None


def sesion() -> Optional[Usuario]:
    return _sesion_actual


def requiere_permiso(modulo: str) -> bool:
    """Verifica si el usuario actual tiene permiso para el módulo."""
    if _sesion_actual is None:
        return False
    return modulo in PERMISOS.get(_sesion_actual.rol, set())


#  Operaciones CRUD 
def registrar_usuario(nombre: str, usuario: str, password: str, rol: str) -> dict:
    """Registra un nuevo usuario con contraseña hasheada."""
    if rol not in PERMISOS:
        return {"ok": False, "error": f"Rol inválido. Opciones: {list(PERMISOS)}"}

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    try:
        conn = get_connection()
        conn.execute(
            "INSERT INTO usuarios (nombre, usuario, password, rol) VALUES (?, ?, ?, ?)",
            (nombre, usuario, hashed, rol)
        )
        conn.commit()
        return {"ok": True, "mensaje": f"Usuario '{usuario}' registrado con rol '{rol}'."}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def iniciar_sesion(usuario: str, password: str) -> dict:
    """Autentica al usuario y abre la sesión activa."""
    global _sesion_actual
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM usuarios WHERE usuario = ? AND activo = 1", (usuario,)
    ).fetchone()
    conn.close()

    if row is None:
        return {"ok": False, "error": "Usuario no encontrado o inactivo."}

    if not bcrypt.checkpw(password.encode(), row["password"].encode()):
        return {"ok": False, "error": "Contraseña incorrecta."}

    _sesion_actual = Usuario(
        id=row["id"], nombre=row["nombre"],
        usuario=row["usuario"], rol=row["rol"], activo=bool(row["activo"])
    )
    return {"ok": True, "usuario": _sesion_actual}


def cerrar_sesion() -> None:
    global _sesion_actual
    _sesion_actual = None


def listar_usuarios() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, nombre, usuario, rol, activo, creado_en FROM usuarios ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def cambiar_estado_usuario(usuario_id: int, activo: bool) -> dict:
    conn = get_connection()
    conn.execute("UPDATE usuarios SET activo = ? WHERE id = ?", (int(activo), usuario_id))
    conn.commit()
    conn.close()
    estado = "activado" if activo else "desactivado"
    return {"ok": True, "mensaje": f"Usuario {usuario_id} {estado}."}