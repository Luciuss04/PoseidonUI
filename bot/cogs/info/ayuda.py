import discord
from discord import app_commands
from discord.ext import commands

from bot.config import OWNER_ID


class HelpSelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        options = [
            discord.SelectOption(label="General", emoji="🏠", description="Comandos básicos"),
            discord.SelectOption(label="Economía", emoji="💰", description="Monedas, tienda, trabajo"),
            discord.SelectOption(label="Comunidad", emoji="👥", description="Niveles, encuestas, utilidades"),
            discord.SelectOption(label="Moderación", emoji="🛡️", description="Guardian, antispam, sanciones"),
            discord.SelectOption(label="Info", emoji="ℹ️", description="Información del bot y soporte"),
        ]
        super().__init__(placeholder="Selecciona una categoría...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        categoria = self.values[0]
        embed = discord.Embed(title=f"📚 Ayuda: {categoria}", color=discord.Color.gold())
        
        cmds = []
        # Filtrado manual simple por ahora, idealmente usaría cogs reales
        if categoria == "General":
            cmds = ["status", "ayuda", "ping"]
        elif categoria == "Economía":
            cmds = ["balance", "daily", "work", "transferir", "tienda", "dar"]
        elif categoria == "Comunidad":
            cmds = ["niveles", "rank", "top", "sugerencia", "anuncio", "evento", "userinfo", "serverinfo"]
        elif categoria == "Moderación":
            cmds = ["kick", "ban", "mute", "unmute", "clear", "lock", "unlock"]
        elif categoria == "Info":
            cmds = ["about", "contacto", "soporte", "terminos", "privacidad"]

        desc = ""
        for cmd_name in cmds:
            cmd = self.bot.tree.get_command(cmd_name)
            if cmd:
                desc += f"**/ {cmd.name}**: {cmd.description}\n"
        
        if not desc:
            desc = "No se encontraron comandos específicos o están en mantenimiento."
            
        embed.description = desc
        await interaction.response.edit_message(embed=embed, view=self.view)

class HelpView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=120)
        self.add_item(HelpSelect(bot))

class AyudaInfo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ayuda", description="Muestra el panel de ayuda interactivo")
    async def ayuda(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⚡ Panel de Ayuda de Atenea",
            description="Selecciona una categoría en el menú de abajo para ver los comandos disponibles.",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        embed.set_footer(text="Usa / para ver todos los comandos disponibles en Discord.")
        
        await interaction.response.send_message(embed=embed, view=HelpView(self.bot))

    @app_commands.command(name="planes", description="Planes y funcionalidades")
    async def planes(self, interaction: discord.Interaction):
        txt = (
            "Básico: status, guardian, about\n"
            "Pro: oraculo, niveles, crear_roles_guardian,\n"
            "antispam, encuestas, recordatorios, monedas\n"
            "Élite: ofertas, sorteos, integraciones web, lol\n"
            "Custom: todo lo anterior"
        )
        await interaction.response.send_message(txt)
        try:
            e = interaction.client.build_log_embed(
                "Info/Ayuda",
                "Planes mostrados",
                user=interaction.user,
                guild=interaction.guild,
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @app_commands.command(name="contacto", description="Contacto con el propietario")
    async def contacto(self, interaction: discord.Interaction):
        try:
            u = await self.bot.fetch_user(int(OWNER_ID))
            await interaction.response.send_message(f"📨 Contacto: {u.mention}")
        except Exception:
            await interaction.response.send_message("📨 Contacto disponible por DM.")
        try:
            e = interaction.client.build_log_embed(
                "Info/Ayuda",
                "Contacto consultado",
                user=interaction.user,
                guild=interaction.guild,
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @app_commands.command(name="soporte", description="Canal de soporte")
    async def soporte(self, interaction: discord.Interaction):
        await interaction.response.send_message("🔧 Abre un ticket con /oraculo o DM.")
        try:
            e = interaction.client.build_log_embed(
                "Info/Ayuda",
                "Soporte consultado",
                user=interaction.user,
                guild=interaction.guild,
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @app_commands.command(name="terminos", description="Términos de uso")
    async def terminos(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Términos: uso responsable, no abuso, licencias activas."
        )
        try:
            e = interaction.client.build_log_embed(
                "Info/Ayuda",
                "Términos consultados",
                user=interaction.user,
                guild=interaction.guild,
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @app_commands.command(name="privacidad", description="Privacidad")
    async def privacidad(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Privacidad: no se almacenan datos personales sensibles."
        )
        try:
            e = interaction.client.build_log_embed(
                "Info/Ayuda",
                "Privacidad consultada",
                user=interaction.user,
                guild=interaction.guild,
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @app_commands.command(name="precio", description="Precios")
    async def precio(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Básico 19€, Pro 39€, Élite 69€, Custom 99€+"
        )
        try:
            e = interaction.client.build_log_embed(
                "Info/Ayuda",
                "Precios consultados",
                user=interaction.user,
                guild=interaction.guild,
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass


async def setup(bot):
    await bot.add_cog(AyudaInfo(bot))
