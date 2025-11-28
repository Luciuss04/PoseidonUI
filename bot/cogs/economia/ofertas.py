import os
import asyncio
from datetime import datetime
import aiohttp
import discord
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()
CANAL_OFERTAS_ID = os.getenv("CANAL_OFERTAS_ID")
CANAL_OFERTAS_ID = int(CANAL_OFERTAS_ID) if CANAL_OFERTAS_ID else None

CHEAPSHARK_URL = "https://www.cheapshark.com/api/1.0/deals"

STORE_MAP = {
    "1": "Steam",
    "7": "Fanatical",
    "11": "Humble Store",
    "15": "GOG",
    "23": "Epic Games"
}

class Ofertas(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        if CANAL_OFERTAS_ID is not None:
            self.publicar_ofertas.start()

    def cog_unload(self):
        self.publicar_ofertas.cancel()

    @app_commands.command(name="ofertas", description="Muestra al menos 30 ofertas de juegos de PC con tienda visible")
    async def ofertas(self, interaction: discord.Interaction):
        await interaction.response.defer()
        juegos = await self.obtener_ofertas()
        if not juegos:
            await interaction.followup.send("⚡ Hoy el Olimpo no encontró tesoros.", ephemeral=True)
            return

        juegos.sort(key=lambda j: float(j.get("savings", 0)), reverse=True)

        fecha = datetime.now().strftime("%d-%m-%Y")
        try:
            thread = await interaction.channel.create_thread(
                name=f"🌌 Profecías del Olimpo — {fecha}",
                type=discord.ChannelType.public_thread
            )
        except Exception:
            await interaction.followup.send("⚠️ No se pudo crear el thread en este canal.", ephemeral=True)
            return

        for idx, j in enumerate(juegos[:30], start=1):
            await thread.send(embed=self.crear_embed(j, idx))

        asyncio.create_task(self.cerrar_thread(thread, horas=24))
        await interaction.followup.send(f"✨ Se ha abierto un pergamino con las 30 profecías en un thread (cerrará en 24h).", ephemeral=True)

    @tasks.loop(hours=24)
    async def publicar_ofertas(self):
        await self.bot.wait_until_ready()
        canal = self.bot.get_channel(CANAL_OFERTAS_ID)
        if not canal:
            return

        juegos = await self.obtener_ofertas()
        if not juegos:
            await canal.send("⚡ Hoy el Olimpo no encontró tesoros.")
            return

        juegos.sort(key=lambda j: float(j.get("savings", 0)), reverse=True)

        fecha = datetime.now().strftime("%d-%m-%Y")
        try:
            thread = await canal.create_thread(
                name=f"🌌 Profecías del Olimpo — {fecha}",
                type=discord.ChannelType.public_thread
            )
        except Exception:
            return

        for idx, j in enumerate(juegos[:30], start=1):
            await thread.send(embed=self.crear_embed(j, idx))

        asyncio.create_task(self.cerrar_thread(thread, horas=24))

    async def cerrar_thread(self, thread, horas=24):
        await asyncio.sleep(horas * 3600)
        try:
            await thread.edit(archived=True, locked=True)
        except Exception:
            pass

    async def obtener_ofertas(self):
        params = {
            "storeID": "1,7,11,15,23",
            "pageSize": "50",
            "sortBy": "savings"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(CHEAPSHARK_URL, params=params) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()

        filtrados = []
        for d in data:
            title = d.get("title", "").lower()
            if any(x in title for x in ["dlc", "bundle", "soundtrack"]):
                continue
            filtrados.append(d)

        return filtrados

    def crear_embed(self, j, idx):
        title = j.get("title")
        store_id = str(j.get("storeID"))
        store = j.get("storeName") or STORE_MAP.get(store_id, "Desconocido")
        price_new = j.get("salePrice")
        price_old = j.get("normalPrice")
        cut = int(float(j.get("savings", 0)))
        link = f"https://www.cheapshark.com/redirect?dealID={j.get('dealID')}"
        thumb = j.get("thumb")

        if cut >= 70:
            emoji = "🔥"
            color = discord.Color.gold()
        elif cut >= 50:
            emoji = "💎"
            color = discord.Color.blue()
        else:
            emoji = "🌙"
            color = discord.Color.dark_gray()

        numeros = ["0️⃣","1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣"]
        contador = "".join(numeros[int(d)] for d in str(idx))

        description = (
            f"✧✦✧ **{store}** ✧✦✧\n"
            f"───\n"
            f"~~{price_old}€~~ → **{price_new}€**\n"
            f"✨ Descuento: **-{cut}%** {emoji}\n"
            f"[🔗 Ver oferta]({link})\n"
            f"───"
        )

        embed = discord.Embed(
            title=f"{contador} {emoji} {title} — 🏷️ {store}",
            description=description,
            color=color
        )
        if thumb:
            embed.set_image(url=thumb)

        embed.set_footer(text="«El Olimpo graba esta profecía»")
        return embed

async def setup(bot: commands.Bot):
    await bot.add_cog(Ofertas(bot))
