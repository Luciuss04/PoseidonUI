import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import re
from bot.themes import Theme

CONFIG_FILE = "automod_config.json"
DEFAULT_BAD_WORDS = ["tonto", "estupido", "idiota", "imbecil", "mierda", "puta", "cabron"]

class AutoMod(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = self._load_config()

    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_config(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4)

    # Grupo de comandos de automoderación
    automod_group = app_commands.Group(name="automod", description="Configuración de AutoMod")

    def get_guild_config(self, guild_id: int):
        sid = str(guild_id)
        if sid not in self.config:
            self.config[sid] = {
                "bad_words": DEFAULT_BAD_WORDS.copy(),
                "enabled_bad_words": False,
                "enabled_caps": False,
                "caps_threshold": 0.7, # 70% mayusculas
                "ignored_roles": [],
                "ignored_channels": []
            }
            self._save_config()
        return self.config[sid]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        
        # Ignorar administradores/manage_messages
        if message.author.guild_permissions.manage_messages or message.author.guild_permissions.administrator:
            return

        conf = self.get_guild_config(message.guild.id)
        
        # Ignorar canales
        if message.channel.id in conf.get("ignored_channels", []):
            return
            
        # Ignorar roles
        user_roles = [r.id for r in message.author.roles]
        for r_id in conf.get("ignored_roles", []):
            if r_id in user_roles:
                return

        # 1. Filtro de Malas Palabras
        if conf.get("enabled_bad_words", False):
            content_lower = message.content.lower()
            # Tokenizar simple
            words = re.findall(r'\w+', content_lower)
            bad_words = conf.get("bad_words", [])
            
            found = False
            for bw in bad_words:
                if bw in words: # Coincidencia exacta de palabra
                    found = True
                    break
                # Opcional: Búsqueda parcial if bw in content_lower
            
            if found:
                await self._punish(message, "Lenguaje inapropiado")
                return

        # 2. Filtro de Mayúsculas
        if conf.get("enabled_caps", False):
            if len(message.content) > 10: # Solo mensajes > 10 chars
                caps_count = sum(1 for c in message.content if c.isupper())
                ratio = caps_count / len(message.content)
                if ratio > conf.get("caps_threshold", 0.7):
                    await self._punish(message, "Exceso de mayúsculas")
                    return

    async def _punish(self, message: discord.Message, reason: str):
        try:
            await message.delete()
        except discord.NotFound:
            pass
        except discord.Forbidden:
            return

        # Avisar al usuario
        try:
            embed = discord.Embed(
                title="🛡️ Auto-Moderación",
                description=f"Tu mensaje fue eliminado.\n**Razón:** {reason}",
                color=Theme.get_color(message.guild.id, 'error')
            )
            msg = await message.channel.send(f"{message.author.mention}", embed=embed)
            await asyncio.sleep(5)
            await msg.delete()
        except Exception:
            pass
            
        # Log
        try:
            e = self.bot.build_log_embed(
                "AutoMod",
                f"Mensaje eliminado: {reason}",
                user=message.author,
                guild=message.guild,
                extra={"Contenido": message.content[:100]}
            )
            await self.bot.log(embed=e, guild=message.guild)
        except Exception:
            pass

    # Comandos de Configuración
    
    @automod_group.command(name="status", description="Muestra la configuración de AutoMod")
    @app_commands.checks.has_permissions(administrator=True)
    async def automod_status(self, interaction: discord.Interaction):
        conf = self.get_guild_config(interaction.guild.id)
        
        bw_status = "✅ Activado" if conf.get("enabled_bad_words") else "❌ Desactivado"
        caps_status = "✅ Activado" if conf.get("enabled_caps") else "❌ Desactivado"
        
        embed = discord.Embed(
            title="🛡️ Configuración AutoMod",
            color=Theme.get_color(interaction.guild.id, 'primary')
        )
        embed.add_field(name="🤬 Filtro Groserías", value=bw_status, inline=True)
        embed.add_field(name="🔠 Filtro Mayúsculas", value=caps_status, inline=True)
        embed.add_field(name="📝 Palabras Prohibidas", value=f"{len(conf.get('bad_words', []))} palabras", inline=False)
        embed.add_field(name="📊 Límite Mayúsculas", value=f"{int(conf.get('caps_threshold', 0.7)*100)}%", inline=True)
        
        embed.set_footer(text="Usa /automod_toggle para activar/desactivar")
        await interaction.response.send_message(embed=embed)

    @automod_group.command(name="toggle", description="Activa/Desactiva filtros")
    @app_commands.describe(filtro="El filtro a configurar")
    @app_commands.choices(filtro=[
        app_commands.Choice(name="Groserías (Bad Words)", value="bad_words"),
        app_commands.Choice(name="Mayúsculas (Caps)", value="caps")
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def automod_toggle(self, interaction: discord.Interaction, filtro: str, estado: bool):
        conf = self.get_guild_config(interaction.guild.id)
        
        key = f"enabled_{filtro}"
        conf[key] = estado
        self._save_config()
        
        await interaction.response.send_message(f"✅ Filtro **{filtro}** establecido a: {'Activado' if estado else 'Desactivado'}")

    @automod_group.command(name="addword", description="Añade una palabra prohibida")
    @app_commands.checks.has_permissions(administrator=True)
    async def automod_addword(self, interaction: discord.Interaction, palabra: str):
        conf = self.get_guild_config(interaction.guild.id)
        words = conf.get("bad_words", [])
        
        palabra = palabra.lower().strip()
        if palabra in words:
            await interaction.response.send_message("⚠️ Esa palabra ya está en la lista.", ephemeral=True)
            return
            
        words.append(palabra)
        conf["bad_words"] = words
        self._save_config()
        
        await interaction.response.send_message(f"✅ Palabra añadida: ||{palabra}||", ephemeral=True)

    @automod_group.command(name="delword", description="Elimina una palabra prohibida")
    @app_commands.checks.has_permissions(administrator=True)
    async def automod_delword(self, interaction: discord.Interaction, palabra: str):
        conf = self.get_guild_config(interaction.guild.id)
        words = conf.get("bad_words", [])
        
        palabra = palabra.lower().strip()
        if palabra not in words:
            await interaction.response.send_message("⚠️ Esa palabra no está en la lista.", ephemeral=True)
            return
            
        words.remove(palabra)
        conf["bad_words"] = words
        self._save_config()
        
        await interaction.response.send_message(f"✅ Palabra eliminada: ||{palabra}||", ephemeral=True)

import asyncio

async def setup(bot):
    await bot.add_cog(AutoMod(bot))
