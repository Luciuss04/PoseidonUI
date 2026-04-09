from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import (
    get_guild_setting,
    load_json_file,
    save_json_file_atomic,
    set_guild_setting,
)
from bot.themes import Theme


class ConfesionModal(discord.ui.Modal, title="Confesión Anónima"):
    content = discord.ui.TextInput(
        label="Tu Confesión",
        style=discord.TextStyle.paragraph,
        placeholder="Escribe aquí tu secreto... Nadie sabrá que fuiste tú.",
        min_length=10,
        max_length=1000,
    )

    def __init__(self, cog, channel_id):
        super().__init__()
        self.cog = cog
        self.channel_id = channel_id

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            await interaction.response.send_message(
                "❌ El canal de confesiones configurado ya no existe.", ephemeral=True
            )
            return

        # Crear embed anónimo
        count = self.cog.get_count(interaction.guild.id) + 1
        self.cog.increment_count(interaction.guild.id)

        embed = discord.Embed(
            title=f"🤫 Confesión #{count}",
            description=self.content.value,
            color=Theme.get_color(interaction.guild.id, "primary"),
            timestamp=datetime.now(),
        )
        embed.set_footer(text="Confesión Anónima • ¿Quién habrá sido?")

        # Enviar al canal
        try:
            await channel.send(embed=embed)
            await interaction.response.send_message(
                "✅ Tu confesión ha sido enviada anónimamente.", ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ No tengo permisos para enviar mensajes en el canal de confesiones.",
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Ocurrió un error: {e}", ephemeral=True)


class Confesiones(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config_file = "confesiones_config.json"
        self.config = self._load_config()

    def _load_config(self):
        data = load_json_file(self.config_file, {})
        return data if isinstance(data, dict) else {}

    def _save_config(self):
        save_json_file_atomic(self.config_file, self.config, indent=4, ensure_ascii=False)

    def get_count(self, guild_id):
        gid = str(guild_id)
        if gid not in self.config:
            return 0
        return self.config[gid].get("count", 0)

    def increment_count(self, guild_id):
        gid = str(guild_id)
        if gid not in self.config:
            self.config[gid] = {"channel_id": None, "count": 0}
        self.config[gid]["count"] = self.config[gid].get("count", 0) + 1
        self._save_config()

    @app_commands.command(
        name="confesion", description="Envía una confesión anónima al canal configurado"
    )
    async def confesion(self, interaction: discord.Interaction):
        gid = str(interaction.guild.id)
        channel_id = get_guild_setting(interaction.guild.id, "confesiones_channel_id", None)
        if not channel_id:
            channel_id = None
            if gid in self.config:
                channel_id = self.config[gid].get("channel_id")
        if not channel_id:
            await interaction.response.send_message(
                "⚠️ El sistema de confesiones no está configurado en este servidor. Pide a un admin que use `/set_confesiones`.",
                ephemeral=True,
            )
            return

        await interaction.response.send_modal(ConfesionModal(self, int(channel_id)))

    @app_commands.command(
        name="set_confesiones", description="Configura el canal para las confesiones"
    )
    @app_commands.describe(canal="Canal donde se enviarán las confesiones")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_confesiones(self, interaction: discord.Interaction, canal: discord.TextChannel):
        gid = str(interaction.guild.id)
        if gid not in self.config:
            self.config[gid] = {"count": 0}

        self.config[gid]["channel_id"] = canal.id
        self._save_config()
        set_guild_setting(interaction.guild.id, "confesiones_channel_id", int(canal.id))

        await interaction.response.send_message(
            f"✅ Canal de confesiones establecido en {canal.mention}. Las confesiones empezarán desde el #{self.config[gid].get('count', 0) + 1}."
        )

    @set_confesiones.error
    async def set_confesiones_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ Necesitas permisos de Administrador para usar este comando.", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Confesiones(bot))
