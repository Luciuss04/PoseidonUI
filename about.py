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

    @app_commands.command(name="activar", description="Activar licencia de PoseidonUI")
    async def activar(self, interaction: discord.Interaction, key: str):
        import re
        import pathlib
        from datetime import datetime
        if not re.fullmatch(r"POSEIDON-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}", key):
            await interaction.response.send_message("❌ Formato inválido de licencia.", ephemeral=True)
            return
        lic_file = pathlib.Path("licenses.txt")
        ok = False
        if lic_file.exists():
            lines = lic_file.read_text(encoding="utf-8").splitlines()
            valid = {ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")}
            ok = key in valid
        if not ok:
            await interaction.response.send_message("❌ Licencia no válida.", ephemeral=True)
            return
        guild_id = interaction.guild.id if interaction.guild else 0
        guild_name = interaction.guild.name if interaction.guild else "DM"
        bind_path = pathlib.Path("license_bindings.txt")
        bound_other = False
        if bind_path.exists():
            lines = [ln.strip() for ln in bind_path.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.strip().startswith("#")]
            for ln in lines:
                try:
                    k, gid, *_ = ln.split("|")
                    if k == key and int(gid) != guild_id and int(gid) != 0:
                        bound_other = True
                        break
                except Exception:
                    pass
        if bound_other:
            await interaction.response.send_message("❌ Esta licencia ya está activa en otro servidor.", ephemeral=True)
            try:
                owner = await self.bot.fetch_user(OWNER_ID)
                await owner.send(f"⚠️ Intento de activar licencia ya usada\nUsuario: {interaction.user} ({interaction.user.id})\nServidor: {guild_name} ({guild_id})\nLicencia: {key}")
            except Exception:
                pass
            return

        pathlib.Path("license_active.txt").write_text(key, encoding="utf-8")
        entry = f"{key}|{guild_id}|{guild_name}|{datetime.utcnow().isoformat()}|PERM|PERM"
        bind_path.open("a", encoding="utf-8").write(entry + "\n")
        await interaction.response.send_message("✅ Licencia activada y vinculada (permanente).", ephemeral=True)
        try:
            owner = await self.bot.fetch_user(OWNER_ID)
            when = datetime.utcnow().isoformat()
            msg = (
                f"🔑 Activación\nUsuario: {interaction.user} ({interaction.user.id})\n"
                f"Servidor: {guild_name} ({guild_id})\nLicencia: {key}\nFecha: {when}\nEstado: PERMANENTE"
            )
            await owner.send(msg)
            pathlib.Path("activations.log").open("a", encoding="utf-8").write(msg + "\n")
        except Exception:
            pass

    @app_commands.command(name="estado_licencia", description="Ver estado y expiración de tu licencia")
    async def estado_licencia(self, interaction: discord.Interaction):
        import pathlib
        lic_active = pathlib.Path("license_active.txt")
        if not lic_active.exists():
            await interaction.response.send_message("ℹ️ No hay licencia activada. Usa /activar o compra con /botinfo.", ephemeral=True)
            return
        key = lic_active.read_text(encoding="utf-8").strip()
        await interaction.response.send_message(f"🔎 Licencia: {key}\nEstado: permanente", ephemeral=True)

    @app_commands.command(name="renovar", description="Renovar licencia añadiendo días de vigencia")
    async def renovar(self, interaction: discord.Interaction, dias: int):
        await interaction.response.send_message("ℹ️ Las licencias son permanentes; no requieren renovación.", ephemeral=True)

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
