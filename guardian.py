import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import secrets

# ====== Configuración ======
WELCOME_CHANNEL = "📜-puertas-del-olimpo"
FAREWELL_CHANNEL = "🏺-el-umbral-de-hades"
ALERT_CHANNEL = "⚔️-alertas"
VERIFY_ROLE = "🧍Humanos"

# ====== Roles temporales del Juicio ======
JUICIO_ROLES = {
    "⚡ Favor divino": "Bendecido",
    "🗡️ Prueba del destino": "Probado",
    "🌫️ Silencio ritual": "Silenciado",
    "🔥 Forja del espíritu": "Forjado",
    "🌌 Visión del Oráculo": "Visionario",
    "🛡️ Bendición de Atenea": "Protegido",
    "🌪️ Viento de cambio": "Transformado",
    "🌊 Purificación": "Purificado",
}
JUICIO_DURATION = 24 * 60 * 60  # 24 horas

# ====== View con botón de verificación ======
class VerifyView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)  # persistente
        self.bot = bot

    @discord.ui.button(label="Jurar ante los dioses", style=discord.ButtonStyle.primary, emoji="🦉", custom_id="verify_button")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name=VERIFY_ROLE)
        if role:
            await interaction.user.add_roles(role, reason="Juramento ritual aceptado")
            await interaction.response.send_message(
                f"🦉 {interaction.user.mention} ha jurado ante los dioses y ahora es parte del Olimpo.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"⚠️ No existe el rol {VERIFY_ROLE}.",
                ephemeral=True
            )

class Guardian(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        # Registrar la View persistente
        self.bot.add_view(VerifyView(self.bot))

    # Bienvenida con botón
    @commands.Cog.listener()
    async def on_member_join(self, member):
        canal = discord.utils.get(member.guild.text_channels, name=WELCOME_CHANNEL)
        if canal:
            embed = discord.Embed(
                title=f"⚡👑 {member.name}, los dioses te reciben en el Olimpo",
                description=(
                    "Has ascendido desde el mundo mortal hasta el reino de los dioses.\n"
                    "Aquí celebramos el streaming, la comunidad y el buen rollo ⚡🎮\n\n"
                    "🔱 **Antes de comenzar tu travesía divina:**\n"
                    "Lee las 📜 reglas del Olimpo para evitar el castigo de Zeus.\n"
                    "Preséntate en 🫂 #chat-general para que los semidioses te conozcan.\n"
                    "Activa tus roles en 🛡 #acceso para desbloquear los salones sagrados.\n\n"
                    "🎙 Cuando el dios del stream esté en directo, lo sabrás en #directo-ahora.\n"
                    "🎁 Participa en eventos, sorteos y desafíos para ganar el favor de los dioses.\n\n"
                    "⚡👑 ¡Que los rayos te acompañen y que tu estancia sea legendaria!\n\n"
                    "🦉 Pulsa el botón para jurar ante los dioses y recibir tu rol de acceso."
                ),
                color=discord.Color.gold()
            )
            embed.set_footer(text="Los dioses observan tu llegada...")
            await canal.send(embed=embed, view=VerifyView(self.bot))

    # Despedida
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        canal = discord.utils.get(member.guild.text_channels, name=FAREWELL_CHANNEL)
        if canal:
            embed = discord.Embed(
                title="🏛️ Un viajero abandona el templo",
                description=f"{member.name} ha partido. Sus huellas quedarán grabadas en la arena del Olimpo.",
                color=discord.Color.dark_gold()
            )
            await canal.send(embed=embed)

    # Juicio Divino con rol temporal
    @app_commands.command(name="juicio", description="Invoca el Juicio de los Dioses sobre un usuario")
    async def juicio(self, interaction: discord.Interaction, usuario: discord.Member):
        titulo = secrets.choice(list(JUICIO_ROLES.keys()))
        mensaje = {
            "⚡ Favor divino": "Los dioses sonríen sobre ti. Que tus pasos sean firmes.",
            "🗡️ Prueba del destino": "Camina sin miedo: cada sombra guarda un aprendizaje.",
            "🌫️ Silencio ritual": "Hoy calla y observa. En el silencio se revelan los hilos del destino.",
            "🔥 Forja del espíritu": "Acepta el calor de la prueba: saldrás templado.",
            "🌌 Visión del Oráculo": "Una estrella te guía. No la pierdas de vista.",
            "🛡️ Bendición de Atenea": "La sabiduría te cubre como un manto sagrado.",
            "🌪️ Viento de cambio": "Prepárate: lo que viene transforma lo que fue.",
            "🌊 Purificación": "Deja que la marea arrastre lo que ya no sirve.",
        }[titulo]

        rol_nombre = JUICIO_ROLES[titulo]
        rol = discord.utils.get(interaction.guild.roles, name=rol_nombre)

        embed = discord.Embed(
            title=f"🔱 Juicio de los Dioses: {titulo}",
            description=f"{usuario.mention}\n{mensaje}",
            color=discord.Color.purple()
        )
        embed.set_footer(text=f"Invocado por {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

        if rol:
            await usuario.add_roles(rol, reason="Juicio divino otorgado")
            await interaction.followup.send(f"🕯️ {usuario.mention} ha recibido el rol **{rol_nombre}** por 24 horas.", ephemeral=True)

            async def remove_role_later():
                await asyncio.sleep(JUICIO_DURATION)
                try:
                    await usuario.remove_roles(rol, reason="Juicio divino expirado")
                    canal_alerta = discord.utils.get(interaction.guild.text_channels, name=ALERT_CHANNEL)
                    if canal_alerta:
                        await canal_alerta.send(f"⌛ El rol **{rol_nombre}** de {usuario.mention} ha expirado tras el Juicio Divino.")
                except discord.Forbidden:
                    pass

            asyncio.create_task(remove_role_later())
        else:
            await interaction.followup.send(f"⚠️ No existe el rol **{rol_nombre}** en el servidor.", ephemeral=True)

# ====== Setup ======
async def setup(bot: commands.Bot):
    await bot.add_cog(Guardian(bot))
