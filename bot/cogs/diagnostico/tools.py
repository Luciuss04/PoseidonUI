import os
import platform
import shutil
import time
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import LOG_CHANNEL_ID, get_guild_setting, set_guild_setting


class ToolsDiagnostico(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start = time.time()

    config_group = app_commands.Group(
        name="config", description="Configuración por servidor"
    )

    @config_group.command(name="ver", description="Ver configuración del servidor")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def config_ver(self, interaction: discord.Interaction):
        g = interaction.guild
        if not g:
            await interaction.response.send_message("⚠️ Solo en servidores.", ephemeral=True)
            return
        log_channel_id = get_guild_setting(g.id, "log_channel_id", LOG_CHANNEL_ID)
        staff_role_ids = get_guild_setting(g.id, "staff_role_ids", None)
        staff_role_names = get_guild_setting(g.id, "staff_role_names", None)
        alert_channel_id = get_guild_setting(g.id, "alert_channel_id", None)
        alert_channel_name = get_guild_setting(g.id, "alert_channel_name", None)

        embed = discord.Embed(
            title="⚙️ Configuración del servidor",
            color=discord.Color.blurple(),
        )
        try:
            ch = g.get_channel(int(log_channel_id)) if log_channel_id else None
        except Exception:
            ch = None
        embed.add_field(
            name="🧾 Canal de logs",
            value=ch.mention if isinstance(ch, discord.TextChannel) else str(log_channel_id),
            inline=False,
        )
        if isinstance(staff_role_ids, list) and staff_role_ids:
            mentions = []
            for rid in staff_role_ids:
                try:
                    r = g.get_role(int(rid))
                    if r:
                        mentions.append(r.mention)
                except Exception:
                    pass
            embed.add_field(
                name="🛡️ Staff (roles)",
                value=" ".join(mentions) if mentions else ", ".join(map(str, staff_role_ids)),
                inline=False,
            )
        elif isinstance(staff_role_names, list) and staff_role_names:
            embed.add_field(
                name="🛡️ Staff (nombres)",
                value=", ".join(map(str, staff_role_names)),
                inline=False,
            )
        if alert_channel_id:
            try:
                ach = g.get_channel(int(alert_channel_id))
            except Exception:
                ach = None
            embed.add_field(
                name="⚔️ Canal de alertas (id)",
                value=ach.mention if isinstance(ach, discord.TextChannel) else str(alert_channel_id),
                inline=False,
            )
        if alert_channel_name:
            embed.add_field(
                name="⚔️ Canal de alertas (nombre)",
                value=str(alert_channel_name),
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @config_group.command(name="logcanal", description="Configura el canal de logs")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def config_logcanal(
        self, interaction: discord.Interaction, canal: discord.TextChannel
    ):
        g = interaction.guild
        if not g:
            await interaction.response.send_message("⚠️ Solo en servidores.", ephemeral=True)
            return
        set_guild_setting(g.id, "log_channel_id", int(canal.id))
        await interaction.response.send_message(
            f"✅ Canal de logs establecido a {canal.mention}", ephemeral=True
        )
        try:
            e = interaction.client.build_log_embed(
                "Config",
                "Canal de logs actualizado",
                user=interaction.user,
                guild=interaction.guild,
                extra={"Canal": str(canal.id)},
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @config_group.command(name="staffrol", description="Configura el rol staff")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def config_staffrol(self, interaction: discord.Interaction, rol: discord.Role):
        g = interaction.guild
        if not g:
            await interaction.response.send_message("⚠️ Solo en servidores.", ephemeral=True)
            return
        set_guild_setting(g.id, "staff_role_ids", [int(rol.id)])
        await interaction.response.send_message(
            f"✅ Rol staff establecido a {rol.mention}", ephemeral=True
        )
        try:
            e = interaction.client.build_log_embed(
                "Config",
                "Rol staff actualizado",
                user=interaction.user,
                guild=interaction.guild,
                extra={"Rol": str(rol.id)},
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @config_group.command(name="alertas", description="Configura el canal de alertas")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def config_alertas(
        self, interaction: discord.Interaction, canal: discord.TextChannel
    ):
        g = interaction.guild
        if not g:
            await interaction.response.send_message("⚠️ Solo en servidores.", ephemeral=True)
            return
        set_guild_setting(g.id, "alert_channel_id", int(canal.id))
        await interaction.response.send_message(
            f"✅ Canal de alertas establecido a {canal.mention}", ephemeral=True
        )
        try:
            e = interaction.client.build_log_embed(
                "Config",
                "Canal de alertas actualizado",
                user=interaction.user,
                guild=interaction.guild,
                extra={"Canal": str(canal.id)},
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @app_commands.command(
        name="diagnostico",
        description="Diagnóstico de dependencias y configuración del servidor",
    )
    @app_commands.guild_only()
    async def diagnostico(self, interaction: discord.Interaction):
        g = interaction.guild
        if not g:
            await interaction.response.send_message("⚠️ Solo en servidores.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        latency_ms = round(self.bot.latency * 1000)
        opus_ok = discord.opus.is_loaded()
        ffmpeg_path = shutil.which("ffmpeg")

        log_channel_id = get_guild_setting(g.id, "log_channel_id", LOG_CHANNEL_ID)
        try:
            log_channel = g.get_channel(int(log_channel_id)) if log_channel_id else None
        except Exception:
            log_channel = None

        embed = discord.Embed(
            title="🧪 Diagnóstico",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="📡 Latencia", value=f"{latency_ms} ms", inline=True)
        embed.add_field(
            name="🎙️ Opus", value="✅ Cargado" if opus_ok else "❌ No cargado", inline=True
        )
        embed.add_field(
            name="🎞️ ffmpeg",
            value=f"✅ {ffmpeg_path}" if ffmpeg_path else "❌ No encontrado en PATH",
            inline=False,
        )
        embed.add_field(
            name="🐍 Python", value=platform.python_version(), inline=True
        )
        embed.add_field(name="📦 discord.py", value=discord.__version__, inline=True)
        embed.add_field(
            name="💻 Sistema",
            value=f"{platform.system()} {platform.release()}",
            inline=False,
        )
        embed.add_field(
            name="🧾 Canal de logs",
            value=log_channel.mention if isinstance(log_channel, discord.TextChannel) else str(log_channel_id),
            inline=False,
        )
        embed.add_field(
            name="🔐 DISCORD_TOKEN",
            value="✅ Configurado" if bool(os.getenv("DISCORD_TOKEN")) else "❌ No configurado",
            inline=True,
        )
        embed.add_field(
            name="🔑 LICENSE_KEY",
            value="✅ Configurado" if bool(os.getenv("LICENSE_KEY")) else "ℹ️ No configurado",
            inline=True,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        try:
            e = interaction.client.build_log_embed(
                "Diagnóstico/Tools",
                "Diagnóstico ejecutado",
                user=interaction.user,
                guild=interaction.guild,
                extra={
                    "Latencia": f"{latency_ms} ms",
                    "Opus": "ok" if opus_ok else "no",
                    "ffmpeg": ffmpeg_path or "no",
                },
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

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

    @app_commands.command(name="novedades", description="Actualizaciones de Discord (Marzo 2026)")
    async def novedades(self, interaction: discord.Interaction):
        """Muestra las novedades de Discord de Marzo 2026 y cómo PoseidonUI las aprovecha."""
        embed = discord.Embed(
            title="🔱 PoseidonUI • Novedades Marzo 2026",
            description="Estoy al día con las últimas actualizaciones de la API de Discord.",
            color=Theme.get_color(interaction.guild.id, "info"),
        )

        # 1. DAVE Protocol (Voice E2EE)
        embed.add_field(
            name="🔒 Protocolo DAVE",
            value=(
                "Obligatorio desde el 1 de Marzo para llamadas de voz. "
                "PoseidonUI ha sido actualizado a `discord.py v2.7.0` "
                "para garantizar que la música y la voz sigan funcionando."
            ),
            inline=False,
        )

        # 2. Permissions Split (Pin Messages)
        embed.add_field(
            name="📌 Permisos Granulares",
            value=(
                "El permiso `MANAGE_MESSAGES` ya no permite fijar mensajes. "
                "Ahora usamos `PIN_MESSAGES` de forma independiente para "
                "garantizar que los oráculos y ofertas se fijen correctamente."
            ),
            inline=False,
        )

        # 3. New Markdown @time
        now = int(time.time())
        embed.add_field(
            name="⏰ Nuevo Markdown @time",
            value=(
                f"Ahora podemos usar marcas de tiempo nativas. Ejemplo: <t:{now}:R>\n"
                "Esto permite que los recordatorios y eventos sean relativos a tu zona horaria."
            ),
            inline=False,
        )

        # 4. Context Menu Limits
        embed.add_field(
            name="🖱️ Menús de Contexto",
            value=(
                "Discord aumentó el límite de 5 a 15 comandos por tipo. "
                "Esto nos permite añadir más acciones rápidas al hacer clic derecho."
            ),
            inline=False,
        )

        embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
        await interaction.response.send_message(embed=embed)

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
