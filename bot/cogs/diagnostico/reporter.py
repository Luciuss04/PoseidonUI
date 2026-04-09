import asyncio
import os

import aiohttp
import discord
from discord.ext import commands

from bot.config import BOT_VERSION
from bot.themes import Theme


class Reporter(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.webhook_url = os.getenv("STATUS_WEBHOOK_URL")
        # Ya no iniciamos el bucle, solo una tarea única
        asyncio.create_task(self.initial_report())

    async def initial_report(self):
        """Envía el reporte inicial una sola vez al encenderse el bot."""
        await self.bot.wait_until_ready()
        # Espera un poco para asegurar que todo cargó bien
        await asyncio.sleep(10)
        await self.send_heartbeat()

    async def send_heartbeat(self):
        if not self.webhook_url:
            return

        try:
            # Gather Data
            guild = self.bot.guilds[0] if self.bot.guilds else None
            if not guild:
                return

            plan = getattr(self.bot, "active_plan", "Basic")
            key = getattr(self.bot, "license_key", "NO-LICENSE")

            # Payload
            embed = discord.Embed(
                title="💓 Bot Heartbeat",
                color=Theme.get_color(guild.id, "success"),
                timestamp=discord.utils.utcnow(),
            )
            embed.add_field(name="Server", value=guild.name, inline=True)
            embed.add_field(name="ID", value=str(guild.id), inline=True)
            embed.add_field(name="Plan", value=str(plan).upper(), inline=True)
            embed.add_field(name="Members", value=str(guild.member_count), inline=True)
            embed.add_field(name="Version", value=f"v{BOT_VERSION}", inline=True)
            embed.set_footer(text=f"KEY:{key}|GID:{guild.id}")

            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(self.webhook_url, session=session)
                await webhook.send(
                    username=f"Poseidon Reporter - {guild.name}",
                    avatar_url=self.bot.user.avatar.url if self.bot.user.avatar else None,
                    embed=embed,
                )

            print(f"✅ [Reporter] Heartbeat sent for {guild.name}")

        except Exception as e:
            print(f"⚠️ [Reporter] Failed to send heartbeat: {e}")


async def setup(bot: commands.Bot):
    # Only load if webhook is configured
    if os.getenv("STATUS_WEBHOOK_URL"):
        await bot.add_cog(Reporter(bot))
    else:
        print("ℹ️ [Reporter] STATUS_WEBHOOK_URL not set. Skipping reporter.")
