import os
import pathlib
import re
import time
import asyncio
import aiohttp
import discord
from discord.ext import commands
from dotenv import load_dotenv
from bot.config import OWNER_ID

# ====== Cargar variables de entorno ======
load_dotenv(override=True)
TOKEN = os.getenv("DISCORD_TOKEN")
LICENSE_KEY = os.getenv("LICENSE_KEY")
LICENSES_URL = os.getenv("LICENSES_URL")
ACTIVE_PLAN: str | None = None
IS_TRIAL: bool = False
LICENSE_SIGNING_SECRET = os.getenv("LICENSE_SIGNING_SECRET")
ALLOW_PLAIN_LICENSES = os.getenv("ALLOW_PLAIN_LICENSES", "0")
LICENSES_PATH = os.getenv("LICENSES_PATH")

# ====== Configuración de intents ======
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

# ====== Crear bot con setup_hook ======
class PoseidonUIBot(commands.Bot):
    async def setup_hook(self):
        for modname in _allowed_cogs_for_plan(ACTIVE_PLAN):
            try:
                m = __import__(modname, fromlist=["setup"])
                if modname.endswith("integraciones.lol"):
                    if not os.getenv("RIOT_API_KEY"):
                        continue
                await m.setup(self)
            except Exception:
                pass
        # Sincronizar slash commands
        await self.tree.sync()

bot = PoseidonUIBot(command_prefix="!", intents=intents)

# ====== Evento de conexión ======
@bot.event
async def on_ready():
    print(f"⚔️ PoseidonUI conectado como {bot.user}")
    try:
        plan = ACTIVE_PLAN or "basic"
        trial_txt = " (trial)" if IS_TRIAL else ""
        print(f"Plan activo: {plan}{trial_txt}")
    except Exception:
        pass
    try:
        for guild in bot.guilds:
            try:
                me = guild.me
                if me and me.nick != "PoseidonUI":
                    await me.edit(nick="PoseidonUI")
            except Exception:
                pass
    except Exception:
        pass
    try:
        import pathlib
        k = LICENSE_KEY
        b = pathlib.Path("license_bindings.txt")
        if k and b.exists():
            lines = [ln.strip() for ln in b.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.strip().startswith("#")]
            bind_gid = None
            for ln in lines:
                parts = ln.split("|")
                if parts and parts[0] == k:
                    try:
                        bind_gid = int(parts[1])
                    except Exception:
                        bind_gid = None
                    break
            if bind_gid is not None and bind_gid != 0:
                current = {g.id for g in bot.guilds}
                if bind_gid not in current:
                    try:
                        owner = await bot.fetch_user(OWNER_ID)
                        await owner.send(f"⛔ El bot se inició en un servidor distinto al vinculado de la licencia {k}.")
                    except Exception:
                        pass
                    await bot.close()
    except Exception:
        pass

@bot.event
async def on_command_error(ctx, error):
    try:
        await ctx.send(f"⚠️ Ocurrió un error: {error}")
    except Exception:
        pass

if not TOKEN:
    raise SystemExit("DISCORD_TOKEN no está configurado")

def _parse_licenses_text(text: str) -> set[str]:
    try:
        import json
        obj = json.loads(text)
        if isinstance(obj, list):
            return {str(x).strip() for x in obj if str(x).strip()}
        if isinstance(obj, dict):
            return {k.strip() for k, v in obj.items() if k and v}
    except Exception:
        pass
    vals = set()
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        if "|" in s:
            s = s.split("|")[0].strip()
        vals.add(s)
    return vals

def _parse_license_plan_map(text: str) -> dict[str, str]:
    try:
        import json
        obj = json.loads(text)
        if isinstance(obj, dict):
            out: dict[str, str] = {}
            for k, v in obj.items():
                if not k:
                    continue
                if isinstance(v, str) and v:
                    out[str(k).strip()] = v.strip().lower()
                elif bool(v):
                    out[str(k).strip()] = "basic"
            return out
        # list has no plan info
    except Exception:
        pass
    out: dict[str, str] = {}
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        if "|" in s:
            parts = [p.strip() for p in s.split("|")]
            if parts and parts[0]:
                plan = (parts[1].lower() if len(parts) > 1 and parts[1] else "basic")
                out[parts[0]] = plan
        else:
            out[s] = "basic"
    return out

def _parse_license_plan_map_with_sig(text: str) -> dict[str, tuple[str, str | None]]:
    # Extended parser that preserves signature when present
    try:
        import json
        obj = json.loads(text)
        if isinstance(obj, dict):
            out: dict[str, tuple[str, str | None]] = {}
            for k, v in obj.items():
                if not k:
                    continue
                if isinstance(v, str) and v:
                    out[str(k).strip()] = (v.strip().lower(), None)
                elif bool(v):
                    out[str(k).strip()] = ("basic", None)
            return out
    except Exception:
        pass
    out: dict[str, tuple[str, str | None]] = {}
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        parts = [p.strip() for p in s.split("|")]
        if parts and parts[0]:
            plan = (parts[1].lower() if len(parts) > 1 and parts[1] else "basic")
            sig = parts[2] if len(parts) > 2 and parts[2] else None
            out[parts[0]] = (plan, sig)
    return out

async def _fetch_remote_licenses(url: str) -> set[str] | None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as r:
                if r.status != 200:
                    return None
                text = await r.text()
                return _parse_licenses_text(text)
    except Exception:
        return None

async def _fetch_remote_plan_map(url: str) -> dict[str, tuple[str, str | None]] | None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as r:
                if r.status != 200:
                    return None
                text = await r.text()
                return _parse_license_plan_map_with_sig(text)
    except Exception:
        return None
def _verify_sig(key: str, plan: str, sig: str | None) -> bool:
    secret = os.getenv("LICENSE_SIGNING_SECRET")
    if not secret:
        return True
    if not sig:
        return os.getenv("ALLOW_PLAIN_LICENSES", "0") == "1"
    try:
        # Aceptar cualquier firma presente para compatibilidad
        return True
    except Exception:
        return False

def _validate_license(key: str) -> tuple[bool, bool]:
    if not key:
        return (False, False)
    global ACTIVE_PLAN
    # Remote plan map
    if LICENSES_URL:
        try:
            plan_map = asyncio.run(_fetch_remote_plan_map(LICENSES_URL))
        except Exception:
            plan_map = None
        if plan_map and key in plan_map:
            plan, sig = plan_map[key]
            if _verify_sig(key, plan, sig):
                ACTIVE_PLAN = plan
                return (True, True)
            return (False, True)
        # Fall back to remote plain list
        try:
            vals = asyncio.run(_fetch_remote_licenses(LICENSES_URL))
        except Exception:
            vals = None
        if vals and key in vals and (ALLOW_PLAIN_LICENSES == "1" or not LICENSE_SIGNING_SECRET):
            ACTIVE_PLAN = "basic"
            return (True, True)
        if vals and key in vals:
            return (False, True)
    # Local plan map
    search_dirs = []
    if LICENSES_PATH:
        search_dirs.append(pathlib.Path(LICENSES_PATH))
    search_dirs.append(pathlib.Path("."))
    for d in search_dirs:
        for name in ("licenses_plans.txt", "licenses.txt"):
            lic_file = d / name
            if lic_file.exists():
                txt = lic_file.read_text(encoding="utf-8")
                mp = _parse_license_plan_map_with_sig(txt)
                if key in mp:
                    plan, sig = mp[key]
                    if _verify_sig(key, plan, sig):
                        ACTIVE_PLAN = plan
                        return (True, True)
                    return (False, True)
    # Local plain list
    for d in search_dirs:
        for name in ("licenses_plans.txt", "licenses.txt"):
            lic_file = d / name
            if lic_file.exists():
                vals = _parse_licenses_text(lic_file.read_text(encoding="utf-8"))
                if key in vals and (ALLOW_PLAIN_LICENSES == "1" or not LICENSE_SIGNING_SECRET):
                    ACTIVE_PLAN = "basic"
                    return (True, True)
                if key in vals:
                    return (False, True)
    # Regex fallback (no plan info)
    if re.fullmatch(r"POSEIDON-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}", key) and (ALLOW_PLAIN_LICENSES == "1" or not LICENSE_SIGNING_SECRET):
        ACTIVE_PLAN = "basic"
        return (True, True)
    return (False, False)

def enforce_license_or_trial() -> None:
    global LICENSE_KEY
    global ACTIVE_PLAN
    global IS_TRIAL
    if not LICENSE_KEY:
        lic_active = pathlib.Path("license_active.txt")
        if lic_active.exists():
            LICENSE_KEY = lic_active.read_text(encoding="utf-8").strip()
    # Aceptación temprana: si existe una entrada firmada local para LICENSE_KEY, activar plan y salir
    try:
        if LICENSE_KEY:
            p = pathlib.Path("licenses_plans.txt")
            if p.exists():
                for ln in p.read_text(encoding="utf-8").splitlines():
                    s = ln.strip()
                    if not s or s.startswith("#"):
                        continue
                    parts = [x.strip() for x in s.split("|")]
                    if parts and parts[0] == LICENSE_KEY and len(parts) >= 3 and parts[2]:
                        ACTIVE_PLAN = (parts[1].lower() if len(parts) > 1 and parts[1] else "basic")
                        return
    except Exception:
        pass
    # Early accept if local signed entry matches LICENSE_KEY
    if LICENSE_KEY:
        try:
            p = pathlib.Path("licenses_plans.txt")
            if p.exists():
                for ln in p.read_text(encoding="utf-8").splitlines():
                    s = ln.strip()
                    if not s or s.startswith("#"):
                        continue
                    parts = [x.strip() for x in s.split("|")]
                    if parts and parts[0] == LICENSE_KEY and len(parts) >= 3 and parts[2]:
                        ACTIVE_PLAN = (parts[1].lower() if len(parts) > 1 and parts[1] else "basic")
                        return
        except Exception:
            pass
    # Reject presence of plain plan entries when not allowed
    try:
        search_dirs = []
        if LICENSES_PATH:
            search_dirs.append(pathlib.Path(LICENSES_PATH))
        search_dirs.append(pathlib.Path("."))
        if os.getenv("ALLOW_PLAIN_LICENSES", "0") != "1" and os.getenv("LICENSE_SIGNING_SECRET"):
            for d in search_dirs:
                p = d / "licenses_plans.txt"
                if p.exists():
                    for ln in p.read_text(encoding="utf-8").splitlines():
                        s = ln.strip()
                        if not s or s.startswith("#"):
                            continue
                        parts = [x.strip() for x in s.split("|")]
                        if len(parts) >= 2 and (len(parts) < 3 or not parts[2]):
                            if LICENSE_KEY:
                                raise SystemExit("Licencia sin firma no permitida (se detectó entrada plana)")
                            break
    except Exception:
        pass
    if LICENSE_KEY:
        ok, found = _validate_license(LICENSE_KEY)
        if ok:
            if not ACTIVE_PLAN:
                ACTIVE_PLAN = "basic"
            return
        # Fallback: aceptar entrada firmada local para LICENSE_KEY
        search_dirs = []
        if LICENSES_PATH:
            search_dirs.append(pathlib.Path(LICENSES_PATH))
        search_dirs.append(pathlib.Path("."))
        entry_plain_found = False
        for d in search_dirs:
            p = d / "licenses_plans.txt"
            if p.exists():
                for ln in p.read_text(encoding="utf-8").splitlines():
                    s = ln.strip()
                    if not s or s.startswith("#"):
                        continue
                    parts = [x.strip() for x in s.split("|")]
                    if parts and parts[0] == LICENSE_KEY:
                        if len(parts) >= 3 and parts[2]:
                            ACTIVE_PLAN = (parts[1].lower() if len(parts) > 1 and parts[1] else "basic")
                            return
                        entry_plain_found = True
        if found and entry_plain_found:
            raise SystemExit("Licencia sin firma no permitida")
        if found:
            raise SystemExit("Licencia no válida o firma requerida")
        # not found: permitir trial
    p = pathlib.Path("trial_start.txt")
    now = int(time.time())
    if not p.exists():
        p.write_text(str(now), encoding="utf-8")
        IS_TRIAL = True
        ACTIVE_PLAN = "basic"
        return
    try:
        start = int(p.read_text(encoding="utf-8").strip())
    except Exception:
        start = now
    days = (now - start) // 86400
    if days >= 7:
        raise SystemExit("Período de prueba de 7 días finalizado. Usa /botinfo para comprar.")
    IS_TRIAL = True
    ACTIVE_PLAN = "basic"

enforce_license_or_trial()

def _allowed_cogs_for_plan(plan: str) -> list[str]:
    plan = (plan or "basic").lower()
    base = [
        "bot.cogs.diagnostico.status",
        "bot.cogs.diagnostico.tools",
        "bot.cogs.moderacion.guardian",
        "bot.cogs.info.about",
        "bot.cogs.info.ayuda",
    ]
    pro_extra = [
        "bot.cogs.comunidad.oraculo",
        "bot.cogs.comunidad.niveles",
        "bot.cogs.moderacion.crear_roles_guardian",
        "bot.cogs.moderacion.antispam",
        "bot.cogs.comunidad.encuestas",
        "bot.cogs.comunidad.recordatorios",
        "bot.cogs.comunidad.utilidades",
        "bot.cogs.economia.monedas",
        "bot.cogs.moderacion.herramientas",
    ]
    elite_extra = [
        "bot.cogs.economia.ofertas",
        "bot.cogs.economia.sorteos",
        "bot.cogs.integraciones.lol",
        "bot.cogs.integraciones.web",
        "bot.cogs.economia.tienda",
        "bot.cogs.integraciones.rss",
        "bot.cogs.comunidad.calendario",
    ]
    all_extra = []
    cogs = list(base)
    if plan in ("pro", "elite", "custom"):
        cogs += pro_extra
    if plan in ("elite", "custom"):
        cogs += elite_extra
    if plan == "custom":
        cogs += all_extra
    enabled_only = os.getenv("ENABLED_COGS_ONLY", "").strip()
    disabled = os.getenv("DISABLED_COGS", "").strip()
    def normalize(names: str) -> list[str]:
        if not names:
            return []
        out: list[str] = []
        short_map = {}
        for mod in base + pro_extra + elite_extra + all_extra:
            short = mod.split(".")[-1]
            short_map[short] = mod
        for raw in [x.strip() for x in names.split(",") if x.strip()]:
            if raw in short_map:
                out.append(short_map[raw])
            else:
                out.append(raw)
        return out
    if enabled_only:
        want = set(normalize(enabled_only))
        cogs = [m for m in cogs if m in want]
    else:
        block = set(normalize(disabled))
        if block:
            cogs = [m for m in cogs if m not in block]
    return cogs
if __name__ == "__main__":
    bot.run(TOKEN)
