# -*- coding: utf-8 -*-
import hashlib
import json
import os

# Configuración de seguridad para el Dashboard
DASHBOARD_CONFIG_FILE = "dashboard_auth.json"


def get_auth_config():
    if os.path.exists(DASHBOARD_CONFIG_FILE):
        with open(DASHBOARD_CONFIG_FILE, "r") as f:
            return json.load(f)
    # Credenciales por defecto (recomendar cambiar en el primer inicio)
    default_auth = {
        "username": "admin",
        "password_hash": hashlib.sha256("poseidon2026".encode()).hexdigest(),
    }
    with open(DASHBOARD_CONFIG_FILE, "w") as f:
        json.dump(default_auth, f, indent=4)
    return default_auth


def verify_login(username, password):
    config = get_auth_config()
    # Usar hmac.compare_digest para prevenir ataques de tiempo
    import hmac

    pw_hash = hashlib.sha256(password.encode()).hexdigest()

    user_ok = hmac.compare_digest(username, config["username"])
    pass_ok = hmac.compare_digest(pw_hash, config["password_hash"])

    return user_ok and pass_ok


def update_auth(username, password):
    new_config = {
        "username": username,
        "password_hash": hashlib.sha256(password.encode()).hexdigest(),
    }
    with open(DASHBOARD_CONFIG_FILE, "w") as f:
        json.dump(new_config, f, indent=4)
    return True
