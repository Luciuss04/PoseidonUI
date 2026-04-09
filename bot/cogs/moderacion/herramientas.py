import os
import shutil
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.config import DATA_FILE, GUILD_CONFIG_FILE
from bot.themes import Theme


class HerramientasModeracion(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.backup_loop.start()
        # Registro de Message Command (Context Menu)
        self.ctx_report = app_commands.ContextMenu(
            name="Reportar al Olimpo",
            callback=self.reportar_mensaje,
        )
        self.bot.tree.add_command(self.ctx_report)

    def cog_unload(self):
        self.backup_loop.cancel()
        self.bot.tree.remove_command(self.ctx_report.name, type=self.ctx_report.type)

    async def reportar_mensaje(self, interaction: discord.Interaction, message: discord.Message):
        """Permite reportar un mensaje directamente desde el menú de contexto."""
        # Evitar auto-reportes o reportar al propio bot
        if message.author == interaction.user:
            await interaction.response.send_message(
                "❌ No puedes reportar tus propios mensajes.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🚨 Reporte del Olimpo",
            description=f"Se ha recibido un reporte sobre un mensaje en {message.channel.mention}.",
            color=Theme.get_color(interaction.guild.id, "error"),
            timestamp=discord.utils.utcnow(),
        )

        embed.add_field(
            name="Autor del mensaje", value=f"{message.author} (`{message.author.id}`)", inline=True
        )
        embed.add_field(
            name="Reportado por", value=f"{interaction.user} (`{interaction.user.id}`)", inline=True
        )

        content = message.content[:1000] or "*[Sin contenido de texto]* "
        if message.attachments:
            content += f"\n\n📎 *Contiene {len(message.attachments)} adjuntos*"

        embed.add_field(name="Contenido reportado", value=content, inline=False)
        embed.add_field(
            name="Enlace directo", value=f"[Ir al mensaje]({message.jump_url})", inline=False
        )

        embed.set_footer(text=f"ID del Mensaje: {message.id}")

        # Enviar al canal de logs del servidor
        try:
            await interaction.client.log(embed=embed, guild=interaction.guild)
            await interaction.response.send_message(
                "✅ Gracias. El reporte ha sido enviado al Staff para su revisión.", ephemeral=True
            )
        except Exception:
            await interaction.response.send_message(
                "❌ Error al enviar el reporte. Contacta con un administrador.", ephemeral=True
            )

    # Grupo de comandos de moderación
    mod_group = app_commands.Group(name="mod", description="Herramientas de moderación")
    backup_group = app_commands.Group(
        name="backup",
        description="Sistema de copias de seguridad",
        parent=mod_group,
    )

    @tasks.loop(hours=24)
    async def backup_loop(self):
        """Tarea automática de backup cada 24 horas."""
        await self._create_auto_backup()

    @backup_loop.before_loop
    async def before_backup_loop(self):
        await self.bot.wait_until_ready()

    async def _create_auto_backup(self):
        """Lógica interna para crear backups."""
        backup_dir = "backups"
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"backup_auto_{timestamp}")
        os.makedirs(backup_path)

        files_to_backup = [DATA_FILE, GUILD_CONFIG_FILE, "theme_config.json"]
        for f in files_to_backup:
            if os.path.exists(f):
                shutil.copy2(f, os.path.join(backup_path, f))

        # Mantener solo los últimos 7 backups
        all_backups = sorted(
            [
                os.path.join(backup_dir, d)
                for d in os.listdir(backup_dir)
                if os.path.isdir(os.path.join(backup_dir, d))
            ],
            key=os.path.getmtime,
        )
        if len(all_backups) > 7:
            for old_backup in all_backups[:-7]:
                shutil.rmtree(old_backup)

    @backup_group.command(name="crear", description="Crea un backup manual de los datos")
    @app_commands.checks.has_permissions(administrator=True)
    async def create_manual_backup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            backup_dir = "backups"
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, f"backup_manual_{timestamp}")
            os.makedirs(backup_path)

            files_to_backup = [DATA_FILE, GUILD_CONFIG_FILE, "theme_config.json"]
            for f in files_to_backup:
                if os.path.exists(f):
                    shutil.copy2(f, os.path.join(backup_path, f))

            await interaction.followup.send(
                f"✅ Backup manual creado con éxito: `{backup_path}`", ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Error al crear backup: {e}", ephemeral=True)

    @backup_group.command(name="lista", description="Lista los backups disponibles")
    @app_commands.checks.has_permissions(administrator=True)
    async def list_backups(self, interaction: discord.Interaction):
        backup_dir = "backups"
        if not os.path.exists(backup_dir) or not os.listdir(backup_dir):
            await interaction.response.send_message(
                "📂 No hay backups disponibles.", ephemeral=True
            )
            return

        backups = sorted(
            [d for d in os.listdir(backup_dir) if os.path.isdir(os.path.join(backup_dir, d))],
            key=lambda x: os.path.getmtime(os.path.join(backup_dir, x)),
            reverse=True,
        )

        txt = "**Últimos backups disponibles:**\n"
        for b in backups[:10]:
            txt += f"• `{b}`\n"

        await interaction.response.send_message(txt, ephemeral=True)

    @mod_group.command(name="clear", description="Borra mensajes recientes")
    async def clear(self, interaction: discord.Interaction, cantidad: int):
        if cantidad < 1 or cantidad > 100:
            await interaction.response.send_message("⚠️ Cantidad inválida (1-100).", ephemeral=True)
            return
        await interaction.channel.purge(limit=cantidad)
        await interaction.response.send_message(f"✅ Borrados {cantidad} mensajes.", ephemeral=True)
        try:
            e = interaction.client.build_log_embed(
                "Moderación/Herramientas",
                f"Clear: {cantidad}",
                user=interaction.user,
                guild=interaction.guild,
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @mod_group.command(name="slowmode", description="Aplica slowmode al canal")
    async def slowmode(self, interaction: discord.Interaction, segundos: int):
        if segundos < 0 or segundos > 21600:
            await interaction.response.send_message(
                "⚠️ Segundos inválidos (0-21600).", ephemeral=True
            )
            return
        await interaction.channel.edit(slowmode_delay=segundos)
        await interaction.response.send_message(f"⏱️ Slowmode: {segundos}s.", ephemeral=True)
        try:
            e = interaction.client.build_log_embed(
                "Moderación/Herramientas",
                f"Slowmode: {segundos}s",
                user=interaction.user,
                guild=interaction.guild,
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @mod_group.command(name="mute", description="Silencia a un usuario en minutos")
    async def mute(self, interaction: discord.Interaction, usuario: discord.Member, minutos: int):
        if minutos < 1 or minutos > 10080:
            await interaction.response.send_message(
                "⚠️ Minutos inválidos (1-10080).", ephemeral=True
            )
            return
        try:
            await usuario.edit(
                timed_out_until=discord.utils.utcnow() + discord.timedelta(minutes=minutos)
            )
            await interaction.response.send_message(
                f"🔇 {usuario.mention} silenciado por {minutos} minutos."
            )
            try:
                e = interaction.client.build_log_embed(
                    "Moderación/Herramientas",
                    "Mute",
                    user=interaction.user,
                    guild=interaction.guild,
                    extra={
                        "Usuario": f"{usuario} ({usuario.id})",
                        "Minutos": str(minutos),
                    },
                )
                await interaction.client.log(embed=e, guild=interaction.guild)
            except Exception:
                pass
            try:
                interaction.client.dispatch("mod_mute", interaction.guild, usuario)
            except Exception:
                pass
        except Exception:
            await interaction.response.send_message("⚠️ No se pudo silenciar.", ephemeral=True)

    @mod_group.command(name="unmute", description="Quita el silencio a un usuario")
    async def unmute(self, interaction: discord.Interaction, usuario: discord.Member):
        try:
            await usuario.edit(timed_out_until=None)
            await interaction.response.send_message(f"🔊 {usuario.mention} ya no está silenciado.")
            try:
                e = interaction.client.build_log_embed(
                    "Moderación/Herramientas",
                    "Unmute",
                    user=interaction.user,
                    guild=interaction.guild,
                    extra={"Usuario": f"{usuario} ({usuario.id})"},
                )
                await interaction.client.log(embed=e, guild=interaction.guild)
            except Exception:
                pass
            try:
                interaction.client.dispatch("mod_unmute", interaction.guild, usuario)
            except Exception:
                pass
        except Exception:
            await interaction.response.send_message("⚠️ No se pudo desilenciar.", ephemeral=True)

    @mod_group.command(name="lock", description="Bloquea un canal para escribir")
    async def lock(
        self, interaction: discord.Interaction, canal: discord.TextChannel | None = None
    ):
        canal = canal or interaction.channel
        overwrite = canal.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = False
        await canal.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.response.send_message(f"🔒 Canal bloqueado: {canal.mention}")
        try:
            e = interaction.client.build_log_embed(
                "Moderación/Herramientas",
                "Lock canal",
                user=interaction.user,
                guild=interaction.guild,
                extra={"Canal": canal.mention},
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @mod_group.command(name="unlock", description="Desbloquea un canal")
    async def unlock(
        self, interaction: discord.Interaction, canal: discord.TextChannel | None = None
    ):
        canal = canal or interaction.channel
        overwrite = canal.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = True
        await canal.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.response.send_message(f"🔓 Canal desbloqueado: {canal.mention}")
        try:
            e = interaction.client.build_log_embed(
                "Moderación/Herramientas",
                "Unlock canal",
                user=interaction.user,
                guild=interaction.guild,
                extra={"Canal": canal.mention},
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @mod_group.command(name="warn", description="Advierte a un usuario")
    async def warn(self, interaction: discord.Interaction, usuario: discord.Member, razon: str):
        try:
            await usuario.send(f"⚠️ Advertencia en {interaction.guild.name}: {razon}")
        except Exception:
            pass
        await interaction.response.send_message(f"⚠️ Advertencia enviada a {usuario.mention}.")
        try:
            e = interaction.client.build_log_embed(
                "Moderación/Herramientas",
                "Warn",
                user=interaction.user,
                guild=interaction.guild,
                extra={"Usuario": f"{usuario} ({usuario.id})", "Razón": razon[:180]},
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass
        try:
            interaction.client.dispatch("mod_warn", interaction.guild, usuario)
        except Exception:
            pass


async def setup(bot):
    await bot.add_cog(HerramientasModeracion(bot))
