"""
Pruebas de Integración para la Aplicación Web (Flask Test Client)
"""
import unittest
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app import app
from seed import poblar_datos


class TestWebApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        poblar_datos()

    def setUp(self):
        self.client = app.test_client()

    def test_01_login_fallido(self):
        resp = self.client.post("/login", data={"usuario": "admin", "password": "wrongpassword"}, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Contraseña incorrecta", resp.get_data(as_text=True))

    def test_02_login_exitoso_y_acceso_pos(self):
        resp = self.client.post("/login", data={"usuario": "admin", "password": "admin123"}, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Punto de Venta", resp.get_data(as_text=True))

    def test_03_api_productos(self):
        with self.client.session_transaction() as sess:
            sess["usuario"] = {"id": 1, "nombre": "Admin", "usuario": "admin", "rol": "admin"}
        resp = self.client.get("/api/productos")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    def test_04_api_cobro_pos_efectivo_con_cambio(self):
        with self.client.session_transaction() as sess:
            sess["usuario"] = {"id": 1, "nombre": "Admin", "usuario": "admin", "rol": "admin"}

        # Obtener un producto
        resp_prods = self.client.get("/api/productos")
        prod = resp_prods.get_json()[0]

        # Simular compra de 2 unidades pagando con 100 Bs
        total_esperado = round(prod["precio"] * 2, 2)
        monto_recibido = total_esperado + 40.0
        cambio_esperado = 40.0

        payload = {
            "items": [{"producto_id": prod["id"], "cantidad": 2}],
            "metodo_pago": "efectivo",
            "monto_recibido": monto_recibido,
            "cliente_nit": "1234567",
            "cliente_nombre": "Juan Perez"
        }

        resp_cobro = self.client.post("/api/pos/cobrar", json=payload)
        self.assertEqual(resp_cobro.status_code, 200)
        data = resp_cobro.get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["cambio"], cambio_esperado)
        self.assertIn("Ticket #", data["ticket"])

    def test_05_exportar_csv(self):
        with self.client.session_transaction() as sess:
            sess["usuario"] = {"id": 1, "nombre": "Admin", "usuario": "admin", "rol": "admin"}
        resp = self.client.get("/exportar/ventas")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Venta ID,Fecha y Hora", resp.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
