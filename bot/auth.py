# -*- coding: utf-8 -*-
import hashlib
import json
import os
import hmac

# Archivo para múltiples usuarios (NUEVO)
WEB_USERS_FILE = "web_users.json"
# Archivo antiguo para compatibilidad
DASHBOARD_CONFIG_FILE = "dashboard_auth.json"

def _load_web_users():
    if not os.path.exists(WEB_USERS_FILE):
        # Migrar desde el archivo antiguo si existe
        if os.path.exists(DASHBOARD_CONFIG_FILE):
            try:
                with open(DASHBOARD_CONFIG_FILE, "r") as f:
                    old = json.load(f)
                users = {
                    old["username"]: {
                        "username": old["username"],
                        "password_hash": old["password_hash"],
                        "is_global_admin": True,
                        "guild_id": None
                    }
                }
                _save_web_users(users)
                return users
            except:
                pass
        
        # Credenciales por defecto iniciales
        default_users = {
            "admin": {
                "username": "admin",
                "password_hash": hashlib.sha256("poseidon2026".encode()).hexdigest(),
                "is_global_admin": True,
                "guild_id": None
            }
        }
        _save_web_users(default_users)
        return default_users
    
    try:
        with open(WEB_USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def _save_web_users(users):
    with open(WEB_USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4)

def verify_login(username, password):
    users = _load_web_users()
    if username not in users:
        return False
    
    user_data = users[username]
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    
    return hmac.compare_digest(pw_hash, user_data["password_hash"])

def get_user_data(username):
    users = _load_web_users()
    return users.get(username)

def add_web_user(username, password, guild_id=None, discord_id=None, avatar_url=None, is_global_admin=False):
    users = _load_web_users()
    users[username] = {
        "username": username,
        "password_hash": hashlib.sha256(password.encode()).hexdigest(),
        "guild_id": guild_id,
        "discord_id": discord_id,
        "avatar_url": avatar_url,
        "is_global_admin": is_global_admin
    }
    _save_web_users(users)
    return True

def update_auth(username, password):
    """Actualiza la contraseña del admin global (para compatibilidad)."""
    return add_web_user(username, password, is_global_admin=True)
