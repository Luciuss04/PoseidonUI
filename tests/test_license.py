import os
import pathlib
import time
import unittest


class TestLicenseTrial(unittest.TestCase):
    def setUp(self):
        self.cwd = pathlib.Path(__file__).parent.parent
        os.environ.pop("LICENSE_KEY", None)
        os.environ.pop("LICENSES_URL", None)
        for fname in ["license_active.txt", "trial_start.txt", "licenses.txt"]:
            p = self.cwd / fname
            if p.exists():
                p.unlink()

    def test_trial_starts_and_allows(self):
        import importlib

        spec = importlib.util.spec_from_file_location(
            "app_main", str(self.cwd / "main.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertTrue((self.cwd / "trial_start.txt").exists())

    def test_trial_expires_after_7_days(self):
        start = int(time.time()) - (8 * 86400)
        (self.cwd / "trial_start.txt").write_text(str(start), encoding="utf-8")
        import importlib

        spec = importlib.util.spec_from_file_location(
            "app_main2", str(self.cwd / "main.py")
        )
        mod = importlib.util.module_from_spec(spec)
        with self.assertRaises(SystemExit):
            spec.loader.exec_module(mod)


class TestLicenseParsing(unittest.TestCase):
    def test_parse_text_and_json(self):
        import importlib

        cwd = pathlib.Path(__file__).parent.parent
        spec = importlib.util.spec_from_file_location("app_main3", str(cwd / "main.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        txt = "# comment\nPOSEIDON-ABCD-EFGH-IJKL\nX123|extra"
        vals = mod._parse_licenses_text(txt)
        self.assertIn("POSEIDON-ABCD-EFGH-IJKL", vals)
        self.assertIn("X123", vals)
        js = '["A", "B"]'
        self.assertEqual(mod._parse_licenses_text(js), {"A", "B"})
        js2 = '{"K1": true, "K2": false}'
        self.assertEqual(mod._parse_licenses_text(js2), {"K1"})

    def test_plan_map_parsing(self):
        import importlib

        cwd = pathlib.Path(__file__).parent.parent
        spec = importlib.util.spec_from_file_location("app_main4", str(cwd / "main.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        txt = "POSE-PRO|pro\nPOSE-BASIC|basic\nPOSE-CUSTOM|custom\n# comment\nJUSTKEY"
        mp = mod._parse_license_plan_map(txt)
        self.assertEqual(mp["POSE-PRO"], "pro")
        self.assertEqual(mp["POSE-BASIC"], "basic")
        self.assertEqual(mp["POSE-CUSTOM"], "custom")
        self.assertEqual(mp["JUSTKEY"], "basic")
        js = '{"L1": "elite", "L2": true}'
        mp2 = mod._parse_license_plan_map(js)
        self.assertEqual(mp2["L1"], "elite")
        self.assertEqual(mp2["L2"], "basic")


if __name__ == "__main__":
    unittest.main()
