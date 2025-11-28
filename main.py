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

# ====== Configuración de intents ======
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

# ====== Crear bot con setup_hook ======
class PoseidonUIBot(commands.Bot):
    async def setup_hook(self):
        from bot.cogs.comunidad import oraculo
        from bot.cogs.integraciones import lol
        from bot.cogs.comunidad import niveles
        from bot.cogs.moderacion import guardian
        from bot.cogs.moderacion import crear_roles_guardian
        from bot.cogs.diagnostico import status
        from bot.cogs.economia import ofertas
        from bot.cogs.info import about

        # Cargar todos los módulos
        await oraculo.setup(self)
        await lol.setup(self)
        await niveles.setup(self)
        await guardian.setup(self)
        await crear_roles_guardian.setup(self) 
        await status.setup(self)
        await ofertas.setup(self)
        await about.setup(self)
        # Sincronizar slash commands
        await self.tree.sync()

bot = PoseidonUIBot(command_prefix="!", intents=intents)

# ====== Evento de conexión ======
@bot.event
async def on_ready():
    print(f"⚔️ PoseidonUI conectado como {bot.user}")
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
def _validate_license(key: str) -> bool:
    if not key:
        return False
    if LICENSES_URL:
        try:
            vals = asyncio.run(_fetch_remote_licenses(LICENSES_URL))
        except Exception:
            vals = None
        if vals:
            return key in vals
    if not re.fullmatch(r"POSEIDON-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}", key):
        pass
    lic_file = pathlib.Path("licenses.txt")
    if lic_file.exists():
        txt = lic_file.read_text(encoding="utf-8")
        vals = _parse_licenses_text(txt)
        return key in vals
    return False

def enforce_license_or_trial() -> None:
    global LICENSE_KEY
    if not LICENSE_KEY:
        lic_active = pathlib.Path("license_active.txt")
        if lic_active.exists():
            LICENSE_KEY = lic_active.read_text(encoding="utf-8").strip()
    if LICENSE_KEY and _validate_license(LICENSE_KEY):
        return
    p = pathlib.Path("trial_start.txt")
    now = int(time.time())
    if not p.exists():
        p.write_text(str(now), encoding="utf-8")
        return
    try:
        start = int(p.read_text(encoding="utf-8").strip())
    except Exception:
        start = now
    days = (now - start) // 86400
    if days >= 7:
        raise SystemExit("Período de prueba de 7 días finalizado. Usa /botinfo para comprar.")

enforce_license_or_trial()
if __name__ == "__main__":
    bot.run(TOKEN)
