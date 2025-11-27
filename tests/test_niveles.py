import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import unittest
from niveles import xp_necesaria, obtener_rango


class TestNiveles(unittest.TestCase):
    def test_xp_necesaria(self):
        self.assertEqual(xp_necesaria(1), 100)
        self.assertEqual(xp_necesaria(5), 500)

    def test_obtener_rango(self):
        self.assertEqual(obtener_rango(1), "🌱 Mortal Errante")
        self.assertEqual(obtener_rango(10), "🔥 Héroe Forjado por Hefesto")
        self.assertEqual(obtener_rango(40), "👑 Dios del Olimpo")


if __name__ == '__main__':
    unittest.main()
