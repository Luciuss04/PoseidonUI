import discord
from discord.ext import commands
from discord import app_commands


class About(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="botinfo", description="Resumen de funciones y módulos disponibles")
    async def botinfo(self, interaction: discord.Interaction):
        features = (
            "⚡ Oráculo: creación y cierre de canales de ayuda"
            "\n🛡 Guardian: verificación y roles temporales"
            "\n🌟 Niveles: XP por actividad y rangos"
            "\n🏆 LoL: invocador y ranked (requiere RIOT_API_KEY)"
            "\n🏷 Ofertas: threads diarios con ofertas de juegos"
            "\n📊 Status: panel de diagnóstico y salud"
        )
        embed = discord.Embed(
            title="Atenea Bot",
            description=features,
            color=discord.Color.blurple()
        )
        embed.add_field(name="Prefijo", value="!", inline=True)
        embed.add_field(name="Slash", value="/botinfo /status /juicio /crear_roles_guardian /ofertas", inline=False)
        embed.set_footer(text="Configura .env y ejecuta start.bat")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(About(bot))
