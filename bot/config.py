# -*- coding: utf-8 -*-
import json
import os
import tempfile
import threading

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
_FILE_LOCKS: dict[str, threading.Lock] = {}
_FILE_LOCKS_GUARD = threading.Lock()
GUILD_CONFIG_SCHEMA_VERSION = 1
GUILD_CONFIG_META_KEY = "__meta__"


def _get_file_lock(file_path: str) -> threading.Lock:
    normalized = os.path.abspath(file_path)
    with _FILE_LOCKS_GUARD:
        lock = _FILE_LOCKS.get(normalized)
        if lock is None:
            lock = threading.Lock()
            _FILE_LOCKS[normalized] = lock
        return lock


def load_json_file(file_path: str, default):
    if not os.path.exists(file_path):
        return default
    try:
        with _get_file_lock(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        return data
    except Exception:
        return default


def save_json_file_atomic(
    file_path: str, data, *, indent: int = 4, ensure_ascii: bool = False
) -> None:
    dir_path = os.path.dirname(os.path.abspath(file_path)) or "."
    os.makedirs(dir_path, exist_ok=True)
    lock = _get_file_lock(file_path)
    with lock:
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=dir_path,
                delete=False,
                prefix=os.path.basename(file_path) + ".",
                suffix=".tmp",
            ) as tmp:
                tmp_path = tmp.name
                json.dump(data, tmp, indent=indent, ensure_ascii=ensure_ascii)
                tmp.flush()
                os.fsync(tmp.fileno())
            os.replace(tmp_path, file_path)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass


def _migrate_guild_config(data: dict) -> tuple[dict[str, dict], bool]:
    if not isinstance(data, dict):
        return {}, True

    changed = False
    migrated: dict[str, dict] = {}

    for k, v in data.items():
        if k == GUILD_CONFIG_META_KEY:
            continue
        if not str(k).isdigit():
            changed = True
            continue
        if not isinstance(v, dict):
            changed = True
            continue
        migrated[str(int(k))] = v

    meta = data.get(GUILD_CONFIG_META_KEY)
    if not isinstance(meta, dict):
        meta = {}
        changed = True

    schema_version = meta.get("schema_version")
    if not isinstance(schema_version, int):
        schema_version = 0
        changed = True

    if schema_version < 1:
        for gid, conf in migrated.items():
            staff_role_id = conf.get("staff_role_id")
            if "staff_role_ids" not in conf and staff_role_id is not None:
                try:
                    conf["staff_role_ids"] = [int(staff_role_id)]
                    changed = True
                except Exception:
                    pass
            if "staff_role_id" in conf:
                conf.pop("staff_role_id", None)
                changed = True

            if "log_channel_id" not in conf and "log_channel" in conf:
                conf["log_channel_id"] = conf.get("log_channel")
                conf.pop("log_channel", None)
                changed = True

            staff_role_ids = conf.get("staff_role_ids")
            if isinstance(staff_role_ids, (int, str)):
                try:
                    conf["staff_role_ids"] = [int(staff_role_ids)]
                    changed = True
                except Exception:
                    conf["staff_role_ids"] = []
                    changed = True
            elif isinstance(staff_role_ids, list):
                normalized_ids: list[int] = []
                for rid in staff_role_ids:
                    try:
                        normalized_ids.append(int(rid))
                    except Exception:
                        changed = True
                conf["staff_role_ids"] = normalized_ids

            theme = conf.get("theme")
            if theme is not None and not isinstance(theme, str):
                conf["theme"] = str(theme)
                changed = True

        schema_version = 1
        changed = True

    meta["schema_version"] = min(schema_version, GUILD_CONFIG_SCHEMA_VERSION)
    migrated[GUILD_CONFIG_META_KEY] = meta

    return migrated, changed


def _load_guild_config() -> dict[str, dict]:
    global _GUILD_CONFIG_CACHE
    if _GUILD_CONFIG_CACHE is not None:
        return _GUILD_CONFIG_CACHE
    raw = load_json_file(GUILD_CONFIG_FILE, {})
    if isinstance(raw, dict):
        data, changed = _migrate_guild_config(raw)
        _GUILD_CONFIG_CACHE = data
        if changed:
            try:
                save_json_file_atomic(GUILD_CONFIG_FILE, data, indent=4, ensure_ascii=False)
            except Exception:
                pass
        return data
    _GUILD_CONFIG_CACHE = {}
    return _GUILD_CONFIG_CACHE


def _save_guild_config(data: dict[str, dict]) -> None:
    global _GUILD_CONFIG_CACHE
    _GUILD_CONFIG_CACHE = data
    try:
        save_json_file_atomic(GUILD_CONFIG_FILE, data, indent=4, ensure_ascii=False)
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
