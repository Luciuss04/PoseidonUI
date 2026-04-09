import os
import time

import discord
from discord.ext import commands

from bot.config import get_guild_setting
from bot.themes import Theme


class Streaming(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_alerts = {}  # (guild_id, member_id) -> timestamp
        self._cooldown = 3600  # 1 hora de cooldown por streamer para evitar spam

    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        if after.bot:
            return

        # Obtener configuración del servidor
        guild_id = after.guild.id
        streaming_config = get_guild_setting(guild_id, "streaming_config", {})

        # Si no hay configuración o no está habilitado, ignorar
        if not streaming_config or not streaming_config.get("enabled", False):
            return

        # Lista de IDs de usuarios a monitorear
        target_ids = streaming_config.get("target_ids", [])
        if not target_ids:
            # Si no hay IDs específicos, tal vez queramos monitorear a todos con un rol específico
            target_role_id = streaming_config.get("target_role_id")
            if target_role_id:
                role = after.guild.get_role(int(target_role_id))
                if role not in after.roles:
                    return
            else:
                # Si no hay IDs ni Rol, solo monitoreamos al dueño configurado en .env por compatibilidad
                owner_id = int(os.getenv("STREAMING_USER_ID", "0"))
                if after.id != owner_id:
                    return
        elif after.id not in [int(tid) for tid in target_ids]:
            return

        # Verificar si empezó a transmitir
        was_streaming = (
            any(isinstance(act, discord.Streaming) for act in before.activities)
            if before.activities
            else False
        )

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
            alert_key = (guild_id, after.id)
            last_alert = self._last_alerts.get(alert_key, 0)

            if now - last_alert < self._cooldown:
                return

            self._last_alerts[alert_key] = now

            # Canal de notificaciones
            channel_id = streaming_config.get("channel_id")
            channel = None
            if channel_id:
                channel = after.guild.get_channel(int(channel_id))

            if not channel:
                # Fallback: canal de logs o primer canal disponible
                log_cid = get_guild_setting(guild_id, "log_channel_id")
                if log_cid:
                    channel = after.guild.get_channel(int(log_cid))

            if channel:
                url = stream_activity.url
                title = stream_activity.name
                platform = stream_activity.platform or "Directo"

                # Mensaje personalizable
                custom_msg = streaming_config.get(
                    "message", "¡@everyone **{user}** está en directo en {platform}! 🔴"
                )
                msg_content = custom_msg.format(
                    user=after.display_name, platform=platform, url=url, title=title
                )

                # Si el mensaje no incluye la URL, la añadimos al final
                if url not in msg_content:
                    msg_content += f"\n{url}"

                embed = discord.Embed(
                    title=f"🔴 ¡{after.display_name} está en directo!",
                    description=f"**{title}**\n\n🔗 [Ver en {platform}]({url})",
                    color=Theme.get_color(guild_id, "secondary"),
                )
                if after.avatar:
                    embed.set_thumbnail(url=after.avatar.url)

                # Imagen del stream si está disponible (algunas plataformas lo envían)
                if hasattr(stream_activity, "assets") and stream_activity.assets.get("large_image"):
                    # Esto es un poco complejo de obtener directo de discord.py para Streaming,
                    # pero a veces está en la URL de la actividad
                    pass

                embed.set_footer(text=Theme.get_footer_text(guild_id))

                try:
                    await channel.send(content=msg_content, embed=embed)
                except Exception as e:
                    print(f"Error enviando notificación de stream en {after.guild.name}: {e}")


async def setup(bot):
    await bot.add_cog(Streaming(bot))
