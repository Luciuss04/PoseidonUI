import datetime

import discord
from discord.ext import commands

from bot.config import get_guild_setting
from bot.themes import Theme


class LogsModeracion(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.log_channel_name = "📜-logs"

    async def _get_log_channel(self, guild: discord.Guild):
        ch_id = get_guild_setting(guild.id, "moderacion_logs_channel_id", None)
        if ch_id:
            try:
                ch = guild.get_channel(int(ch_id))
                if isinstance(ch, discord.TextChannel):
                    return ch
            except Exception:
                pass
        channel = discord.utils.get(guild.text_channels, name=self.log_channel_name)
        if not channel:
            # Intentar buscar variaciones o crearlo si es necesario (opcional)
            pass
        return channel

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot:
            return
        if before.content == after.content:
            return

        channel = await self._get_log_channel(before.guild)
        if not channel:
            return

        embed = discord.Embed(
            title="✏️ Mensaje Editado",
            description=f"**Autor:** {before.author.mention} ({before.author.id})\n**Canal:** {before.channel.mention}",
            color=Theme.get_color(before.guild.id, "warning"),
            timestamp=datetime.datetime.utcnow(),
        )
        embed.add_field(
            name="Antes",
            value=before.content[:1020] or "[Contenido multimedia/vacío]",
            inline=False,
        )
        embed.add_field(
            name="Después",
            value=after.content[:1020] or "[Contenido multimedia/vacío]",
            inline=False,
        )
        embed.set_footer(text=Theme.get_footer_text(before.guild.id) + f" • ID: {before.id}")

        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot:
            return

        channel = await self._get_log_channel(message.guild)
        if not channel:
            return

        embed = discord.Embed(
            title="🗑️ Mensaje Borrado",
            description=f"**Autor:** {message.author.mention} ({message.author.id})\n**Canal:** {message.channel.mention}",
            color=Theme.get_color(message.guild.id, "error"),
            timestamp=datetime.datetime.utcnow(),
        )
        embed.add_field(
            name="Contenido",
            value=message.content[:1020] or "[Contenido multimedia/vacío]",
            inline=False,
        )
        if message.attachments:
            embed.add_field(
                name="Adjuntos", value=f"{len(message.attachments)} archivos", inline=True
            )

        embed.set_footer(text=Theme.get_footer_text(message.guild.id) + f" • ID: {message.id}")

        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        channel = await self._get_log_channel(before.guild)
        if not channel:
            return

        # Cambio de roles
        if before.roles != after.roles:
            added = [r for r in after.roles if r not in before.roles]
            removed = [r for r in before.roles if r not in after.roles]

            if added or removed:
                embed = discord.Embed(
                    title="🎭 Roles Actualizados",
                    description=f"**Usuario:** {after.mention} ({after.id})",
                    color=Theme.get_color(before.guild.id, "primary"),
                    timestamp=datetime.datetime.utcnow(),
                )
                if added:
                    embed.add_field(
                        name="Roles Añadidos",
                        value=", ".join([r.mention for r in added]),
                        inline=False,
                    )
                if removed:
                    embed.add_field(
                        name="Roles Quitados",
                        value=", ".join([r.mention for r in removed]),
                        inline=False,
                    )

                embed.set_footer(text=Theme.get_footer_text(before.guild.id))
                await channel.send(embed=embed)

        # Cambio de nick
        if before.nick != after.nick:
            embed = discord.Embed(
                title="🏷️ Apodo Cambiado",
                description=f"**Usuario:** {after.mention} ({after.id})",
                color=Theme.get_color(before.guild.id, "primary"),
                timestamp=datetime.datetime.utcnow(),
            )
            embed.add_field(name="Antes", value=before.nick or "[Original]", inline=True)
            embed.add_field(name="Ahora", value=after.nick or "[Original]", inline=True)
            embed.set_footer(text=Theme.get_footer_text(before.guild.id))
            await channel.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(LogsModeracion(bot))
