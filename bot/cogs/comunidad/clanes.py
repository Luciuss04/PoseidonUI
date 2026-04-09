import json
import os
import random
import time

import discord
from discord import app_commands
from discord.ext import commands

from bot.themes import Theme


class Clanes(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.clanes_file = "clanes.json"
        self.clanes = self._load_clanes()

    def _load_clanes(self):
        if os.path.exists(self.clanes_file):
            try:
                with open(self.clanes_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_clanes(self):
        with open(self.clanes_file, "w", encoding="utf-8") as f:
            json.dump(self.clanes, f, indent=4, ensure_ascii=False)

    def _get_user_clan(self, user_id: int):
        user_id_str = str(user_id)
        for clan_name, data in self.clanes.items():
            if user_id_str in data["members"] or user_id_str == str(data["owner"]):
                return clan_name
        return None

    def _add_log(self, clan_name: str, message: str):
        if clan_name not in self.clanes:
            return
        if "bank_log" not in self.clanes[clan_name]:
            self.clanes[clan_name]["bank_log"] = []

        # Keep only last 20 logs
        timestamp = int(time.time())
        self.clanes[clan_name]["bank_log"].insert(0, {"t": timestamp, "m": message})
        self.clanes[clan_name]["bank_log"] = self.clanes[clan_name]["bank_log"][:20]

    @app_commands.command(name="clan", description="Sistema de Clanes y Olimpos")
    @app_commands.describe(
        accion="crear, unirse, info, salir, listar, expulsar, banco, guerra, mejorar, roles, salario, escudo, ranking",
        nombre="Nombre / Cantidad / Item / URL Escudo",
        descripcion="Descripción del clan (solo al crear) / Rol",
    )
    @app_commands.choices(
        accion=[
            app_commands.Choice(name="Crear Olimpo (Clan)", value="crear"),
            app_commands.Choice(name="Ver Info", value="info"),
            app_commands.Choice(name="Unirse a Olimpo", value="unirse"),
            app_commands.Choice(name="Abandonar Olimpo", value="salir"),
            app_commands.Choice(name="Listar Olimpos", value="listar"),
            app_commands.Choice(name="Banco (Depositar/Retirar)", value="banco"),
            app_commands.Choice(name="Declarar Guerra", value="guerra"),
            app_commands.Choice(name="Expulsar Miembro (Líder)", value="expulsar"),
            app_commands.Choice(name="Mejorar Olimpo", value="mejorar"),
            app_commands.Choice(name="Gestionar Roles", value="roles"),
            app_commands.Choice(name="Configurar Salario (Líder)", value="config_salario"),
            app_commands.Choice(name="Cobrar Salario", value="salario"),
            app_commands.Choice(name="Cambiar Escudo (URL)", value="escudo"),
            app_commands.Choice(name="Ver Registros (Logs)", value="registros"),
            app_commands.Choice(name="Ranking Global", value="ranking"),
        ]
    )
    async def clan(
        self,
        interaction: discord.Interaction,
        accion: str,
        nombre: str = None,
        descripcion: str = None,
    ):
        user_id = str(interaction.user.id)
        monedas = self.bot.get_cog("Monedas")

        if accion == "crear":
            if self._get_user_clan(interaction.user.id):
                await interaction.response.send_message(
                    "❌ Ya perteneces a un Olimpo. Debes salirte antes de crear uno.",
                    ephemeral=True,
                )
                return

            if not nombre:
                await interaction.response.send_message(
                    "⚠️ Debes especificar un nombre para tu Olimpo.", ephemeral=True
                )
                return

            if nombre in self.clanes:
                await interaction.response.send_message(
                    "⚠️ Ya existe un Olimpo con ese nombre.", ephemeral=True
                )
                return

            # Costo de creación
            costo_creacion = 1000
            if monedas:
                if not monedas.remove_balance(interaction.user.id, costo_creacion):
                    await interaction.response.send_message(
                        f"❌ Necesitas {costo_creacion} monedas para fundar un Olimpo.",
                        ephemeral=True,
                    )
                    return

            self.clanes[nombre] = {
                "owner": user_id,
                "description": descripcion or "Un nuevo Olimpo se alza.",
                "members": [user_id],
                "roles": {},  # {user_id: "rol"}
                "level": 1,
                "wins": 0,
                "bank": 0,
                "daily_salary": 0,
                "last_salary": {},  # {user_id: timestamp}
                "bank_log": [],
            }
            self._save_clanes()
            self._add_log(nombre, f"Olimpo fundado por <@{user_id}>")
            await interaction.response.send_message(
                f"🏛️ **¡El Olimpo {nombre} ha sido fundado!**\nLíder: {interaction.user.mention}\nCosto: 💰 {costo_creacion}"
            )

        elif accion == "info":
            target_clan = nombre if nombre else self._get_user_clan(interaction.user.id)
            if not target_clan:
                await interaction.response.send_message(
                    "❌ No estás en un clan y no especificaste ninguno.", ephemeral=True
                )
                return

            if target_clan not in self.clanes:
                await interaction.response.send_message("❌ Ese Olimpo no existe.", ephemeral=True)
                return

            data = self.clanes[target_clan]
            owner = interaction.guild.get_member(int(data["owner"]))
            owner_name = owner.display_name if owner else "Desconocido"

            embed = discord.Embed(
                title=f"🏛️ Olimpo: {target_clan}",
                description=data["description"],
                color=Theme.get_color(interaction.guild.id, "secondary"),
            )
            embed.add_field(name="👑 Líder", value=owner_name, inline=True)
            embed.add_field(
                name="👥 Miembros",
                value=f"{len(data['members'])}/{data['level'] * 5 + 5}",
                inline=True,
            )
            embed.add_field(name="⭐ Nivel", value=str(data["level"]), inline=True)
            embed.add_field(name="🏆 Victorias", value=str(data.get("wins", 0)), inline=True)
            embed.add_field(name="💰 Tesoro", value=str(data.get("bank", 0)), inline=True)
            embed.add_field(
                name="💸 Salario Diario", value=str(data.get("daily_salary", 0)), inline=True
            )

            member_names = []
            roles = data.get("roles", {})
            for mid in data["members"][:10]:  # Mostrar solo primeros 10
                m = interaction.guild.get_member(int(mid))
                if m:
                    role = roles.get(mid, "Miembro")
                    if mid == str(data["owner"]):
                        role = "Líder"
                    member_names.append(f"{m.display_name} ({role})")

            if len(data["members"]) > 10:
                member_names.append(f"... y {len(data['members']) - 10} más")

            embed.add_field(
                name="Lista de Miembros",
                value=", ".join(member_names) if member_names else "Ninguno visible",
                inline=False,
            )
            embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
            await interaction.response.send_message(embed=embed)

        elif accion == "unirse":
            current_clan = self._get_user_clan(interaction.user.id)
            if current_clan:
                await interaction.response.send_message(
                    f"❌ Ya estás en el Olimpo **{current_clan}**.", ephemeral=True
                )
                return

            if not nombre:
                await interaction.response.send_message(
                    "⚠️ Debes especificar el nombre del Olimpo al que quieres unirte.",
                    ephemeral=True,
                )
                return

            if nombre not in self.clanes:
                await interaction.response.send_message("❌ Ese Olimpo no existe.", ephemeral=True)
                return

            clan_data = self.clanes[nombre]
            limit = clan_data["level"] * 5 + 5
            if len(clan_data["members"]) >= limit:
                await interaction.response.send_message(
                    f"❌ El Olimpo **{nombre}** está lleno (Máx {limit}). Necesitan mejorar el clan.",
                    ephemeral=True,
                )
                return

            # En un sistema real, aquí iría una solicitud/invitación. Para simplificar, entrada libre.
            self.clanes[nombre]["members"].append(user_id)
            self._save_clanes()
            await interaction.response.send_message(f"✅ Te has unido al Olimpo **{nombre}**.")

        elif accion == "salir":
            clan_name = self._get_user_clan(interaction.user.id)
            if not clan_name:
                await interaction.response.send_message(
                    "❌ No perteneces a ningún Olimpo.", ephemeral=True
                )
                return

            clan_data = self.clanes[clan_name]

            if str(clan_data["owner"]) == user_id:
                # Si es el líder, disolver o transferir. Aquí disolvemos.
                del self.clanes[clan_name]
                self._save_clanes()
                await interaction.response.send_message(
                    f"🗑️ Como eras el líder, el Olimpo **{clan_name}** ha sido disuelto.",
                    ephemeral=True,
                )
            else:
                if user_id in clan_data["members"]:
                    clan_data["members"].remove(user_id)
                    # Limpiar rol
                    if "roles" in clan_data and user_id in clan_data["roles"]:
                        del clan_data["roles"][user_id]
                    self._save_clanes()
                    await interaction.response.send_message(
                        f"👋 Has abandonado el Olimpo **{clan_name}**.", ephemeral=True
                    )

        elif accion == "listar":
            if not self.clanes:
                await interaction.response.send_message(
                    "No hay Olimpos fundados aún.", ephemeral=True
                )
                return

            txt = "**🏛️ Lista de Olimpos:**\n"
            for name, data in list(self.clanes.items())[:10]:
                txt += f"• **{name}** (Nvl {data['level']}) - � {len(data['members'])} - �� {data.get('bank', 0)}\n"

            await interaction.response.send_message(txt)

        elif accion == "banco":
            clan_name = self._get_user_clan(interaction.user.id)
            if not clan_name:
                await interaction.response.send_message(
                    "❌ No perteneces a ningún Olimpo.", ephemeral=True
                )
                return

            try:
                amount = int(nombre) if nombre else 100
            except Exception:
                await interaction.response.send_message(
                    "⚠️ Debes especificar una cantidad válida en 'nombre'. Ej: 100 o -50 (retirar)",
                    ephemeral=True,
                )
                return

            if amount == 0:
                await interaction.response.send_message(
                    f"💰 El tesoro de **{clan_name}** tiene: **{self.clanes[clan_name].get('bank', 0)}** monedas.",
                    ephemeral=True,
                )
                return

            if amount > 0:
                # Depositar
                if monedas:
                    if not monedas.remove_balance(interaction.user.id, amount):
                        await interaction.response.send_message(
                            f"❌ No tienes suficientes monedas ({amount}) para depositar.",
                            ephemeral=True,
                        )
                        return
                else:
                    await interaction.response.send_message(
                        "⚠️ Sistema de economía no disponible. No se descontó dinero (modo prueba).",
                        ephemeral=True,
                    )

                self.clanes[clan_name]["bank"] = self.clanes[clan_name].get("bank", 0) + amount
                self._add_log(clan_name, f"Depósito: +{amount} por <@{interaction.user.id}>")
                self._save_clanes()
                await interaction.response.send_message(
                    f"💰 Has donado **{amount}** al tesoro de **{clan_name}**."
                )

            else:
                # Retirar (Solo líder)
                if self.clanes[clan_name]["owner"] != user_id:
                    await interaction.response.send_message(
                        "❌ Solo el líder puede retirar fondos del banco.", ephemeral=True
                    )
                    return

                withdraw = abs(amount)
                if self.clanes[clan_name].get("bank", 0) < withdraw:
                    await interaction.response.send_message(
                        "❌ No hay suficientes fondos en el banco del clan.", ephemeral=True
                    )
                    return

                self.clanes[clan_name]["bank"] -= withdraw
                self._add_log(clan_name, f"Retiro: -{withdraw} por <@{interaction.user.id}>")
                if monedas:
                    monedas.add_balance(interaction.user.id, withdraw)

                self._save_clanes()
                await interaction.response.send_message(
                    f"💸 Has retirado **{withdraw}** del tesoro de **{clan_name}**."
                )

        elif accion == "guerra":
            my_clan = self._get_user_clan(interaction.user.id)
            if not my_clan:
                await interaction.response.send_message("❌ No tienes clan.", ephemeral=True)
                return

            clan_data = self.clanes[my_clan]
            if (
                clan_data["owner"] != user_id
                and clan_data.get("roles", {}).get(user_id) != "General"
            ):
                await interaction.response.send_message(
                    "❌ Solo el Líder o un General pueden declarar guerras.", ephemeral=True
                )
                return

            enemy_clan = nombre
            if not enemy_clan or enemy_clan not in self.clanes:
                await interaction.response.send_message(
                    "⚠️ Debes especificar un clan enemigo válido en 'nombre'.", ephemeral=True
                )
                return

            if enemy_clan == my_clan:
                await interaction.response.send_message(
                    "❌ No puedes atacarte a ti mismo.", ephemeral=True
                )
                return

            # Simulación de batalla mejorada
            my_power = (
                clan_data["level"] * 20 + len(clan_data["members"]) * 10 + random.randint(1, 50)
            )
            enemy_power = (
                self.clanes[enemy_clan]["level"] * 20
                + len(self.clanes[enemy_clan]["members"]) * 10
                + random.randint(1, 50)
            )

            if my_power > enemy_power:
                loot = int(self.clanes[enemy_clan].get("bank", 0) * 0.15)  # 15% robo
                self.clanes[enemy_clan]["bank"] -= loot
                self.clanes[my_clan]["bank"] += loot
                self.clanes[my_clan]["wins"] = self.clanes[my_clan].get("wins", 0) + 1

                self._add_log(my_clan, f"Guerra ganada vs {enemy_clan}: +{loot}")
                self._add_log(enemy_clan, f"Guerra perdida vs {my_clan}: -{loot}")

                msg = f"🏆 **¡VICTORIA!**\n**{my_clan}** (Poder: {my_power}) ha aplastado a **{enemy_clan}** (Poder: {enemy_power}).\nBotín robado: 💰 {loot}"
            else:
                # El atacante pierde un poco de oro por la derrota
                penalty = int(clan_data.get("bank", 0) * 0.05)
                self.clanes[my_clan]["bank"] -= penalty
                self.clanes[enemy_clan]["wins"] = self.clanes[enemy_clan].get("wins", 0) + 1

                self._add_log(my_clan, f"Guerra perdida vs {enemy_clan}: -{penalty}")
                self._add_log(enemy_clan, f"Defensa exitosa vs {my_clan}")

                msg = f"💀 **DERROTA...**\n**{enemy_clan}** (Poder: {enemy_power}) ha defendido su honor contra **{my_clan}** (Poder: {my_power}).\nPerdieron 💰 {penalty} en la retirada."

            self._save_clanes()
            await interaction.response.send_message(msg)

        elif accion == "expulsar":
            my_clan = self._get_user_clan(interaction.user.id)
            if not my_clan:
                return

            if self.clanes[my_clan]["owner"] != user_id:
                await interaction.response.send_message(
                    "❌ Solo el líder puede expulsar.", ephemeral=True
                )
                return

            # Simplificado: usar ID en 'nombre'
            if not nombre:
                await interaction.response.send_message(
                    "⚠️ Debes especificar el ID o mención del usuario a expulsar.", ephemeral=True
                )
                return

            target_id = nombre.replace("<@", "").replace(">", "").replace("!", "")

            if target_id in self.clanes[my_clan]["members"]:
                if target_id == user_id:
                    await interaction.response.send_message(
                        "❌ No puedes expulsarte a ti mismo.", ephemeral=True
                    )
                    return
                self.clanes[my_clan]["members"].remove(target_id)
                if "roles" in self.clanes[my_clan] and target_id in self.clanes[my_clan]["roles"]:
                    del self.clanes[my_clan]["roles"][target_id]
                self._save_clanes()
                await interaction.response.send_message(f"👋 Miembro <@{target_id}> expulsado.")
            else:
                await interaction.response.send_message(
                    "❌ Ese usuario no está en tu Olimpo (asegúrate de usar su ID).", ephemeral=True
                )

        elif accion == "mejorar":
            my_clan = self._get_user_clan(interaction.user.id)
            if not my_clan:
                return

            data = self.clanes[my_clan]
            if data["owner"] != user_id:
                await interaction.response.send_message(
                    "❌ Solo el líder puede mejorar el Olimpo.", ephemeral=True
                )
                return

            current_level = data["level"]
            cost = current_level * 5000

            if data.get("bank", 0) < cost:
                await interaction.response.send_message(
                    f"❌ Fondos insuficientes en el banco del clan.\nNivel actual: {current_level}\nCosto siguiente nivel: 💰 {cost}\nFondos disponibles: 💰 {data.get('bank', 0)}",
                    ephemeral=True,
                )
                return

            data["bank"] -= cost
            data["level"] += 1
            self._add_log(my_clan, f"Mejora de Olimpo a Nivel {data['level']}: -{cost}")
            self._save_clanes()
            await interaction.response.send_message(
                f"🆙 **¡El Olimpo ha ascendido!**\nAhora es Nivel {data['level']}.\nCapacidad de miembros aumentada."
            )

        elif accion == "roles":
            # nombre = usuario_id, descripcion = rol (General, Veterano, Miembro)
            my_clan = self._get_user_clan(interaction.user.id)
            if not my_clan:
                return

            if self.clanes[my_clan]["owner"] != user_id:
                await interaction.response.send_message(
                    "❌ Solo el líder gestiona roles.", ephemeral=True
                )
                return

            if not nombre or not descripcion:
                await interaction.response.send_message(
                    "⚠️ Uso: `nombre`=ID_Usuario o Mención, `descripcion`=Rol (General/Veterano/Miembro)",
                    ephemeral=True,
                )
                return

            # Extract ID from mention if present
            target_id = nombre.replace("<@", "").replace(">", "").replace("!", "")
            new_role = descripcion.capitalize()

            if target_id not in self.clanes[my_clan]["members"]:
                await interaction.response.send_message(
                    "❌ Ese usuario no está en el clan.", ephemeral=True
                )
                return

            valid_roles = ["General", "Veterano", "Miembro"]
            if new_role not in valid_roles:
                await interaction.response.send_message(
                    f"❌ Rol no válido. Usa: {', '.join(valid_roles)}", ephemeral=True
                )
                return

            if "roles" not in self.clanes[my_clan]:
                self.clanes[my_clan]["roles"] = {}
            self.clanes[my_clan]["roles"][target_id] = new_role
            self._save_clanes()
            await interaction.response.send_message(
                f"✅ Rol de <@{target_id}> actualizado a **{new_role}**."
            )

        elif accion == "config_salario":
            my_clan = self._get_user_clan(interaction.user.id)
            if not my_clan:
                return

            if self.clanes[my_clan]["owner"] != user_id:
                await interaction.response.send_message(
                    "❌ Solo el líder puede configurar el salario.", ephemeral=True
                )
                return

            try:
                salary = int(nombre)
            except Exception:
                await interaction.response.send_message(
                    "⚠️ Debes especificar una cantidad válida en 'nombre'.", ephemeral=True
                )
                return

            if salary < 0:
                await interaction.response.send_message(
                    "❌ El salario no puede ser negativo.", ephemeral=True
                )
                return

            # Optional: Max salary limit based on clan level?
            max_salary = self.clanes[my_clan]["level"] * 100
            if salary > max_salary:
                await interaction.response.send_message(
                    f"❌ El salario máximo para nivel {self.clanes[my_clan]['level']} es 💰 {max_salary}.",
                    ephemeral=True,
                )
                return

            self.clanes[my_clan]["daily_salary"] = salary
            self._add_log(my_clan, f"Salario actualizado a {salary} por <@{user_id}>")
            self._save_clanes()
            await interaction.response.send_message(
                f"💸 Salario diario actualizado a **{salary}** monedas."
            )

        elif accion == "salario":
            my_clan = self._get_user_clan(interaction.user.id)
            if not my_clan:
                return

            data = self.clanes[my_clan]
            salary = data.get("daily_salary", 0)

            if salary <= 0:
                await interaction.response.send_message(
                    "❌ El líder aún no ha configurado un salario diario.", ephemeral=True
                )
                return

            last_claim = data.get("last_salary", {}).get(user_id, 0)
            if time.time() - last_claim < 86400:
                await interaction.response.send_message(
                    "⏳ Ya cobraste tu salario hoy.", ephemeral=True
                )
                return

            if data.get("bank", 0) < salary:
                await interaction.response.send_message(
                    "❌ El banco del clan está en bancarrota. No hay para salarios.", ephemeral=True
                )
                return

            data["bank"] -= salary
            if "last_salary" not in data:
                data["last_salary"] = {}
            data["last_salary"][user_id] = time.time()
            self._add_log(my_clan, f"Salario cobrado: {salary} por <@{user_id}>")

            if monedas:
                monedas.add_balance(interaction.user.id, salary)

            self._save_clanes()
            await interaction.response.send_message(
                f"� Has cobrado tu salario diario de **{salary}** monedas."
            )

        elif accion == "escudo":
            my_clan = self._get_user_clan(interaction.user.id)
            if not my_clan:
                return

            if self.clanes[my_clan]["owner"] != user_id:
                await interaction.response.send_message(
                    "❌ Solo el líder puede cambiar el escudo.", ephemeral=True
                )
                return

            if not nombre or not nombre.startswith("http"):
                await interaction.response.send_message(
                    "⚠️ Debes proporcionar una URL válida de imagen en el campo 'nombre'.",
                    ephemeral=True,
                )
                return

            self.clanes[my_clan]["logo"] = nombre
            self._save_clanes()
            await interaction.response.send_message(
                f"�️ Escudo de **{my_clan}** actualizado correctamente."
            )

        elif accion == "ranking":
            if not self.clanes:
                await interaction.response.send_message(
                    "❌ No hay Olimpos registrados.", ephemeral=True
                )
                return

            # Sort by Level (desc), then Wins (desc), then Bank (desc)
            sorted_clanes = sorted(
                self.clanes.items(),
                key=lambda x: (x[1].get("level", 1), x[1].get("wins", 0), x[1].get("bank", 0)),
                reverse=True,
            )[:10]

            embed = discord.Embed(
                title="🏆 Ranking Global de Olimpos",
                color=Theme.get_color(interaction.guild.id, "warning"),
            )

            for i, (name, data) in enumerate(sorted_clanes, 1):
                level = data.get("level", 1)
                wins = data.get("wins", 0)
                bank = data.get("bank", 0)
                members = len(data.get("members", []))

                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                embed.add_field(
                    name=f"{medal} {name}",
                    value=f"⭐ Nivel {level} | ⚔️ Victorias: {wins} | 💰 Banco: {bank} | 👥 {members} Miembros",
                    inline=False,
                )

            await interaction.response.send_message(embed=embed)

        elif accion == "registros":
            my_clan = self._get_user_clan(interaction.user.id)
            if not my_clan:
                await interaction.response.send_message(
                    "❌ No perteneces a ningún Olimpo.", ephemeral=True
                )
                return

            logs = self.clanes[my_clan].get("bank_log", [])
            if not logs:
                await interaction.response.send_message(
                    f"📜 El registro de **{my_clan}** está vacío.", ephemeral=True
                )
                return

            lines = []
            for entry in logs:
                ts = entry.get("t", 0)
                msg = entry.get("m", "???")
                # Format timestamp <t:TS:R> for relative time in Discord
                lines.append(f"• <t:{ts}:R> {msg}")

            embed = discord.Embed(
                title=f"📜 Registros de {my_clan}",
                description="\n".join(lines),
                color=Theme.get_color(interaction.guild.id, "primary"),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Clanes(bot))
