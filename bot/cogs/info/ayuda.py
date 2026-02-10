import discord
from discord import app_commands
from discord.ext import commands

from bot.config import LOG_CHANNEL_ID
from bot.themes import Theme


class HelpSelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        options = [
            discord.SelectOption(label="General", emoji="🛠️", description="Utilidades básicas"),
            discord.SelectOption(label="Economía", emoji="💰", description="Dinero, Tienda, Casino"),
            discord.SelectOption(label="Comunidad", emoji="👥", description="Clanes, Matrimonios, Niveles"),
            discord.SelectOption(label="Música", emoji="🎵", description="Reproducción de Música"),
            discord.SelectOption(label="Juegos", emoji="🎮", description="Mascotas, Minijuegos, RPG"),
            discord.SelectOption(label="Integraciones", emoji="🌐", description="LoL, RSS, Web"),
            discord.SelectOption(label="Moderación", emoji="🛡️", description="Seguridad y Gestión"),
            discord.SelectOption(label="Información", emoji="ℹ️", description="Acerca del bot")
        ]
        super().__init__(placeholder="Selecciona una categoría...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            categoria = self.values[0]
            category_emojis = {
                "General": "🛠️",
                "Economía": "🔱", 
                "Comunidad": "👥",
                "Música": "🎵",
                "Juegos": "🎮",
                "Integraciones": "🌐",
                "Moderación": "🛡️",
                "Información": "ℹ️"
            }
            
            emoji_titulo = category_emojis.get(categoria, "📚")
            embed = discord.Embed(
                title=f"{emoji_titulo} Ayuda: {categoria}", 
                color=Theme.get_color(interaction.guild.id, 'secondary')
            )
            
            cmds = []
            desc = ""
            
            if categoria == "General":
                cmds = ["ayuda", "status", "ping", "uptime", "servidor", "roles", "canales", "comandos", "perms", "avatar", "userinfo", "serverinfo", "anuncio"]
                desc = "Comandos de utilidad general y diagnóstico."
            elif categoria == "Economía":
                cmds = ["balance", "daily", "work", "transferir", "top", "slots", "blackjack", "ruleta", "dar", "quitar", "comprar", "inventario", "regalar", "tienda_clear", "ofertas", "sorteo"]
                desc = "Sistema completo de economía: monedas, tienda, casino y sorteos."
            elif categoria == "Comunidad":
                cmds = ["clan", "love", "niveles", "leaderboard", "encuesta", "recordatorio", "oraculo_help", "evento_add", "evento_del", "evento_list", "tag", "tag_set", "canal_temp"]
                desc = "Sistemas sociales: Clanes, Matrimonios, Niveles, Eventos y utilidades."
            elif categoria == "Música":
                cmds = ["play", "stop", "skip", "queue", "pause", "resume"]
                desc = "Sistema de música de alta calidad."
            elif categoria == "Juegos":
                cmds = ["mascota", "rpg", "ship", "dado", "moneda", "ppt", "eleccion", "buscaminas", "hack", "meme_txt", "8ball"]
                desc = "Diversión, mascotas evolutivas, RPG y minijuegos."
            elif categoria == "Moderación":
                cmds = ["setup", "stats_olimpo", "clear", "slowmode", "mute", "unmute", "lock", "unlock", "warn", "crear_roles_guardian"]
                desc = "Herramientas de moderación y configuración del sistema Guardian."
            elif categoria == "Integraciones":
                cmds = ["lol", "activar"]
                desc = "Integraciones externas y activación de licencia."
            elif categoria == "Información":
                cmds = ["planes", "contacto", "soporte", "terminos", "privacidad", "precio"]
                desc = "Información legal, soporte y planes."

            if desc:
                desc += "\n\n"

            for cmd_name in cmds:
                cmd = self.bot.tree.get_command(cmd_name)
                if cmd:
                    desc += f"**/ {cmd.name}**: {cmd.description}\n"
                else:
                    # Fallback para comandos no encontrados en el tree (posiblemente no sincronizados aun o nombres incorrectos)
                    desc += f"**/ {cmd_name}**: (Comando no sincronizado o no encontrado)\n"

            
            if not desc:
                desc = "No se encontraron comandos específicos o están en mantenimiento."
                
            embed.description = desc
            embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
            await interaction.edit_original_response(embed=embed, view=self.view)
        
        except Exception as e:
            print(f"Error en Ayuda callback: {e}")
            await interaction.followup.send(f"❌ Error al cargar la ayuda: {str(e)}", ephemeral=True)

class HelpView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=120)
        self.add_item(HelpSelect(bot))

class AyudaInfo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ayuda", description="Muestra el panel de ayuda interactivo")
    async def ayuda(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🏛️ Panel de Ayuda del Olimpo",
            description="Explora los dominios del Olimpo usando el menú desplegable.",
            color=Theme.get_color(interaction.guild.id, 'secondary')
        )
        embed.set_thumbnail(url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        embed.set_footer(text=Theme.get_footer_text(interaction.guild.id), icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        
        await interaction.response.send_message(embed=embed, view=HelpView(self.bot))

    @app_commands.command(name="planes", description="Planes y funcionalidades actualizados")
    async def planes(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="💎 Planes de Suscripción Atenea",
            description="Elige el poder que necesita tu servidor. ¡Mejora tu comunidad hoy mismo!",
            color=Theme.get_color(interaction.guild.id, 'primary')
        )

        embed.add_field(
            name="🌑 Básico (19€/mes)",
            value="• Moderación Básica (Logs, Guardian)\n• Comandos de Utilidad\n• Información del Servidor",
            inline=False
        )
        
        embed.add_field(
            name="🌘 Pro (39€/mes)",
            value="• Todo lo del Básico\n• **Niveles y XP**\n• Oráculo (IA Básica)\n• Encuestas y Recordatorios\n• Economía Básica (Monedas)",
            inline=False
        )
        
        embed.add_field(
            name="🌕 Élite (69€/mes) - ¡RECOMENDADO!",
            value="• Todo lo del Pro\n• **Mascotas Evolutivas v2.0** 🐉\n• **Sistema de Música** 🎵\n• Economía Avanzada (Bolsa, Casino, Tienda)\n• Integraciones (LoL, RSS)\n• Clanes y Matrimonios",
            inline=False
        )
        
        embed.add_field(
            name="✨ Custom (99€+/mes)",
            value="• Bot de marca blanca (Tu nombre y foto)\n• Funciones a medida\n• Soporte prioritario 24/7",
            inline=False
        )

        embed.set_footer(text=f"{Theme.get_footer_text(interaction.guild.id)} • Contacta con soporte para adquirir una licencia.")
        
        await interaction.response.send_message(embed=embed)
        try:
            e = interaction.client.build_log_embed(
                "Info/Ayuda",
                "Planes mostrados",
                user=interaction.user,
                guild=interaction.guild,
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @app_commands.command(name="contacto", description="Contacto con el soporte")
    async def contacto(self, interaction: discord.Interaction):
        await interaction.response.send_message("📨 Contacto: Soporte disponible por DM o ticket.")
        try:
            e = interaction.client.build_log_embed(
                "Info/Ayuda",
                "Contacto consultado",
                user=interaction.user,
                guild=interaction.guild,
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @app_commands.command(name="soporte", description="Canal de soporte")
    async def soporte(self, interaction: discord.Interaction):
        await interaction.response.send_message("🔧 Abre un ticket con /oraculo o DM.")
        try:
            e = interaction.client.build_log_embed(
                "Info/Ayuda",
                "Soporte consultado",
                user=interaction.user,
                guild=interaction.guild,
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @app_commands.command(name="terminos", description="Términos de uso")
    async def terminos(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Términos: uso responsable, no abuso, licencias activas."
        )
        try:
            e = interaction.client.build_log_embed(
                "Info/Ayuda",
                "Términos consultados",
                user=interaction.user,
                guild=interaction.guild,
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @app_commands.command(name="privacidad", description="Privacidad")
    async def privacidad(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Privacidad: no se almacenan datos personales sensibles."
        )
        try:
            e = interaction.client.build_log_embed(
                "Info/Ayuda",
                "Privacidad consultada",
                user=interaction.user,
                guild=interaction.guild,
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @app_commands.command(name="precio", description="Precios")
    async def precio(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Básico 19€, Pro 39€, Élite 69€, Custom 99€+"
        )
        try:
            e = interaction.client.build_log_embed(
                "Info/Ayuda",
                "Precios consultados",
                user=interaction.user,
                guild=interaction.guild,
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass


async def setup(bot):
    await bot.add_cog(AyudaInfo(bot))
