# -*- coding: utf-8 -*-
import json
import os

DATA_FILE = "niveles.json"
BOT_VERSION = "4.2"

RANGOS = {
    1: "🌱 Mortal Errante",
    5: "🛡️ Guerrero del Ágora",
    10: "🔥 Héroe Forjado por Hefesto",
    15: "🦉 Discípulo de Atenea",
    20: "⚡ Semidiós del Olimpo",
    30: "🌌 Elegido de los Titanes",
    40: "👑 Dios del Olimpo",
}

STAFF_ROLE_ID = 1339567560047198328
CATEGORY_NAME = "📂 Oráculos"
LOG_CHANNEL_ID = 1425811285538242691

GUILD_CONFIG_FILE = "guild_config.json"
_GUILD_CONFIG_CACHE: dict[str, dict] | None = None


def _load_guild_config() -> dict[str, dict]:
    global _GUILD_CONFIG_CACHE
    if _GUILD_CONFIG_CACHE is not None:
        return _GUILD_CONFIG_CACHE
    if os.path.exists(GUILD_CONFIG_FILE):
        try:
            with open(GUILD_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                _GUILD_CONFIG_CACHE = data
                return data
        except Exception:
            pass
    _GUILD_CONFIG_CACHE = {}
    return _GUILD_CONFIG_CACHE


def _save_guild_config(data: dict[str, dict]) -> None:
    global _GUILD_CONFIG_CACHE
    _GUILD_CONFIG_CACHE = data
    try:
        with open(GUILD_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception:
        pass


def get_guild_config(guild_id: int | None) -> dict:
    if not guild_id:
        return {}
    data = _load_guild_config()
    key = str(int(guild_id))
    conf = data.get(key)
    if isinstance(conf, dict):
        return conf
    return {}


def set_guild_config(guild_id: int, updates: dict) -> dict:
    data = _load_guild_config()
    key = str(int(guild_id))
    cur = data.get(key)
    if not isinstance(cur, dict):
        cur = {}
    for k, v in (updates or {}).items():
        cur[k] = v
    data[key] = cur
    _save_guild_config(data)
    return cur


def get_guild_setting(guild_id: int | None, key: str, default=None):
    conf = get_guild_config(guild_id)
    if key in conf:
        return conf.get(key)
    return default


def set_guild_setting(guild_id: int, key: str, value) -> dict:
    return set_guild_config(guild_id, {key: value})
