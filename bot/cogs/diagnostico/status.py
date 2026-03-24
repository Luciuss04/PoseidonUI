import platform
import random
import time

import discord
import psutil
from discord import app_commands
from discord.ext import commands, tasks

from bot.config import get_guild_setting
from bot.themes import Theme

STAFF_ROLES = ["Semidios", "Discípulo de Atena"]
ALERT_CHANNEL = "⚔️-alertas"


class Status(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = time.time()
        self.bot.message_count = 0
        self.bot.command_count = 0
        self.bot.unique_users = set()
        self.bot.raids_blocked = 0
        self.bot.spam_filtered = 0
        self.presence_task.start()

    def cog_unload(self):
        self.presence_task.cancel()

    @tasks.loop(minutes=5)
    async def presence_task(self):
        activities = [
            discord.Activity(type=discord.ActivityType.watching, name="el Olimpo"),
            discord.Activity(type=discord.ActivityType.listening, name="las plegarias"),
            discord.Activity(type=discord.ActivityType.competing, name="los Juegos Olímpicos"),
            discord.Activity(type=discord.ActivityType.playing, name="con el destino"),
            discord.Activity(type=discord.ActivityType.watching, name=f"{len(self.bot.guilds)} servidores"),
        ]
        await self.bot.change_presence(activity=random.choice(activities))

    @presence_task.before_loop
    async def before_presence(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.author.bot:
            self.bot.message_count += 1
            self.bot.unique_users.add(message.author.id)

    @commands.Cog.listener()
    async def on_command(self, ctx):
        self.bot.command_count += 1

    @commands.command(name="status", help="Muestra el estado completo del bot (prefix)")
    async def status_prefix(self, ctx):
        """Versión prefijo del comando status"""
        # Reutilizamos la lógica, adaptando ctx a interaction si es necesario
        # O simplemente copiamos la lógica principal para enviar un embed.
        # Para evitar duplicación, extraemos la lógica de generación del embed.
        embed = await self._generate_status_embed(ctx.guild)
        await ctx.send(embed=embed)

    @app_commands.command(
        name="status", description="Muestra el estado completo del bot (admins y staff)"
    )
    @app_commands.guild_only()
    async def status(self, interaction: discord.Interaction):
        miembro = interaction.user

        if not miembro.guild_permissions.administrator:
            staff_role_ids = get_guild_setting(
                interaction.guild.id, "staff_role_ids", None
            )
            staff_role_names = get_guild_setting(
                interaction.guild.id, "staff_role_names", STAFF_ROLES
            )
            try:
                staff_role_ids = (
                    [int(x) for x in staff_role_ids]
                    if isinstance(staff_role_ids, list)
                    else None
                )
            except Exception:
                staff_role_ids = None
            staff_role_names = (
                staff_role_names
                if isinstance(staff_role_names, list) and staff_role_names
                else STAFF_ROLES
            )
            if staff_role_ids:
                tiene_rol_staff = any(rol.id in staff_role_ids for rol in miembro.roles)
            else:
                tiene_rol_staff = any(rol.name in staff_role_names for rol in miembro.roles)
            if not tiene_rol_staff:
                await interaction.response.send_message(
                    "⛔ Solo administradores o miembros staff pueden usar este comando.",
                    ephemeral=True,
                )
                return

        embed = await self._generate_status_embed(interaction.guild)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Log logic
        await self._log_status(interaction, embed)

    async def _generate_status_embed(self, guild):
        uptime_seconds = int(time.time() - self.start_time)
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        total_users = sum(g.member_count for g in self.bot.guilds if g.member_count)
        total_channels = sum(len(g.channels) for g in self.bot.guilds)
        total_roles = sum(len(g.roles) for g in self.bot.guilds)

        prefix_commands = len(self.bot.commands)
        slash_commands = len(self.bot.tree.get_commands())

        python_version = platform.python_version()
        discord_version = discord.__version__
        system_info = platform.system() + " " + platform.release()

        latency_ms = round(self.bot.latency * 1000)
        if latency_ms < 150:
            latency_status = f"🟢 {latency_ms} ms (Excelente)"
        elif latency_ms < 300:
            latency_status = f"🟡 {latency_ms} ms (Aceptable)"
        else:
            latency_status = f"🔴 {latency_ms} ms (Alta)"

        cpu_percent = psutil.cpu_percent(interval=None)
        memory_info = psutil.virtual_memory()
        memory_percent = memory_info.percent

        if latency_ms < 200 and cpu_percent < 70 and memory_percent < 75:
            health_status = "🕊️ Cielos despejados"
            embed_color = Theme.get_color(guild.id, 'success')
            embed_title = "🔱 PoseidonUI: Estado Óptimo"
        elif latency_ms < 400 and cpu_percent < 85 and memory_percent < 85:
            health_status = "☁️ Nubes en el horizonte"
            embed_color = Theme.get_color(guild.id, 'warning')
            embed_title = "🔱 PoseidonUI: Estado Alerta"
        else:
            health_status = "⚡ Ira de Zeus"
            embed_color = Theme.get_color(guild.id, 'error')
            embed_title = "🔱 PoseidonUI: Estado Crítico"

        embed = discord.Embed(
            title=embed_title,
            description="Panel de diagnóstico del Olimpo.",
            color=embed_color,
        )
        embed.add_field(name="🤖 Bot", value=f"{self.bot.user}", inline=False)
        embed.add_field(name="📡 Latencia", value=latency_status, inline=True)
        embed.add_field(
            name="🌍 Servidores", value=f"{len(self.bot.guilds)}", inline=True
        )
        embed.add_field(name="👥 Usuarios totales", value=f"{total_users}", inline=True)
        embed.add_field(name="📺 Canales", value=f"{total_channels}", inline=True)
        embed.add_field(name="🎭 Roles", value=f"{total_roles}", inline=True)
        embed.add_field(name="⚙️ Prefijo cmds", value=f"{prefix_commands}", inline=True)
        embed.add_field(name="🗂️ Slash cmds", value=f"{slash_commands}", inline=True)
        embed.add_field(
            name="⏱️ Uptime",
            value=f"{days}d {hours}h {minutes}m {seconds}s",
            inline=False,
        )
        embed.add_field(name="🐍 Python", value=python_version, inline=True)
        embed.add_field(name="📦 discord.py", value=discord_version, inline=True)
        embed.add_field(name="💻 Sistema", value=system_info, inline=True)
        embed.add_field(name="🖥️ CPU", value=f"{cpu_percent}%", inline=True)
        embed.add_field(name="💾 Memoria", value=f"{memory_percent}%", inline=True)

        embed.add_field(
            name="✉️ Mensajes procesados", value=f"{self.bot.message_count}", inline=True
        )
        embed.add_field(
            name="🧑‍💻 Comandos ejecutados",
            value=f"{self.bot.command_count}",
            inline=True,
        )
        embed.add_field(
            name="👤 Usuarios únicos",
            value=f"{len(self.bot.unique_users)}",
            inline=True,
        )

        embed.add_field(
            name="🛡️ Raids bloqueados", value=f"{self.bot.raids_blocked}", inline=True
        )
        embed.add_field(
            name="🚫 Spam filtrado", value=f"{self.bot.spam_filtered}", inline=True
        )

        embed.add_field(name="🌌 Salud global", value=health_status, inline=False)

        embed.set_footer(
            text=f"{Theme.get_footer_text(guild.id)} • {time.strftime('%H:%M UTC', time.gmtime())}"
        )
        return embed

    async def _log_status(self, interaction, embed):
        try:
            # Extract health status from embed fields to reuse logic
            health_status = "Desconocido"
            for field in embed.fields:
                if field.name == "🌌 Salud global":
                    health_status = field.value
                    break
            
            # Simple extraction of other metrics is hard from embed, 
            # so we might skip detailed extra fields or re-calculate them.
            # For simplicity, we just log basic info.
            
            e = interaction.client.build_log_embed(
                "Diagnóstico/Status",
                "Panel de diagnóstico mostrado",
                user=interaction.user,
                guild=interaction.guild,
                extra={
                    "Salud": health_status,
                },
                color=embed.color,
            )
            mention = None
            if "🔴" in health_status:
                try:
                    staff_role_ids = get_guild_setting(
                        interaction.guild.id, "staff_role_ids", None
                    )
                    staff_role_names = get_guild_setting(
                        interaction.guild.id, "staff_role_names", STAFF_ROLES
                    )
                    mentions = []
                    if isinstance(staff_role_ids, list) and staff_role_ids:
                        for rid in staff_role_ids:
                            try:
                                r = interaction.guild.get_role(int(rid))
                                if r:
                                    mentions.append(r.mention)
                            except Exception:
                                pass
                    if not mentions and isinstance(staff_role_names, list):
                        for rn in staff_role_names:
                            r = discord.utils.get(interaction.guild.roles, name=rn)
                            if r:
                                mentions.append(r.mention)
                    mention = " ".join(mentions) if mentions else None
                except Exception:
                    mention = None
            await interaction.client.log(
                content=mention, embed=e, guild=interaction.guild
            )
            if "🔴" in health_status:
                try:
                    alert_channel_id = get_guild_setting(
                        interaction.guild.id, "alert_channel_id", None
                    )
                    ch = None
                    try:
                        if alert_channel_id:
                            ch = interaction.guild.get_channel(int(alert_channel_id))
                    except Exception:
                        ch = None
                    if not isinstance(ch, discord.TextChannel):
                        alert_channel_name = get_guild_setting(
                            interaction.guild.id, "alert_channel_name", ALERT_CHANNEL
                        )
                        ch = discord.utils.get(
                            interaction.guild.text_channels, name=alert_channel_name
                        )
                    if isinstance(ch, discord.TextChannel):
                        await ch.send(content=mention, embed=e)
                except Exception:
                    pass
        except Exception:
            pass

    @app_commands.command(
        name="botperfil", description="Muestra plan activo y cogs cargados"
    )
    async def botperfil(self, interaction: discord.Interaction):
        miembro = interaction.user
        if not miembro.guild_permissions.administrator:
            staff_role_ids = get_guild_setting(
                interaction.guild.id, "staff_role_ids", None
            )
            staff_role_names = get_guild_setting(
                interaction.guild.id, "staff_role_names", STAFF_ROLES
            )
            try:
                staff_role_ids = (
                    [int(x) for x in staff_role_ids]
                    if isinstance(staff_role_ids, list)
                    else None
                )
            except Exception:
                staff_role_ids = None
            staff_role_names = (
                staff_role_names
                if isinstance(staff_role_names, list) and staff_role_names
                else STAFF_ROLES
            )
            if staff_role_ids:
                tiene_rol_staff = any(rol.id in staff_role_ids for rol in miembro.roles)
            else:
                tiene_rol_staff = any(rol.name in staff_role_names for rol in miembro.roles)
            if not tiene_rol_staff:
                await interaction.response.send_message(
                    "⛔ Solo administradores o miembros staff pueden usar este comando.",
                    ephemeral=True,
                )
                return
        try:
            import os
            import sys

            # Try to get variables from __main__ or 'main' module
            app_main = sys.modules.get("__main__")
            if not hasattr(app_main, "ACTIVE_PLAN"):
                app_main = sys.modules.get("main")
            
            # Safe defaults if not found
            plan = getattr(app_main, "ACTIVE_PLAN", "basic")
            trial = getattr(app_main, "IS_TRIAL", False)
            
            # No mostrar flags internas del modo dueño
            enabled_only = os.getenv("ENABLED_COGS_ONLY", "")
            disabled = os.getenv("DISABLED_COGS", "")
            mods = sorted({c.__module__ for c in self.bot.cogs.values()})
            embed = discord.Embed(
                title="📦 Perfil del Bot",
                description="Configuración y módulos activos",
                color=Theme.get_color(interaction.guild.id, 'primary'),
            )
            embed.add_field(name="🔑 Plan", value=plan, inline=True)
            embed.add_field(name="🧪 Trial", value="sí" if trial else "no", inline=True)
            # Campos internos omitidos
            embed.add_field(
                name="✅ ENABLED_COGS_ONLY",
                value=enabled_only or "(vacío)",
                inline=False,
            )
            embed.add_field(
                name="🚫 DISABLED_COGS", value=disabled or "(vacío)", inline=False
            )
            lista = "\n".join(mods) if mods else "(sin cogs)"
            embed.add_field(name="📚 Cogs cargados", value=lista, inline=False)
            embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"⚠️ Error: {e}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Status(bot))
