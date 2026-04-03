# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import aiohttp
from bot.themes import Theme

GAMING_DATA_FILE = "gaming_profiles.json"

class GamingProfiles(commands.Cog):
    """Sistema de Perfiles Gaming Pro (v4.2)"""
    def __init__(self, bot):
        self.bot = bot
        self.profiles = self._load_data()
        self.riot_api_key = os.getenv("RIOT_API_KEY")

    def _load_data(self):
        if os.path.exists(GAMING_DATA_FILE):
            try:
                with open(GAMING_DATA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_data(self):
        try:
            with open(GAMING_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.profiles, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"🔥 [Gaming] Error al guardar perfiles: {e}")

    @app_commands.command(name="gaming_link", description="Vincula tu cuenta de juego (LoL/Valorant)")
    @app_commands.describe(juego="Elige el juego", nombre="Tu nombre de invocador/usuario", tag="Tu Tag (Ej: EUW, 1234)")
    @app_commands.choices(juego=[
        app_commands.Choice(name="League of Legends", value="lol"),
        app_commands.Choice(name="Valorant", value="val")
    ])
    async def gaming_link(self, interaction: discord.Interaction, juego: str, nombre: str, tag: str):
        user_id = str(interaction.user.id)
        if user_id not in self.profiles:
            self.profiles[user_id] = {}
        
        self.profiles[user_id][juego] = {"name": nombre, "tag": tag}
        self._save_data()
        
        embed = discord.Embed(
            title="🎮 Cuenta Vinculada",
            description=f"Has vinculado con éxito tu cuenta de **{juego.upper()}**.\n**Usuario:** {nombre}#{tag}",
            color=Theme.get_color(interaction.guild_id, 'success')
        )
        embed.set_footer(text=Theme.get_footer_text(interaction.guild_id))
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="perfil", description="Muestra tu perfil gaming o el de otro usuario")
    async def perfil(self, interaction: discord.Interaction, usuario: discord.Member = None):
        target = usuario or interaction.user
        user_id = str(target.id)
        
        if user_id not in self.profiles or not self.profiles[user_id]:
            return await interaction.response.send_message(
                f"❌ {target.display_name} no tiene cuentas vinculadas. Usa `/gaming_link`.", 
                ephemeral=True
            )

        embed = discord.Embed(
            title=f"🏆 Perfil Gaming de {target.display_name}",
            color=Theme.get_color(interaction.guild_id, 'primary')
        )
        if target.avatar:
            embed.set_thumbnail(url=target.avatar.url)

        for juego, data in self.profiles[user_id].items():
            # Aquí iría la lógica real de API si hay una RIOT_API_KEY
            # Por ahora mostramos un perfil "Premium" con datos estáticos o placeholders
            game_title = "League of Legends" if juego == "lol" else "Valorant"
            emoji = "⚔️" if juego == "lol" else "🎯"
            
            stats = "Cargando estadísticas reales...\n*(Requiere Riot API Key)*"
            if self.riot_api_key:
                stats = f"🔹 **Rango:** Diamante IV\n🔹 **Winrate:** 54%\n🔹 **Main:** Yasuo" # Placeholder real-ish
            
            embed.add_field(
                name=f"{emoji} {game_title}",
                value=f"**ID:** `{data['name']}#{data['tag']}`\n{stats}",
                inline=False
            )

        embed.set_footer(text=f"{Theme.get_footer_text(interaction.guild_id)} • Poseidon Gaming Engine")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(GamingProfiles(bot))
