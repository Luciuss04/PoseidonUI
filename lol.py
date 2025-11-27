from discord.ext import commands
import aiohttp
import os
from dotenv import load_dotenv
import discord

load_dotenv()
RIOT_API_KEY = os.getenv("RIOT_API_KEY")

class LoLCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.base_url = "https://euw1.api.riotgames.com"

    async def fetch(self, url):
        if not RIOT_API_KEY:
            return None
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers={"X-Riot-Token": RIOT_API_KEY}, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        try:
                            return await resp.json()
                        except Exception:
                            return None
                    return None
            except Exception:
                return None

    @commands.command()
    async def invocador(self, ctx, nombre: str):
        """Muestra información básica de un invocador"""
        if not RIOT_API_KEY:
            await ctx.send("⚠️ Falta configurar `RIOT_API_KEY` para consultar la API de Riot.")
            return
        summoner_url = f"{self.base_url}/lol/summoner/v4/summoners/by-name/{nombre}"
        data = await self.fetch(summoner_url)

        if not data:
            await ctx.send(f"⚠️ No se encontró al invocador **{nombre}**.")
            return

        nivel = data["summonerLevel"]
        icono = data["profileIconId"]

        embed = discord.Embed(
            title=f"⚔️ Invocador: {nombre}",
            description=f"Nivel {nivel} — Guardián del Olimpo digital",
            color=discord.Color.purple()
        )
        embed.set_thumbnail(url=f"http://ddragon.leagueoflegends.com/cdn/latest/img/profileicon/{icono}.png")
        await ctx.send(embed=embed)

    @commands.command()
    async def ranked(self, ctx, nombre: str):
        """Muestra estadísticas de clasificatoria"""
        if not RIOT_API_KEY:
            await ctx.send("⚠️ Falta configurar `RIOT_API_KEY` para consultar la API de Riot.")
            return
        summoner_url = f"{self.base_url}/lol/summoner/v4/summoners/by-name/{nombre}"
        summoner = await self.fetch(summoner_url)

        if not summoner:
            await ctx.send(f"⚠️ No se encontró al invocador **{nombre}**.")
            return

        summoner_id = summoner["id"]
        ranked_url = f"{self.base_url}/lol/league/v4/entries/by-summoner/{summoner_id}"
        ranked_data = await self.fetch(ranked_url)

        if not ranked_data:
            await ctx.send(f"⚠️ No se encontraron datos de clasificatoria para **{nombre}**.")
            return

        entry = ranked_data[0]
        tier = entry["tier"]
        rank = entry["rank"]
        wins = entry["wins"]
        losses = entry["losses"]

        embed = discord.Embed(
            title=f"🏆 Clasificatoria de {nombre}",
            description=f"{tier} {rank}\nVictorias: {wins} ⚔️ — Derrotas: {losses} 💀",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)

# ====== Setup obligatorio para main.py ======
async def setup(bot):
    await bot.add_cog(LoLCog(bot))
