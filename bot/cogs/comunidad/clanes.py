import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import random
from typing import Optional

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

    @app_commands.command(name="clan", description="Sistema de Clanes y Olimpos")
    @app_commands.describe(
        accion="crear, unirse, info, salir, listar, expulsar, banco, guerra",
        nombre="Nombre del clan / Cantidad a depositar / Clan enemigo",
        descripcion="Descripción del clan (solo al crear)"
    )
    @app_commands.choices(accion=[
        app_commands.Choice(name="Crear Olimpo (Clan)", value="crear"),
        app_commands.Choice(name="Ver Info", value="info"),
        app_commands.Choice(name="Unirse a Olimpo", value="unirse"),
        app_commands.Choice(name="Abandonar Olimpo", value="salir"),
        app_commands.Choice(name="Listar Olimpos", value="listar"),
        app_commands.Choice(name="Banco (Depositar)", value="banco"),
        app_commands.Choice(name="Declarar Guerra", value="guerra"),
        app_commands.Choice(name="Expulsar Miembro (Líder)", value="expulsar")
    ])
    async def clan(self, interaction: discord.Interaction, accion: str, nombre: str = None, descripcion: str = None):
        user_id = str(interaction.user.id)
        
        if accion == "crear":
            if self._get_user_clan(interaction.user.id):
                await interaction.response.send_message("❌ Ya perteneces a un Olimpo. Debes salirte antes de crear uno.", ephemeral=True)
                return
            
            if not nombre:
                await interaction.response.send_message("⚠️ Debes especificar un nombre para tu Olimpo.", ephemeral=True)
                return
            
            if nombre in self.clanes:
                await interaction.response.send_message("⚠️ Ya existe un Olimpo con ese nombre.", ephemeral=True)
                return

            self.clanes[nombre] = {
                "owner": user_id,
                "description": descripcion or "Un nuevo Olimpo se alza.",
                "members": [user_id],
                "level": 1,
                "wins": 0,
                "bank": 0
            }
            self._save_clanes()
            await interaction.response.send_message(f"🏛️ **¡El Olimpo {nombre} ha sido fundado!**\nLíder: {interaction.user.mention}")

        elif accion == "info":
            target_clan = nombre if nombre else self._get_user_clan(interaction.user.id)
            if not target_clan:
                await interaction.response.send_message("❌ No estás en un clan y no especificaste ninguno.", ephemeral=True)
                return
            
            if target_clan not in self.clanes:
                await interaction.response.send_message("❌ Ese Olimpo no existe.", ephemeral=True)
                return

            data = self.clanes[target_clan]
            owner = interaction.guild.get_member(int(data["owner"]))
            owner_name = owner.display_name if owner else "Desconocido"
            
            embed = discord.Embed(title=f"🏛️ Olimpo: {target_clan}", description=data["description"], color=discord.Color.gold())
            embed.add_field(name="👑 Líder", value=owner_name, inline=True)
            embed.add_field(name="👥 Miembros", value=str(len(data["members"])), inline=True)
            embed.add_field(name="⭐ Nivel", value=str(data["level"]), inline=True)
            embed.add_field(name="🏆 Victorias", value=str(data.get("wins", 0)), inline=True)
            embed.add_field(name="💰 Tesoro", value=str(data.get("bank", 0)), inline=True)
            
            member_names = []
            for mid in data["members"][:10]: # Mostrar solo primeros 10
                m = interaction.guild.get_member(int(mid))
                if m: member_names.append(m.display_name)
            
            if len(data["members"]) > 10:
                member_names.append(f"... y {len(data['members']) - 10} más")
            
            embed.add_field(name="Lista de Miembros", value=", ".join(member_names) if member_names else "Ninguno visible", inline=False)
            await interaction.response.send_message(embed=embed)

        elif accion == "unirse":
            current_clan = self._get_user_clan(interaction.user.id)
            if current_clan:
                await interaction.response.send_message(f"❌ Ya estás en el Olimpo **{current_clan}**.", ephemeral=True)
                return
            
            if not nombre:
                await interaction.response.send_message("⚠️ Debes especificar el nombre del Olimpo al que quieres unirte.", ephemeral=True)
                return
            
            if nombre not in self.clanes:
                await interaction.response.send_message("❌ Ese Olimpo no existe.", ephemeral=True)
                return

            # En un sistema real, aquí iría una solicitud/invitación. Para simplificar, entrada libre.
            self.clanes[nombre]["members"].append(user_id)
            self._save_clanes()
            await interaction.response.send_message(f"✅ Te has unido al Olimpo **{nombre}**.")

        elif accion == "salir":
            clan_name = self._get_user_clan(interaction.user.id)
            if not clan_name:
                await interaction.response.send_message("❌ No perteneces a ningún Olimpo.", ephemeral=True)
                return
            
            clan_data = self.clanes[clan_name]
            
            if str(clan_data["owner"]) == user_id:
                # Si es el líder, disolver o transferir. Aquí disolvemos.
                del self.clanes[clan_name]
                self._save_clanes()
                await interaction.response.send_message(f"🗑️ Como eras el líder, el Olimpo **{clan_name}** ha sido disuelto.", ephemeral=True)
            else:
                if user_id in clan_data["members"]:
                    clan_data["members"].remove(user_id)
                    self._save_clanes()
                    await interaction.response.send_message(f"👋 Has abandonado el Olimpo **{clan_name}**.", ephemeral=True)

        elif accion == "listar":
            if not self.clanes:
                await interaction.response.send_message("No hay Olimpos fundados aún.", ephemeral=True)
                return
            
            txt = "**🏛️ Lista de Olimpos:**\n"
            for name, data in list(self.clanes.items())[:10]:
                txt += f"• **{name}** (Nvl {data['level']}) - 💰 {data.get('bank', 0)}\n"
            
            await interaction.response.send_message(txt)

        elif accion == "banco":
            clan_name = self._get_user_clan(interaction.user.id)
            if not clan_name:
                await interaction.response.send_message("❌ No perteneces a ningún Olimpo.", ephemeral=True)
                return
            
            try:
                amount = int(nombre) if nombre else 100
            except:
                await interaction.response.send_message("⚠️ Debes especificar una cantidad válida en 'nombre'.", ephemeral=True)
                return
            
            if amount <= 0:
                await interaction.response.send_message("❌ La cantidad debe ser positiva.", ephemeral=True)
                return

            # Aquí se debería descontar de la economía del usuario (monedas.py)
            # Como no tenemos acceso directo fácil sin DB compartida, simulamos la donación.
            
            self.clanes[clan_name]["bank"] = self.clanes[clan_name].get("bank", 0) + amount
            self._save_clanes()
            await interaction.response.send_message(f"💰 Has donado **{amount}** al tesoro de **{clan_name}**.")

        elif accion == "guerra":
            my_clan = self._get_user_clan(interaction.user.id)
            if not my_clan:
                await interaction.response.send_message("❌ No tienes clan.", ephemeral=True)
                return
            
            if self.clanes[my_clan]["owner"] != user_id:
                await interaction.response.send_message("❌ Solo el líder puede declarar guerras.", ephemeral=True)
                return
            
            enemy_clan = nombre
            if not enemy_clan or enemy_clan not in self.clanes:
                await interaction.response.send_message("⚠️ Debes especificar un clan enemigo válido en 'nombre'.", ephemeral=True)
                return
            
            if enemy_clan == my_clan:
                await interaction.response.send_message("❌ No puedes atacarte a ti mismo.", ephemeral=True)
                return

            # Simulación de batalla
            my_power = self.clanes[my_clan]["level"] * 10 + len(self.clanes[my_clan]["members"]) * 5 + random.randint(1, 20)
            enemy_power = self.clanes[enemy_clan]["level"] * 10 + len(self.clanes[enemy_clan]["members"]) * 5 + random.randint(1, 20)
            
            if my_power > enemy_power:
                winner = my_clan
                loser = enemy_clan
                loot = int(self.clanes[enemy_clan].get("bank", 0) * 0.1)
                self.clanes[enemy_clan]["bank"] -= loot
                self.clanes[my_clan]["bank"] += loot
                self.clanes[my_clan]["wins"] = self.clanes[my_clan].get("wins", 0) + 1
                msg = f"🏆 **¡VICTORIA!**\n**{my_clan}** ha derrotado a **{enemy_clan}**.\nBotín robado: 💰 {loot}"
            else:
                winner = enemy_clan
                loser = my_clan
                self.clanes[enemy_clan]["wins"] = self.clanes[enemy_clan].get("wins", 0) + 1
                msg = f"💀 **DERROTA...**\n**{enemy_clan}** ha defendido su honor y vencido a **{my_clan}**."
            
            self._save_clanes()
            await interaction.response.send_message(msg)

        elif accion == "expulsar":
            # Requiere nombre de usuario o mención, pero aquí usamos string nombre como ID o nombre para simplificar
            # Mejor pedir mención en una v2.
            await interaction.response.send_message("⚠️ Función en desarrollo. Pide al miembro que salga por su cuenta.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Clanes(bot))
