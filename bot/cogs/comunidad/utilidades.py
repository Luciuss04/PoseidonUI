import discord
from discord import app_commands
from discord.ext import commands

from bot.themes import Theme


class UtilidadesComunidad(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.tags: dict[str, str] = {}

    # Grupo de comandos de utilidad para ahorrar espacio global
    util_group = app_commands.Group(name="utilidad", description="Herramientas de utilidad varias")

    @util_group.command(name="sugerencia", description="Envía una sugerencia al equipo")
    async def sugerencia(self, interaction: discord.Interaction, texto: str):
        channel = discord.utils.get(interaction.guild.text_channels, name="💡-sugerencias")
        if not channel:
            # Fallback si no existe el canal
            channel = interaction.channel

        embed = discord.Embed(
            title="💡 Nueva Sugerencia",
            description=texto,
            color=Theme.get_color(interaction.guild.id, "primary"),
        )
        embed.set_author(
            name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url
        )
        embed.set_footer(
            text=f"ID: {interaction.user.id} | {Theme.get_footer_text(interaction.guild.id)}"
        )

        if channel != interaction.channel:
            msg = await channel.send(embed=embed)
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")
            await interaction.response.send_message(
                f"✅ Sugerencia enviada a {channel.mention}", ephemeral=True
            )
        else:
            msg = await interaction.response.send_message(embed=embed)
            # Recuperar mensaje para reaccionar si es respuesta directa es más complejo con slash commands
            # Asi que simplificamos
            message = await interaction.original_response()
            await message.add_reaction("✅")
            await message.add_reaction("❌")

    @util_group.command(name="avatar", description="Muestra el avatar de un usuario")
    async def avatar(self, interaction: discord.Interaction, usuario: discord.User = None):
        usuario = usuario or interaction.user
        embed = discord.Embed(title=f"Avatar de {usuario.display_name}", color=usuario.color)
        embed.set_image(url=usuario.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @util_group.command(name="anuncio", description="Publica un anuncio en el canal")
    async def anuncio(self, interaction: discord.Interaction, titulo: str, contenido: str):
        embed = discord.Embed(
            title=f"📣 {titulo}",
            description=contenido,
            color=Theme.get_color(interaction.guild.id, "primary"),
        )
        embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
        await interaction.response.send_message(embed=embed)

    @util_group.command(name="evento", description="Crea un evento")
    async def evento(
        self,
        interaction: discord.Interaction,
        titulo: str,
        fecha: str,
        hora: str,
        detalle: str = "",
    ):
        desc = f"Fecha: {fecha}\nHora: {hora}"
        if detalle:
            desc += f"\n{detalle}"
        embed = discord.Embed(
            title=f"📅 Evento: {titulo}",
            description=desc,
            color=Theme.get_color(interaction.guild.id, "primary"),
        )
        embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
        await interaction.response.send_message(embed=embed)

    @util_group.command(name="tag", description="Muestra un tag guardado")
    async def tag(self, interaction: discord.Interaction, nombre: str):
        val = self.tags.get(nombre.lower())
        if not val:
            await interaction.response.send_message("⚠️ No existe ese tag.", ephemeral=True)
            return
        await interaction.response.send_message(val)

    @util_group.command(name="tag_set", description="Define o actualiza un tag")
    async def tag_set(self, interaction: discord.Interaction, nombre: str, contenido: str):
        self.tags[nombre.lower()] = contenido
        await interaction.response.send_message("✅ Tag guardado.", ephemeral=True)

    @util_group.command(name="canal_temp", description="Crea un canal temporal")
    async def canal_temp(self, interaction: discord.Interaction, nombre: str):
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("⚠️ Solo en servidores.", ephemeral=True)
            return
        canal = await guild.create_text_channel(name=nombre)
        await interaction.response.send_message(f"🧪 Canal creado: {canal.mention}")
        try:
            e = interaction.client.build_log_embed(
                "Utilidades",
                f"Canal temporal creado: {canal.mention}",
                user=interaction.user,
                guild=guild,
            )
            await interaction.client.log(embed=e, guild=guild)
        except Exception:
            pass

    @util_group.command(name="userinfo", description="Información detallada de un usuario")
    async def userinfo(self, interaction: discord.Interaction, usuario: discord.Member = None):
        usuario = usuario or interaction.user
        roles = [r.mention for r in usuario.roles if r.name != "@everyone"]

        embed = discord.Embed(
            title=f"👤 Información de {usuario.display_name}", color=usuario.color
        )
        embed.set_thumbnail(url=usuario.avatar.url if usuario.avatar else None)
        embed.add_field(name="🆔 ID", value=usuario.id, inline=True)
        embed.add_field(
            name="📅 Creación", value=usuario.created_at.strftime("%d/%m/%Y"), inline=True
        )
        embed.add_field(
            name="📥 Entrada",
            value=usuario.joined_at.strftime("%d/%m/%Y") if usuario.joined_at else "?",
            inline=True,
        )
        embed.add_field(
            name=f"🎭 Roles ({len(roles)})",
            value=", ".join(roles) if roles else "Sin roles",
            inline=False,
        )

        await interaction.response.send_message(embed=embed)

    @util_group.command(name="serverinfo", description="Información del servidor")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("Solo en servidores.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"🏰 {guild.name}", color=Theme.get_color(interaction.guild.id, "primary")
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(name="🆔 ID", value=guild.id, inline=True)
        embed.add_field(name="👑 Dueño", value=guild.owner.mention, inline=True)
        embed.add_field(name="👥 Miembros", value=guild.member_count, inline=True)
        embed.add_field(
            name="📅 Creación", value=guild.created_at.strftime("%d/%m/%Y"), inline=True
        )
        embed.add_field(
            name="💬 Canales",
            value=f"Texto: {len(guild.text_channels)} | Voz: {len(guild.voice_channels)}",
            inline=False,
        )
        embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))

        await interaction.response.send_message(embed=embed)

    @util_group.command(name="8ball", description="Pregúntale al oráculo mágico")
    async def eightball(self, interaction: discord.Interaction, pregunta: str):
        import random

        respuestas = [
            "Sí, definitivamente.",
            "Es cierto.",
            "Sin duda.",
            "Sí.",
            "Puede ser.",
            "Pregunta de nuevo más tarde.",
            "Mejor no decirte ahora.",
            "No cuentes con ello.",
            "Mi respuesta es no.",
            "Mis fuentes dicen que no.",
            "Muy dudoso.",
        ]
        respuesta = random.choice(respuestas)
        color = (
            Theme.get_color(interaction.guild.id, "success")
            if "Sí" in respuesta or "cierto" in respuesta
            else (
                Theme.get_color(interaction.guild.id, "error")
                if "no" in respuesta or "dudoso" in respuesta
                else Theme.get_color(interaction.guild.id, "warning")
            )
        )
        embed = discord.Embed(title="🎱 Oráculo Mágico", color=color)
        embed.add_field(name="❓ Pregunta", value=pregunta, inline=False)
        embed.add_field(name="🔮 Respuesta", value=respuesta, inline=False)
        embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(UtilidadesComunidad(bot))
