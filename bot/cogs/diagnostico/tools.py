import os
import platform
import shutil
import time

import discord
from discord import app_commands
from discord.ext import commands

from bot.auth import update_auth
from bot.config import LOG_CHANNEL_ID, get_guild_setting, set_guild_setting
from bot.themes import Theme


class ToolsDiagnostico(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start = time.time()

    config_group = app_commands.Group(name="config", description="Configuración por servidor")

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
                value=(
                    ach.mention if isinstance(ach, discord.TextChannel) else str(alert_channel_id)
                ),
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
    async def config_logcanal(self, interaction: discord.Interaction, canal: discord.TextChannel):
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
    async def config_alertas(self, interaction: discord.Interaction, canal: discord.TextChannel):
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

    @config_group.command(name="salud", description="Configura umbrales de salud (alertas)")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def config_salud(
        self,
        interaction: discord.Interaction,
        latencia_warn: int | None = None,
        latencia_crit: int | None = None,
        cpu_warn: int | None = None,
        cpu_crit: int | None = None,
        mem_warn: int | None = None,
        mem_crit: int | None = None,
        errores_warn: int | None = None,
        errores_crit: int | None = None,
    ):
        g = interaction.guild
        if not g:
            await interaction.response.send_message("⚠️ Solo en servidores.", ephemeral=True)
            return

        current = get_guild_setting(g.id, "health_thresholds", {})
        if not isinstance(current, dict):
            current = {}

        updates = {}
        if latencia_warn is not None:
            updates["latency_warn_ms"] = int(latencia_warn)
        if latencia_crit is not None:
            updates["latency_crit_ms"] = int(latencia_crit)
        if cpu_warn is not None:
            updates["cpu_warn_percent"] = int(cpu_warn)
        if cpu_crit is not None:
            updates["cpu_crit_percent"] = int(cpu_crit)
        if mem_warn is not None:
            updates["mem_warn_percent"] = int(mem_warn)
        if mem_crit is not None:
            updates["mem_crit_percent"] = int(mem_crit)
        if errores_warn is not None:
            updates["errors_warn_5m"] = int(errores_warn)
        if errores_crit is not None:
            updates["errors_crit_5m"] = int(errores_crit)

        current.update(updates)
        set_guild_setting(g.id, "health_thresholds", current)

        await interaction.response.send_message(
            "✅ Umbrales de salud actualizados.", ephemeral=True
        )
        try:
            e = interaction.client.build_log_embed(
                "Config",
                "Umbrales de salud actualizados",
                user=interaction.user,
                guild=interaction.guild,
                extra={k: str(v) for k, v in updates.items()} if updates else None,
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
        embed.add_field(name="🐍 Python", value=platform.python_version(), inline=True)
        embed.add_field(name="📦 discord.py", value=discord.__version__, inline=True)
        embed.add_field(
            name="💻 Sistema",
            value=f"{platform.system()} {platform.release()}",
            inline=False,
        )
        embed.add_field(
            name="🧾 Canal de logs",
            value=(
                log_channel.mention
                if isinstance(log_channel, discord.TextChannel)
                else str(log_channel_id)
            ),
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

    @config_group.command(
        name="dashboard", description="Cambia las credenciales del panel web (Admin Bot)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def config_dashboard(self, interaction: discord.Interaction, usuario: str, clave: str):
        # Solo el dueño del bot debería poder cambiar esto por seguridad
        if not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message(
                "⛔ Solo el dueño del bot puede cambiar las credenciales globales.", ephemeral=True
            )
            return

        if update_auth(usuario, clave):
            await interaction.response.send_message(
                f"✅ Credenciales actualizadas.\n**Usuario:** `{usuario}`\n**Clave:** `{clave}`",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "❌ Error al actualizar credenciales.", ephemeral=True
            )

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
            await interaction.response.send_message("⚠️ Solo en servidores.", ephemeral=True)
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
            await interaction.response.send_message("⚠️ Solo en servidores.", ephemeral=True)
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
            await interaction.response.send_message("⚠️ Solo en servidores.", ephemeral=True)
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
        await interaction.response.send_message(f"🧭 {len(self.bot.tree.get_commands())} comandos")
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

    @app_commands.command(
        name="diagnostico_permisos",
        description="Comprueba permisos críticos del bot (pins, escritura, lectura) por canal",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def diagnostico_permisos(self, interaction: discord.Interaction):
        g = interaction.guild
        if not g:
            await interaction.response.send_message("⚠️ Solo en servidores.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        bot_member = g.get_member(self.bot.user.id) if self.bot.user else None
        if not bot_member:
            await interaction.followup.send(
                "❌ No pude obtener el miembro del bot.", ephemeral=True
            )
            return

        def fmt_channel_result(
            ch: discord.abc.GuildChannel, for_pin: bool = False
        ) -> tuple[str, str]:
            p = ch.permissions_for(bot_member)
            missing = []
            if not p.view_channel:
                missing.append("VIEW_CHANNEL")
            if isinstance(ch, discord.TextChannel):
                if not p.read_message_history:
                    missing.append("READ_MESSAGE_HISTORY")
                if not p.send_messages:
                    missing.append("SEND_MESSAGES")
            if for_pin and isinstance(ch, discord.TextChannel):
                if not p.pin_messages:
                    missing.append("PIN_MESSAGES")
            if missing:
                return "🔴", ", ".join(missing)
            return "🟢", "OK"

        def safe_get_channel(channel_id) -> discord.TextChannel | None:
            if not channel_id:
                return None
            try:
                ch = g.get_channel(int(channel_id))
                return ch if isinstance(ch, discord.TextChannel) else None
            except Exception:
                return None

        log_channel = safe_get_channel(get_guild_setting(g.id, "log_channel_id", None))
        alert_channel = safe_get_channel(get_guild_setting(g.id, "alert_channel_id", None))
        confesiones_channel = safe_get_channel(
            get_guild_setting(g.id, "confesiones_channel_id", None)
        )
        modlogs_channel = safe_get_channel(
            get_guild_setting(g.id, "moderacion_logs_channel_id", None)
        )

        embed = discord.Embed(
            title="🔐 Diagnóstico de permisos del bot",
            description="Revisa permisos por canal. Para fijar mensajes ahora es necesario PIN_MESSAGES.",
            color=Theme.get_color(g.id, "primary"),
        )

        embed.add_field(
            name="Intents",
            value=f"MESSAGE_CONTENT: {'✅' if self.bot.intents.message_content else '❌'}",
            inline=False,
        )

        checks: list[tuple[str, discord.TextChannel | None, bool]] = [
            ("Canal logs", log_channel, True),
            ("Canal alertas", alert_channel, False),
            ("Canal confesiones", confesiones_channel, False),
            ("Canal logs moderación", modlogs_channel, True),
        ]

        current_ch = (
            interaction.channel if isinstance(interaction.channel, discord.TextChannel) else None
        )
        checks.append(("Canal actual", current_ch, True))

        for label, ch, needs_pin in checks:
            if not ch:
                embed.add_field(name=label, value="⚪ No configurado / no aplica", inline=False)
                continue
            icon, status = fmt_channel_result(ch, for_pin=needs_pin)
            embed.add_field(name=label, value=f"{icon} {ch.mention} — {status}", inline=False)

        oraculo_cat = discord.utils.get(g.categories, name="📂 Oráculos")
        if oraculo_cat:
            samples = [c for c in oraculo_cat.text_channels][:10]
            if samples:
                missing_any = 0
                for ch in samples:
                    icon, _ = fmt_channel_result(ch, for_pin=True)
                    if icon == "🔴":
                        missing_any += 1
                if missing_any:
                    embed.add_field(
                        name="📂 Oráculos (muestra 10)",
                        value=f"🔴 {missing_any}/10 canales con permisos incompletos (pins/lectura/escritura).",
                        inline=False,
                    )
                else:
                    embed.add_field(
                        name="📂 Oráculos (muestra 10)",
                        value="🟢 OK (pins/lectura/escritura).",
                        inline=False,
                    )

        embed.set_footer(text=Theme.get_footer_text(g.id))
        await interaction.followup.send(embed=embed, ephemeral=True)
        try:
            e = interaction.client.build_log_embed(
                "Diagnóstico/Permisos",
                "Diagnóstico de permisos del bot ejecutado",
                user=interaction.user,
                guild=interaction.guild,
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass


async def setup(bot):
    await bot.add_cog(ToolsDiagnostico(bot))
