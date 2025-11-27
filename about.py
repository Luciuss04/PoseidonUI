import discord
from discord.ext import commands
from discord import app_commands
from config import OWNER_ID


class About(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="botinfo", description="Resumen de funciones y módulos disponibles")
    async def botinfo(self, interaction: discord.Interaction):
        features = (
            "⚡ Oráculo: creación y cierre de canales de ayuda"
            "\n🛡 Guardian: verificación y roles temporales"
            "\n🌟 Niveles: XP por actividad y rangos"
            "\n🏆 LoL: invocador y ranked (requiere RIOT_API_KEY)"
            "\n🏷 Ofertas: threads diarios con ofertas de juegos"
            "\n📊 Status: panel de diagnóstico y salud"
        )
        embed = discord.Embed(
            title="PoseidonUI",
            description=features,
            color=discord.Color.blurple()
        )
        banner_url = "https://raw.githubusercontent.com/Luciuss04/PoseidonUI/main/BotDiscord4.0/banner.png"
        embed.set_image(url=banner_url)
        embed.add_field(name="Prefijo", value="!", inline=True)
        embed.add_field(name="Slash", value="/botinfo /status /juicio /crear_roles_guardian /ofertas", inline=False)
        embed.set_footer(text="Configura .env y ejecuta start.bat")
        await interaction.response.send_message(embed=embed, view=BuyView(self.bot))

    @app_commands.command(name="demo", description="Presentación visual del bot para mostrar a clientes")
    async def demo(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            thread = await interaction.channel.create_thread(
                name="✨ Demo de Atenea Bot",
                type=discord.ChannelType.public_thread
            )
        except Exception:
            thread = interaction.channel

        banner_url = "https://raw.githubusercontent.com/Luciuss04/PoseidonUI/main/BotDiscord4.0/banner.png"

        cards = []
        e1 = discord.Embed(title="⚡ Oráculo", description="Abre canales de ayuda con paneles y cierre guiado.", color=discord.Color.gold())
        e1.set_image(url=banner_url); cards.append(e1)

        e2 = discord.Embed(title="🛡 Guardian", description="Verificación con botón y roles rituales temporales.", color=discord.Color.dark_gold())
        e2.set_image(url=banner_url); cards.append(e2)

        e3 = discord.Embed(title="🌟 Niveles", description="XP automática por actividad con rangos temáticos.", color=discord.Color.purple())
        e3.set_image(url=banner_url); cards.append(e3)

        e4 = discord.Embed(title="🏆 LoL", description="Consulta invocadores y clasificatorias.", color=discord.Color.blue())
        e4.set_image(url=banner_url); cards.append(e4)

        e5 = discord.Embed(title="🏷 Ofertas", description="Threads diarios con 30+ ofertas destacadas.", color=discord.Color.green())
        e5.set_image(url=banner_url); cards.append(e5)

        e6 = discord.Embed(title="📊 Status", description="Diagnóstico de salud del bot y sistema.", color=discord.Color.blurple())
        e6.set_image(url=banner_url); cards.append(e6)

        for c in cards:
            await thread.send(embed=c)
        await interaction.followup.send("✨ Demo publicada", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(About(bot))


class BuyView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.selected_plan = {}

        self.add_item(PlanSelect(self))

    @discord.ui.button(label="Comprar / Solicitar", style=discord.ButtonStyle.success, emoji="🛒", custom_id="buy_button")
    async def buy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        plan = self.selected_plan.get(interaction.user.id, "No especificado")
        await interaction.response.send_message(f"✅ Solicitud enviada (Plan: {plan}). Te contactaremos pronto.", ephemeral=True)
        try:
            owner = await self.bot.fetch_user(OWNER_ID)
            await owner.send(
                f"🛒 Nueva solicitud de compra\nUsuario: {interaction.user} ({interaction.user.id})\nServidor: {interaction.guild.name if interaction.guild else 'DM'}\nPlan: {plan}"
            )
        except Exception:
            pass


class PlanSelect(discord.ui.Select):
    def __init__(self, view: BuyView):
        self.view_ref = view
        options = [
            discord.SelectOption(label="Básico", description="Botinfo, Demo, Status, Guardian", emoji="🟢"),
            discord.SelectOption(label="Pro", description="+ Oráculo, Niveles, ajuste roles", emoji="🔵"),
            discord.SelectOption(label="Élite", description="+ Ofertas y LoL", emoji="🟣"),
            discord.SelectOption(label="Personalizado", description="Branding y features a medida", emoji="🟡"),
        ]
        super().__init__(placeholder="Elige un plan", min_values=1, max_values=1, options=options, custom_id="plan_select")

    async def callback(self, interaction: discord.Interaction):
        plan = self.values[0]
        self.view_ref.selected_plan[interaction.user.id] = plan
        await interaction.response.send_message(f"🛒 Plan seleccionado: {plan}", ephemeral=True)
    async def cog_load(self):
        self.bot.add_view(BuyView(self.bot))
