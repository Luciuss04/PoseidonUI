import os
import time
import discord
from discord.ext import commands
from bot.themes import Theme


class Streaming(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_alert = 0
        self._cooldown = 300  # 5 minutes cooldown

    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        # Determine target user ID
        target_id = int(os.getenv("STREAMING_USER_ID", "0"))
        
        if after.id != target_id:
            return

        # Check if started streaming
        was_streaming = False
        if before.activities:
            for act in before.activities:
                if isinstance(act, discord.Streaming):
                    was_streaming = True
                    break
        
        is_streaming = False
        stream_activity = None
        if after.activities:
            for act in after.activities:
                if isinstance(act, discord.Streaming):
                    is_streaming = True
                    stream_activity = act
                    break
        
        if not was_streaming and is_streaming and stream_activity:
            now = time.time()
            if now - self._last_alert < self._cooldown:
                return
            
            self._last_alert = now
            
            # Find channel
            channel_id = os.getenv("STREAMING_CHANNEL_ID")
            channel = None
            if channel_id:
                try:
                    channel = self.bot.get_channel(int(channel_id))
                except:
                    pass
            
            if not channel:
                # Fallback to searching by name
                for ch_name in ["📣-voz-de-zeus", "directos", "anuncios", "general", "chat-general"]:
                    channel = discord.utils.get(after.guild.text_channels, name=ch_name)
                    if channel:
                        break
            
            if channel:
                url = stream_activity.url
                title = stream_activity.name
                # Platform detection
                platform_name = stream_activity.platform or "Directo"
                
                embed = discord.Embed(
                    title=f"🔴 ¡{after.display_name} está en directo!",
                    description=f"**{title}**\n\n🔗 [Ver en {platform_name}]({url})",
                    color=Theme.get_color(after.guild.id, 'secondary')
                )
                if after.avatar:
                    embed.set_thumbnail(url=after.avatar.url)
                embed.set_footer(text=Theme.get_footer_text(after.guild.id))
                
                msg_content = f"¡Corred insensatos! 🏃‍♂️💨 {url}"
                role_id = os.getenv("STREAMING_PING_ROLE_ID", "1425818449732436059")
                if role_id:
                    msg_content = f"<@&{role_id}> {msg_content}"
                
                try:
                    await channel.send(content=msg_content, embed=embed)
                except Exception:
                    pass

async def setup(bot):
    await bot.add_cog(Streaming(bot))
