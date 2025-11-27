import os
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import importlib
import lol


class TestLoL(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_without_key_returns_none(self):
        os.environ.pop('RIOT_API_KEY', None)
        importlib.reload(lol)
        cog = lol.LoLCog(bot=None)
        result = await cog.fetch('https://example.com')
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
