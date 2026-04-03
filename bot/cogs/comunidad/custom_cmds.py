# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
from discord import app_commands
import json
import os

from bot.config import get_guild_setting, set_guild_setting

class CustomCommands(commands.Cog):
    """Motor de Comandos Personalizados Dinámicos (v4.2)"""
    def __init__(self, bot):
        self.bot = bot
        self.bot.tree.on_error = self.on_tree_error # Capturar errores de comandos dinámicos

    async def on_tree_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandNotFound):
            return # Ignorar si no existe
        print(f"🔥 [CustomCmds] Error en el árbol: {error}")

    def _get_cmds(self, guild_id):
        return get_guild_setting(guild_id, "custom_commands", {})

    @commands.Cog.listener()
    async def on_ready(self):
        # Al iniciar, podríamos registrar comandos dinámicos aquí si fuera necesario,
        # pero para Slash Commands dinámicos por servidor usaremos el evento on_interaction
        # o un comando base que actúe como router.
        pass

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.application_command:
            return
            
        # Solo procesamos si el comando NO existe en el árbol oficial
        # (Esto es un fallback para comandos dinámicos que no requieren sync global)
        cmd_name = interaction.data.get('name')
        if not cmd_name: return
        
        # Verificar si el comando existe en el árbol oficial del bot
        official_cmds = [c.name for c in self.bot.tree.get_commands(guild=interaction.guild)]
        if cmd_name in official_cmds:
            return # Dejar que el árbol oficial lo maneje

        # Buscar en comandos personalizados del servidor
        if not interaction.guild: return
        cmds = self._get_cmds(interaction.guild.id)
        
        if cmd_name in cmds:
            cmd_data = cmds[cmd_name]
            response = cmd_data.get("response", "No hay respuesta configurada.")
            
            # Variables básicas en la respuesta
            response = response.replace("{user}", interaction.user.mention)
            response = response.replace("{server}", interaction.guild.name)
            
            await interaction.response.send_message(response)

async def setup(bot):
    await bot.add_cog(CustomCommands(bot))
