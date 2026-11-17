"""
MarketHub - Módulo de Usuarios
Gestiona autenticación con bcrypt, control de sesiones y permisos por roles.
"""
from __future__ import annotations
import sqlite3
from dataclasses import dataclass
from typing import Optional
import bcrypt

from modules.database import get_connection

# Permisos granulares por rol
PERMISOS = {
    "admin": {"ventas", "inventario", "pagos", "usuarios", "reportes", "caja"},
    "cajero": {"ventas", "pagos", "caja"},
    "almacenero": {"inventario"},
}


@dataclass
class Usuario:
    id: int
    nombre: str
    usuario: str
    rol: str
    activo: bool

    def tiene_permiso(self, modulo: str) -> bool:
        if not self.activo:
            return False
        return modulo in PERMISOS.get(self.rol, set())


# Sesión activa en memoria (para CLI y GUI)
_sesion_actual: Optional[Usuario] = None


def sesion() -> Optional[Usuario]:
    """Retorna la sesión activa."""
    return _sesion_actual


def establecer_sesion(usuario: Optional[Usuario]) -> None:
    """Establece la sesión activa en memoria."""
    global _sesion_actual
    _sesion_actual = usuario


def cerrar_sesion() -> None:
    """Limpia la sesión activa."""
    global _sesion_actual
    _sesion_actual = None


def requiere_permiso(modulo: str, usuario: Optional[Usuario] = None) -> bool:
    """Verifica si el usuario indicado (o el de sesión actual) tiene permiso."""
    usr = usuario or _sesion_actual
    if usr is None:
        return False
    return usr.tiene_permiso(modulo)


def registrar_usuario(nombre: str, usuario: str, password: str, rol: str) -> dict:
    """Registra un nuevo usuario con contraseña cifrada mediante bcrypt."""
    nombre = nombre.strip()
    usuario = usuario.strip().lower()
    rol = rol.strip().lower()

    if rol not in PERMISOS:
        return {"ok": False, "error": f"Rol inválido '{rol}'. Opciones permitidas: {list(PERMISOS.keys())}"}

    if not usuario or not password:
        return {"ok": False, "error": "El nombre de usuario y la contraseña no pueden estar vacíos."}

    if len(password) < 4:
        return {"ok": False, "error": "La contraseña debe tener al menos 4 caracteres."}

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO usuarios (nombre, usuario, password, rol) VALUES (?, ?, ?, ?)",
            (nombre, usuario, hashed, rol)
        )
        conn.commit()
        nuevo_id = cursor.lastrowid
        return {"ok": True, "id": nuevo_id, "mensaje": f"Usuario '{usuario}' registrado exitosamente."}
    except sqlite3.IntegrityError:
        return {"ok": False, "error": f"El nombre de usuario '{usuario}' ya se encuentra registrado."}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def verificar_credenciales(usuario: str, password: str) -> dict:
    """Valida usuario y contraseña sin modificar la sesión global."""
    usuario = usuario.strip().lower()
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM usuarios WHERE LOWER(usuario) = ? AND activo = 1", (usuario,)
    ).fetchone()
    conn.close()

    if row is None:
        return {"ok": False, "error": "Usuario no encontrado o inactivo."}

    try:
        password_bytes = password.encode("utf-8")
        hash_bytes = row["password"].encode("utf-8")
        if not bcrypt.checkpw(password_bytes, hash_bytes):
            return {"ok": False, "error": "Contraseña incorrecta."}
    except Exception:
        return {"ok": False, "error": "Error al validar la contraseña."}

    usr_obj = Usuario(
        id=row["id"],
        nombre=row["nombre"],
        usuario=row["usuario"],
        rol=row["rol"],
        activo=bool(row["activo"])
    )
    return {"ok": True, "usuario": usr_obj}


def iniciar_sesion(usuario: str, password: str) -> dict:
    """Autentica al usuario y establece la sesión activa."""
    resultado = verificar_credenciales(usuario, password)
    if resultado["ok"]:
        establecer_sesion(resultado["usuario"])
    return resultado


def listar_usuarios() -> list[dict]:
    """Retorna la lista de usuarios sin exponer hashes de contraseña."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, nombre, usuario, rol, activo, creado_en FROM usuarios ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def obtener_usuario_por_id(usuario_id: int) -> Optional[dict]:
    """Obtiene un usuario por su ID sin exponer contraseña."""
    conn = get_connection()
    row = conn.execute(
        "SELECT id, nombre, usuario, rol, activo, creado_en FROM usuarios WHERE id = ?", (usuario_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def editar_usuario(usuario_id: int, nombre: str, usuario: str, rol: str,
                   password: Optional[str] = None) -> dict:
    """Actualiza datos del usuario y opcionalmente su contraseña."""
    nombre = nombre.strip()
    usuario = usuario.strip().lower()
    rol = rol.strip().lower()

    if rol not in PERMISOS:
        return {"ok": False, "error": f"Rol inválido. Opciones: {list(PERMISOS.keys())}"}

    conn = get_connection()
    try:
        if password and password.strip():
            if len(password.strip()) < 4:
                return {"ok": False, "error": "La contraseña debe tener al menos 4 caracteres."}
            hashed = bcrypt.hashpw(password.strip().encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            conn.execute(
                "UPDATE usuarios SET nombre = ?, usuario = ?, rol = ?, password = ? WHERE id = ?",
                (nombre, usuario, rol, hashed, usuario_id)
            )
        else:
            conn.execute(
                "UPDATE usuarios SET nombre = ?, usuario = ?, rol = ? WHERE id = ?",
                (nombre, usuario, rol, usuario_id)
            )
        conn.commit()
        return {"ok": True, "mensaje": f"Usuario '{usuario}' actualizado correctamente."}
    except sqlite3.IntegrityError:
        return {"ok": False, "error": f"El nombre de usuario '{usuario}' ya está en uso."}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def cambiar_estado_usuario(usuario_id: int, activo: bool) -> dict:
    """Activa o desactiva un usuario en el sistema."""
    conn = get_connection()
    conn.execute("UPDATE usuarios SET activo = ? WHERE id = ?", (int(activo), usuario_id))
    conn.commit()
    conn.close()
    estado = "activado" if activo else "desactivado"
    return {"ok": True, "mensaje": f"Usuario {usuario_id} {estado} correctamente."}
