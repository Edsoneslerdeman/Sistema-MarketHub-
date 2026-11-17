"""
Pruebas Unitarias para el Módulo de Inventario
Verifica control de stock, kardex de movimientos y validación de categorías.
"""
import unittest
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from modules.database import inicializar_bd, get_connection
from modules import usuarios as usr
from modules import inventario as inv

TEST_DB = os.path.join(BASE_DIR, "data", "test_inv.db")


class TestInventario(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import modules.database as db_mod
        db_mod.DB_PATH = TEST_DB
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
        inicializar_bd()

        usr.registrar_usuario("Admin", "admin_inv", "1234", "admin")
        usr.iniciar_sesion("admin_inv", "1234")

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_DB):
            try:
                os.remove(TEST_DB)
            except Exception:
                pass

    def test_01_agregar_producto_y_movimiento(self):
        cat = inv.agregar_categoria("Limpieza")
        res = inv.agregar_producto("Jabón Líquido", "JAB-001", 15.0, 30, 5, cat["id"])
        self.assertTrue(res["ok"])

        # Verificar kardex
        movs = inv.historial_movimientos(res["id"])
        self.assertGreater(len(movs), 0)
        self.assertEqual(movs[0]["tipo"], "entrada")
        self.assertEqual(movs[0]["cantidad"], 30)

    def test_02_entrada_stock(self):
        prod = inv.buscar_producto("JAB-001")
        stock_previo = prod["stock"]

        res = inv.entrada_stock(prod["id"], 20, "Reposición de stock")
        self.assertTrue(res["ok"])

        prod_act = inv.buscar_producto("JAB-001")
        self.assertEqual(prod_act["stock"], stock_previo + 20)

    def test_03_no_permite_precios_negativos(self):
        res = inv.agregar_producto("Producto Invalido", "INV-001", -5.0, 10, 2)
        self.assertFalse(res["ok"])


if __name__ == "__main__":
    unittest.main()
