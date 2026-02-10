import collections
import re
import time

import discord
from discord.ext import commands

WINDOW_SECONDS = 10
MAX_MSGS = 7
MAX_MENTIONS = 5
ALERT_CHANNEL = "⚔️-alertas"
INVITE_REGEX = re.compile(r"(discord\.gg\/|discord\.com\/invite\/)")


from bot.themes import Theme

class AntiSpam(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.hist: dict[int, collections.deque] = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # Ignorar si tiene permisos de gestionar mensajes
        if message.author.guild_permissions.manage_messages:
            return

        # 1. Check Invites
        if INVITE_REGEX.search(message.content):
            await self._handle_spam(message, "Enlace de invitación no permitido")
            return

        # 2. Check Mentions
        if len(message.mentions) > MAX_MENTIONS:
            await self._handle_spam(message, f"Demasiadas menciones ({len(message.mentions)})")
            return

        # 3. Check Rate Limit
        now = time.time()
        dq = self.hist.setdefault(message.author.id, collections.deque())
        dq.append(now)
        while dq and now - dq[0] > WINDOW_SECONDS:
            dq.popleft()
        if len(dq) > MAX_MSGS:
            await self._handle_spam(message, "Mensajes demasiado rápidos")

    async def _handle_spam(self, message: discord.Message, reason: str):
        try:
            await message.delete()
        except Exception:
            pass
        
        try:
            await message.author.send(f"⚠️ **Anti-Spam**: {reason}.")
        except Exception:
            pass

        canal = discord.utils.get(message.guild.text_channels, name=ALERT_CHANNEL)
        if canal:
            try:
                embed = discord.Embed(
                    title="⚠️ Spam detectado",
                    description=f"**Razón:** {reason}",
                    color=Theme.get_color(message.guild.id, 'warning')
                )
                embed.add_field(name="Usuario", value=message.author.mention, inline=True)
                embed.add_field(name="Canal", value=message.channel.mention, inline=True)
                embed.set_footer(text=Theme.get_footer_text(message.guild.id))
                await canal.send(embed=embed)
            except Exception:
                pass


async def setup(bot):
    await bot.add_cog(AntiSpam(bot))
