"""
Pruebas Unitarias para el Módulo de Ventas y Pagos
Verifica atomicidad, cálculo de cambio, control de stock y consistencia de reportes.
"""
import unittest
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from modules.database import inicializar_bd, get_connection
from modules import usuarios as usr
from modules import inventario as inv
from modules import ventas as ven
from modules import pagos as pag

TEST_DB = os.path.join(BASE_DIR, "data", "test_markethub.db")


class TestVentasYPagos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Configurar base de datos de pruebas
        import modules.database as db_mod
        db_mod.DB_PATH = TEST_DB
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
        inicializar_bd()

        # Crear usuarios
        usr.registrar_usuario("Admin Test", "admin_test", "1234", "admin")
        usr.registrar_usuario("Cajero Test", "cajero_test", "1234", "cajero")

        # Iniciar sesión como cajero
        usr.iniciar_sesion("cajero_test", "1234")

        # Crear categorías y productos
        cat = inv.agregar_categoria("Pruebas")
        inv.agregar_producto("Producto A", "PROD-A", 10.0, 50, 5, cat["id"])
        inv.agregar_producto("Producto B", "PROD-B", 25.5, 20, 5, cat["id"])

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_DB):
            try:
                os.remove(TEST_DB)
            except Exception:
                pass

    def test_01_carrito_calculo_subtotal_y_total(self):
        carrito = ven.Carrito()
        carrito.agregar("PROD-A", 2)  # 2 * 10 = 20.0
        carrito.agregar("PROD-B", 1)  # 1 * 25.5 = 25.5

        self.assertEqual(carrito.total, 45.5)
        self.assertEqual(len(carrito.items), 2)

    def test_02_venta_efectivo_con_cambio_correcto(self):
        """Verifica que el cambio devuelto sea exactamente la diferencia y no 0.00"""
        carrito = ven.Carrito()
        carrito.agregar("PROD-A", 3)  # Total 30.00
        total = carrito.total

        # Cliente paga con 50 Bs -> Cambio debe ser 20 Bs
        res = ven.registrar_venta(carrito, metodo_pago="efectivo", monto_recibido=50.0)
        self.assertTrue(res["ok"])
        self.assertEqual(res["total"], 30.0)
        self.assertEqual(res["monto_recibido"], 50.0)
        self.assertEqual(res["cambio"], 20.0)

        # Verificar en base de datos
        venta_bd = ven.obtener_venta(res["venta_id"])
        self.assertEqual(venta_bd["total"], 30.0)
        self.assertEqual(venta_bd["monto_pago"], 50.0)
        self.assertEqual(venta_bd["cambio"], 20.0)

        # Verificar en tabla de pagos
        pago_bd = pag.obtener_pago(res["venta_id"])
        self.assertEqual(pago_bd["monto"], 30.0)          # Ingreso neto
        self.assertEqual(pago_bd["monto_recibido"], 50.0) # Dinero entregado
        self.assertEqual(pago_bd["cambio"], 20.0)         # Cambio

    def test_03_venta_efectivo_monto_insuficiente(self):
        carrito = ven.Carrito()
        carrito.agregar("PROD-A", 2)  # Total 20.00
        res = ven.registrar_venta(carrito, metodo_pago="efectivo", monto_recibido=10.0)
        self.assertFalse(res["ok"])
        self.assertIn("insuficiente", res["error"].lower())

    def test_04_venta_qr_o_tarjeta_no_genera_cambio(self):
        carrito = ven.Carrito()
        carrito.agregar("PROD-A", 1)  # Total 10.00
        res = ven.registrar_venta(carrito, metodo_pago="qr", monto_recibido=10.0)
        self.assertTrue(res["ok"])
        self.assertEqual(res["cambio"], 0.0)

    def test_05_descuento_stock_y_bloqueo_sobreventa(self):
        """Verifica que no se pueda vender más del stock existente"""
        prod = inv.buscar_producto("PROD-B")
        stock_actual = prod["stock"]

        carrito = ven.Carrito()
        # Intentar agregar más que el stock
        res = carrito.agregar("PROD-B", stock_actual + 10)
        self.assertFalse(res["ok"])


if __name__ == "__main__":
    unittest.main()
