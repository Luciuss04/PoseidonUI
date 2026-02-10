import json
import random
import os
import discord

from discord import app_commands
from discord.ext import commands

from bot.config import DATA_FILE, RANGOS
from bot.themes import Theme

SETTINGS_FILE = "niveles_settings.json"

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


def cargar_settings():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        return {"enabled": True}
    except Exception:
        return {"enabled": True}


def guardar_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)


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


class NivelesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.niveles = cargar_niveles()
        self.settings = cargar_settings()

    @app_commands.command(name="niveles", description="Muestra tu nivel y experiencia actual")
    async def niveles(self, interaction: discord.Interaction, usuario: discord.User | None = None):
        target = usuario or interaction.user
        uid = str(target.id)
        
        data = self.niveles.get(uid, {"xp": 0, "nivel": 1})
        nivel = data["nivel"]
        xp = data["xp"]
        xp_next = xp_necesaria(nivel)
        rango = obtener_rango(nivel)
        
        # Calcular progreso
        porcentaje = int((xp / xp_next) * 10)
        barra = "🟦" * porcentaje + "⬜" * (10 - porcentaje)
        
        embed = discord.Embed(
            title=f"⭐ Nivel de {target.display_name}",
            color=Theme.get_color(interaction.guild.id, 'secondary')
        )
        embed.set_thumbnail(url=target.avatar.url if target.avatar else None)
        
        embed.add_field(name="Nivel", value=f"**{nivel}**", inline=True)
        embed.add_field(name="Rango", value=f"**{rango or 'Mortal'}**", inline=True)
        embed.add_field(name="Progreso", value=f"`{xp}/{xp_next} XP`\n{barra}", inline=False)
        
        embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="Ranking global de niveles")
    async def leaderboard(self, interaction: discord.Interaction):
        # Convertir a lista y ordenar
        lista = []
        for uid, data in self.niveles.items():
            lista.append((uid, data["nivel"], data["xp"]))
            
        # Ordenar por nivel (desc) y luego XP (desc)
        lista.sort(key=lambda x: (x[1], x[2]), reverse=True)
        
        top_10 = lista[:10]
        
        embed = discord.Embed(title="🏆 Ranking de Niveles", color=Theme.get_color(interaction.guild.id, 'primary'))
        
        desc = ""
        for i, (uid, nivel, xp) in enumerate(top_10, 1):
            try:
                user = await self.bot.fetch_user(int(uid))
                name = user.display_name
            except:
                name = f"Usuario {uid}"
                
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            desc += f"**{medal} {name}** — Nivel {nivel} ({xp} XP)\n"
            
        if not desc:
            desc = "No hay datos aún."
            
        embed.description = desc
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="niveles_toggle", description="Activar/desactivar el sistema de niveles (Admin-only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def niveles_toggle(self, interaction: discord.Interaction):
        current_state = self.settings.get("enabled", True)
        new_state = not current_state
        self.settings["enabled"] = new_state
        guardar_settings(self.settings)
        
        status = "✅ Activado" if new_state else "⛔ Desactivado"
        await interaction.response.send_message(f"Sistema de niveles {status}.")

    @niveles_toggle.error
    async def niveles_toggle_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ No tienes permisos de administrador para usar este comando.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Error: {error}", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if not self.settings.get("enabled", True):
            return

        nuevo_nivel, rango = procesar_mensaje(message, self.niveles)
        guardar_niveles(self.niveles)

        if nuevo_nivel:
            await message.channel.send(
                f"🌟 {message.author.mention} ha alcanzado el nivel **{nuevo_nivel}** ({rango}) ⚔️"
            )


async def setup(bot):
    await bot.add_cog(NivelesCog(bot))
