import asyncio
import random

import discord
from discord import app_commands
from discord.ext import commands
from bot.themes import Theme


class SorteoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.participantes: set[int] = set()

    @discord.ui.button(
        label="Participar",
        style=discord.ButtonStyle.success,
        emoji="🎟️",
        custom_id="sorteo_participar",
    )
    async def participar(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        uid = interaction.user.id
        self.participantes.add(uid)
        await interaction.response.send_message(
            "🎟️ Te has apuntado al sorteo.", ephemeral=True
        )
        try:
            e = interaction.client.build_log_embed(
                "Economía/Sorteos",
                "Participación en sorteo",
                user=interaction.user,
                guild=interaction.guild,
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass


class Sorteos(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="sorteo", description="Inicia un sorteo con premio y duración en minutos"
    )
    async def sorteo(self, interaction: discord.Interaction, premio: str, minutos: int):
        if minutos < 1 or minutos > 1440:
            await interaction.response.send_message(
                "⚠️ Duración inválida (1-1440 minutos).", ephemeral=True
            )
            return
        embed = discord.Embed(
            title="🎁 Sorteo activo",
            description=f"Premio: **{premio}**\nDuración: {minutos} min",
            color=Theme.get_color(interaction.guild.id, 'success'),
        )
        embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
        view = SorteoView()
        await interaction.response.send_message(embed=embed, view=view)
        try:
            e = interaction.client.build_log_embed(
                "Economía/Sorteos",
                f"Sorteo iniciado: {premio}",
                user=interaction.user,
                guild=interaction.guild,
                extra={"Duración": str(minutos)},
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass
        msg = await interaction.original_response()
        await asyncio.sleep(minutos * 60)
        if not view.participantes:
            await msg.edit(content="⚠️ No hubo participantes.", view=None)
            return
        ganador_id = random.choice(list(view.participantes))
        ganador = await self.bot.fetch_user(ganador_id)
        embed_fin = discord.Embed(
            title="🏆 Sorteo finalizado",
            description=f"Ganador: **{ganador.mention}**\nPremio: **{premio}**",
            color=Theme.get_color(interaction.guild.id, 'primary'),
        )
        embed_fin.set_footer(text=Theme.get_footer_text(interaction.guild.id))
        await msg.edit(embed=embed_fin, view=None)
        try:
            await ganador.send(f"🏆 ¡Has ganado el sorteo! Premio: {premio}")
        except Exception:
            pass
        try:
            e = self.bot.build_log_embed(
                "Economía/Sorteos",
                f"Sorteo finalizado: {premio}",
                guild=interaction.guild,
                extra={"Ganador": f"{ganador} ({ganador.id})"},
                color=Theme.get_color(interaction.guild.id, 'primary'),
            )
            await self.bot.log(embed=e, guild=interaction.guild)
        except Exception:
            pass


async def setup(bot):
    await bot.add_cog(Sorteos(bot))
