import json, random
from discord.ext import commands
from config import DATA_FILE, RANGOS

def cargar_niveles():
    try:
        with open(DATA_FILE, "r") as f:
            contenido = f.read().strip()
            if not contenido:
                return {}
            return json.loads(contenido)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def guardar_niveles(niveles):
    with open(DATA_FILE, "w") as f:
        json.dump(niveles, f, indent=4)

def xp_necesaria(nivel):
    return nivel * 100

def procesar_mensaje(message, niveles):
    user_id = str(message.author.id)
    if user_id not in niveles:
        niveles[user_id] = {"xp": 0, "nivel": 1}

    niveles[user_id]["xp"] += random.randint(5, 15)
    nivel_actual = niveles[user_id]["nivel"]

    if niveles[user_id]["xp"] >= xp_necesaria(nivel_actual):
        niveles[user_id]["nivel"] += 1
        niveles[user_id]["xp"] = 0
        nuevo_nivel = niveles[user_id]["nivel"]

        rango = obtener_rango(nuevo_nivel)
        return nuevo_nivel, rango

    return None, None

def obtener_rango(nivel):
    rango = None
    for lvl, nombre in sorted(RANGOS.items()):
        if nivel >= lvl:
            rango = nombre
    return rango

# ====== Cog para integrarlo con el bot ======
class NivelesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.niveles = cargar_niveles()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        nuevo_nivel, rango = procesar_mensaje(message, self.niveles)
        guardar_niveles(self.niveles)

        if nuevo_nivel:
            await message.channel.send(
                f"🌟 {message.author.mention} ha alcanzado el nivel **{nuevo_nivel}** ({rango}) ⚔️"
            )

# ====== Setup obligatorio para main.py ======
async def setup(bot):
    await bot.add_cog(NivelesCog(bot))
