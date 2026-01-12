import discord
from discord import app_commands
from discord.ext import commands

from bot.config import OWNER_ID


class About(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="botinfo", description="Resumen de funciones y módulos disponibles"
    )
    async def botinfo(self, interaction: discord.Interaction):
        features = (
            "⚡ Oráculo: creación y cierre de canales de ayuda"
            "\n🛡 Guardian: verificación y roles temporales"
            "\n🌟 Niveles: XP por actividad y rangos"
            "\n🏆 LoL: invocador y ranked (requiere RIOT_API_KEY)"
            "\n🏷 Ofertas: threads diarios con ofertas de juegos"
            "\n📊 Status: panel de diagnóstico y salud"
            "\n✨ Novedades: comando /novedades para ver cambios recientes"
        )
        embed = discord.Embed(
            title="PoseidonUI", description=features, color=discord.Color.blurple()
        )
        banner_url = "https://raw.githubusercontent.com/Luciuss04/PoseidonUI/main/BotDiscord4.0/banner.png"
        embed.set_image(url=banner_url)
        embed.add_field(name="Prefijo", value="!", inline=True)
        embed.add_field(
            name="Slash",
            value="/botinfo /status /juicio /crear_roles_guardian /ofertas /novedades",
            inline=False,
        )
        embed.add_field(name="Contacto", value="Discord: Luciuss04", inline=True)
        embed.set_footer(text="Configura .env y ejecuta start.bat")
        await interaction.response.send_message(embed=embed, view=BuyView(self.bot))

    @app_commands.command(
        name="novedades", description="Muestra las últimas novedades y actualizaciones del bot"
    )
    async def novedades(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="✨ Novedades de PoseidonUI",
            description="¡El Olimpo se renueva! Aquí tienes las últimas mejoras implementadas:",
            color=discord.Color.gold()
        )
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        
        embed.add_field(
            name="💰 Economía Divina", 
            value="• **`/transfer`**: ¡Envía monedas a otros usuarios!\n• **`/slots`**: ¡Prueba tu suerte en las tragaperras divinas!",
            inline=False
        )
        embed.add_field(
            name="🛠️ Diagnóstico y Estabilidad",
            value="• **`!status`**: Comando de prefijo rápido para verificar estado.\n• **`/status`**: Arreglado y optimizado para admins/staff.\n• **Logs**: Mejoras en el sistema de reporte de errores.",
            inline=False
        )
        embed.add_field(
            name="👥 Comunidad y Diversión",
            value="• **`/userinfo` y `/serverinfo`**: Información detallada al instante.\n• **`/8ball`**: ¡Pregúntale al oráculo mágico!\n• **`/ship`**: Calculadora de amor.\n• **`/hack`**: Simulación divertida.\n• **`/dado` y `/moneda`**: Azar básico.\n• **Sugerencias**: Sistema optimizado para feedback.",
            inline=False
        )
        
        import datetime
        fecha = datetime.datetime.utcnow().strftime('%d/%m/%Y')
        embed.set_footer(text=f"Versión 4.1.0 • {fecha}")
        await interaction.response.send_message(embed=embed)


    @app_commands.command(name="activar", description="Activar licencia de PoseidonUI")
    async def activar(self, interaction: discord.Interaction, key: str):
        import pathlib
        import re
        from datetime import datetime

        if not re.fullmatch(r"POSEIDON-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}", key):
            await interaction.response.send_message(
                "❌ Formato inválido de licencia.", ephemeral=True
            )
            return
        lic_file = pathlib.Path("licenses.txt")
        ok = False
        if lic_file.exists():
            lines = lic_file.read_text(encoding="utf-8").splitlines()
            valid = {
                ln.strip()
                for ln in lines
                if ln.strip() and not ln.strip().startswith("#")
            }
            ok = key in valid
        if not ok:
            await interaction.response.send_message(
                "❌ Licencia no válida.", ephemeral=True
            )
            return
        guild_id = interaction.guild.id if interaction.guild else 0
        guild_name = interaction.guild.name if interaction.guild else "DM"
        bind_path = pathlib.Path("license_bindings.txt")
        bound_other = False
        if bind_path.exists():
            lines = [
                ln.strip()
                for ln in bind_path.read_text(encoding="utf-8").splitlines()
                if ln.strip() and not ln.strip().startswith("#")
            ]
            for ln in lines:
                try:
                    k, gid, *_ = ln.split("|")
                    if k == key and int(gid) != guild_id and int(gid) != 0:
                        bound_other = True
                        break
                except Exception:
                    pass
        if bound_other:
            await interaction.response.send_message(
                "❌ Esta licencia ya está activa en otro servidor.", ephemeral=True
            )
            try:
                owner = await self.bot.fetch_user(OWNER_ID)
                msg = (
                    "⚠️ Intento de activar licencia ya usada\n"
                    f"Usuario: {interaction.user} ({interaction.user.id})\n"
                    f"Servidor: {guild_name} ({guild_id})\n"
                    f"Licencia: {key}"
                )
                await owner.send(msg)
            except Exception:
                pass
            return

        pathlib.Path("license_active.txt").write_text(key, encoding="utf-8")
        entry = (
            f"{key}|{guild_id}|{guild_name}|{datetime.utcnow().isoformat()}|PERM|PERM"
        )
        bind_path.open("a", encoding="utf-8").write(entry + "\n")
        await interaction.response.send_message(
            "✅ Licencia activada y vinculada (permanente).", ephemeral=True
        )
        try:
            e = interaction.client.build_log_embed(
                "Info/Licencia",
                "Licencia activada",
                user=interaction.user,
                guild=interaction.guild,
                extra={"Clave": key, "Servidor": str(interaction.guild.id)},
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass
        try:
            owner = await self.bot.fetch_user(OWNER_ID)
            when = datetime.utcnow().isoformat()
            msg = (
                "🔑 Activación\n"
                f"Usuario: {interaction.user} ({interaction.user.id})\n"
                f"Servidor: {guild_name} ({guild_id})\n"
                f"Licencia: {key}\n"
                f"Fecha: {when}\n"
                "Estado: PERMANENTE"
            )
            await owner.send(msg)
            pathlib.Path("activations.log").open("a", encoding="utf-8").write(
                msg + "\n"
            )
        except Exception:
            pass


class BuyView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="Comprar licencia", style=discord.ButtonStyle.success, emoji="💳"
    )
    async def buy(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Contáctame por Discord: Luciuss04", ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(About(bot))
