# 🛒 MarketHub — Sistema Integral de Gestión para Minimercados

**MarketHub** es un sistema de gestión y punto de venta (POS) para minimercados y comercios minoristas desarrollado en Python. Permite automatizar ventas, emisión de tickets térmicos, control de inventario en tiempo real con kardex, arqueo de caja y reportes analíticos de rentabilidad.

El sistema cuenta con **tres interfaces sincronizadas**:
1. 🌐 **Aplicación Web Moderna (Recomendada)**: Accesible desde cualquier navegador en PC, tablet o celular en la red local (`http://127.0.0.1:5000`).
2. 🖥️ **Aplicación de Escritorio**: Desarrollada en Tkinter para equipos locales.
3. 💻 **Línea de Comandos (CLI)**: Para pruebas rápidas y auditoría con tablas enriquecidas (`rich`).

---

## 🚀 Novedades y Mejoras Implementadas

- **Corrección Definitiva del Cálculo de Cambio**:
  - Se eliminó el reseteo prematuro a `0.00 Bs` en la interfaz. El cambio permanece visible hasta completar la entrega.
  - Atajos rápidos de billetes (+10, +20, +50, +100, +200 Bs y botón de Pago Exacto).
  - Cálculo reactivo en vivo según el cliente entrega el dinero.
- **Transacciones Atómicas Seguras (ACID)**:
  - La venta, el descuento de existencias y el registro del pago se ejecutan en una sola transacción. Si el pago o el stock fallan, la base de datos revierte automáticamente todos los cambios sin dejar datos huérfanos.
- **Reportes Auditados y Confiables**:
  - Se corrigió la distorsión donde los pagos inflaban las ventas registradas. Los ingresos diarios reflejan únicamente el total neto cobrado.
  - Separación maestro-detalle en el historial: ya no se duplica el total de la venta en cada fila de producto.
- **Emisión de Tickets Térmicos (58mm / 80mm)**:
  - Generación de comprobante térmico con fecha, hora, cajero, cliente (NIT/CI), detalle de productos, subtotal, total, dinero recibido y cambio.
- **Ventas en Espera (Parked Carts)**:
  - Permite pausar una compra a mitad del cobro para atender a otro cliente y reanudarla posteriormente sin perder los artículos escaneados.
- **Soporte de Roles Completo**:
  - **Administrador**: Control total del sistema, reportes financieros, anulación de ventas y gestión de personal.
  - **Cajero**: Terminal de venta (POS), cobros, arqueo de caja y reimpresión de tickets.
  - **Almacenero**: Catálogo de productos, reposición de mercadería y consulta de kardex.
- **Exportación de Datos**:
  - Descarga de reportes de ventas e inventario valorizado a formato CSV compatible con Microsoft Excel.

---

## 📋 Requisitos del Sistema

- **Python 3.10** o superior.
- Dependencias indicadas en `requirements.txt`:
  ```bash
  pip install -r requirements.txt
  ```

---

## ⚡ Guía de Instalación y Uso

### 1. Clonar o abrir la carpeta del proyecto
```bash
cd Sistema-MarketHub
```

### 2. Instalar librerías necesarias
```bash
py -m pip install -r requirements.txt
```

### 3. Poblar la base de datos inicial (Seeder)
Para crear las tablas y cargar productos y usuarios iniciales de prueba:
```bash
py seed.py
```
*(Si desea reiniciar los datos a cero en cualquier momento: `py seed.py --reset`)*

---

## 🌐 Iniciar la Aplicación Web (Modo Principal)

Ejecute el servidor web:
```bash
py app.py
```

Abra su navegador web favorito en:
👉 **`http://127.0.0.1:5000`**

### Usuarios y Credenciales por Defecto:
| Rol | Usuario | Contraseña | Permisos |
| :--- | :--- | :--- | :--- |
| **Administrador** | `admin` | `admin123` | Acceso total a todas las funciones y reportes |
| **Cajero** | `cajero` | `cajero123` | Punto de Venta (POS) y reimpresión de tickets |
| **Almacenero** | `almacen` | `almacen123` | Control de stock, inventario y kardex |

---

## 🖥️ Iniciar la Aplicación de Escritorio (Tkinter)

Si prefiere utilizar la interfaz gráfica tradicional de escritorio de Windows:
```bash
py gui.py
```

---

## 💻 Ejecutar Demostración por Consola (CLI)

Para correr la suite de verificación por terminal con tablas estilizadas:
```bash
py main.py
```

---

## 🧪 Ejecutar Pruebas Automatizadas

El proyecto incluye pruebas unitarias y de integración para garantizar que las ventas y el inventario funcionen con exactitud matemática:
```bash
py -m unittest discover tests
```

---

## 📁 Estructura del Proyecto

```text
Sistema-MarketHub/
├── app.py                   # Servidor web Flask con API REST y POS
├── gui.py                   # Aplicación de escritorio Tkinter refactorizada
├── main.py                  # Interfaz de línea de comandos (CLI Demo)
├── seed.py                  # Script para poblar y resetear datos limpios
├── requirements.txt         # Dependencias (Flask, bcrypt, rich)
├── .gitignore               # Exclusión de bases de datos y archivos temporales
├── data/                    # Directorio de almacenamiento SQLite
│   └── markethub.db        # Base de datos relacional
├── modules/
│   ├── database.py          # Conexión y esquema con restricciones relacionales
│   ├── usuarios.py          # Autenticación bcrypt y roles
│   ├── inventario.py        # Catálogo, stock y movimientos kardex
│   ├── ventas.py            # Carrito, ventas atómicas y tickets
│   ├── pagos.py             # Procesamiento y cálculo de cambio
│   └── reportes.py          # KPIs, cierre de caja y exportación CSV
├── static/
│   └── css/styles.css       # Estilos y formato de impresión de ticket térmico
├── templates/               # Vistas web HTML5 con Tailwind CSS
│   ├── base.html            # Layout maestro responsivo
│   ├── login.html           # Inicio de sesión estilizado
│   ├── pos.html             # Terminal Punto de Venta táctil y con scanner
│   ├── inventario.html      # Gestión de productos y kardex
│   ├── ventas.html          # Historial de ventas y detalle auditado
│   ├── reportes.html        # Panel de control y cierre de caja
│   └── usuarios.html        # Módulo de personal y permisos
└── tests/                   # Pruebas unitarias y de integración
    ├── test_ventas.py       # Pruebas de ventas, pagos y cambio
    ├── test_inventario.py   # Pruebas de stock y kardex
    └── test_web.py          # Pruebas de endpoints web y sesiones
```
