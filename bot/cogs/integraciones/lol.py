import os
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from bot.themes import Theme

load_dotenv()
RIOT_API_KEY = os.getenv("RIOT_API_KEY")

class LoLCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.base_url = "https://euw1.api.riotgames.com" # Default region EUW

    async def fetch(self, url):
        if not RIOT_API_KEY:
            return None
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    url,
                    headers={"X-Riot-Token": RIOT_API_KEY},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        try:
                            return await resp.json()
                        except Exception:
                            return None
                    return None
            except Exception:
                return None

    @app_commands.command(name="lol", description="Sistema de integración con League of Legends")
    @app_commands.describe(accion="perfil, ranked", nombre="Nombre de invocador (Riot ID)")
    @app_commands.choices(accion=[
        app_commands.Choice(name="Ver Perfil", value="perfil"),
        app_commands.Choice(name="Ver Ranked", value="ranked")
    ])
    async def lol(self, interaction: discord.Interaction, accion: str, nombre: str):
        if not RIOT_API_KEY:
            await interaction.response.send_message("⚠️ Falta configurar `RIOT_API_KEY` en el archivo .env.", ephemeral=True)
            return

        # Nota: La API de Riot ha cambiado a Riot ID (Name#Tag).
        # Este código usa la API v4 de Summoner por nombre, que puede estar deprecada o requerir ajustes.
        # Se mantiene la estructura para cuando se tenga una Key válida.
        
        # Intentamos limpiar el nombre
        summoner_name = nombre.replace(" ", "%20")
        
        if accion == "perfil":
            summoner_url = f"{self.base_url}/lol/summoner/v4/summoners/by-name/{summoner_name}"
            data = await self.fetch(summoner_url)

            if not data:
                await interaction.response.send_message(f"⚠️ No se encontró al invocador **{nombre}** (o la API falló).", ephemeral=True)
                return

            nivel = data.get("summonerLevel", "Unknown")
            icono = data.get("profileIconId", 0)

            embed = discord.Embed(
                title=f"⚔️ Invocador: {nombre}",
                description=f"Nivel {nivel} — Guardián del Olimpo digital",
                color=Theme.get_color(interaction.guild.id, 'secondary'),
            )
            embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
            embed.set_thumbnail(
                url=f"http://ddragon.leagueoflegends.com/cdn/latest/img/profileicon/{icono}.png"
            )
            await interaction.response.send_message(embed=embed)

        elif accion == "ranked":
            # Primero obtenemos ID
            summoner_url = f"{self.base_url}/lol/summoner/v4/summoners/by-name/{summoner_name}"
            summoner = await self.fetch(summoner_url)

            if not summoner:
                await interaction.response.send_message(f"⚠️ No se encontró al invocador **{nombre}**.", ephemeral=True)
                return

            summoner_id = summoner["id"]
            ranked_url = f"{self.base_url}/lol/league/v4/entries/by-summoner/{summoner_id}"
            ranked_data = await self.fetch(ranked_url)

            if not ranked_data:
                await interaction.response.send_message(f"⚠️ No se encontraron datos de clasificatoria para **{nombre}**.", ephemeral=True)
                return

            # Buscar Solo/Duo queue
            entry = None
            for e in ranked_data:
                if e["queueType"] == "RANKED_SOLO_5x5":
                    entry = e
                    break
            
            if not entry and ranked_data: entry = ranked_data[0] # Fallback

            if entry:
                tier = entry["tier"]
                rank = entry["rank"]
                wins = entry["wins"]
                losses = entry["losses"]
                lp = entry["leaguePoints"]
                
                embed = discord.Embed(
                    title=f"🏆 Clasificatoria de {nombre}",
                    description=f"**{tier} {rank}** - {lp} LP\nVictorias: {wins} ⚔️ — Derrotas: {losses} 💀",
                    color=Theme.get_color(interaction.guild.id, 'primary'),
                )
                embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message(f"⚠️ **{nombre}** no tiene clasificación visible.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(LoLCog(bot))
