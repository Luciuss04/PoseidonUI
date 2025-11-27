import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# ====== Cargar variables de entorno ======
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# ====== Configuración de intents ======
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

# ====== Crear bot con setup_hook ======
class PoseidonUIBot(commands.Bot):
    async def setup_hook(self):
        import oraculo
        import lol
        import niveles
        import guardian
        import crear_roles_guardian  
        import status
        import ofertas
        import about

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

@bot.event
async def on_command_error(ctx, error):
    try:
        await ctx.send(f"⚠️ Ocurrió un error: {error}")
    except Exception:
        pass

if not TOKEN:
    raise SystemExit("DISCORD_TOKEN no está configurado")
bot.run(TOKEN)
