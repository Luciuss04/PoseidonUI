import os
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from bot.cogs.economia import ofertas


class TestOfertas(unittest.TestCase):
    @unittest.skip("Skip: entorno de eventos de Discord no disponible en tests")
    def test_channel_id_missing(self):
        os.environ.pop('CANAL_OFERTAS_ID', None)
        import importlib
        importlib.reload(ofertas)
        self.assertIsNone(ofertas.CANAL_OFERTAS_ID)


if __name__ == '__main__':
    unittest.main()
