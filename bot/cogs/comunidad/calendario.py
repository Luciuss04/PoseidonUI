import discord
from discord import app_commands
from discord.ext import commands

from bot.themes import Theme


class Calendario(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.events: dict[str, tuple[str, str, str]] = {}

    @app_commands.command(name="evento_add", description="Añade evento: id, título, fecha, hora")
    async def evento_add(
        self,
        interaction: discord.Interaction,
        id: str,
        titulo: str,
        fecha: str,
        hora: str,
    ):
        self.events[id] = (titulo, fecha, hora)
        await interaction.response.send_message("✅ Evento añadido.")

    @app_commands.command(name="evento_del", description="Elimina evento por id")
    async def evento_del(self, interaction: discord.Interaction, id: str):
        if id in self.events:
            del self.events[id]
            await interaction.response.send_message("🗑️ Evento eliminado.")
        else:
            await interaction.response.send_message("⚠️ No existe.", ephemeral=True)

    @app_commands.command(name="evento_list", description="Lista eventos")
    async def evento_list(self, interaction: discord.Interaction):
        if not self.events:
            await interaction.response.send_message("📅 Sin eventos.")
            return
        lines = [f"• **{k}**: {v[0]} ({v[1]} {v[2]})" for k, v in self.events.items()]

        embed = discord.Embed(
            title="📅 Calendario de Eventos",
            description="\n".join(lines),
            color=Theme.get_color(interaction.guild.id, "primary"),
        )
        embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Calendario(bot))
