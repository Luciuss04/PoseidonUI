import discord
from discord import app_commands
from discord.ext import commands


class HerramientasModeracion(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="clear", description="Borra mensajes recientes")
    async def clear(self, interaction: discord.Interaction, cantidad: int):
        if cantidad < 1 or cantidad > 100:
            await interaction.response.send_message(
                "⚠️ Cantidad inválida (1-100).", ephemeral=True
            )
            return
        await interaction.channel.purge(limit=cantidad)
        await interaction.response.send_message(
            f"✅ Borrados {cantidad} mensajes.", ephemeral=True
        )
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

    @app_commands.command(name="slowmode", description="Aplica slowmode al canal")
    async def slowmode(self, interaction: discord.Interaction, segundos: int):
        if segundos < 0 or segundos > 21600:
            await interaction.response.send_message(
                "⚠️ Segundos inválidos (0-21600).", ephemeral=True
            )
            return
        await interaction.channel.edit(slowmode_delay=segundos)
        await interaction.response.send_message(
            f"⏱️ Slowmode: {segundos}s.", ephemeral=True
        )
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

    @app_commands.command(name="mute", description="Silencia a un usuario en minutos")
    async def mute(
        self, interaction: discord.Interaction, usuario: discord.Member, minutos: int
    ):
        if minutos < 1 or minutos > 10080:
            await interaction.response.send_message(
                "⚠️ Minutos inválidos (1-10080).", ephemeral=True
            )
            return
        try:
            await usuario.edit(
                timed_out_until=discord.utils.utcnow()
                + discord.timedelta(minutes=minutos)
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
            await interaction.response.send_message(
                "⚠️ No se pudo silenciar.", ephemeral=True
            )

    @app_commands.command(name="unmute", description="Quita el silencio a un usuario")
    async def unmute(self, interaction: discord.Interaction, usuario: discord.Member):
        try:
            await usuario.edit(timed_out_until=None)
            await interaction.response.send_message(
                f"🔊 {usuario.mention} ya no está silenciado."
            )
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
            await interaction.response.send_message(
                "⚠️ No se pudo desilenciar.", ephemeral=True
            )

    @app_commands.command(name="lock", description="Bloquea un canal para escribir")
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

    @app_commands.command(name="unlock", description="Desbloquea un canal")
    async def unlock(
        self, interaction: discord.Interaction, canal: discord.TextChannel | None = None
    ):
        canal = canal or interaction.channel
        overwrite = canal.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = True
        await canal.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.response.send_message(
            f"🔓 Canal desbloqueado: {canal.mention}"
        )
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

    @app_commands.command(name="warn", description="Advierte a un usuario")
    async def warn(
        self, interaction: discord.Interaction, usuario: discord.Member, razon: str
    ):
        try:
            await usuario.send(f"⚠️ Advertencia en {interaction.guild.name}: {razon}")
        except Exception:
            pass
        await interaction.response.send_message(
            f"⚠️ Advertencia enviada a {usuario.mention}."
        )
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
