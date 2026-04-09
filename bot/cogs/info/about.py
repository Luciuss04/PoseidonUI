import sys
import time

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import BOT_VERSION
from bot.themes import Theme


def _is_owner_check():
    async def predicate(interaction: discord.Interaction) -> bool:
        try:
            return await interaction.client.is_owner(interaction.user)
        except Exception:
            return False

    return app_commands.check(predicate)


class About(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Registro del User Command (Context Menu)
        self.ctx_menu = app_commands.ContextMenu(
            name="Ver Perfil Divino",
            callback=self.perfil_divino,
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self):
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    async def perfil_divino(self, interaction: discord.Interaction, member: discord.Member):
        """Muestra información detallada del usuario desde el menú de contexto."""
        embed = discord.Embed(
            title=f"🔱 Perfil Divino • {member.display_name}",
            color=Theme.get_color(interaction.guild.id, "info"),
        )

        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)

        embed.add_field(name="ID", value=f"`{member.id}`", inline=True)
        embed.add_field(
            name="Cuenta creada", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True
        )
        embed.add_field(
            name="Unión al servidor",
            value=f"<t:{int(member.joined_at.timestamp())}:R>",
            inline=True,
        )

        roles = [r.mention for r in reversed(member.roles) if r != interaction.guild.default_role]
        embed.add_field(
            name=f"Roles ({len(roles)})", value=" ".join(roles[:10]) or "Ninguno", inline=False
        )

        embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
        await interaction.response.send_message(embed=embed, ephemeral=True)

    def _trial_days_left(self) -> int | None:
        try:
            import pathlib

            p = pathlib.Path("trial_start.txt")
            if not p.exists():
                return None
            start = int(p.read_text(encoding="utf-8").strip() or "0")
            if not start:
                return None
            now = int(time.time())
            days_used = max(0, (now - start) // 86400)
            return max(0, 7 - int(days_used))
        except Exception:
            return None

    def _license_control_state(self) -> tuple[bool, int, str]:
        try:
            main = sys.modules.get("__main__") or sys.modules.get("app")
            get_control = getattr(main, "get_license_control", None)
            data = get_control() if callable(get_control) else {}
            revoked = bool(data.get("revoked") is True)
            try:
                exp = int(data.get("expires_at") or 0)
            except Exception:
                exp = 0
            reason = str(data.get("reason") or "").strip()
            return (revoked, exp, reason)
        except Exception:
            return (False, 0, "")

    def _mask_key(self, key: str | None) -> str:
        k = (key or "").strip()
        if not k or k.lower() == "unknown":
            return "NO-LICENSE"
        if len(k) <= 12:
            return k
        return f"{k[:8]}…{k[-4:]}"

    @app_commands.command(name="tema", description="Cambia el tema visual del bot (Admin)")
    @app_commands.describe(nombre="Nombre del tema a aplicar")
    async def tema(self, interaction: discord.Interaction, nombre: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "⛔ Solo administradores pueden cambiar el tema.",
                ephemeral=True,
            )
            return

        # Verificar si el tema existe en ThemeManager
        all_themes = Theme.get_all_themes()
        if nombre not in all_themes:
            await interaction.response.send_message(
                f"❌ El tema `{nombre}` no existe.",
                ephemeral=True,
            )
            return

        if Theme.set_theme(nombre, guild_id=interaction.guild.id):
            theme_data = all_themes[nombre]
            embed = discord.Embed(
                title="🎨 Tema Actualizado",
                description=(
                    f"El tema se ha cambiado a **{theme_data['name']}**.\n"
                    "Los próximos mensajes usarán este estilo."
                ),
                color=Theme.get_color(interaction.guild.id, "success"),
            )
            embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ Error al cambiar el tema.", ephemeral=True)

    @tema.autocomplete("nombre")
    async def tema_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        all_themes = Theme.get_all_themes()
        choices = []
        for key, data in all_themes.items():
            # Filtrar por búsqueda
            if current.lower() in data["name"].lower() or current.lower() in key.lower():
                choices.append(app_commands.Choice(name=data["name"], value=key))

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
            revoked, expires_at, reason = self._license_control_state()
            trial_left = self._trial_days_left()

            # Formatear Plan
            plan_emojis = {
                "basic": "🥉 Básico",
                "pro": "🥈 Pro",
                "elite": "🥇 Élite",
                "custom": "👑 Custom",
                "expired": "⛔ Restringido",
                "unknown": "❓ Desconocido",
            }
            # Normalizar a string y minúsculas para búsqueda
            plan_str = str(plan).lower()
            plan_display = plan_emojis.get(plan_str, f"❓ {str(plan).capitalize()}")

            if is_trial:
                plan_display += " (Trial)"
            masked_key = self._mask_key(str(key))

            embed = discord.Embed(
                title="📋 Panel del Olimpo",
                description="Información de tu suscripción y versión del sistema.",
                color=Theme.get_color(interaction.guild.id, "primary"),
            )

            embed.add_field(name="🤖 Versión del Bot", value=f"`v{BOT_VERSION}`", inline=True)
            embed.add_field(name="📦 Plan Activo", value=f"**{plan_display}**", inline=True)
            embed.add_field(name="🔑 Licencia", value=f"`{masked_key}`", inline=False)

            # Estado
            if plan_str == "expired" or revoked:
                status = "⛔ Restringido"
            elif plan_str == "unknown":
                status = "❓ Sin verificar"
            else:
                status = "✅ Activo"
            embed.add_field(name="Estado del Servicio", value=status, inline=True)

            if is_trial:
                if trial_left is None:
                    embed.add_field(name="Trial", value="Activa", inline=True)
                else:
                    embed.add_field(
                        name="Trial",
                        value=f"{trial_left} día(s) restantes",
                        inline=True,
                    )

            if revoked:
                embed.add_field(name="Control", value="Revocada", inline=True)
            elif expires_at:
                embed.add_field(name="Vencimiento", value=f"<t:{expires_at}:R>", inline=True)
            else:
                embed.add_field(name="Vencimiento", value="Sin vencimiento", inline=True)
            if reason:
                embed.add_field(name="Motivo", value=reason[:1024], inline=False)

            # Footer
            embed.set_footer(
                text=(
                    f"{Theme.get_footer_text(interaction.guild.id)} | "
                    f"ID Servidor: {interaction.guild.id}"
                )
            )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error al obtener info del plan: {e}",
                ephemeral=True,
            )

    @app_commands.command(name="info", description="Resumen de funciones y módulos disponibles")
    async def info(self, interaction: discord.Interaction):
        try:
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
                title=f"🏛️ PoseidonUI v{BOT_VERSION}",
                description=features,
                color=Theme.get_color(interaction.guild.id, "primary"),
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
        name="versiones", description="Muestra las últimas novedades y actualizaciones del bot"
    )
    async def versiones(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="✨ Novedades de PoseidonUI",
            description="¡El Olimpo se renueva! Aquí tienes las últimas mejoras implementadas:",
            color=Theme.get_color(interaction.guild.id, "secondary"),
        )
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)

        embed.add_field(
            name="💰 Economía Divina",
            value=(
                "• **`/transfer`**: ¡Envía monedas a otros usuarios!\n"
                "• **`/slots`**: ¡Prueba tu suerte en las tragaperras divinas!"
            ),
            inline=False,
        )
        embed.add_field(
            name="🛠️ Diagnóstico y Estabilidad",
            value=(
                "• **`!status`**: Comando de prefijo rápido para verificar estado.\n"
                "• **`/status`**: Arreglado y optimizado para admins/staff.\n"
                "• **Logs**: Mejoras en el sistema de reporte de errores."
            ),
            inline=False,
        )
        embed.add_field(
            name="👥 Comunidad y Diversión",
            value=(
                "• **`/userinfo` y `/serverinfo`**: Información detallada al instante.\n"
                "• **`/8ball`**: ¡Pregúntale al oráculo mágico!\n"
                "• **`/ship`**: Calculadora de amor.\n"
                "• **`/hack`**: Simulación divertida.\n"
                "• **`/dado` y `/moneda`**: Azar básico.\n"
                "• **Sugerencias**: Sistema optimizado para feedback."
            ),
            inline=False,
        )

        import datetime

        fecha = datetime.datetime.utcnow().strftime("%d/%m/%Y")
        embed.set_footer(
            text=f"{Theme.get_footer_text(interaction.guild.id)} • Versión {BOT_VERSION} • {fecha}"
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="admin_panel", description="[DESACTIVADO] Panel de administración")
    async def admin_panel(self, interaction: discord.Interaction, modo: str = "local"):
        await interaction.response.send_message("❌ Comando desactivado.", ephemeral=True)

    @app_commands.command(
        name="activar",
        description="Activar licencia de PoseidonUI",
    )
    async def activar(self, interaction: discord.Interaction, key: str):
        import pathlib
        import re
        from datetime import datetime

        key = key.strip()

        # Regex flexible: POSEIDON-XXXX-XXXX-XXXX o POSE-CUSTOM-XXXX
        pattern = r"(POSEIDON-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4})|(POSE-CUSTOM-[A-Z0-9]+)"
        if not re.fullmatch(pattern, key):
            await interaction.response.send_message(
                (
                    f"❌ Formato inválido de licencia (`{key}`).\n"
                    "Asegúrate de copiarla exactamente."
                ),
                ephemeral=True,
            )
            return

        # Usar ruta absoluta basada en la ubicación del bot para asegurar que encuentra el archivo
        base_path = pathlib.Path(__file__).parent.parent.parent.parent
        lic_files = [
            base_path / "licenses.txt",
            base_path / "licenses_plans.txt",
            pathlib.Path("licenses.txt"),  # Fallback relativo
            pathlib.Path("licenses_plans.txt"),  # Fallback relativo
        ]

        ok = False
        valid_plans = {}

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
        now_iso = datetime.utcnow().isoformat()
        entry = f"{key}|{guild_id}|{guild_name}|{now_iso}|PERM|PERM"

        try:
            existing = []
            if bind_path.exists():
                existing = bind_path.read_text(encoding="utf-8").splitlines()
            out = []
            for ln in existing:
                s = ln.strip()
                if not s or s.startswith("#"):
                    out.append(ln)
                    continue
                parts = [p.strip() for p in ln.split("|")]
                if parts and parts[0] == key:
                    continue
                out.append(ln)
            out.append(entry)
            bind_path.write_text("\n".join(out).rstrip("\n") + "\n", encoding="utf-8")
        except Exception:
            bind_path.open("a", encoding="utf-8").write(entry + "\n")

        # ACTUALIZAR ESTADO EN MEMORIA
        new_plan = valid_plans[key]
        self.bot.license_key = key
        self.bot.active_plan = new_plan
        self.bot.is_trial = False

        try:
            main = sys.modules.get("__main__") or sys.modules.get("app")
            apply_plan = getattr(main, "apply_plan_runtime", None)
            if callable(apply_plan):
                await apply_plan(self.bot, new_plan, False)
        except Exception:
            pass

        embed = discord.Embed(
            title="✅ Licencia activada",
            description="La licencia se ha validado y el plan ya está activo en este servidor.",
            color=Theme.get_color(interaction.guild.id, "success"),
        )
        embed.add_field(name="Plan", value=str(new_plan).capitalize(), inline=True)
        embed.add_field(name="Licencia", value=f"`{self._mask_key(key)}`", inline=True)
        embed.add_field(
            name="Siguiente paso",
            value="Usa `/plan` para ver el estado.",
            inline=False,
        )
        embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
        await interaction.response.send_message(embed=embed, ephemeral=True)
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

    @app_commands.command(
        name="licencia_revocar",
        description="[OWNER] Revoca la licencia y restringe el bot",
    )
    @app_commands.describe(motivo="Motivo interno (opcional)")
    @_is_owner_check()
    async def licencia_revocar(self, interaction: discord.Interaction, motivo: str = ""):
        try:
            main = sys.modules.get("__main__") or sys.modules.get("app")
            set_control = getattr(main, "set_license_control", None)
            apply_plan = getattr(main, "apply_plan_runtime", None)
            if callable(set_control):
                set_control(revoked=True, reason=motivo)
            if callable(apply_plan):
                await apply_plan(self.bot, "expired", False)
            await interaction.response.send_message(
                "✅ Licencia revocada. Modo restringido activo.",
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error al revocar licencia: {e}",
                ephemeral=True,
            )

    @app_commands.command(
        name="licencia_restaurar",
        description="[OWNER] Restaura la licencia (si es válida)",
    )
    @_is_owner_check()
    async def licencia_restaurar(self, interaction: discord.Interaction):
        try:
            main = sys.modules.get("__main__") or sys.modules.get("app")
            set_control = getattr(main, "set_license_control", None)
            recompute = getattr(main, "recompute_license_state", None)
            apply_plan = getattr(main, "apply_plan_runtime", None)
            if callable(set_control):
                set_control(revoked=False, reason="")
            plan = getattr(self.bot, "active_plan", None)
            is_trial = bool(getattr(self.bot, "is_trial", False))
            if callable(recompute):
                plan, is_trial = recompute()
            if callable(apply_plan):
                await apply_plan(self.bot, plan or "basic", bool(is_trial))
            await interaction.response.send_message(
                "✅ Licencia restaurada (si era válida).",
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error al restaurar licencia: {e}",
                ephemeral=True,
            )

    @app_commands.command(
        name="licencia_vencimiento",
        description="[OWNER] Define vencimiento (días) para cortar acceso",
    )
    @app_commands.describe(dias="Días hasta vencimiento (0 = sin vencimiento)")
    @_is_owner_check()
    async def licencia_vencimiento(self, interaction: discord.Interaction, dias: int):
        try:
            dias = int(dias)
        except Exception:
            dias = 0
        if dias < 0:
            dias = 0
        try:
            expires_at = int(time.time()) + (dias * 86400) if dias else 0
            main = sys.modules.get("__main__") or sys.modules.get("app")
            set_control = getattr(main, "set_license_control", None)
            recompute = getattr(main, "recompute_license_state", None)
            apply_plan = getattr(main, "apply_plan_runtime", None)
            if callable(set_control):
                set_control(revoked=False, expires_at=expires_at)
            plan = getattr(self.bot, "active_plan", None)
            is_trial = bool(getattr(self.bot, "is_trial", False))
            if callable(recompute):
                plan, is_trial = recompute()
            if callable(apply_plan):
                await apply_plan(self.bot, plan or "basic", bool(is_trial))
            await interaction.response.send_message("✅ Vencimiento actualizado.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error al actualizar vencimiento: {e}",
                ephemeral=True,
            )

    @app_commands.command(
        name="licencia_estado",
        description="[OWNER] Muestra estado de control de licencia",
    )
    @_is_owner_check()
    async def licencia_estado(self, interaction: discord.Interaction):
        try:
            revoked, exp, reason = self._license_control_state()
            plan = getattr(self.bot, "active_plan", "Unknown") or "Unknown"
            is_trial = bool(getattr(self.bot, "is_trial", False))
            key = getattr(self.bot, "license_key", None)
            trial_left = self._trial_days_left()

            embed = discord.Embed(
                title="🔒 Estado de Licencia",
                color=Theme.get_color(interaction.guild.id, "primary"),
            )
            embed.add_field(name="Plan", value=str(plan), inline=True)
            embed.add_field(name="Trial", value=str(bool(is_trial)), inline=True)
            embed.add_field(name="Licencia", value=f"`{self._mask_key(str(key))}`", inline=False)
            embed.add_field(name="Revocada", value=str(bool(revoked)), inline=True)
            if exp:
                embed.add_field(name="Vence", value=f"<t:{exp}:R>", inline=True)
            else:
                embed.add_field(name="Vence", value="0 (sin vencimiento)", inline=True)
            if is_trial and trial_left is not None:
                embed.add_field(name="Trial restante", value=f"{trial_left} día(s)", inline=True)
            if reason:
                embed.add_field(name="Motivo", value=reason[:1024], inline=False)
            embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error al leer estado: {e}", ephemeral=True)


class BuyView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Comprar licencia", style=discord.ButtonStyle.success, emoji="💳")
    async def buy(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="💎 Planes de Licencia PoseidonUI",
            description="Elige el poder que necesitas para tu servidor.",
            color=Theme.get_color(interaction.guild.id, "warning"),
        )
        embed.add_field(
            name="🥉 Básico — 19€",
            value="• Status y Guardian\n• Licencia Permanente\n• Soporte Básico",
            inline=False,
        )
        embed.add_field(
            name="🥈 Pro — 39€",
            value=(
                "• Todo lo Básico +\n"
                "• Oráculo (Tickets) y Niveles\n"
                "• Economía y Anti-Spam\n"
                "• Soporte Prioritario"
            ),
            inline=False,
        )
        embed.add_field(
            name="🥇 Élite — 69€",
            value=(
                "• Todo lo Pro +\n"
                "• Ofertas, Sorteos y LoL\n"
                "• Integraciones Web\n"
                "• Soporte VIP 24/7"
            ),
            inline=False,
        )
        embed.add_field(
            name="👑 Custom — 99€+",
            value="• Desarrollo a medida\n• Funciones exclusivas\n• Branding personalizado",
            inline=False,
        )
        embed.set_footer(
            text=(
                f"{Theme.get_footer_text(interaction.guild.id)} • "
                "Para adquirir una licencia, contacta al desarrollador."
            )
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(About(bot))
