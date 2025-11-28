import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import time
import pathlib
import re
from bot.config import OWNER_ID

# ====== Cargar variables de entorno ======
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
LICENSE_KEY = os.getenv("LICENSE_KEY")

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
def _validate_license(key: str) -> bool:
    if not key:
        return False
    if not re.fullmatch(r"POSEIDON-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}", key):
        return False
    lic_file = pathlib.Path("licenses.txt")
    if lic_file.exists():
        lines = lic_file.read_text(encoding="utf-8").splitlines()
        valid = {ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")}
        return key in valid
    return False

# Cargar licencia desde archivo si no está en .env
if not LICENSE_KEY:
    lic_active = pathlib.Path("license_active.txt")
    if lic_active.exists():
        LICENSE_KEY = lic_active.read_text(encoding="utf-8").strip()

if LICENSE_KEY and _validate_license(LICENSE_KEY):
    pass
else:
    p = pathlib.Path("trial_start.txt")
    now = int(time.time())
    if not p.exists():
        p.write_text(str(now), encoding="utf-8")
    else:
        try:
            start = int(p.read_text(encoding="utf-8").strip())
        except Exception:
            start = now
        days = (now - start) // 86400
        if days >= 7:
            raise SystemExit("Período de prueba de 7 días finalizado. Usa /botinfo para comprar.")
bot.run(TOKEN)
