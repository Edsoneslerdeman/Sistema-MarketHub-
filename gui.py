"""
MarketHub — Interfaz de Escritorio (Tkinter)
Sistema de Gestión para Minimercado MarketHub
Universidad Simón I. Patiño — Ingeniería en Sistemas
Estudiante: Edson Jesús Rodríguez Terrazas
"""
import sys, os, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from modules.database import inicializar_bd, get_connection
from modules import usuarios as usr
from modules import inventario as inv
from modules import ventas as ven
from modules import pagos as pag
from modules import reportes as rep

C = {
    "bg":"#EEF2F0","sidebar":"#2C3E35","sidebar_h":"#1E2D26",
    "accent":"#2E6B50","green":"#27A067","red":"#C0392B","yellow":"#D4880A",
    "white":"#FAFAF8","card":"#FFFFFF","text":"#1C2B22","text_lt":"#5A7265",
    "border":"#D4DDD8","row_even":"#FAFAF8","row_odd":"#EFF4F1",
    "header_bg":"#2E6B50","header_fg":"#FFFFFF","sel":"#4A9970",
}
FONT_TITLE=("Segoe UI",16,"bold"); FONT_LABEL=("Segoe UI",10)
FONT_BOLD=("Segoe UI",10,"bold"); FONT_SMALL=("Segoe UI",9)

def _aplicar_estilo():
    s=ttk.Style()
    try: s.theme_use("clam")
    except: pass
    s.configure("MH.Treeview",background=C["row_even"],fieldbackground=C["row_even"],
                rowheight=28,font=("Segoe UI",9))
    s.configure("MH.Treeview.Heading",background=C["header_bg"],foreground=C["header_fg"],
                font=("Segoe UI",9,"bold"),relief="flat",padding=(8,5))
    s.map("MH.Treeview.Heading",background=[("active",C["accent"])])
    s.map("MH.Treeview",background=[("selected",C["sel"])],foreground=[("selected","#FFF")])

def _make_tree(parent,cols,anchos=None,height=12):
    tv=ttk.Treeview(parent,columns=cols,show="headings",height=height,
                    style="MH.Treeview",selectmode="browse")
    for col in cols:
        w=(anchos or {}).get(col,110)
        tv.heading(col,text=col,anchor="center")
        tv.column(col,anchor="center",width=w,minwidth=40,stretch=True)
    tv.tag_configure("par",background=C["row_even"])
    tv.tag_configure("impar",background=C["row_odd"])
    tv.tag_configure("bajo",background="#FDE8E8",foreground=C["red"])
    return tv

def _tabla_frame(parent,cols,anchos=None,height=14):
    w=tk.Frame(parent,bg=C["bg"]); w.columnconfigure(0,weight=1); w.rowconfigure(0,weight=1)
    tv=_make_tree(w,cols,anchos,height)
    vsb=ttk.Scrollbar(w,orient="vertical",command=tv.yview)
    tv.configure(yscrollcommand=vsb.set)
    tv.grid(row=0,column=0,sticky="nsew"); vsb.grid(row=0,column=1,sticky="ns")
    return w,tv

def _fill_tree(tv,rows):
    for r in tv.get_children(): tv.delete(r)
    for i,vals in enumerate(rows):
        tv.insert("","end",values=vals,tags=("par" if i%2==0 else "impar",))

def _page_title(parent,title,subtitle=""):
    f=tk.Frame(parent,bg=C["bg"])
    tk.Label(f,text=title,font=FONT_TITLE,bg=C["bg"],fg=C["text"]).pack(anchor="w")
    if subtitle: tk.Label(f,text=subtitle,font=FONT_SMALL,bg=C["bg"],fg=C["text_lt"]).pack(anchor="w")
    return f

def _card(parent,title=""):
    f=tk.Frame(parent,bg=C["card"],highlightbackground=C["border"],highlightthickness=1)
    f.columnconfigure(0,weight=1)
    if title:
        tk.Label(f,text=title,font=FONT_BOLD,bg=C["card"],fg=C["text"],padx=12,pady=8).grid(row=0,column=0,sticky="w")
        tk.Frame(f,bg=C["border"],height=1).grid(row=1,column=0,sticky="ew")
    return f

def _kpi_card(parent,label,value,color,sub=""):
    f=tk.Frame(parent,bg=C["card"],highlightbackground=C["border"],highlightthickness=1)
    tk.Frame(f,bg=color,height=4).pack(fill="x")
    b=tk.Frame(f,bg=C["card"],padx=14,pady=10); b.pack(fill="both",expand=True)
    tk.Label(b,text=label,font=FONT_SMALL,bg=C["card"],fg=C["text_lt"]).pack(anchor="w")
    tk.Label(b,text=value,font=("Segoe UI",18,"bold"),bg=C["card"],fg=color).pack(anchor="w")
    if sub: tk.Label(b,text=sub,font=FONT_SMALL,bg=C["card"],fg=C["text_lt"]).pack(anchor="w")
    return f

def _btn(parent,text,color,cmd,**kw):
    return tk.Button(parent,text=text,font=FONT_SMALL,bg=color,fg="#FFF",relief="flat",
                     activebackground=C["sidebar_h"],activeforeground="#FFF",
                     padx=12,pady=6,cursor="hand2",command=cmd,**kw)

def _center_win(win,w,h):
    win.update_idletasks()
    x=(win.winfo_screenwidth()-w)//2; y=(win.winfo_screenheight()-h)//2
    win.geometry(f"{w}x{h}+{x}+{y}")

# ── LOGIN
class LoginWindow(tk.Toplevel):
    def __init__(self,master,on_success):
        super().__init__(master); self.on_success=on_success
        self.title("MarketHub — Iniciar Sesión"); self.resizable(False,False)
        self.configure(bg=C["bg"]); self.grab_set(); _center_win(self,380,430)
        hdr=tk.Frame(self,bg=C["accent"],height=110); hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr,text="🛒",font=("Segoe UI",32),bg=C["accent"],fg="white").pack(pady=(14,0))
        tk.Label(hdr,text="MarketHub",font=("Segoe UI",14,"bold"),bg=C["accent"],fg="white").pack()
        body=tk.Frame(self,bg=C["bg"],padx=36,pady=28); body.pack(fill="both",expand=True)
        tk.Label(body,text="Sistema de Gestión de Minimercado",font=FONT_SMALL,
                 bg=C["bg"],fg=C["text_lt"]).pack(pady=(0,20))
        for lbl,attr,show in [("Usuario","ent_user",""),("Contraseña","ent_pass","•")]:
            tk.Label(body,text=lbl,font=FONT_BOLD,bg=C["bg"],fg=C["text"],anchor="w").pack(fill="x")
            e=ttk.Entry(body,font=FONT_LABEL,show=show); e.pack(fill="x",pady=(2,12),ipady=6)
            setattr(self,attr,e)
        self.lbl_err=tk.Label(body,text="",font=FONT_SMALL,bg=C["bg"],fg=C["red"]); self.lbl_err.pack()
        _btn(body,"Ingresar",C["accent"],self._login).pack(fill="x",pady=(8,0))
        self.ent_user.bind("<Return>",lambda e:self.ent_pass.focus())
        self.ent_pass.bind("<Return>",lambda e:self._login())
        self.ent_user.focus()
        self.protocol("WM_DELETE_WINDOW", lambda: master.destroy())

    def _login(self):
        u,p=self.ent_user.get().strip(),self.ent_pass.get().strip()
        if not u or not p: self.lbl_err.config(text="Completa todos los campos."); return
        res=usr.iniciar_sesion(u,p)
        if res["ok"]: self.destroy(); self.on_success()
        else: self.lbl_err.config(text=res["error"]); self.ent_pass.delete(0,"end")

# ── APP PRINCIPAL 
class MarketHubApp(tk.Tk):
    def __init__(self):
        super().__init__(); self.withdraw()
        _aplicar_estilo(); inicializar_bd()
        usr.registrar_usuario("Administrador","admin","admin123","admin")
        usr.registrar_usuario("Cajero Demo","cajero","cajero123","cajero")
        self.title("MarketHub — Sistema de Gestión")
        self.configure(bg=C["bg"]); self.minsize(1000,620)
        self.carrito=ven.Carrito(); self._frame_actual=None
        LoginWindow(self,self._post_login); self.mainloop()

    def _post_login(self):
        self.deiconify()
        if sys.platform=="win32": self.state("zoomed")
        else: self.attributes("-zoomed",True)
        self._build_layout()
        if usr.sesion().rol=="cajero": self._mostrar_mis_ventas()
        else: self._mostrar_panel_control()

    def _build_layout(self):
        self.columnconfigure(1,weight=1); self.rowconfigure(0,weight=1)
        self.sidebar=tk.Frame(self,bg=C["sidebar"],width=215)
        self.sidebar.grid(row=0,column=0,sticky="ns"); self.sidebar.grid_propagate(False)
        self._build_sidebar()
        self.content=tk.Frame(self,bg=C["bg"])
        self.content.grid(row=0,column=1,sticky="nsew")
        self.content.columnconfigure(0,weight=1); self.content.rowconfigure(0,weight=1)

    def _build_sidebar(self):
        logo_f=tk.Frame(self.sidebar,bg=C["accent"],pady=18); logo_f.pack(fill="x")
        tk.Label(logo_f,text="🛒 MarketHub",font=("Segoe UI",13,"bold"),
                 bg=C["accent"],fg="white").pack()
        u=usr.sesion()
        tk.Label(logo_f,text=f"{u.nombre}\n[{u.rol}]",font=FONT_SMALL,
                 bg=C["accent"],fg="#B8D4C5",justify="center").pack(pady=(4,0))
        tk.Frame(self.sidebar,bg="#1A2B22",height=1).pack(fill="x",pady=6)
        self._btns_menu={}
        rol=u.rol
        menus=[]
        if rol=="admin":
            menus.append(("🏠  Panel de Control","panel",self._mostrar_panel_control))
        if rol=="cajero":
            menus.append(("📋  Mis Ventas","mis_ventas",self._mostrar_mis_ventas))
        menus+=[
            ("🛒  Punto de Venta","ventas",self._mostrar_ventas),
            ("📦  Inventario","inventario",self._mostrar_inventario),
            ("💳  Pagos","pagos",self._mostrar_pagos),
            ("📊  Reportes","reportes",self._mostrar_reportes),
            ("👤  Usuarios","usuarios",self._mostrar_usuarios),
        ]
        perms={"ventas":"ventas","inventario":"inventario","pagos":"pagos",
               "reportes":"reportes","usuarios":"usuarios"}
        for label,key,cmd in menus:
            req=perms.get(key)
            if req and not usr.requiere_permiso(req): continue
            b=tk.Button(self.sidebar,text=label,font=FONT_LABEL,bg=C["sidebar"],fg="#B8D4C5",
                        relief="flat",activebackground=C["accent"],activeforeground="white",
                        anchor="w",padx=20,pady=10,cursor="hand2",
                        command=lambda c=cmd,k=key:self._nav(c,k))
            b.pack(fill="x"); self._btns_menu[key]=b
        tk.Frame(self.sidebar,bg="#1A2B22",height=1).pack(fill="x",side="bottom",pady=4)
        tk.Button(self.sidebar,text="⬅  Cerrar Sesión",font=FONT_LABEL,bg=C["sidebar"],
                  fg="#F87171",relief="flat",activebackground="#3B0A0A",activeforeground="white",
                  anchor="w",padx=20,pady=10,cursor="hand2",
                  command=self._cerrar_sesion).pack(fill="x",side="bottom")

    def _nav(self,cmd,key):
        for k,b in self._btns_menu.items(): b.config(bg=C["sidebar"],fg="#B8D4C5")
        if key in self._btns_menu: self._btns_menu[key].config(bg=C["accent"],fg="white")
        cmd()

    def _set_frame(self,frame):
        if self._frame_actual: self._frame_actual.destroy()
        self._frame_actual=frame
        frame.grid(row=0,column=0,sticky="nsew",padx=20,pady=20)

    def _cerrar_sesion(self):
        usr.cerrar_sesion(); self.destroy(); MarketHubApp()

    # ── MIS VENTAS (cajero) 
    def _mostrar_mis_ventas(self):
        self._nav(lambda:None,"mis_ventas")
        f=tk.Frame(self.content,bg=C["bg"]); f.columnconfigure(0,weight=1); f.rowconfigure(2,weight=1)
        cajero=usr.sesion(); hoy=datetime.date.today().isoformat()
        _page_title(f,"📋 Mis Ventas",f"Ventas del día — {cajero.nombre}").grid(
            row=0,column=0,sticky="w",pady=(0,10))
        conn=get_connection()
        res=conn.execute("SELECT COUNT(*) as n,COALESCE(SUM(total),0) as t FROM ventas WHERE usuario_id=? AND date(fecha)=?",
                         (cajero.id,hoy)).fetchone()
        conn.close()
        kpi_f=tk.Frame(f,bg=C["bg"]); kpi_f.grid(row=1,column=0,sticky="ew",pady=(0,10))
        kpi_f.columnconfigure((0,1),weight=1)
        _kpi_card(kpi_f,"Ventas realizadas hoy",str(res["n"]),C["accent"]).grid(row=0,column=0,padx=(0,5),sticky="nsew")
        _kpi_card(kpi_f,"Total facturado (Bs.)",f"{res['t']:.2f}",C["green"]).grid(row=0,column=1,padx=(5,0),sticky="nsew")
        wrap,tv=_tabla_frame(f,("Venta #","Hora","Total Bs.","Método","Cambio Bs."),
                             {"Venta #":70,"Hora":90,"Total Bs.":100,"Método":100,"Cambio Bs.":100},16)
        wrap.grid(row=2,column=0,sticky="nsew")
        conn=get_connection()
        ventas=conn.execute("""SELECT id,strftime('%H:%M:%S',fecha) as hora,total,metodo_pago,
                               COALESCE(cambio,0) as cambio FROM ventas
                               WHERE usuario_id=? AND date(fecha)=? ORDER BY fecha DESC""",
                            (cajero.id,hoy)).fetchall()
        conn.close()
        _fill_tree(tv,[(v["id"],v["hora"],f"{v['total']:.2f}",v["metodo_pago"],f"{v['cambio']:.2f}") for v in ventas])
        def ver_det(event):
            sel=tv.selection()
            if not sel: return
            vid=int(tv.item(sel[0],"values")[0]); venta=ven.obtener_venta(vid)
            if not venta: return
            lines=["Detalle Venta #"+str(vid),"Fecha: "+venta["fecha"],
                   "Metodo: "+venta["metodo_pago"],"","Productos:"]
            for d in venta["detalle"]:
                lines.append(f"  - {d['producto']} x{d['cantidad']} = Bs.{d['subtotal']:.2f}")
            # Obtener monto recibido del cliente
            conn_d=get_connection()
            pago_row=conn_d.execute("SELECT monto FROM pagos WHERE venta_id=? ORDER BY id DESC LIMIT 1",(vid,)).fetchone()
            conn_d.close()
            monto_rec=pago_row["monto"] if pago_row else venta["total"]
            cambio_real=max(0.0,round(monto_rec-venta["total"],2))
            lines+=["",
                    f"Total: Bs.{venta['total']:.2f}",
                    f"Monto recibido: Bs.{monto_rec:.2f}",
                    f"Cambio entregado: Bs.{cambio_real:.2f}"]
            messagebox.showinfo("Detalle","\n".join(lines))
        tv.bind("<Double-1>",ver_det)
        tk.Label(f,text="Doble clic en una venta para ver detalle",font=FONT_SMALL,
                 bg=C["bg"],fg=C["text_lt"]).grid(row=3,column=0,sticky="w",pady=(4,0))
        self._set_frame(f)

    # ── PANEL DE CONTROL (admin) 
    def _mostrar_panel_control(self):
        self._nav(lambda:None,"panel")
        f=tk.Frame(self.content,bg=C["bg"]); f.columnconfigure((0,1,2,3),weight=1); f.rowconfigure(2,weight=1)
        _page_title(f,"🏠 Panel de Control","Resumen del día").grid(
            row=0,column=0,columnspan=4,sticky="w",pady=(0,14))
        dash=rep.dashboard_hoy(); cierre=ven.cierre_caja(); ri=rep.reporte_inventario()
        kpis=[
            ("Ventas hoy",str(dash.get("ventas_hoy",0)),C["accent"]),
            ("Ingresos (Bs.)",f"{dash.get('ingresos_hoy',0.0):.2f}",C["green"]),
            ("Alertas stock",str(dash.get("alertas_stock",0)),C["red"] if dash.get("alertas_stock") else C["green"]),
            ("Productos activos",str(ri.get("total_productos_activos",0)),C["yellow"]),
        ]
        for col,(lbl,val,color) in enumerate(kpis):
            _kpi_card(f,lbl,val,color).grid(row=1,column=col,padx=5,pady=4,sticky="nsew")
        # Top productos
        tp_w=tk.Frame(f,bg=C["bg"]); tp_w.grid(row=2,column=0,columnspan=2,sticky="nsew",padx=(0,6),pady=6)
        tp_w.columnconfigure(0,weight=1); tp_w.rowconfigure(1,weight=1)
        tk.Label(tp_w,text="🏆 Top Productos del Día",font=FONT_BOLD,bg=C["bg"],fg=C["text"]).grid(row=0,column=0,sticky="w",pady=(0,4))
        _,tv_tp=_tabla_frame(tp_w,("Producto","Unidades","Ingreso Bs."),
                             {"Producto":220,"Unidades":90,"Ingreso Bs.":100},7)
        tv_tp.master.grid(row=1,column=0,sticky="nsew")
        _fill_tree(tv_tp,[(p["nombre"],p["uds"],f"{p['ingreso']:.2f}") for p in cierre.get("top_5_productos",[])])
        # Ventas por método
        pm_w=tk.Frame(f,bg=C["bg"]); pm_w.grid(row=2,column=2,columnspan=2,sticky="nsew",padx=(6,0),pady=6)
        pm_w.columnconfigure(0,weight=1); pm_w.rowconfigure(1,weight=1)
        tk.Label(pm_w,text="💳 Ventas por Método de Pago",font=FONT_BOLD,bg=C["bg"],fg=C["text"]).grid(row=0,column=0,sticky="w",pady=(0,4))
        _,tv_pm=_tabla_frame(pm_w,("Método","Cantidad","Total Bs."),
                             {"Método":110,"Cantidad":90,"Total Bs.":100},7)
        tv_pm.master.grid(row=1,column=0,sticky="nsew")
        _fill_tree(tv_pm,[(m["metodo_pago"],m["n"],f"{m['t']:.2f}") for m in cierre.get("por_metodo_pago",[])])
        # Botón reiniciar
        _btn(f,"🔄 Reiniciar sistema",C["red"],self._confirmar_reinicio).grid(
            row=3,column=0,columnspan=4,sticky="e",pady=(8,0))
        self._set_frame(f)

    def _confirmar_reinicio(self):
        if not messagebox.askyesno("Reiniciar sistema",
            "Esto eliminara TODOS los datos (ventas, productos, pagos).\n"
            "Solo quedara el usuario actual. No se puede deshacer."):
            return
        c2=simpledialog.askstring("Confirmar","Escribe REINICIAR para confirmar:",parent=self)
        if c2!="REINICIAR": messagebox.showinfo("Cancelado","Reinicio cancelado."); return
        u=usr.sesion()
        conn=get_connection()
        for t in ["detalle_ventas","movimientos_inventario","pagos","ventas","productos","categorias"]:
            conn.execute(f"DELETE FROM {t}")
        # Resetear secuencias de IDs
        for t in ["productos","categorias","ventas","detalle_ventas","pagos","movimientos_inventario"]:
            conn.execute(f"DELETE FROM sqlite_sequence WHERE name=?",  (t,))
        conn.execute("DELETE FROM usuarios WHERE id!=?",(u.id,))
        # Guardar datos del usuario actual
        cur_u=conn.execute("SELECT nombre,usuario,password,rol FROM usuarios WHERE id=?",(u.id,)).fetchone()
        conn.execute("DELETE FROM usuarios WHERE id=?",(u.id,))
        conn.execute("DELETE FROM sqlite_sequence WHERE name='usuarios'")
        # Reinsertar con ID 1
        conn.execute("INSERT INTO usuarios (nombre,usuario,password,rol) VALUES (?,?,?,?)",
                     (cur_u["nombre"],cur_u["usuario"],cur_u["password"],cur_u["rol"]))
        conn.commit(); conn.close()
        # Actualizar sesión
        usr.iniciar_sesion(cur_u["usuario"], "")  # sesion se recarga al reingresar
        self.carrito.limpiar()
        messagebox.showinfo("Reiniciado",f"Sistema reiniciado. Solo queda el usuario '{u.usuario}'.")
        self._mostrar_panel_control()

    # ── PUNTO DE VENTA 
    def _mostrar_ventas(self):
        f=tk.Frame(self.content,bg=C["bg"]); f.columnconfigure(0,weight=2); f.columnconfigure(1,weight=1); f.rowconfigure(1,weight=1)
        _page_title(f,"🛒 Punto de Venta","Registra ventas y procesa pagos").grid(row=0,column=0,columnspan=2,sticky="w",pady=(0,10))
        # Izquierda
        left=tk.Frame(f,bg=C["card"],highlightbackground=C["border"],highlightthickness=1)
        left.grid(row=1,column=0,sticky="nsew",padx=(0,8)); left.columnconfigure(0,weight=1); left.rowconfigure(2,weight=1)
        bus=tk.Frame(left,bg=C["card"],padx=10,pady=10); bus.grid(row=0,column=0,sticky="ew"); bus.columnconfigure(0,weight=1)
        tk.Label(bus,text="Código producto:",font=FONT_SMALL,bg=C["card"],fg=C["text_lt"]).grid(row=0,column=0,sticky="w")
        tk.Label(bus,text="Cant:",font=FONT_SMALL,bg=C["card"],fg=C["text_lt"]).grid(row=0,column=1,padx=(8,0))
        self.ent_codigo=ttk.Entry(bus,font=FONT_LABEL); self.ent_codigo.grid(row=1,column=0,sticky="ew",ipady=5)
        self.ent_cant=ttk.Entry(bus,font=FONT_LABEL,width=5); self.ent_cant.insert(0,"1"); self.ent_cant.grid(row=1,column=1,padx=(8,0),ipady=5)
        _btn(bus,"➕ Agregar",C["accent"],self._agregar_al_carrito).grid(row=1,column=2,padx=(6,0),ipady=4)
        self.ent_codigo.bind("<Return>",lambda e:self._agregar_al_carrito())
        self.lbl_prod_info=tk.Label(bus,text="",font=FONT_SMALL,bg=C["card"],fg=C["green"])
        self.lbl_prod_info.grid(row=2,column=0,columnspan=3,sticky="w",pady=(4,0))
        tk.Frame(left,bg=C["border"],height=1).grid(row=1,column=0,sticky="ew")
        self.tv_carrito=_make_tree(left,("Producto","Cant.","Precio Unit.","Subtotal"),
                                    {"Producto":200,"Cant.":55,"Precio Unit.":110,"Subtotal":100},12)
        self.tv_carrito.grid(row=2,column=0,sticky="nsew",padx=4,pady=4)
        q_btn=tk.Button(left,text="🗑 Quitar seleccionado",font=FONT_SMALL,bg="#FDE8E8",fg=C["red"],
                        relief="flat",pady=4,cursor="hand2",command=self._quitar_del_carrito)
        q_btn.grid(row=3,column=0,sticky="w",padx=10,pady=6)
        # Derecha
        right=tk.Frame(f,bg=C["card"],highlightbackground=C["border"],highlightthickness=1)
        right.grid(row=1,column=1,sticky="nsew")
        inner=tk.Frame(right,bg=C["card"],padx=16,pady=10); inner.pack(fill="both",expand=True)
        inner.columnconfigure(0,weight=1)
        tk.Label(inner,text="Cobro",font=FONT_BOLD,bg=C["card"],fg=C["text"]).pack(anchor="w")
        tk.Frame(inner,bg=C["border"],height=1).pack(fill="x",pady=8)
        self.lbl_total=tk.Label(inner,text="Bs. 0.00",font=("Segoe UI",26,"bold"),bg=C["card"],fg=C["accent"])
        self.lbl_total.pack()
        tk.Label(inner,text="TOTAL A COBRAR",font=FONT_SMALL,bg=C["card"],fg=C["text_lt"]).pack()
        tk.Frame(inner,bg=C["border"],height=1).pack(fill="x",pady=10)
        tk.Label(inner,text="Método de pago:",font=FONT_BOLD,bg=C["card"],fg=C["text"],anchor="w").pack(fill="x")
        self.var_metodo=tk.StringVar(value="efectivo")
        for m,lbl in [("efectivo","💵 Efectivo"),("qr","📱 QR"),("tarjeta","💳 Tarjeta")]:
            tk.Radiobutton(inner,text=lbl,variable=self.var_metodo,value=m,font=FONT_LABEL,
                           bg=C["card"],fg=C["text"],selectcolor=C["card"],
                           activebackground=C["card"]).pack(anchor="w",pady=1)
        tk.Label(inner,text="Monto recibido (Bs.):",font=FONT_BOLD,bg=C["card"],fg=C["text"],anchor="w").pack(fill="x",pady=(10,0))
        self.ent_monto=ttk.Entry(inner,font=("Segoe UI",13)); self.ent_monto.pack(fill="x",ipady=6,pady=(4,0))
        self.ent_monto.bind("<KeyRelease>",self._calcular_cambio_live)
        self.lbl_cambio=tk.Label(inner,text="Cambio: Bs. 0.00",font=FONT_BOLD,bg=C["card"],fg=C["green"])
        self.lbl_cambio.pack(pady=8)
        _btn(inner,"✅ REGISTRAR VENTA",C["green"],self._registrar_venta).pack(fill="x",pady=4,ipady=6)
        tk.Button(inner,text="🗑 Limpiar carrito",font=FONT_SMALL,bg="#FDE8E8",fg=C["red"],
                  relief="flat",pady=6,cursor="hand2",command=self._limpiar_carrito).pack(fill="x")
        self._actualizar_carrito_vista(); self._set_frame(f); self.ent_codigo.focus()

    def _calcular_cambio_live(self,event=None):
        try:
            monto=float(self.ent_monto.get().strip())
            cambio=max(0.0,round(monto-self.carrito.total,2))
            self.lbl_cambio.config(text=f"Cambio: Bs. {cambio:.2f}",fg=C["green"])
        except ValueError:
            self.lbl_cambio.config(text="Cambio: Bs. 0.00",fg=C["green"])

    def _agregar_al_carrito(self):
        codigo=self.ent_codigo.get().strip()
        try: cant=int(self.ent_cant.get().strip())
        except: cant=1
        if not codigo: return
        res=self.carrito.agregar(codigo,cant)
        self.lbl_prod_info.config(text=("✓ "+res["mensaje"]) if res["ok"] else ("✗ "+res["error"]),
                                   fg=C["green"] if res["ok"] else C["red"])
        self.ent_codigo.delete(0,"end"); self.ent_cant.delete(0,"end"); self.ent_cant.insert(0,"1")
        self._actualizar_carrito_vista()

    def _quitar_del_carrito(self):
        sel=self.tv_carrito.selection()
        if not sel: return
        idx=self.tv_carrito.index(sel[0])
        if idx<len(self.carrito.items):
            nombre=self.carrito.items[idx].nombre
            self.carrito.quitar(self.carrito.items[idx].producto_id)
            self.lbl_prod_info.config(text=f"✗ '{nombre}' quitado.",fg=C["text_lt"])
            self._actualizar_carrito_vista()

    def _limpiar_carrito(self):
        self.carrito.limpiar(); self._actualizar_carrito_vista()
        self.lbl_prod_info.config(text=""); self.lbl_cambio.config(text="Cambio: Bs. 0.00",fg=C["green"])

    def _actualizar_carrito_vista(self):
        _fill_tree(self.tv_carrito,[(i.nombre,i.cantidad,f"Bs. {i.precio_unit:.2f}",f"Bs. {i.subtotal:.2f}") for i in self.carrito.items])
        if hasattr(self,"lbl_total"): self.lbl_total.config(text=f"Bs. {self.carrito.total:.2f}")

    def _registrar_venta(self):
        if not self.carrito.items: messagebox.showwarning("Carrito vacío","Agrega productos antes de cobrar."); return
        metodo=self.var_metodo.get()
        txt=self.ent_monto.get().strip()
        try: monto=float(txt) if txt else self.carrito.total
        except: messagebox.showerror("Error","Monto inválido."); return
        total=self.carrito.total; cambio=max(0.0,round(monto-total,2))
        res=ven.registrar_venta(self.carrito,metodo,monto)
        if res["ok"]:
            self.lbl_cambio.config(text=f"Cambio: Bs. {cambio:.2f}")
            messagebox.showinfo("Venta Registrada",
                f"Venta #{res['venta_id']} completada.  Total: Bs. {total:.2f}  Monto recibido: Bs. {monto:.2f}  Cambio: Bs. {cambio:.2f}")
            self._limpiar_carrito(); self.ent_monto.delete(0,"end")
        else: messagebox.showerror("Error en venta",res["error"])

    # ── INVENTARIO 
    def _mostrar_inventario(self):
        f=tk.Frame(self.content,bg=C["bg"]); f.columnconfigure(0,weight=1); f.rowconfigure(2,weight=1)
        _page_title(f,"📦 Inventario","Gestión de productos y stock").grid(row=0,column=0,sticky="w",pady=(0,10))
        bar=tk.Frame(f,bg=C["bg"]); bar.grid(row=1,column=0,sticky="ew",pady=(0,8))
        _btn(bar,"➕ Nuevo",C["accent"],self._dlg_nuevo_producto).pack(side="left",padx=(0,6))
        _btn(bar,"✏️ Editar",C["yellow"],self._dlg_editar_producto).pack(side="left",padx=(0,6))
        _btn(bar,"📥 Entrada Stock",C["green"],self._dlg_entrada_stock).pack(side="left",padx=(0,6))
        _btn(bar,"🗑 Eliminar",C["red"],self._eliminar_producto).pack(side="left",padx=(0,6))
        _btn(bar,"🔄 Actualizar",C["text_lt"],self._cargar_inventario).pack(side="left")
        tabla_f=tk.Frame(f,bg=C["bg"]); tabla_f.grid(row=2,column=0,sticky="nsew")
        tabla_f.columnconfigure(0,weight=1); tabla_f.rowconfigure(0,weight=1)
        cols=("ID","Nombre","Código","Precio Bs.","Stock","Mín.","Categoría")
        anchos={"ID":45,"Nombre":200,"Código":100,"Precio Bs.":90,"Stock":70,"Mín.":60,"Categoría":120}
        self.tv_inv=_make_tree(tabla_f,cols,anchos,20)
        vsb=ttk.Scrollbar(tabla_f,orient="vertical",command=self.tv_inv.yview)
        self.tv_inv.configure(yscrollcommand=vsb.set)
        self.tv_inv.grid(row=0,column=0,sticky="nsew"); vsb.grid(row=0,column=1,sticky="ns")
        self._cargar_inventario(); self._set_frame(f)

    def _cargar_inventario(self,bajo_stock=False):
        for r in self.tv_inv.get_children(): self.tv_inv.delete(r)
        # Obtener IDs de bajo stock directamente sin depender de reporte_inventario
        conn=get_connection()
        bajo_rows=conn.execute("SELECT id FROM productos WHERE activo=1 AND stock<=stock_minimo").fetchall()
        conn.close()
        bajo_ids={row[0] for row in bajo_rows}
        for i,p in enumerate(inv.listar_productos(con_bajo_stock=bajo_stock)):
            pid=p["id"] if "id" in p.keys() else p[0]
            tag="bajo" if pid in bajo_ids else ("par" if i%2==0 else "impar")
            self.tv_inv.insert("","end",tags=(tag,),
                values=(pid,p["nombre"],p["codigo"],f"{p['precio']:.2f}",
                        p["stock"],p["stock_minimo"],p.get("categoria") or "—"))

    def _dlg_nuevo_producto(self):
        self._dlg_producto(None)

    def _dlg_editar_producto(self):
        sel=self.tv_inv.selection()
        if not sel: messagebox.showwarning("Selecciona","Elige un producto de la tabla."); return
        vals=self.tv_inv.item(sel[0],"values")
        conn=get_connection()
        prod=conn.execute("SELECT * FROM productos WHERE id=?",(int(vals[0]),)).fetchone()
        conn.close()
        if prod: self._dlg_producto(dict(prod))

    def _dlg_producto(self,prod=None):
        es_edicion=prod is not None
        d=tk.Toplevel(self); d.title("Editar Producto" if es_edicion else "Nuevo Producto")
        d.resizable(False,False); d.configure(bg=C["bg"]); d.grab_set()
        _center_win(d,400,480); d.columnconfigure(1,weight=1)
        campos=[("Nombre","nombre"),("Código","codigo"),("Precio (Bs.)","precio"),
                ("Stock","stock"),("Stock mínimo","stock_min")]
        entradas={}
        for i,(lbl,key) in enumerate(campos):
            tk.Label(d,text=lbl,font=FONT_BOLD,bg=C["bg"],fg=C["text"]).grid(row=i,column=0,sticky="w",padx=20,pady=(10,0))
            e=ttk.Entry(d,font=FONT_LABEL); e.grid(row=i,column=1,padx=20,pady=(10,0),ipady=4,sticky="ew")
            if es_edicion:
                val_map={"nombre":prod.get("nombre",""),"codigo":prod.get("codigo",""),
                         "precio":str(prod.get("precio",0)),"stock":str(prod.get("stock",0)),
                         "stock_min":str(prod.get("stock_minimo",5))}
                e.insert(0,val_map.get(key,""))
            entradas[key]=e
        tk.Label(d,text="Categoría",font=FONT_BOLD,bg=C["bg"],fg=C["text"]).grid(row=len(campos),column=0,sticky="w",padx=20,pady=(10,0))
        cats=inv.listar_categorias(); cat_nombres=[c["nombre"] for c in cats] or ["Sin categoría"]
        var_cat=tk.StringVar(value=cat_nombres[0])
        if es_edicion and prod.get("categoria_id"):
            cat_match=[c["nombre"] for c in cats if c["id"]==prod["categoria_id"]]
            if cat_match: var_cat.set(cat_match[0])
        cb=ttk.Combobox(d,textvariable=var_cat,values=cat_nombres,state="readonly",font=FONT_LABEL)
        cb.grid(row=len(campos),column=1,padx=20,pady=(10,0),sticky="ew")
        tk.Button(d,text="+ Nueva categoría",font=FONT_SMALL,bg=C["bg"],fg=C["accent"],relief="flat",cursor="hand2",
                  command=lambda:self._nueva_categoria(cb,var_cat)).grid(row=len(campos)+1,column=1,sticky="w",padx=20)
        def guardar():
            try:
                nombre=entradas["nombre"].get().strip(); codigo=entradas["codigo"].get().strip()
                precio=float(entradas["precio"].get()); stock=int(entradas["stock"].get())
                smin=int(entradas["stock_min"].get())
            except: messagebox.showerror("Error","Precio y stock deben ser números.",parent=d); return
            if not nombre or not codigo: messagebox.showerror("Error","Nombre y código son obligatorios.",parent=d); return
            cat_id=next((c["id"] for c in cats if c["nombre"]==var_cat.get()),None)
            if es_edicion:
                conn=get_connection()
                conn.execute("UPDATE productos SET nombre=?,codigo=?,precio=?,stock=?,stock_minimo=?,categoria_id=? WHERE id=?",
                             (nombre,codigo,precio,stock,smin,cat_id,prod["id"]))
                conn.commit(); conn.close()
                messagebox.showinfo("✅",f"'{nombre}' actualizado.",parent=d)
            else:
                res=inv.agregar_producto(nombre,codigo,precio,stock,smin,cat_id)
                if not res["ok"]: messagebox.showerror("Error",res["error"],parent=d); return
                messagebox.showinfo("✅",f"'{nombre}' registrado.",parent=d)
            d.destroy(); self._cargar_inventario()
        _btn(d,"Guardar",C["accent"],guardar).grid(row=len(campos)+2,column=0,columnspan=2,sticky="ew",padx=20,pady=16,ipady=4)

    def _nueva_categoria(self,combo,var):
        nombre=simpledialog.askstring("Nueva categoría","Nombre:",parent=self)
        if nombre:
            inv.agregar_categoria(nombre.strip())
            cats=inv.listar_categorias(); nombres=[c["nombre"] for c in cats]
            combo.config(values=nombres); var.set(nombre.strip())

    def _dlg_entrada_stock(self):
        sel=self.tv_inv.selection()
        if not sel: messagebox.showwarning("Selecciona","Elige un producto."); return
        vals=self.tv_inv.item(sel[0],"values"); pid,nombre=int(vals[0]),vals[1]
        cant=simpledialog.askinteger("Entrada de stock",f"Unidades a agregar a '{nombre}':",parent=self,minvalue=1)
        if cant:
            res=inv.entrada_stock(pid,cant)
            if res["ok"]: messagebox.showinfo("✅",res["mensaje"]); self._cargar_inventario()
            else: messagebox.showerror("Error",res["error"])

    def _eliminar_producto(self):
        sel=self.tv_inv.selection()
        if not sel: messagebox.showwarning("Selecciona","Elige un producto."); return
        vals=self.tv_inv.item(sel[0],"values"); pid,nombre=int(vals[0]),vals[1]
        if not messagebox.askyesno("Confirmar",f"¿Eliminar '{nombre}'?"): return
        conn=get_connection(); conn.execute("UPDATE productos SET activo=0 WHERE id=?",(pid,))
        conn.commit(); conn.close()
        messagebox.showinfo("✅",f"'{nombre}' eliminado."); self._cargar_inventario()

    # ── PAGOS 
    def _mostrar_pagos(self):
        f=tk.Frame(self.content,bg=C["bg"]); f.columnconfigure(0,weight=1); f.rowconfigure(2,weight=1)
        _page_title(f,"💳 Pagos","Historial de transacciones del día").grid(row=0,column=0,sticky="w",pady=(0,10))
        # KPIs: usar total real de venta (no monto recibido del cliente)
        conn_kpi=get_connection()
        hoy_kpi=datetime.date.today().isoformat()
        kpi_rows=conn_kpi.execute("""
            SELECT v.metodo_pago as metodo, COUNT(*) as n, SUM(v.total) as total
            FROM ventas v WHERE date(v.fecha)=? GROUP BY v.metodo_pago
        """,(hoy_kpi,)).fetchall()
        conn_kpi.close()
        kpi_data={"efectivo":{"n":0,"total":0.0},"qr":{"n":0,"total":0.0},"tarjeta":{"n":0,"total":0.0}}
        for r in kpi_rows: kpi_data[r["metodo"]]={"n":r["n"],"total":round(r["total"],2)}
        kpi_f=tk.Frame(f,bg=C["bg"]); kpi_f.grid(row=1,column=0,sticky="ew",pady=(0,10)); kpi_f.columnconfigure((0,1,2),weight=1)
        for col,m in enumerate(["efectivo","qr","tarjeta"]):
            datos=kpi_data[m]; icons={"efectivo":"💵","qr":"📱","tarjeta":"💳"}
            _kpi_card(kpi_f,f"{icons[m]} {m.title()}",f"Bs. {datos['total']:.2f}",C["accent"],f"{datos['n']} transac.").grid(row=0,column=col,padx=5,sticky="nsew")
        cols=("ID","Venta #","Método","Total Bs.","Recibido Bs.","Cambio Bs.","Estado","Fecha")
        anchos={"ID":40,"Venta #":60,"Método":80,"Total Bs.":85,"Recibido Bs.":90,"Cambio Bs.":80,"Estado":80,"Fecha":150}
        wrap,self.tv_pagos=_tabla_frame(f,cols,anchos,16)
        wrap.grid(row=2,column=0,sticky="nsew")
        conn=get_connection()
        rows=conn.execute("""SELECT pg.id,pg.venta_id,pg.metodo,v.total as total_v,
                              pg.monto as recibido,
                              CASE WHEN pg.monto > v.total THEN ROUND(pg.monto - v.total, 2) ELSE 0.0 END as cambio,
                              pg.estado,pg.fecha FROM pagos pg
                              JOIN ventas v ON pg.venta_id=v.id ORDER BY pg.fecha DESC""").fetchall()
        conn.close()
        _fill_tree(self.tv_pagos,[(r["id"],r["venta_id"],r["metodo"],f"{r['total_v']:.2f}",
                                   f"{r['recibido']:.2f}",f"{r['cambio']:.2f}",r["estado"],r["fecha"]) for r in rows])
        self._set_frame(f)

    # ── REPORTES 
    def _mostrar_reportes(self):
        f=tk.Frame(self.content,bg=C["bg"]); f.columnconfigure(0,weight=1); f.rowconfigure(2,weight=1)
        _page_title(f,"📊 Reportes","Análisis de ventas e inventario").grid(row=0,column=0,sticky="w",pady=(0,10))
        ctrl=tk.Frame(f,bg=C["bg"]); ctrl.grid(row=1,column=0,sticky="ew",pady=(0,8))
        hoy=datetime.date.today().isoformat()
        tk.Label(ctrl,text="Desde:",font=FONT_BOLD,bg=C["bg"]).pack(side="left")
        self.ent_fi=ttk.Entry(ctrl,font=FONT_LABEL,width=12); self.ent_fi.insert(0,hoy); self.ent_fi.pack(side="left",padx=6,ipady=4)
        tk.Label(ctrl,text="Hasta:",font=FONT_BOLD,bg=C["bg"]).pack(side="left")
        self.ent_ff=ttk.Entry(ctrl,font=FONT_LABEL,width=12); self.ent_ff.insert(0,hoy); self.ent_ff.pack(side="left",padx=6,ipady=4)
        _btn(ctrl,"🔍 Generar",C["accent"],self._generar_reporte).pack(side="left",padx=8)
        nb=ttk.Notebook(f); nb.grid(row=2,column=0,sticky="nsew")
        # Ventas
        tab_v=tk.Frame(nb,bg=C["card"]); nb.add(tab_v,text="  Ventas  ")
        tab_v.columnconfigure(0,weight=1); tab_v.rowconfigure(1,weight=1)
        self.lbl_rv=tk.Label(tab_v,text="",font=FONT_SMALL,bg=C["card"],fg=C["text"])
        self.lbl_rv.grid(row=0,column=0,sticky="w",padx=12,pady=6)
        _,self.tv_rv=_tabla_frame(tab_v,("Día","Transacciones","Total Bs."),{"Día":130,"Transacciones":110,"Total Bs.":110},14)
        self.tv_rv.master.grid(row=1,column=0,sticky="nsew",padx=4)
        # Top Productos
        tab_p=tk.Frame(nb,bg=C["card"]); nb.add(tab_p,text="  Top Productos  ")
        tab_p.columnconfigure(0,weight=1); tab_p.rowconfigure(0,weight=1)
        _,self.tv_rp=_tabla_frame(tab_p,("Producto","Código","Unidades","Ingreso Bs."),
                                   {"Producto":210,"Código":100,"Unidades":90,"Ingreso Bs.":110},16)
        self.tv_rp.master.grid(row=0,column=0,sticky="nsew",padx=4,pady=4)
        # Inventario
        tab_i=tk.Frame(nb,bg=C["card"]); nb.add(tab_i,text="  Inventario  ")
        tab_i.columnconfigure(0,weight=1); tab_i.rowconfigure(1,weight=1)
        self.lbl_ri=tk.Label(tab_i,text="",font=FONT_SMALL,bg=C["card"],fg=C["text"])
        self.lbl_ri.grid(row=0,column=0,sticky="w",padx=12,pady=6)
        _,self.tv_ri=_tabla_frame(tab_i,("Producto","Código","Stock","Mínimo"),
                                   {"Producto":210,"Código":100,"Stock":80,"Mínimo":80},14)
        self.tv_ri.master.grid(row=1,column=0,sticky="nsew",padx=4)
        # Detalle Ventas
        tab_d=tk.Frame(nb,bg=C["card"]); nb.add(tab_d,text="  Detalle Ventas  ")
        tab_d.columnconfigure(0,weight=1); tab_d.rowconfigure(0,weight=1)
        _,self.tv_rd=_tabla_frame(tab_d,("Venta #","Fecha","Cajero","Producto","Cant.","Precio","Subtotal","Método","Pagó","Cambio"),
                                   {"Venta #":65,"Fecha":140,"Cajero":100,"Producto":160,"Cant.":50,
                                    "Precio":80,"Subtotal":80,"Método":80,"Pagó":80,"Cambio":70},16)
        self.tv_rd.master.grid(row=0,column=0,sticky="nsew",padx=4,pady=4)
        self._generar_reporte(); self._set_frame(f)

    def _generar_reporte(self):
        if not hasattr(self,"ent_fi"): return
        fi=self.ent_fi.get().strip(); ff=self.ent_ff.get().strip()
        rv=rep.reporte_ventas(fi,ff)
        if rv["ok"]:
            r=rv["resumen"]
            self.lbl_rv.config(text=f"Transacciones: {r['total_transacciones']}  |  Ingresos: Bs.{r['ingresos_brutos']:.2f}  |  Ticket prom.: Bs.{r['ticket_promedio']:.2f}")
            _fill_tree(self.tv_rv,[(d["dia"],d["n"],f"{d['total']:.2f}") for d in rv["por_dia"]])
        tp=rep.reporte_top_productos(fi,ff)
        if tp["ok"]: _fill_tree(self.tv_rp,[(p["nombre"],p["codigo"],p["unidades_vendidas"],f"{p['ingresos']:.2f}") for p in tp["top_productos"]])
        ri=rep.reporte_inventario()
        if ri["ok"] and hasattr(self,"lbl_ri"):
            self.lbl_ri.config(text=f"Activos: {ri['total_productos_activos']}  |  Valor: Bs.{ri['valor_inventario_bs']:.2f}  |  Sin stock: {len(ri['sin_stock'])}")
            conn=get_connection()
            bajo_rows=conn.execute("SELECT id FROM productos WHERE activo=1 AND stock<=stock_minimo").fetchall()
            conn.close()
            bajo_ids={row[0] for row in bajo_rows}
            todos=inv.listar_productos()
            for r in self.tv_ri.get_children(): self.tv_ri.delete(r)
            for i,p in enumerate(todos):
                pid=p["id"] if "id" in p.keys() else p[0]
                tag="bajo" if pid in bajo_ids else ("par" if i%2==0 else "impar")
                self.tv_ri.insert("","end",tags=(tag,),values=(p["nombre"],p["codigo"],p["stock"],p["stock_minimo"]))
        if hasattr(self,"tv_rd"):
            conn=get_connection()
            detalles=conn.execute("""SELECT v.id,v.fecha,u.nombre as cajero,p.nombre as producto,
                                      d.cantidad,d.precio_unit,d.subtotal,v.metodo_pago,
                                      COALESCE(v.monto_pago,v.total) as pago,COALESCE(v.cambio,0) as cambio
                                      FROM detalle_ventas d JOIN ventas v ON d.venta_id=v.id
                                      JOIN productos p ON d.producto_id=p.id
                                      JOIN usuarios u ON v.usuario_id=u.id
                                      WHERE date(v.fecha) BETWEEN ? AND ? ORDER BY v.fecha DESC,d.id""",(fi,ff)).fetchall()
            conn.close()
            _fill_tree(self.tv_rd,[(r["id"],r["fecha"],r["cajero"],r["producto"],r["cantidad"],
                                    f"{r['precio_unit']:.2f}",f"{r['subtotal']:.2f}",r["metodo_pago"],
                                    f"{r['pago']:.2f}",f"{r['cambio']:.2f}") for r in detalles])

    # ── USUARIOS 
    def _mostrar_usuarios(self):
        f=tk.Frame(self.content,bg=C["bg"]); f.columnconfigure(0,weight=1); f.rowconfigure(2,weight=1)
        _page_title(f,"👤 Usuarios","Control de acceso y roles").grid(row=0,column=0,sticky="w",pady=(0,10))
        bar=tk.Frame(f,bg=C["bg"]); bar.grid(row=1,column=0,sticky="ew",pady=(0,8))
        _btn(bar,"➕ Nuevo Usuario",C["accent"],self._dlg_nuevo_usuario).pack(side="left",padx=(0,6))
        _btn(bar,"✏️ Editar Usuario",C["yellow"],self._dlg_editar_usuario).pack(side="left",padx=(0,6))
        _btn(bar,"🗑 Desactivar",C["red"],self._desactivar_usuario).pack(side="left",padx=(0,6))
        _btn(bar,"✅ Activar",C["green"],self._activar_usuario).pack(side="left",padx=(0,6))
        _btn(bar,"🔄 Actualizar",C["text_lt"],self._cargar_usuarios).pack(side="left")
        tabla_f=tk.Frame(f,bg=C["bg"]); tabla_f.grid(row=2,column=0,sticky="nsew")
        tabla_f.columnconfigure(0,weight=1); tabla_f.rowconfigure(0,weight=1)
        # Incluir contraseña (hash truncado para referencia)
        cols=("ID","Nombre","Usuario","Contraseña","Rol","Estado","Creado")
        anchos={"ID":40,"Nombre":160,"Usuario":110,"Contraseña":130,"Rol":80,"Estado":90,"Creado":150}
        self.tv_usr=_make_tree(tabla_f,cols,anchos,18)
        vsb=ttk.Scrollbar(tabla_f,orient="vertical",command=self.tv_usr.yview)
        self.tv_usr.configure(yscrollcommand=vsb.set)
        self.tv_usr.grid(row=0,column=0,sticky="nsew"); vsb.grid(row=0,column=1,sticky="ns")
        self._cargar_usuarios(); self._set_frame(f)

    def _cargar_usuarios(self):
        for r in self.tv_usr.get_children(): self.tv_usr.delete(r)
        conn=get_connection()
        rows=conn.execute("SELECT id,nombre,usuario,password,rol,activo,creado_en FROM usuarios ORDER BY id").fetchall()
        conn.close()
        for i,u in enumerate(rows):
            estado="✅ Activo" if u["activo"] else "❌ Inactivo"
            tag="par" if i%2==0 else "impar"
            # Mostrar los primeros 20 chars del hash como referencia
            self.tv_usr.insert("","end",tags=(tag,),
                values=(u["id"],u["nombre"],u["usuario"],"••••••••",u["rol"],estado,u["creado_en"]))

    def _dlg_nuevo_usuario(self):
        self._dlg_usuario(None)

    def _dlg_editar_usuario(self):
        sel=self.tv_usr.selection()
        if not sel: messagebox.showwarning("Selecciona","Elige un usuario de la lista."); return
        uid=int(self.tv_usr.item(sel[0],"values")[0])
        conn=get_connection()
        u=conn.execute("SELECT * FROM usuarios WHERE id=?",(uid,)).fetchone()
        conn.close()
        if u: self._dlg_usuario(dict(u))

    def _dlg_usuario(self,u=None):
        es_edicion=u is not None
        d=tk.Toplevel(self); d.title("Editar Usuario" if es_edicion else "Nuevo Usuario")
        d.resizable(False,False); d.configure(bg=C["bg"]); d.grab_set()
        _center_win(d,380,370); d.columnconfigure(1,weight=1)
        campos=[("Nombre completo","nombre"),("Usuario (login)","usuario"),("Contraseña","password")]
        entradas={}
        for i,(lbl,key) in enumerate(campos):
            tk.Label(d,text=lbl,font=FONT_BOLD,bg=C["bg"],fg=C["text"]).grid(row=i,column=0,sticky="w",padx=20,pady=(12,0))
            e=ttk.Entry(d,font=FONT_LABEL,show="•" if key=="password" else "")
            e.grid(row=i,column=1,padx=20,pady=(12,0),ipady=5,sticky="ew")
            if es_edicion and key!="password": e.insert(0,u.get(key,""))
            entradas[key]=e
        if es_edicion:
            tk.Label(d,text="(Dejar vacío para no cambiar contraseña)",font=("Segoe UI",8),
                     bg=C["bg"],fg=C["text_lt"]).grid(row=2,column=1,sticky="w",padx=20)
        tk.Label(d,text="Rol",font=FONT_BOLD,bg=C["bg"],fg=C["text"]).grid(row=3,column=0,sticky="w",padx=20,pady=(12,0))
        var_rol=tk.StringVar(value=u["rol"] if es_edicion else "cajero")
        for j,rol in enumerate(["admin","cajero"]):
            tk.Radiobutton(d,text=rol.title(),variable=var_rol,value=rol,font=FONT_LABEL,
                           bg=C["bg"],activebackground=C["bg"]).grid(row=3+j,column=1,sticky="w",padx=20)
        def guardar():
            nombre=entradas["nombre"].get().strip(); usuario_login=entradas["usuario"].get().strip()
            password=entradas["password"].get().strip(); rol=var_rol.get()
            if not nombre or not usuario_login: messagebox.showerror("Error","Nombre y usuario son obligatorios.",parent=d); return
            if es_edicion:
                conn=get_connection()
                if password:
                    import bcrypt
                    hashed=bcrypt.hashpw(password.encode(),bcrypt.gensalt()).decode()
                    conn.execute("UPDATE usuarios SET nombre=?,usuario=?,password=?,rol=? WHERE id=?",
                                 (nombre,usuario_login,hashed,rol,u["id"]))
                else:
                    conn.execute("UPDATE usuarios SET nombre=?,usuario=?,rol=? WHERE id=?",
                                 (nombre,usuario_login,rol,u["id"]))
                conn.commit(); conn.close()
                messagebox.showinfo("✅",f"Usuario '{usuario_login}' actualizado.",parent=d)
            else:
                if not password: messagebox.showerror("Error","La contraseña es obligatoria.",parent=d); return
                res=usr.registrar_usuario(nombre,usuario_login,password,rol)
                if not res["ok"]: messagebox.showerror("Error",res["error"],parent=d); return
                messagebox.showinfo("✅",res["mensaje"],parent=d)
            d.destroy(); self._cargar_usuarios()
        _btn(d,"Guardar",C["accent"],guardar).grid(row=5,column=0,columnspan=2,sticky="ew",padx=20,pady=16,ipady=4)

    def _activar_usuario(self):
        sel=self.tv_usr.selection()
        if not sel: messagebox.showwarning("Selecciona","Elige un usuario de la lista."); return
        vals=self.tv_usr.item(sel[0],"values"); uid,nombre=int(vals[0]),vals[1]
        conn=get_connection(); conn.execute("UPDATE usuarios SET activo=1 WHERE id=?",(uid,))
        conn.commit(); conn.close()
        messagebox.showinfo("✅",f"Usuario '{nombre}' activado correctamente.")
        self._cargar_usuarios()

    def _desactivar_usuario(self):
        sel=self.tv_usr.selection()
        if not sel: messagebox.showwarning("Selecciona","Elige un usuario de la lista."); return
        vals=self.tv_usr.item(sel[0],"values"); uid,nombre,login=int(vals[0]),vals[1],vals[2]
        if usr.sesion() and usr.sesion().usuario==login:
            messagebox.showerror("Error","No puedes desactivar tu propio usuario."); return
        if not messagebox.askyesno("Confirmar",f"¿Desactivar al usuario '{nombre}' ({login})?"): return
        conn=get_connection(); conn.execute("UPDATE usuarios SET activo=0 WHERE id=?",(uid,))
        conn.commit(); conn.close()
        messagebox.showinfo("✅",f"Usuario '{nombre}' desactivado."); self._cargar_usuarios()

if __name__=="__main__":
    MarketHubApp()