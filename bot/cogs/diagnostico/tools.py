import time

import discord
from discord import app_commands
from discord.ext import commands


class ToolsDiagnostico(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start = time.time()

    @app_commands.command(name="ping", description="Latencia del bot")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"🏓 {round(self.bot.latency*1000)} ms")
        try:
            e = interaction.client.build_log_embed(
                "Diagnóstico/Tools",
                "Ping",
                user=interaction.user,
                guild=interaction.guild,
                extra={"Latencia": f"{round(self.bot.latency*1000)} ms"},
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @app_commands.command(name="uptime", description="Tiempo activo")
    async def uptime(self, interaction: discord.Interaction):
        secs = int(time.time() - self.start)
        mins = secs // 60
        hrs = mins // 60
        await interaction.response.send_message(f"⏳ {hrs} h {mins%60} min")
        try:
            e = interaction.client.build_log_embed(
                "Diagnóstico/Tools",
                "Uptime",
                user=interaction.user,
                guild=interaction.guild,
                extra={"Horas": str(hrs), "Minutos": str(mins % 60)},
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @app_commands.command(name="servidor", description="Información del servidor")
    async def servidor(self, interaction: discord.Interaction):
        g = interaction.guild
        if not g:
            await interaction.response.send_message(
                "⚠️ Solo en servidores.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            f"👥 {g.member_count} usuarios, {len(g.text_channels)} canales de texto"
        )
        try:
            e = interaction.client.build_log_embed(
                "Diagnóstico/Tools",
                "Servidor info",
                user=interaction.user,
                guild=interaction.guild,
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @app_commands.command(name="roles", description="Listado de roles (top 10)")
    async def roles(self, interaction: discord.Interaction):
        g = interaction.guild
        if not g:
            await interaction.response.send_message(
                "⚠️ Solo en servidores.", ephemeral=True
            )
            return
        names = [r.name for r in g.roles][-10:]
        await interaction.response.send_message("🔖 " + ", ".join(names))
        try:
            e = interaction.client.build_log_embed(
                "Diagnóstico/Tools",
                "Roles mostrados",
                user=interaction.user,
                guild=interaction.guild,
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @app_commands.command(name="canales", description="Resumen de canales")
    async def canales(self, interaction: discord.Interaction):
        g = interaction.guild
        if not g:
            await interaction.response.send_message(
                "⚠️ Solo en servidores.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            f"📚 texto: {len(g.text_channels)}, voz: {len(g.voice_channels)}"
        )
        try:
            e = interaction.client.build_log_embed(
                "Diagnóstico/Tools",
                "Canales mostrados",
                user=interaction.user,
                guild=interaction.guild,
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @app_commands.command(name="comandos", description="Total de comandos disponibles")
    async def comandos(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"🧭 {len(self.bot.tree.get_commands())} comandos"
        )
        try:
            e = interaction.client.build_log_embed(
                "Diagnóstico/Tools",
                "Comandos totales",
                user=interaction.user,
                guild=interaction.guild,
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @app_commands.command(name="perms", description="Permisos del usuario en el canal")
    async def perms(self, interaction: discord.Interaction):
        p = interaction.channel.permissions_for(interaction.user)
        await interaction.response.send_message(
            f"🔐 enviar: {p.send_messages}, adjuntar: {p.attach_files}, links: {p.embed_links}"
        )
        try:
            e = interaction.client.build_log_embed(
                "Diagnóstico/Tools",
                "Permisos usuario",
                user=interaction.user,
                guild=interaction.guild,
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass


async def setup(bot):
    await bot.add_cog(ToolsDiagnostico(bot))
