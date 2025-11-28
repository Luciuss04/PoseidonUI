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
            out = {}
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
    out = {}
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        if "|" in s:
            parts = [p.strip() for p in s.split("|", 1)]
            if parts and parts[0]:
                out[parts[0]] = (parts[1].lower() if len(parts) > 1 and parts[1] else "basic")
        else:
            out[s] = "basic"
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

async def _fetch_remote_plan_map(url: str) -> dict[str, str] | None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as r:
                if r.status != 200:
                    return None
                text = await r.text()
                return _parse_license_plan_map(text)
    except Exception:
        return None
def _get_plan_for_key_local(key: str) -> str | None:
    lic_file = pathlib.Path("licenses.txt")
    if lic_file.exists():
        txt = lic_file.read_text(encoding="utf-8")
        mp = _parse_license_plan_map(txt)
        return mp.get(key)
    return None

def _validate_license(key: str) -> bool:
    if not key:
        return False
    global ACTIVE_PLAN
    # Remote plan map
    if LICENSES_URL:
        try:
            plan_map = asyncio.run(_fetch_remote_plan_map(LICENSES_URL))
        except Exception:
            plan_map = None
        if plan_map and key in plan_map:
            ACTIVE_PLAN = plan_map[key]
            return True
        # Fall back to remote plain list
        try:
            vals = asyncio.run(_fetch_remote_licenses(LICENSES_URL))
        except Exception:
            vals = None
        if vals and key in vals:
            ACTIVE_PLAN = "basic"
            return True
    # Local plan map
    plan_local = _get_plan_for_key_local(key)
    if plan_local:
        ACTIVE_PLAN = plan_local
        return True
    # Local plain list
    lic_file = pathlib.Path("licenses.txt")
    if lic_file.exists():
        vals = _parse_licenses_text(lic_file.read_text(encoding="utf-8"))
        if key in vals:
            ACTIVE_PLAN = "basic"
            return True
    # Regex fallback (no plan info)
    if re.fullmatch(r"POSEIDON-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}", key):
        ACTIVE_PLAN = "basic"
        return True
    return False

def enforce_license_or_trial() -> None:
    global LICENSE_KEY
    global ACTIVE_PLAN
    global IS_TRIAL
    if not LICENSE_KEY:
        lic_active = pathlib.Path("license_active.txt")
        if lic_active.exists():
            LICENSE_KEY = lic_active.read_text(encoding="utf-8").strip()
    if LICENSE_KEY and _validate_license(LICENSE_KEY):
        if not ACTIVE_PLAN:
            ACTIVE_PLAN = "basic"
        return
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
        "bot.cogs.moderacion.guardian",
        "bot.cogs.info.about",
    ]
    pro_extra = [
        "bot.cogs.comunidad.oraculo",
        "bot.cogs.comunidad.niveles",
        "bot.cogs.moderacion.crear_roles_guardian",
    ]
    elite_extra = [
        "bot.cogs.economia.ofertas",
    ]
    all_extra = [
        "bot.cogs.integraciones.lol",
    ]
    cogs = list(base)
    if plan in ("pro", "elite", "custom"):
        cogs += pro_extra
    if plan in ("elite", "custom"):
        cogs += elite_extra
    if plan == "custom":
        cogs += all_extra
    return cogs
if __name__ == "__main__":
    bot.run(TOKEN)
