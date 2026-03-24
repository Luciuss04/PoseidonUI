# -*- coding: utf-8 -*-
import os
import json
import hashlib

# Configuración de seguridad para el Dashboard
DASHBOARD_CONFIG_FILE = "dashboard_auth.json"

def get_auth_config():
    if os.path.exists(DASHBOARD_CONFIG_FILE):
        with open(DASHBOARD_CONFIG_FILE, "r") as f:
            return json.load(f)
    # Credenciales por defecto (recomendar cambiar en el primer inicio)
    default_auth = {
        "username": "admin",
        "password_hash": hashlib.sha256("poseidon2026".encode()).hexdigest()
    }
    with open(DASHBOARD_CONFIG_FILE, "w") as f:
        json.dump(default_auth, f, indent=4)
    return default_auth

def verify_login(username, password):
    config = get_auth_config()
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    return username == config["username"] and pw_hash == config["password_hash"]
