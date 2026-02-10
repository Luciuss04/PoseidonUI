import asyncio

import discord
from discord import app_commands
from discord.ext import commands
from bot.themes import Theme


class Recordatorios(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="recordatorio",
        description="Programa un recordatorio en minutos y el texto",
    )
    async def recordatorio(
        self, interaction: discord.Interaction, minutos: int, texto: str
    ):
        if minutos < 1 or minutos > 10080:
            await interaction.response.send_message(
                "⚠️ Minutos inválidos (1-10080).", ephemeral=True
            )
            return
        await interaction.response.send_message(
            f"⏰ Recordatorio programado en {minutos} min.", ephemeral=True
        )
        await asyncio.sleep(minutos * 60)
        try:
            embed = discord.Embed(
                title="⏰ Recordatorio",
                description=texto,
                color=Theme.get_color(interaction.guild.id, 'primary')
            )
            embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
            await interaction.user.send(embed=embed)
        except Exception:
            pass


async def setup(bot):
    await bot.add_cog(Recordatorios(bot))
