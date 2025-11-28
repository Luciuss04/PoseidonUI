import discord
from discord import app_commands
from discord.ext import commands
import time
import platform
import psutil

STAFF_ROLES = ["Semidios", "Discípulo de Atena"]

class Status(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = time.time()
        self.bot.message_count = 0
        self.bot.command_count = 0
        self.bot.unique_users = set()
        self.bot.raids_blocked = 0
        self.bot.spam_filtered = 0

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.author.bot:
            self.bot.message_count += 1
            self.bot.unique_users.add(message.author.id)

    @commands.Cog.listener()
    async def on_command(self, ctx):
        self.bot.command_count += 1

    @app_commands.command(name="status", description="Muestra el estado completo del bot (admins y staff)")
    async def status(self, interaction: discord.Interaction):
        miembro = interaction.user

        if not miembro.guild_permissions.administrator:
            tiene_rol_staff = any(rol.name in STAFF_ROLES for rol in miembro.roles)
            if not tiene_rol_staff:
                await interaction.response.send_message(
                    "⛔ Solo administradores o miembros con rol **Semidios** o **Discípulo de Atena** pueden usar este comando.",
                    ephemeral=True
                )
                return

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
            health_status = "🟢 Olimpo estable"
            embed_color = discord.Color.green()
            embed_title = "⚡ Olimpo en calma"
            footer_text = "Los dioses sonríen sobre el Olimpo"
        elif latency_ms < 400 and cpu_percent < 85 and memory_percent < 85:
            health_status = "🟡 Vigilancia activa"
            embed_color = discord.Color.gold()
            embed_title = "⚠️ Olimpo en guardia"
            footer_text = "Los dioses vigilan con atención"
        else:
            health_status = "🔴 Crisis detectada"
            embed_color = discord.Color.red()
            embed_title = "🔥 Olimpo en crisis"
            footer_text = "Los dioses se enfurecen y claman justicia"

        embed = discord.Embed(
            title=embed_title,
            description="Panel de diagnóstico completo de Atenea ⚡",
            color=embed_color
        )
        embed.add_field(name="🤖 Bot", value=f"{self.bot.user}", inline=False)
        embed.add_field(name="📡 Latencia", value=latency_status, inline=True)
        embed.add_field(name="🌍 Servidores", value=f"{len(self.bot.guilds)}", inline=True)
        embed.add_field(name="👥 Usuarios totales", value=f"{total_users}", inline=True)
        embed.add_field(name="📺 Canales", value=f"{total_channels}", inline=True)
        embed.add_field(name="🎭 Roles", value=f"{total_roles}", inline=True)
        embed.add_field(name="⚙️ Prefijo cmds", value=f"{prefix_commands}", inline=True)
        embed.add_field(name="🗂️ Slash cmds", value=f"{slash_commands}", inline=True)
        embed.add_field(name="⏱️ Uptime", value=f"{days}d {hours}h {minutes}m {seconds}s", inline=False)
        embed.add_field(name="🐍 Python", value=python_version, inline=True)
        embed.add_field(name="📦 discord.py", value=discord_version, inline=True)
        embed.add_field(name="💻 Sistema", value=system_info, inline=True)
        embed.add_field(name="🖥️ CPU", value=f"{cpu_percent}%", inline=True)
        embed.add_field(name="💾 Memoria", value=f"{memory_percent}%", inline=True)

        embed.add_field(name="✉️ Mensajes procesados", value=f"{self.bot.message_count}", inline=True)
        embed.add_field(name="🧑‍💻 Comandos ejecutados", value=f"{self.bot.command_count}", inline=True)
        embed.add_field(name="👤 Usuarios únicos", value=f"{len(self.bot.unique_users)}", inline=True)

        embed.add_field(name="🛡️ Raids bloqueados", value=f"{self.bot.raids_blocked}", inline=True)
        embed.add_field(name="🚫 Spam filtrado", value=f"{self.bot.spam_filtered}", inline=True)

        embed.add_field(name="🌌 Salud global", value=health_status, inline=False)

        embed.add_field(name="⚡ Lema", value="«El Olimpo vigila y protege»", inline=False)

        embed.set_footer(text=f"{footer_text} • Hora UTC: {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())}")

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Status(bot))

