import base64
import hashlib
import hmac
import importlib.util
import os
import pathlib
import unittest


def make_sig(secret: str, key: str, plan: str) -> str:
    mac = hmac.new(secret.encode(), f"{key}|{plan}".encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(mac).decode().rstrip("=")


class TestLicenseSecurity(unittest.TestCase):
    def setUp(self):
        self.cwd = pathlib.Path(__file__).parent.parent
        for fname in [
            "license_active.txt",
            "trial_start.txt",
            "licenses_plans.txt",
            "licenses.txt",
        ]:
            p = self.cwd / fname
            if p.exists():
                p.unlink()
        os.environ["LICENSES_URL"] = ""
        os.environ["ALLOW_PLAIN_LICENSES"] = "0"
        os.environ["LICENSE_SIGNING_SECRET"] = "s3cr3t"
        os.environ["LICENSE_KEY"] = "POSE-CUSTOM-9999"

    def test_signed_license_accepts(self):
        key = "POSE-CUSTOM-9999"
        plan = "custom"
        sig = make_sig(os.environ["LICENSE_SIGNING_SECRET"], key, plan)
        (self.cwd / "licenses_plans.txt").write_text(
            f"{key}|{plan}|{sig}\n", encoding="utf-8"
        )
        spec = importlib.util.spec_from_file_location(
            "app_main_signed", str(self.cwd / "main.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual(mod.ACTIVE_PLAN, "custom")

    def test_plain_license_rejected_without_allow(self):
        key = "POSE-PRO-2222"
        plan = "pro"
        (self.cwd / "licenses_plans.txt").write_text(
            f"{key}|{plan}\n", encoding="utf-8"
        )
        with self.assertRaises(SystemExit):
            spec = importlib.util.spec_from_file_location(
                "app_main_plain", str(self.cwd / "main.py")
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)


if __name__ == "__main__":
    unittest.main()
