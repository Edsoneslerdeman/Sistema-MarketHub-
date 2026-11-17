"""
MarketHub — Interfaz de Escritorio (Tkinter)
Sistema de Gestión para Minimercado MarketHub
Refactorizado con corrección de cambio reactivo, reportes consistentes y roles completos.
"""
import sys
import os
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from modules.database import inicializar_bd, get_connection
from modules import usuarios as usr
from modules import inventario as inv
from modules import ventas as ven
from modules import pagos as pag
from modules import reportes as rep
import seed

# Paleta de Colores
C = {
    "bg": "#EEF2F0",
    "sidebar": "#1E2D24",
    "sidebar_h": "#2A3D32",
    "accent": "#2E6B50",
    "green": "#16A34A",
    "red": "#DC2626",
    "yellow": "#D97706",
    "white": "#FAFAF8",
    "card": "#FFFFFF",
    "text": "#1E293B",
    "text_lt": "#64748B",
    "border": "#CBD5E1",
    "row_even": "#FAFAF8",
    "row_odd": "#F1F5F3",
    "header_bg": "#2E6B50",
    "header_fg": "#FFFFFF",
    "sel": "#2E6B50",
}

FONT_TITLE = ("Segoe UI", 16, "bold")
FONT_LABEL = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_SMALL = ("Segoe UI", 9)


def _aplicar_estilo():
    s = ttk.Style()
    try:
        s.theme_use("clam")
    except Exception:
        pass
    s.configure(
        "MH.Treeview",
        background=C["row_even"],
        fieldbackground=C["row_even"],
        rowheight=28,
        font=("Segoe UI", 9)
    )
    s.configure(
        "MH.Treeview.Heading",
        background=C["header_bg"],
        foreground=C["header_fg"],
        font=("Segoe UI", 9, "bold"),
        relief="flat",
        padding=(8, 5)
    )
    s.map("MH.Treeview.Heading", background=[("active", C["accent"])])
    s.map("MH.Treeview", background=[("selected", C["sel"])], foreground=[("selected", "#FFF")])


def _make_tree(parent, cols, anchos=None, height=12):
    tv = ttk.Treeview(
        parent,
        columns=cols,
        show="headings",
        height=height,
        style="MH.Treeview",
        selectmode="browse"
    )
    for col in cols:
        w = (anchos or {}).get(col, 110)
        tv.heading(col, text=col, anchor="center")
        tv.column(col, anchor="center", width=w, minwidth=40, stretch=True)
    tv.tag_configure("par", background=C["row_even"])
    tv.tag_configure("impar", background=C["row_odd"])
    tv.tag_configure("bajo", background="#FEE2E2", foreground=C["red"])
    return tv


def _tabla_frame(parent, cols, anchos=None, height=14):
    w = tk.Frame(parent, bg=C["bg"])
    w.columnconfigure(0, weight=1)
    w.rowconfigure(0, weight=1)
    tv = _make_tree(w, cols, anchos, height)
    vsb = ttk.Scrollbar(w, orient="vertical", command=tv.yview)
    tv.configure(yscrollcommand=vsb.set)
    tv.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    return w, tv


def _fill_tree(tv, rows):
    for r in tv.get_children():
        tv.delete(r)
    for i, vals in enumerate(rows):
        tag = "par" if i % 2 == 0 else "impar"
        tv.insert("", "end", values=vals, tags=(tag,))


def _page_title(parent, title, subtitle=""):
    f = tk.Frame(parent, bg=C["bg"])
    tk.Label(f, text=title, font=FONT_TITLE, bg=C["bg"], fg=C["text"]).pack(anchor="w")
    if subtitle:
        tk.Label(f, text=subtitle, font=FONT_SMALL, bg=C["bg"], fg=C["text_lt"]).pack(anchor="w")
    return f


def _kpi_card(parent, label, value, color, sub=""):
    f = tk.Frame(parent, bg=C["card"], highlightbackground=C["border"], highlightthickness=1)
    tk.Frame(f, bg=color, height=4).pack(fill="x")
    b = tk.Frame(f, bg=C["card"], padx=14, pady=10)
    b.pack(fill="both", expand=True)
    tk.Label(b, text=label, font=FONT_SMALL, bg=C["card"], fg=C["text_lt"]).pack(anchor="w")
    tk.Label(b, text=value, font=("Segoe UI", 18, "bold"), bg=C["card"], fg=color).pack(anchor="w")
    if sub:
        tk.Label(b, text=sub, font=FONT_SMALL, bg=C["card"], fg=C["text_lt"]).pack(anchor="w")
    return f


def _btn(parent, text, color, cmd, **kw):
    return tk.Button(
        parent, text=text, font=FONT_SMALL, bg=color, fg="#FFF", relief="flat",
        activebackground=C["sidebar_h"], activeforeground="#FFF",
        padx=12, pady=6, cursor="hand2", command=cmd, **kw
    )


def _center_win(win, w, h):
    win.update_idletasks()
    x = (win.winfo_screenwidth() - w) // 2
    y = (win.winfo_screenheight() - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")


# ==========================================
# Ventana de Login
# ==========================================

class LoginWindow(tk.Toplevel):
    def __init__(self, master, on_success):
        super().__init__(master)
        self.on_success = on_success
        self.title("MarketHub — Iniciar Sesión")
        self.resizable(False, False)
        self.configure(bg=C["bg"])
        self.grab_set()
        _center_win(self, 380, 440)

        hdr = tk.Frame(self, bg=C["accent"], height=100)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🛒", font=("Segoe UI", 28), bg=C["accent"], fg="white").pack(pady=(10, 0))
        tk.Label(hdr, text="MarketHub", font=("Segoe UI", 14, "bold"), bg=C["accent"], fg="white").pack()

        body = tk.Frame(self, bg=C["bg"], padx=36, pady=24)
        body.pack(fill="both", expand=True)
        tk.Label(body, text="Sistema de Gestión de Minimercado", font=FONT_SMALL,
                 bg=C["bg"], fg=C["text_lt"]).pack(pady=(0, 16))

        tk.Label(body, text="Usuario:", font=FONT_BOLD, bg=C["bg"], fg=C["text"], anchor="w").pack(fill="x")
        self.ent_user = ttk.Entry(body, font=FONT_LABEL)
        self.ent_user.pack(fill="x", pady=(2, 10), ipady=4)

        tk.Label(body, text="Contraseña:", font=FONT_BOLD, bg=C["bg"], fg=C["text"], anchor="w").pack(fill="x")
        self.ent_pass = ttk.Entry(body, font=FONT_LABEL, show="•")
        self.ent_pass.pack(fill="x", pady=(2, 10), ipady=4)

        self.lbl_err = tk.Label(body, text="", font=FONT_SMALL, bg=C["bg"], fg=C["red"])
        self.lbl_err.pack(pady=(0, 6))

        _btn(body, "Ingresar al Sistema", C["accent"], self._login).pack(fill="x", ipady=4)

        # Accesos rápidos
        demo_f = tk.Frame(body, bg=C["bg"])
        demo_f.pack(fill="x", pady=(14, 0))
        tk.Label(demo_f, text="Accesos demo:", font=("Segoe UI", 8), bg=C["bg"], fg=C["text_lt"]).pack(anchor="w")
        btn_box = tk.Frame(demo_f, bg=C["bg"])
        btn_box.pack(fill="x", pady=2)
        tk.Button(btn_box, text="Admin", font=("Segoe UI", 8), command=lambda: self._set_cred("admin", "admin123")).pack(side="left", padx=(0, 4))
        tk.Button(btn_box, text="Cajero", font=("Segoe UI", 8), command=lambda: self._set_cred("cajero", "cajero123")).pack(side="left", padx=(0, 4))
        tk.Button(btn_box, text="Almacén", font=("Segoe UI", 8), command=lambda: self._set_cred("almacen", "almacen123")).pack(side="left")

        self.ent_user.bind("<Return>", lambda e: self.ent_pass.focus())
        self.ent_pass.bind("<Return>", lambda e: self._login())
        self.ent_user.focus()
        self.protocol("WM_DELETE_WINDOW", lambda: master.destroy())

    def _set_cred(self, u, p):
        self.ent_user.delete(0, "end")
        self.ent_user.insert(0, u)
        self.ent_pass.delete(0, "end")
        self.ent_pass.insert(0, p)

    def _login(self):
        u = self.ent_user.get().strip()
        p = self.ent_pass.get().strip()
        if not u or not p:
            self.lbl_err.config(text="Complete todos los campos.")
            return
        res = usr.iniciar_sesion(u, p)
        if res["ok"]:
            self.destroy()
            self.on_success()
        else:
            self.lbl_err.config(text=res["error"])
            self.ent_pass.delete(0, "end")


# ==========================================
# Aplicación Principal
# ==========================================

class MarketHubApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        _aplicar_estilo()
        inicializar_bd()

        self.title("MarketHub — Sistema de Gestión")
        self.configure(bg=C["bg"])
        self.minsize(1050, 650)
        self.carrito = ven.Carrito()
        self._frame_actual = None

        LoginWindow(self, self._post_login)
        self.mainloop()

    def _post_login(self):
        self.deiconify()
        if sys.platform == "win32":
            self.state("zoomed")
        self._build_layout()

        rol = usr.sesion().rol
        if rol == "cajero":
            self._mostrar_ventas()
        elif rol == "almacenero":
            self._mostrar_inventario()
        else:
            self._mostrar_panel_control()

    def _build_layout(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.sidebar = tk.Frame(self, bg=C["sidebar"], width=225)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)
        self._build_sidebar()

        self.content = tk.Frame(self, bg=C["bg"])
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)

    def _build_sidebar(self):
        logo_f = tk.Frame(self.sidebar, bg=C["accent"], pady=16)
        logo_f.pack(fill="x")
        tk.Label(logo_f, text="🛒 MarketHub", font=("Segoe UI", 13, "bold"), bg=C["accent"], fg="white").pack()
        u = usr.sesion()
        tk.Label(logo_f, text=f"{u.nombre}\n[{u.rol.upper()}]", font=FONT_SMALL,
                 bg=C["accent"], fg="#B8D4C5", justify="center").pack(pady=(4, 0))

        tk.Frame(self.sidebar, bg="#141F18", height=1).pack(fill="x", pady=6)
        self._btns_menu = {}
        rol = u.rol

        menus = []
        if rol == "admin":
            menus.append(("🏠  Panel de Control", "panel", self._mostrar_panel_control))
        if rol in ["admin", "cajero"]:
            menus.append(("🛒  Punto de Venta", "ventas", self._mostrar_ventas))
            menus.append(("📋  Historial Ventas", "historial", self._mostrar_historial_ventas))
        if rol in ["admin", "almacenero"]:
            menus.append(("📦  Inventario y Stock", "inventario", self._mostrar_inventario))
        if rol == "admin":
            menus.append(("📊  Reportes y Cierre", "reportes", self._mostrar_reportes))
            menus.append(("👤  Personal y Roles", "usuarios", self._mostrar_usuarios))

        for label, key, cmd in menus:
            b = tk.Button(
                self.sidebar, text=label, font=FONT_LABEL, bg=C["sidebar"], fg="#B8D4C5",
                relief="flat", activebackground=C["accent"], activeforeground="white",
                anchor="w", padx=20, pady=10, cursor="hand2",
                command=lambda c=cmd, k=key: self._nav(c, k)
            )
            b.pack(fill="x")
            self._btns_menu[key] = b

        tk.Frame(self.sidebar, bg="#141F18", height=1).pack(fill="x", side="bottom", pady=4)
        tk.Button(
            self.sidebar, text="⬅  Cerrar Sesión", font=FONT_LABEL, bg=C["sidebar"],
            fg="#F87171", relief="flat", activebackground="#3B0A0A", activeforeground="white",
            anchor="w", padx=20, pady=10, cursor="hand2",
            command=self._cerrar_sesion
        ).pack(fill="x", side="bottom")

    def _nav(self, cmd, key):
        for k, b in self._btns_menu.items():
            b.config(bg=C["sidebar"], fg="#B8D4C5")
        if key in self._btns_menu:
            self._btns_menu[key].config(bg=C["accent"], fg="white")
        cmd()

    def _set_frame(self, frame):
        if self._frame_actual:
            self._frame_actual.destroy()
        self._frame_actual = frame
        frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

    def _cerrar_sesion(self):
        usr.cerrar_sesion()
        self.destroy()
        MarketHubApp()

    # ==========================================
    # Panel de Control (Dashboard)
    # ==========================================

    def _mostrar_panel_control(self):
        self._nav(lambda: None, "panel")
        f = tk.Frame(self.content, bg=C["bg"])
        f.columnconfigure((0, 1, 2, 3), weight=1)
        f.rowconfigure(2, weight=1)

        _page_title(f, "🏠 Panel de Control", "Resumen diario de operaciones").grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 14)
        )
        dash = rep.dashboard_hoy()
        cierre = ven.cierre_caja()
        ri = rep.reporte_inventario()

        kpis = [
            ("Ventas Hoy", str(dash.get("ventas_hoy", 0)), C["accent"]),
            ("Ingresos Hoy (Bs.)", f"{dash.get('ingresos_hoy', 0.0):.2f}", C["green"]),
            ("Alertas Stock", str(dash.get("alertas_stock", 0)), C["red"] if dash.get("alertas_stock") else C["green"]),
            ("Productos Activos", str(ri.get("total_productos_activos", 0)), C["yellow"]),
        ]
        for col, (lbl, val, color) in enumerate(kpis):
            _kpi_card(f, lbl, val, color).grid(row=1, column=col, padx=4, pady=4, sticky="nsew")

        # Top productos
        tp_w = tk.Frame(f, bg=C["bg"])
        tp_w.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=(0, 6), pady=6)
        tp_w.columnconfigure(0, weight=1)
        tp_w.rowconfigure(1, weight=1)
        tk.Label(tp_w, text="🏆 Top Productos del Día", font=FONT_BOLD, bg=C["bg"], fg=C["text"]).grid(row=0, column=0, sticky="w", pady=(0, 4))
        _, tv_tp = _tabla_frame(tp_w, ("Producto", "Unidades", "Ingreso Bs."), {"Producto": 200, "Unidades": 80, "Ingreso Bs.": 90}, 7)
        tv_tp.master.grid(row=1, column=0, sticky="nsew")
        _fill_tree(tv_tp, [(p["nombre"], p["unidades"], f"{p['ingreso']:.2f}") for p in cierre.get("top_5_productos", [])])

        # Ventas por método de pago
        pm_w = tk.Frame(f, bg=C["bg"])
        pm_w.grid(row=2, column=2, columnspan=2, sticky="nsew", padx=(6, 0), pady=6)
        pm_w.columnconfigure(0, weight=1)
        pm_w.rowconfigure(1, weight=1)
        tk.Label(pm_w, text="💳 Ventas por Método de Pago", font=FONT_BOLD, bg=C["bg"], fg=C["text"]).grid(row=0, column=0, sticky="w", pady=(0, 4))
        _, tv_pm = _tabla_frame(pm_w, ("Método", "Cantidad", "Total Bs."), {"Método": 110, "Cantidad": 80, "Total Bs.": 100}, 7)
        tv_pm.master.grid(row=1, column=0, sticky="nsew")
        _fill_tree(tv_pm, [(m["metodo_pago"].upper(), m["cantidad"], f"{m['subtotal']:.2f}") for m in cierre.get("por_metodo_pago", [])])

        self._set_frame(f)

    # ==========================================
    # Punto de Venta (POS) — CORREGIDO
    # ==========================================

    def _mostrar_ventas(self):
        self._nav(lambda: None, "ventas")
        f = tk.Frame(self.content, bg=C["bg"])
        f.columnconfigure(0, weight=2)
        f.columnconfigure(1, weight=1)
        f.rowconfigure(1, weight=1)

        _page_title(f, "🛒 Punto de Venta", "Registro y cobro de transacciones en tiempo real").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )

        # Columna Izquierda: Entrada de Código y Carrito
        left = tk.Frame(f, bg=C["card"], highlightbackground=C["border"], highlightthickness=1)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(2, weight=1)

        bus = tk.Frame(left, bg=C["card"], padx=10, pady=10)
        bus.grid(row=0, column=0, sticky="ew")
        bus.columnconfigure(0, weight=1)

        tk.Label(bus, text="Código de barras o producto:", font=FONT_SMALL, bg=C["card"], fg=C["text_lt"]).grid(row=0, column=0, sticky="w")
        tk.Label(bus, text="Cant:", font=FONT_SMALL, bg=C["card"], fg=C["text_lt"]).grid(row=0, column=1, padx=(8, 0))

        self.ent_codigo = ttk.Entry(bus, font=FONT_LABEL)
        self.ent_codigo.grid(row=1, column=0, sticky="ew", ipady=5)
        self.ent_cant = ttk.Entry(bus, font=FONT_LABEL, width=5)
        self.ent_cant.insert(0, "1")
        self.ent_cant.grid(row=1, column=1, padx=(8, 0), ipady=5)

        _btn(bus, "➕ Agregar", C["accent"], self._agregar_al_carrito).grid(row=1, column=2, padx=(6, 0), ipady=4)
        self.ent_codigo.bind("<Return>", lambda e: self._agregar_al_carrito())

        self.lbl_prod_info = tk.Label(bus, text="", font=FONT_SMALL, bg=C["card"], fg=C["green"])
        self.lbl_prod_info.grid(row=2, column=0, columnspan=3, sticky="w", pady=(4, 0))

        tk.Frame(left, bg=C["border"], height=1).grid(row=1, column=0, sticky="ew")

        self.tv_carrito = _make_tree(
            left, ("Producto", "Cant.", "Precio Unit.", "Subtotal"),
            {"Producto": 210, "Cant.": 55, "Precio Unit.": 100, "Subtotal": 100}, 12
        )
        self.tv_carrito.grid(row=2, column=0, sticky="nsew", padx=4, pady=4)

        q_btn = tk.Button(
            left, text="🗑 Quitar seleccionado", font=FONT_SMALL, bg="#FEE2E2", fg=C["red"],
            relief="flat", pady=4, cursor="hand2", command=self._quitar_del_carrito
        )
        q_btn.grid(row=3, column=0, sticky="w", padx=10, pady=6)

        # Columna Derecha: Panel de Cobro
        right = tk.Frame(f, bg=C["card"], highlightbackground=C["border"], highlightthickness=1)
        right.grid(row=1, column=1, sticky="nsew")
        inner = tk.Frame(right, bg=C["card"], padx=16, pady=10)
        inner.pack(fill="both", expand=True)

        tk.Label(inner, text="Cobro y Liquidación", font=FONT_BOLD, bg=C["card"], fg=C["text"]).pack(anchor="w")
        tk.Frame(inner, bg=C["border"], height=1).pack(fill="x", pady=8)

        self.lbl_total = tk.Label(inner, text="Bs. 0.00", font=("Segoe UI", 26, "bold"), bg=C["card"], fg=C["accent"])
        self.lbl_total.pack()
        tk.Label(inner, text="TOTAL A COBRAR", font=FONT_SMALL, bg=C["card"], fg=C["text_lt"]).pack()
        tk.Frame(inner, bg=C["border"], height=1).pack(fill="x", pady=10)

        tk.Label(inner, text="Método de pago:", font=FONT_BOLD, bg=C["card"], fg=C["text"], anchor="w").pack(fill="x")
        self.var_metodo = tk.StringVar(value="efectivo")
        for m, lbl in [("efectivo", "💵 Efectivo"), ("qr", "📱 QR"), ("tarjeta", "💳 Tarjeta")]:
            rb = tk.Radiobutton(
                inner, text=lbl, variable=self.var_metodo, value=m, font=FONT_LABEL,
                bg=C["card"], fg=C["text"], selectcolor=C["card"],
                activebackground=C["card"], command=self._calcular_cambio_live
            )
            rb.pack(anchor="w", pady=1)

        tk.Label(inner, text="Monto recibido del cliente (Bs.):", font=FONT_BOLD, bg=C["card"], fg=C["text"], anchor="w").pack(fill="x", pady=(10, 0))
        self.ent_monto = ttk.Entry(inner, font=("Segoe UI", 13))
        self.ent_monto.pack(fill="x", ipady=6, pady=(4, 0))
        self.ent_monto.bind("<KeyRelease>", self._calcular_cambio_live)

        # Etiqueta de Cambio Reactiva (NUNCA se pierde)
        self.lbl_cambio = tk.Label(inner, text="Cambio: Bs. 0.00", font=FONT_BOLD, bg=C["card"], fg=C["green"])
        self.lbl_cambio.pack(pady=8)

        _btn(inner, "✅ CONFIRMAR VENTA", C["green"], self._registrar_venta).pack(fill="x", pady=4, ipady=6)
        tk.Button(
            inner, text="🗑 Limpiar carrito", font=FONT_SMALL, bg="#FEE2E2", fg=C["red"],
            relief="flat", pady=6, cursor="hand2", command=self._limpiar_carrito
        ).pack(fill="x")

        self._actualizar_carrito_vista()
        self._set_frame(f)
        self.ent_codigo.focus()

    def _calcular_cambio_live(self, event=None):
        metodo = self.var_metodo.get()
        if metodo != "efectivo":
            self.lbl_cambio.config(text="Cambio: Bs. 0.00 (Cobro exacto)", fg=C["text_lt"])
            return

        try:
            monto = float(self.ent_monto.get().strip())
            total = self.carrito.total
            if monto >= total:
                cambio = round(monto - total, 2)
                self.lbl_cambio.config(text=f"Cambio: Bs. {cambio:.2f}", fg=C["green"])
            else:
                falta = round(total - monto, 2)
                self.lbl_cambio.config(text=f"Falta: Bs. {falta:.2f}", fg=C["red"])
        except ValueError:
            self.lbl_cambio.config(text="Cambio: Bs. 0.00", fg=C["green"])

    def _agregar_al_carrito(self):
        cod = self.ent_codigo.get().strip()
        try:
            cant = int(self.ent_cant.get().strip())
        except Exception:
            cant = 1
        if not cod:
            return

        res = self.carrito.agregar(cod, cant)
        if res["ok"]:
            self.lbl_prod_info.config(text="✓ " + res["mensaje"], fg=C["green"])
        else:
            self.lbl_prod_info.config(text="✗ " + res["error"], fg=C["red"])

        self.ent_codigo.delete(0, "end")
        self.ent_cant.delete(0, "end")
        self.ent_cant.insert(0, "1")
        self._actualizar_carrito_vista()
        self._calcular_cambio_live()

    def _quitar_del_carrito(self):
        sel = self.tv_carrito.selection()
        if not sel:
            return
        idx = self.tv_carrito.index(sel[0])
        if idx < len(self.carrito.items):
            pid = self.carrito.items[idx].producto_id
            self.carrito.quitar(pid)
            self._actualizar_carrito_vista()
            self._calcular_cambio_live()

    def _limpiar_carrito(self):
        self.carrito.limpiar()
        self._actualizar_carrito_vista()
        self.lbl_prod_info.config(text="")
        # Nota: No reseteamos forzosamente self.lbl_cambio si ya hay un cambio de venta recién hecha

    def _actualizar_carrito_vista(self):
        _fill_tree(
            self.tv_carrito,
            [(i.nombre, i.cantidad, f"Bs. {i.precio_unit:.2f}", f"Bs. {i.subtotal:.2f}") for i in self.carrito.items]
        )
        if hasattr(self, "lbl_total"):
            self.lbl_total.config(text=f"Bs. {self.carrito.total:.2f}")

    def _registrar_venta(self):
        """Procesa la venta con la lógica atómica corregida y mantiene visible el cambio."""
        if not self.carrito.items:
            messagebox.showwarning("Carrito Vacío", "Agregue productos antes de cobrar.")
            return

        metodo = self.var_metodo.get()
        total = self.carrito.total
        txt_monto = self.ent_monto.get().strip()

        if metodo == "efectivo":
            try:
                monto_recibido = float(txt_monto) if txt_monto else total
            except ValueError:
                messagebox.showerror("Error", "Monto recibido inválido.")
                return

            if monto_recibido < total:
                messagebox.showerror(
                    "Monto Insuficiente",
                    f"El monto recibido (Bs. {monto_recibido:.2f}) es menor al total a pagar (Bs. {total:.2f})."
                )
                return
        else:
            monto_recibido = total

        cambio_esperado = max(0.0, round(monto_recibido - total, 2)) if metodo == "efectivo" else 0.0

        res = ven.registrar_venta(
            carrito=self.carrito,
            metodo_pago=metodo,
            monto_recibido=monto_recibido
        )

        if res["ok"]:
            # MANTENER VISIBLE EL CAMBIO EN LA PANTALLA PRINCIPAL
            self.lbl_cambio.config(text=f"Cambio: Bs. {res['cambio']:.2f}", fg=C["green"])
            self.ent_monto.delete(0, "end")
            self._actualizar_carrito_vista()

            ticket_txt = ven.generar_ticket_texto(res["venta_id"])
            self._mostrar_ticket_modal(res["venta_id"], res["cambio"], ticket_txt)
        else:
            messagebox.showerror("Error en Venta", res["error"])

    def _mostrar_ticket_modal(self, venta_id, cambio, ticket_txt):
        d = tk.Toplevel(self)
        d.title(f"Venta #{venta_id} Completada")
        d.configure(bg=C["bg"])
        d.grab_set()
        _center_win(d, 360, 480)

        tk.Label(d, text="✓ Venta Registrada", font=FONT_TITLE, bg=C["bg"], fg=C["green"]).pack(pady=(12, 2))
        tk.Label(d, text=f"CAMBIO A ENTREGAR: Bs. {cambio:.2f}", font=("Segoe UI", 13, "bold"),
                 bg=C["bg"], fg=C["accent"]).pack(pady=(0, 10))

        txt = tk.Text(d, font=("Courier New", 9), height=14, width=38, relief="solid", bd=1)
        txt.insert("1.0", ticket_txt)
        txt.config(state="disabled")
        txt.pack(padx=16, pady=4)

        _btn(d, "Cerrar y Continuar", C["accent"], d.destroy).pack(fill="x", padx=16, pady=(10, 12))

    # ==========================================
    # Historial de Ventas
    # ==========================================

    def _mostrar_historial_ventas(self):
        self._nav(lambda: None, "historial")
        f = tk.Frame(self.content, bg=C["bg"])
        f.columnconfigure(0, weight=1)
        f.rowconfigure(1, weight=1)

        _page_title(f, "📋 Historial de Ventas", "Listado auditado de transacciones").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )

        cols = ("Venta #", "Fecha y Hora", "Cajero", "Método", "Total Bs.", "Monto Recibido", "Cambio Bs.", "Estado")
        anchos = {"Venta #": 65, "Fecha y Hora": 140, "Cajero": 110, "Método": 85,
                  "Total Bs.": 90, "Monto Recibido": 105, "Cambio Bs.": 90, "Estado": 90}

        wrap, tv = _tabla_frame(f, cols, anchos, 18)
        wrap.grid(row=1, column=0, sticky="nsew")

        ventas = ven.listar_ventas(limite=150)
        _fill_tree(
            tv,
            [(v["id"], v["fecha"], v["cajero"], v["metodo_pago"].upper(),
              f"{v['total']:.2f}", f"{v['monto_pago']:.2f}", f"{v['cambio']:.2f}", v["estado"].upper())
             for v in ventas]
        )

        def ver_detalle_venta(e):
            sel = tv.selection()
            if not sel:
                return
            vid = int(tv.item(sel[0], "values")[0])
            ticket_txt = ven.generar_ticket_texto(vid)
            self._mostrar_ticket_modal(vid, 0, ticket_txt)

        tv.bind("<Double-1>", ver_detalle_venta)
        tk.Label(f, text="Doble clic en una fila para ver el ticket completo.", font=FONT_SMALL,
                 bg=C["bg"], fg=C["text_lt"]).grid(row=2, column=0, sticky="w", pady=(4, 0))

        self._set_frame(f)

    # ==========================================
    # Inventario
    # ==========================================

    def _mostrar_inventario(self):
        self._nav(lambda: None, "inventario")
        f = tk.Frame(self.content, bg=C["bg"])
        f.columnconfigure(0, weight=1)
        f.rowconfigure(2, weight=1)

        _page_title(f, "📦 Inventario y Stock", "Gestión de catálogo y existencias").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )

        bar = tk.Frame(f, bg=C["bg"])
        bar.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        _btn(bar, "➕ Nuevo Producto", C["accent"], self._dlg_nuevo_producto).pack(side="left", padx=(0, 6))
        _btn(bar, "✏️ Editar Producto", C["yellow"], self._dlg_editar_producto).pack(side="left", padx=(0, 6))
        _btn(bar, "📥 Entrada Stock", C["green"], self._dlg_entrada_stock).pack(side="left", padx=(0, 6))
        _btn(bar, "🗑 Desactivar", C["red"], self._eliminar_producto).pack(side="left", padx=(0, 6))
        _btn(bar, "🔄 Actualizar", C["text_lt"], self._cargar_inventario).pack(side="left")

        cols = ("ID", "Nombre", "Código", "Precio Bs.", "Stock", "Mínimo", "Categoría")
        anchos = {"ID": 45, "Nombre": 200, "Código": 100, "Precio Bs.": 90, "Stock": 70, "Mínimo": 60, "Categoría": 120}

        tabla_f = tk.Frame(f, bg=C["bg"])
        tabla_f.grid(row=2, column=0, sticky="nsew")
        tabla_f.columnconfigure(0, weight=1)
        tabla_f.rowconfigure(0, weight=1)

        self.tv_inv = _make_tree(tabla_f, cols, anchos, 20)
        vsb = ttk.Scrollbar(tabla_f, orient="vertical", command=self.tv_inv.yview)
        self.tv_inv.configure(yscrollcommand=vsb.set)
        self.tv_inv.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self._cargar_inventario()
        self._set_frame(f)

    def _cargar_inventario(self):
        for r in self.tv_inv.get_children():
            self.tv_inv.delete(r)

        productos = inv.listar_productos()
        for i, p in enumerate(productos):
            tag = "bajo" if p["stock"] <= p["stock_minimo"] else ("par" if i % 2 == 0 else "impar")
            self.tv_inv.insert(
                "", "end", tags=(tag,),
                values=(p["id"], p["nombre"], p["codigo"], f"{p['precio']:.2f}",
                        p["stock"], p["stock_minimo"], p.get("categoria") or "—")
            )

    def _dlg_nuevo_producto(self):
        self._dlg_producto(None)

    def _dlg_editar_producto(self):
        sel = self.tv_inv.selection()
        if not sel:
            messagebox.showwarning("Seleccione", "Elija un producto de la tabla.")
            return
        pid = int(self.tv_inv.item(sel[0], "values")[0])
        prod = inv.buscar_producto(pid)
        if prod:
            self._dlg_producto(prod)

    def _dlg_producto(self, prod=None):
        es_edicion = prod is not None
        d = tk.Toplevel(self)
        d.title("Editar Producto" if es_edicion else "Nuevo Producto")
        d.resizable(False, False)
        d.configure(bg=C["bg"])
        d.grab_set()
        _center_win(d, 400, 480)
        d.columnconfigure(1, weight=1)

        campos = [("Nombre", "nombre"), ("Código", "codigo"), ("Precio (Bs.)", "precio"),
                  ("Stock inicial", "stock"), ("Stock mínimo", "stock_min")]
        entradas = {}

        for i, (lbl, key) in enumerate(campos):
            tk.Label(d, text=lbl, font=FONT_BOLD, bg=C["bg"], fg=C["text"]).grid(row=i, column=0, sticky="w", padx=20, pady=(10, 0))
            e = ttk.Entry(d, font=FONT_LABEL)
            e.grid(row=i, column=1, padx=20, pady=(10, 0), ipady=4, sticky="ew")
            if es_edicion:
                val_map = {
                    "nombre": prod["nombre"],
                    "codigo": prod["codigo"],
                    "precio": str(prod["precio"]),
                    "stock": str(prod["stock"]),
                    "stock_min": str(prod["stock_minimo"])
                }
                e.insert(0, val_map.get(key, ""))
                if key == "stock":
                    e.config(state="disabled")  # En edición no se altera el stock directamente
            entradas[key] = e

        cats = inv.listar_categorias()
        cat_nombres = [c["nombre"] for c in cats] or ["Sin categoría"]
        var_cat = tk.StringVar(value=cat_nombres[0])
        if es_edicion and prod.get("categoria_id"):
            c_match = [c["nombre"] for c in cats if c["id"] == prod["categoria_id"]]
            if c_match:
                var_cat.set(c_match[0])

        tk.Label(d, text="Categoría", font=FONT_BOLD, bg=C["bg"], fg=C["text"]).grid(row=len(campos), column=0, sticky="w", padx=20, pady=(10, 0))
        cb = ttk.Combobox(d, textvariable=var_cat, values=cat_nombres, state="readonly", font=FONT_LABEL)
        cb.grid(row=len(campos), column=1, padx=20, pady=(10, 0), sticky="ew")

        def guardar():
            nombre = entradas["nombre"].get().strip()
            codigo = entradas["codigo"].get().strip()
            try:
                precio = float(entradas["precio"].get().strip())
                smin = int(entradas["stock_min"].get().strip())
            except ValueError:
                messagebox.showerror("Error", "Precio y stock mínimo deben ser números válidos.", parent=d)
                return

            cat_id = next((c["id"] for c in cats if c["nombre"] == var_cat.get()), None)

            if es_edicion:
                res = inv.editar_producto(
                    producto_id=prod["id"],
                    nombre=nombre,
                    codigo=codigo,
                    precio=precio,
                    stock_minimo=smin,
                    categoria_id=cat_id
                )
            else:
                try:
                    stock_ini = int(entradas["stock"].get().strip())
                except ValueError:
                    stock_ini = 0
                res = inv.agregar_producto(
                    nombre=nombre,
                    codigo=codigo,
                    precio=precio,
                    stock_inicial=stock_ini,
                    stock_minimo=smin,
                    categoria_id=cat_id
                )

            if res["ok"]:
                messagebox.showinfo("Éxito", res["mensaje"], parent=d)
                d.destroy()
                self._cargar_inventario()
            else:
                messagebox.showerror("Error", res["error"], parent=d)

        _btn(d, "Guardar", C["accent"], guardar).grid(row=len(campos) + 1, column=0, columnspan=2, sticky="ew", padx=20, pady=16, ipady=4)

    def _dlg_entrada_stock(self):
        sel = self.tv_inv.selection()
        if not sel:
            messagebox.showwarning("Seleccione", "Elija un producto.")
            return
        vals = self.tv_inv.item(sel[0], "values")
        pid, nombre = int(vals[0]), vals[1]
        cant = simpledialog.askinteger("Entrada de Stock", f"Unidades a reponer de '{nombre}':", parent=self, minvalue=1)
        if cant:
            res = inv.entrada_stock(pid, cant, motivo="Reposición de mercadería")
            if res["ok"]:
                messagebox.showinfo("Éxito", res["mensaje"])
                self._cargar_inventario()
            else:
                messagebox.showerror("Error", res["error"])

    def _eliminar_producto(self):
        sel = self.tv_inv.selection()
        if not sel:
            messagebox.showwarning("Seleccione", "Elija un producto.")
            return
        vals = self.tv_inv.item(sel[0], "values")
        pid, nombre = int(vals[0]), vals[1]
        if messagebox.askyesno("Confirmar", f"¿Desactivar el producto '{nombre}' del catálogo?"):
            res = inv.eliminar_producto(pid)
            if res["ok"]:
                messagebox.showinfo("Éxito", res["mensaje"])
                self._cargar_inventario()
            else:
                messagebox.showerror("Error", res["error"])

    # ==========================================
    # Reportes y Cierre de Caja
    # ==========================================

    def _mostrar_reportes(self):
        self._nav(lambda: None, "reportes")
        f = tk.Frame(self.content, bg=C["bg"])
        f.columnconfigure(0, weight=1)
        f.rowconfigure(2, weight=1)

        _page_title(f, "📊 Reportes y Cierre de Caja", "Indicadores de ventas auditados").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )

        ctrl = tk.Frame(f, bg=C["bg"])
        ctrl.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        hoy = datetime.date.today().isoformat()
        hace_siete = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()

        tk.Label(ctrl, text="Desde:", font=FONT_BOLD, bg=C["bg"]).pack(side="left")
        self.ent_fi = ttk.Entry(ctrl, font=FONT_LABEL, width=12)
        self.ent_fi.insert(0, hace_siete)
        self.ent_fi.pack(side="left", padx=6)

        tk.Label(ctrl, text="Hasta:", font=FONT_BOLD, bg=C["bg"]).pack(side="left")
        self.ent_ff = ttk.Entry(ctrl, font=FONT_LABEL, width=12)
        self.ent_ff.insert(0, hoy)
        self.ent_ff.pack(side="left", padx=6)

        _btn(ctrl, "🔍 Generar", C["accent"], self._generar_reportes_gui).pack(side="left", padx=8)

        nb = ttk.Notebook(f)
        nb.grid(row=2, column=0, sticky="nsew")

        # Pestaña 1: Ventas por Día
        tab_v = tk.Frame(nb, bg=C["card"])
        nb.add(tab_v, text="  Ventas Diarias  ")
        tab_v.columnconfigure(0, weight=1)
        tab_v.rowconfigure(1, weight=1)
        self.lbl_rv = tk.Label(tab_v, text="", font=FONT_SMALL, bg=C["card"], fg=C["text"])
        self.lbl_rv.grid(row=0, column=0, sticky="w", padx=12, pady=6)
        _, self.tv_rv = _tabla_frame(tab_v, ("Día", "Transacciones", "Total Bs."), {"Día": 130, "Transacciones": 110, "Total Bs.": 110}, 14)
        self.tv_rv.master.grid(row=1, column=0, sticky="nsew", padx=4)

        # Pestaña 2: Top Productos
        tab_p = tk.Frame(nb, bg=C["card"])
        nb.add(tab_p, text="  Top Productos  ")
        tab_p.columnconfigure(0, weight=1)
        tab_p.rowconfigure(0, weight=1)
        _, self.tv_rp = _tabla_frame(tab_p, ("Producto", "Código", "Unidades", "Ingreso Bs."), {"Producto": 210, "Código": 100, "Unidades": 90, "Ingreso Bs.": 110}, 16)
        self.tv_rp.master.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        # Pestaña 3: Cierre de Hoy
        tab_c = tk.Frame(nb, bg=C["card"])
        nb.add(tab_c, text="  Cierre de Caja Hoy  ")
        tab_c.columnconfigure(0, weight=1)
        tab_c.rowconfigure(1, weight=1)
        self.lbl_rc = tk.Label(tab_c, text="", font=FONT_BOLD, bg=C["card"], fg=C["accent"])
        self.lbl_rc.grid(row=0, column=0, sticky="w", padx=12, pady=6)
        _, self.tv_rc = _tabla_frame(tab_c, ("Método de Pago", "Cantidad", "Total Bs."), {"Método de Pago": 140, "Cantidad": 100, "Total Bs.": 120}, 12)
        self.tv_rc.master.grid(row=1, column=0, sticky="nsew", padx=4)

        self._generar_reportes_gui()
        self._set_frame(f)

    def _generar_reportes_gui(self):
        if not hasattr(self, "ent_fi"):
            return
        fi = self.ent_fi.get().strip()
        ff = self.ent_ff.get().strip()

        rv = rep.reporte_ventas(fi, ff)
        if rv["ok"]:
            r = rv["resumen"]
            self.lbl_rv.config(
                text=f"Total Ventas: {r['total_transacciones']} | Ingresos: Bs. {r['ingresos_brutos']:.2f} | Ticket Promedio: Bs. {r['ticket_promedio']:.2f}"
            )
            _fill_tree(self.tv_rv, [(d["dia"], d["n"], f"{d['total']:.2f}") for d in rv["por_dia"]])

        tp = rep.reporte_top_productos(fi, ff)
        if tp["ok"]:
            _fill_tree(self.tv_rp, [(p["nombre"], p["codigo"], p["unidades_vendidas"], f"{p['ingresos']:.2f}") for p in tp["top_productos"]])

        cierre = ven.cierre_caja()
        self.lbl_rc.config(
            text=f"Fecha: {cierre['fecha']} — Total Facturado: Bs. {cierre['ingresos_totales']:.2f} ({cierre['total_ventas']} ventas)"
        )
        _fill_tree(self.tv_rc, [(m["metodo_pago"].upper(), m["cantidad"], f"{m['subtotal']:.2f}") for m in cierre.get("por_metodo_pago", [])])

    # ==========================================
    # Personal y Roles
    # ==========================================

    def _mostrar_usuarios(self):
        self._nav(lambda: None, "usuarios")
        f = tk.Frame(self.content, bg=C["bg"])
        f.columnconfigure(0, weight=1)
        f.rowconfigure(2, weight=1)

        _page_title(f, "👤 Personal y Roles", "Control de acceso de empleados").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )

        bar = tk.Frame(f, bg=C["bg"])
        bar.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        _btn(bar, "➕ Nuevo Usuario", C["accent"], self._dlg_nuevo_usuario).pack(side="left", padx=(0, 6))
        _btn(bar, "✏️ Editar Usuario", C["yellow"], self._dlg_editar_usuario).pack(side="left", padx=(0, 6))
        _btn(bar, "🗑 Desactivar", C["red"], self._desactivar_usuario).pack(side="left", padx=(0, 6))
        _btn(bar, "✅ Activar", C["green"], self._activar_usuario).pack(side="left", padx=(0, 6))
        _btn(bar, "🔄 Actualizar", C["text_lt"], self._cargar_usuarios).pack(side="left")

        cols = ("ID", "Nombre", "Usuario", "Rol", "Estado", "Fecha Alta")
        anchos = {"ID": 40, "Nombre": 180, "Usuario": 110, "Rol": 90, "Estado": 90, "Fecha Alta": 150}

        tabla_f = tk.Frame(f, bg=C["bg"])
        tabla_f.grid(row=2, column=0, sticky="nsew")
        tabla_f.columnconfigure(0, weight=1)
        tabla_f.rowconfigure(0, weight=1)

        self.tv_usr = _make_tree(tabla_f, cols, anchos, 18)
        vsb = ttk.Scrollbar(tabla_f, orient="vertical", command=self.tv_usr.yview)
        self.tv_usr.configure(yscrollcommand=vsb.set)
        self.tv_usr.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self._cargar_usuarios()
        self._set_frame(f)

    def _cargar_usuarios(self):
        for r in self.tv_usr.get_children():
            self.tv_usr.delete(r)
        usuarios = usr.listar_usuarios()
        for i, u in enumerate(usuarios):
            estado = "✅ Activo" if u["activo"] else "❌ Inactivo"
            tag = "par" if i % 2 == 0 else "impar"
            self.tv_usr.insert("", "end", tags=(tag,), values=(u["id"], u["nombre"], u["usuario"], u["rol"].upper(), estado, u["creado_en"]))

    def _dlg_nuevo_usuario(self):
        self._dlg_usuario(None)

    def _dlg_editar_usuario(self):
        sel = self.tv_usr.selection()
        if not sel:
            messagebox.showwarning("Seleccione", "Elija un usuario de la lista.")
            return
        uid = int(self.tv_usr.item(sel[0], "values")[0])
        u = usr.obtener_usuario_por_id(uid)
        if u:
            self._dlg_usuario(u)

    def _dlg_usuario(self, u=None):
        es_edicion = u is not None
        d = tk.Toplevel(self)
        d.title("Editar Usuario" if es_edicion else "Nuevo Usuario")
        d.resizable(False, False)
        d.configure(bg=C["bg"])
        d.grab_set()
        _center_win(d, 380, 390)
        d.columnconfigure(1, weight=1)

        campos = [("Nombre completo", "nombre"), ("Usuario (login)", "usuario"), ("Contraseña", "password")]
        entradas = {}

        for i, (lbl, key) in enumerate(campos):
            tk.Label(d, text=lbl, font=FONT_BOLD, bg=C["bg"], fg=C["text"]).grid(row=i, column=0, sticky="w", padx=20, pady=(12, 0))
            e = ttk.Entry(d, font=FONT_LABEL, show="•" if key == "password" else "")
            e.grid(row=i, column=1, padx=20, pady=(12, 0), ipady=5, sticky="ew")
            if es_edicion and key != "password":
                e.insert(0, u.get(key, ""))
            entradas[key] = e

        if es_edicion:
            tk.Label(d, text="(Dejar vacío para mantener contraseña)", font=("Segoe UI", 8), bg=C["bg"], fg=C["text_lt"]).grid(row=2, column=1, sticky="w", padx=20)

        tk.Label(d, text="Rol", font=FONT_BOLD, bg=C["bg"], fg=C["text"]).grid(row=3, column=0, sticky="w", padx=20, pady=(12, 0))
        var_rol = tk.StringVar(value=u["rol"] if es_edicion else "cajero")
        roles_box = tk.Frame(d, bg=C["bg"])
        roles_box.grid(row=3, column=1, sticky="w", padx=20, pady=(12, 0))
        for rol in ["admin", "cajero", "almacenero"]:
            tk.Radiobutton(roles_box, text=rol.title(), variable=var_rol, value=rol, font=FONT_LABEL, bg=C["bg"]).pack(anchor="w")

        def guardar():
            nombre = entradas["nombre"].get().strip()
            usuario_login = entradas["usuario"].get().strip()
            password = entradas["password"].get().strip()
            rol = var_rol.get()

            if es_edicion:
                res = usr.editar_usuario(u["id"], nombre, usuario_login, rol, password or None)
            else:
                res = usr.registrar_usuario(nombre, usuario_login, password, rol)

            if res["ok"]:
                messagebox.showinfo("Éxito", res["mensaje"], parent=d)
                d.destroy()
                self._cargar_usuarios()
            else:
                messagebox.showerror("Error", res["error"], parent=d)

        _btn(d, "Guardar Usuario", C["accent"], guardar).grid(row=4, column=0, columnspan=2, sticky="ew", padx=20, pady=16, ipady=4)

    def _activar_usuario(self):
        sel = self.tv_usr.selection()
        if not sel:
            messagebox.showwarning("Seleccione", "Elija un usuario.")
            return
        uid = int(self.tv_usr.item(sel[0], "values")[0])
        res = usr.cambiar_estado_usuario(uid, True)
        messagebox.showinfo("Éxito", res["mensaje"])
        self._cargar_usuarios()

    def _desactivar_usuario(self):
        sel = self.tv_usr.selection()
        if not sel:
            messagebox.showwarning("Seleccione", "Elija un usuario.")
            return
        uid = int(self.tv_usr.item(sel[0], "values")[0])
        if usr.sesion() and usr.sesion().id == uid:
            messagebox.showerror("Error", "No puedes desactivar tu propia cuenta activa.")
            return
        if messagebox.askyesno("Confirmar", "¿Desactivar a este usuario?"):
            res = usr.cambiar_estado_usuario(uid, False)
            messagebox.showinfo("Éxito", res["mensaje"])
            self._cargar_usuarios()


if __name__ == "__main__":
    MarketHubApp()
