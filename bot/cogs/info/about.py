import discord
from discord import app_commands
from discord.ext import commands
from discord import app_commands
from bot.config import BOT_VERSION
from bot.themes import Theme, THEMES

class About(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="tema", description="Cambia el tema visual del bot (Admin)")
    @app_commands.describe(nombre="Nombre del tema a aplicar")
    async def tema(self, interaction: discord.Interaction, nombre: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("⛔ Solo administradores pueden cambiar el tema.", ephemeral=True)
            return

        # Verificar si el tema existe en ThemeManager
        all_themes = Theme.get_all_themes()
        if nombre not in all_themes:
             await interaction.response.send_message(f"❌ El tema `{nombre}` no existe.", ephemeral=True)
             return

        if Theme.set_theme(nombre, guild_id=interaction.guild.id):
            theme_data = all_themes[nombre]
            embed = discord.Embed(
                title="🎨 Tema Actualizado",
                description=f"El tema se ha cambiado a **{theme_data['name']}**.\nLos próximos mensajes usarán este estilo.",
                color=Theme.get_color(interaction.guild.id, 'success')
            )
            embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ Error al cambiar el tema.", ephemeral=True)

    @tema.autocomplete('nombre')
    async def tema_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        all_themes = Theme.get_all_themes()
        choices = []
        for key, data in all_themes.items():
            # Filtrar por búsqueda
            if current.lower() in data['name'].lower() or current.lower() in key.lower():
                choices.append(app_commands.Choice(name=data['name'], value=key))
        
        # Discord permite max 25 opciones
        return choices[:25]

    @app_commands.command(
        name="plan", description="Muestra información sobre tu plan y licencia actual"
    )
    async def plan(self, interaction: discord.Interaction):
        try:
            # Recuperar info del bot
            plan = getattr(self.bot, "active_plan", "Unknown") or "Unknown"
            key = getattr(self.bot, "license_key", "Unknown")
            is_trial = getattr(self.bot, "is_trial", False)
            
            # Formatear Plan
            plan_emojis = {
                "basic": "🥉 Básico",
                "pro": "🥈 Pro",
                "elite": "🥇 Élite",
                "custom": "👑 Custom",
                "unknown": "❓ Desconocido"
            }
            # Normalizar a string y minúsculas para búsqueda
            plan_str = str(plan).lower()
            plan_display = plan_emojis.get(plan_str, f"❓ {str(plan).capitalize()}")
            
            if is_trial:
                plan_display += " (Trial / Prueba)"

            # Enmascarar Licencia
            if key and str(key).lower() != "unknown" and len(str(key)) > 10:
                key_str = str(key)
                masked_key = f"{key_str[:9]}****-****-{key_str[-4:]}"
            else:
                masked_key = "NO-LICENSE"

            embed = discord.Embed(
                title="📋 Panel del Olimpo",
                description="Información de tu suscripción y versión del sistema.",
                color=Theme.get_color(interaction.guild.id, 'primary')
            )
            
            embed.add_field(name="🤖 Versión del Bot", value=f"`v{BOT_VERSION}`", inline=True)
            embed.add_field(name="📦 Plan Activo", value=f"**{plan_display}**", inline=True)
            embed.add_field(name="🔑 Licencia", value=f"`{masked_key}`", inline=False)
            
            # Estado
            status = "✅ Activo" if plan_str != "unknown" else "❌ Inactivo"
            embed.add_field(name="Estado del Servicio", value=status, inline=True)
            
            # Footer
            embed.set_footer(text=f"{Theme.get_footer_text(interaction.guild.id)} | ID Servidor: {interaction.guild.id}")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error al obtener info del plan: {e}", ephemeral=True)

    @app_commands.command(
        name="info", description="Resumen de funciones y módulos disponibles"
    )
    async def info(self, interaction: discord.Interaction):
        try:
            print(f"DEBUG: /info triggered by {interaction.user}")
            features = (
                "⚡ **Oráculo**: Canales de ayuda y tickets"
                "\n🛡 **Guardian**: Verificación y seguridad"
                "\n🌟 **Niveles**: XP, rangos y recompensas"
                "\n🐶 **Mascotas**: Crianza, evoluciones y duelos"
                "\n🏛️ **Clanes**: Olimpos, guerras y ranking global"
                "\n💍 **Social**: Matrimonios, familia y ship"
                "\n💰 **Economía**: Global, tiendas y apuestas"
                "\n🏆 **LoL**: Estadísticas en tiempo real"
                "\n📊 **Status**: Diagnóstico del sistema"
            )
            embed = discord.Embed(
                title=f"🏛️ PoseidonUI v{BOT_VERSION}", description=features, color=Theme.get_color(interaction.guild.id, 'primary')
            )
            banner_url = "https://raw.githubusercontent.com/Luciuss04/PoseidonUI/main/BotDiscord4.0/banner.png"
            embed.set_image(url=banner_url)
            embed.add_field(name="Versión", value=f"{BOT_VERSION} (Stable)", inline=True)
            embed.add_field(
                name="Comandos Clave",
                value="`/ayuda` `/clan` `/mascota` `/love` `/top`",
                inline=False,
            )
            embed.add_field(name="Desarrollador", value="Luciuss04", inline=True)
            embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
            await interaction.response.send_message(embed=embed, view=BuyView(self.bot))
        except Exception as e:
            import traceback
            traceback.print_exc()
            await interaction.response.send_message(f"❌ Error interno: {e}", ephemeral=True)

    @app_commands.command(
        name="novedades", description="Muestra las últimas novedades y actualizaciones del bot"
    )
    async def novedades(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="✨ Novedades de PoseidonUI",
            description="¡El Olimpo se renueva! Aquí tienes las últimas mejoras implementadas:",
            color=Theme.get_color(interaction.guild.id, 'secondary')
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
        embed.set_footer(text=f"{Theme.get_footer_text(interaction.guild.id)} • Versión {BOT_VERSION} • {fecha}")
        await interaction.response.send_message(embed=embed)


    @app_commands.command(
        name="admin_panel", description="[DESACTIVADO] Panel de administración"
    )
    async def admin_panel(self, interaction: discord.Interaction, modo: str = "local"):
        await interaction.response.send_message("❌ Comando desactivado.", ephemeral=True)

    @app_commands.command(
        name="activar", description="Activar licencia de PoseidonUI")
    async def activar(self, interaction: discord.Interaction, key: str):
        import pathlib
        import re
        from datetime import datetime

        key = key.strip()
        print(f"DEBUG ACTIVAR: Recibida key='{key}' User={interaction.user}")

        # Regex flexible: POSEIDON-XXXX-XXXX-XXXX o POSE-CUSTOM-XXXX
        if not re.fullmatch(r"(POSEIDON-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4})|(POSE-CUSTOM-[A-Z0-9]+)", key):
            await interaction.response.send_message(
                f"❌ Formato inválido de licencia (`{key}`).\nAsegúrate de copiarla exactamente.", ephemeral=True
            )
            return
            
        # Usar ruta absoluta basada en la ubicación del bot para asegurar que encuentra el archivo
        base_path = pathlib.Path(__file__).parent.parent.parent.parent
        lic_files = [
            base_path / "licenses.txt",
            base_path / "licenses_plans.txt",
            pathlib.Path("licenses.txt"),      # Fallback relativo
            pathlib.Path("licenses_plans.txt") # Fallback relativo
        ]
        
        ok = False
        valid_plans = {}
        # Debug: Hardcode de emergencia para la clave generada
        valid_plans["POSEIDON-GI22-KNG9-NEJX"] = "custom"

        for lic_file in lic_files:
            if lic_file.exists():
                try:
                    lines = lic_file.read_text(encoding="utf-8").splitlines()
                    for ln in lines:
                        s = ln.strip()
                        if not s or s.startswith("#"):
                            continue
                        # Si es formato KEY|PLAN|SIG o KEY|PLAN, tomamos solo la KEY y PLAN
                        parts = s.split("|")
                        if parts:
                            key_part = parts[0].strip()
                            if key_part:
                                plan_part = "basic"
                                if len(parts) > 1 and parts[1].strip():
                                    plan_part = parts[1].strip().lower()
                                valid_plans[key_part] = plan_part
                except Exception as e:
                    print(f"Error leyendo {lic_file}: {e}")
        
        ok = key in valid_plans
        
        if not ok:
            print(f"DEBUG: Key '{key}' not found in valid set: {list(valid_plans.keys())}")
            await interaction.response.send_message(
                "❌ Licencia no válida (no encontrada en el registro).", ephemeral=True
            )
            return
        
        # Verificar binding
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
            return

        pathlib.Path("license_active.txt").write_text(key, encoding="utf-8")
        entry = (
            f"{key}|{guild_id}|{guild_name}|{datetime.utcnow().isoformat()}|PERM|PERM"
        )
        bind_path.open("a", encoding="utf-8").write(entry + "\n")
        
        # ACTUALIZAR ESTADO EN MEMORIA
        new_plan = valid_plans[key]
        self.bot.license_key = key
        self.bot.active_plan = new_plan
        self.bot.is_trial = False
        print(f"DEBUG: Plan actualizado en memoria a '{new_plan}' para key '{key}'")
        
        await interaction.response.send_message(
            f"✅ Licencia activada y vinculada (Plan: **{new_plan.capitalize()}**).", ephemeral=True
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


class BuyView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="Comprar licencia", style=discord.ButtonStyle.success, emoji="💳"
    )
    async def buy(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="💎 Planes de Licencia PoseidonUI",
            description="Elige el poder que necesitas para tu servidor.",
            color=Theme.get_color(interaction.guild.id, 'warning')
        )
        embed.add_field(
            name="🥉 Básico — 19€",
            value="• Status y Guardian\n• Licencia Permanente\n• Soporte Básico",
            inline=False
        )
        embed.add_field(
            name="🥈 Pro — 39€",
            value="• Todo lo Básico +\n• Oráculo (Tickets) y Niveles\n• Economía y Anti-Spam\n• Soporte Prioritario",
            inline=False
        )
        embed.add_field(
            name="🥇 Élite — 69€",
            value="• Todo lo Pro +\n• Ofertas, Sorteos y LoL\n• Integraciones Web\n• Soporte VIP 24/7",
            inline=False
        )
        embed.add_field(
            name="👑 Custom — 99€+",
            value="• Desarrollo a medida\n• Funciones exclusivas\n• Branding personalizado",
            inline=False
        )
        embed.set_footer(text=f"{Theme.get_footer_text(interaction.guild.id)} • Para adquirir una licencia, contacta al desarrollador.")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(About(bot))
