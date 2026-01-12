import collections
import time

import discord
from discord.ext import commands

WINDOW_SECONDS = 10
MAX_MSGS = 7
ALERT_CHANNEL = "⚔️-alertas"


class AntiSpam(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.hist: dict[int, collections.deque] = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        now = time.time()
        dq = self.hist.setdefault(message.author.id, collections.deque())
        dq.append(now)
        while dq and now - dq[0] > WINDOW_SECONDS:
            dq.popleft()
        if len(dq) > MAX_MSGS:
            try:
                await message.delete()
            except Exception:
                pass
            try:
                await message.author.send(
                    "⚠️ Estás enviando mensajes demasiado rápido. Reduce el ritmo."
                )
            except Exception:
                pass
            canal = discord.utils.get(message.guild.text_channels, name=ALERT_CHANNEL)
            if canal:
                try:
                    msg = (
                        f"⚠️ Posible spam detectado: {message.author.mention} "
                        f"en {message.channel.mention}"
                    )
                    await canal.send(msg)
                except Exception:
                    pass


async def setup(bot):
    await bot.add_cog(AntiSpam(bot))
