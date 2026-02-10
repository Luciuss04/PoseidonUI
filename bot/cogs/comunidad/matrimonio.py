import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import time
import random
from datetime import datetime
from bot.themes import Theme

class Matrimonio(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_file = "matrimonios.json"
        self.data = self._load_data()
        self.proposals = {} # {target_id: proposer_id} - En memoria volátil

    def _load_data(self):
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_data(self):
        with open(self.db_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def _get_partner(self, user_id):
        uid = str(user_id)
        if uid in self.data:
            return self.data[uid]["partner"]
        # Buscar inversamente por si acaso
        for u, d in self.data.items():
            if str(d["partner"]) == uid:
                return u
        return None

    @app_commands.command(name="love", description="Sistema de Matrimonios y Vínculos")
    @app_commands.describe(
        accion="Acción a realizar",
        objetivo="Usuario objetivo (para propuestas/interacciones/ship)",
        texto="Nombre (hijo/anillo), Cantidad (banco) o Tipo (besar/cita)"
    )
    @app_commands.choices(accion=[
        app_commands.Choice(name="Proponer Matrimonio", value="proponer"),
        app_commands.Choice(name="Aceptar Propuesta", value="aceptar"),
        app_commands.Choice(name="Divorciarse", value="divorcio"),
        app_commands.Choice(name="Ver Estado (Info)", value="info"),
        app_commands.Choice(name="Comprar Anillo", value="anillo"),
        app_commands.Choice(name="Adoptar Hijo (NPC)", value="adoptar"),
        app_commands.Choice(name="Interactuar (Amor)", value="interactuar"),
        app_commands.Choice(name="Cuenta Conjunta", value="banco"),
        app_commands.Choice(name="Ship (Compatibilidad)", value="ship")
    ])
    async def love(self, interaction: discord.Interaction, accion: str, objetivo: discord.User = None, texto: str = None):
        user_id = str(interaction.user.id)
        monedas = self.bot.get_cog("Monedas")
        
        if accion == "proponer":
            if not objetivo:
                await interaction.response.send_message("⚠️ Debes mencionar a quien quieres proponerle matrimonio.", ephemeral=True)
                return
            
            target_id = str(objetivo.id)
            if target_id == user_id:
                await interaction.response.send_message("❌ No puedes casarte contigo mismo.", ephemeral=True)
                return
            
            if objetivo.bot:
                await interaction.response.send_message("❌ No puedes casarte con un bot.", ephemeral=True)
                return
            
            if self._get_partner(user_id):
                await interaction.response.send_message("❌ ¡Ya estás casado!", ephemeral=True)
                return
            
            if self._get_partner(target_id):
                await interaction.response.send_message(f"❌ **{objetivo.display_name}** ya está casado.", ephemeral=True)
                return
            
            self.proposals[target_id] = user_id
            await interaction.response.send_message(f"💍 **{interaction.user.mention}** le ha propuesto matrimonio a **{objetivo.mention}**.\nUsa `/love aceptar` para decir que sí.")

        elif accion == "aceptar":
            if user_id not in self.proposals:
                await interaction.response.send_message("😢 Nadie te ha propuesto matrimonio recientemente.", ephemeral=True)
                return
            
            proposer_id = self.proposals[user_id]
            if self._get_partner(proposer_id):
                 await interaction.response.send_message("❌ El proponente ya se casó con alguien más.", ephemeral=True)
                 del self.proposals[user_id]
                 return

            # Datos iniciales
            match_data = {
                "partner": proposer_id,
                "date": time.time(),
                "ring": "Anillo de Hojalata",
                "children": [],
                "love_points": 0,
                "bank": 0,
                "last_interact": 0
            }
            
            self.data[user_id] = match_data
            self.data[proposer_id] = {
                "partner": user_id,
                "date": time.time(),
                "ring": "Anillo de Hojalata",
                "children": [],
                "love_points": 0,
                "bank": 0, # Shared logic needs synch, but here we just copy. 
                           # BETTER: One source of truth. But current struct is separate.
                           # We will sync updates manually for now.
                "last_interact": 0
            }
            
            del self.proposals[user_id]
            self._save_data()
            
            embed = discord.Embed(title="💒 ¡VIVAN LOS NOVIOS! 💒", description=f"**{interaction.user.mention}** y **<@{proposer_id}>** han unido sus vidas en sagrado matrimonio.", color=Theme.get_color(interaction.guild.id, 'primary'))
            embed.add_field(name="💍 Anillo Inicial", value="Anillo de Hojalata", inline=True)
            embed.add_field(name="📅 Fecha", value=f"<t:{int(time.time())}:D>", inline=True)
            embed.set_footer(text=f"{Theme.get_footer_text(interaction.guild.id)} • ¡Que el amor perdure para siempre!")
            
            await interaction.response.send_message(embed=embed)

        elif accion == "divorcio":
            partner_id = self._get_partner(user_id)
            if not partner_id:
                await interaction.response.send_message("❌ No estás casado.", ephemeral=True)
                return
            
            # Split bank
            if user_id in self.data:
                money = self.data[user_id].get("bank", 0)
                if money > 0 and monedas:
                    half = money // 2
                    monedas.add_balance(int(user_id), half)
                    monedas.add_balance(int(partner_id), half)
                
                del self.data[user_id]
            
            if str(partner_id) in self.data: del self.data[str(partner_id)]
            
            self._save_data()
            await interaction.response.send_message(f"💔 **{interaction.user.mention}** se ha divorciado. El dinero conjunto se ha repartido.")

        elif accion == "info":
            target = objetivo if objetivo else interaction.user
            target_id = str(target.id)
            
            if target_id not in self.data:
                await interaction.response.send_message(f"ℹ️ **{target.display_name}** está soltero/a.", ephemeral=True)
                return

            data = self.data[target_id]
            partner_id = data["partner"]
            partner_obj = interaction.guild.get_member(int(partner_id))
            partner_name = partner_obj.display_name if partner_obj else "Desconocido"
            
            days = int((time.time() - data["date"]) / 86400)
            
            embed = discord.Embed(title=f"💖 Estado Civil de {target.display_name}", color=Theme.get_color(interaction.guild.id, 'secondary'))
            embed.add_field(name="💍 Cónyuge", value=partner_name, inline=True)
            embed.add_field(name="📅 Tiempo juntos", value=f"{days} días", inline=True)
            embed.add_field(name="💗 Puntos de Amor", value=str(data.get("love_points", 0)), inline=True)
            embed.add_field(name="💰 Cuenta Conjunta", value=str(data.get("bank", 0)), inline=True)
            embed.add_field(name="💎 Anillo", value=data.get("ring", "Ninguno"), inline=True)
            
            children = data.get("children", [])
            if children:
                embed.add_field(name="👶 Hijos", value=", ".join(children), inline=False)
            
            await interaction.response.send_message(embed=embed)

        elif accion == "anillo":
            if not self._get_partner(user_id):
                await interaction.response.send_message("❌ Cásate primero.", ephemeral=True)
                return
            
            if not texto:
                await interaction.response.send_message("⚠️ Especifica el nombre del anillo en 'texto'.", ephemeral=True)
                return
            
            cost = 1000
            if monedas:
                if not monedas.remove_balance(interaction.user.id, cost):
                     await interaction.response.send_message(f"❌ Un nuevo anillo cuesta 💰 {cost}.", ephemeral=True)
                     return

            self.data[user_id]["ring"] = texto
            partner_id = self.data[user_id]["partner"]
            if str(partner_id) in self.data:
                self.data[str(partner_id)]["ring"] = texto
            
            self._save_data()
            await interaction.response.send_message(f"💎 Has comprado un **{texto}** por 💰 {cost}.")

        elif accion == "adoptar":
            if not self._get_partner(user_id):
                await interaction.response.send_message("❌ Debes estar casado.", ephemeral=True)
                return
            
            if not texto:
                await interaction.response.send_message("⚠️ Especifica el nombre de tu hijo/a en 'texto'.", ephemeral=True)
                return
            
            cost = 2000
            if monedas:
                 if not monedas.remove_balance(interaction.user.id, cost):
                     await interaction.response.send_message(f"❌ La adopción cuesta 💰 {cost}.", ephemeral=True)
                     return

            if "children" not in self.data[user_id]: self.data[user_id]["children"] = []
            self.data[user_id]["children"].append(texto)
            
            partner_id = self.data[user_id]["partner"]
            if str(partner_id) in self.data:
                if "children" not in self.data[str(partner_id)]: self.data[str(partner_id)]["children"] = []
                self.data[str(partner_id)]["children"].append(texto)
            
            self._save_data()
            await interaction.response.send_message(f"👶 ¡Felicidades! **{texto}** ahora es parte de la familia (Coste: 💰 {cost}).")

        elif accion == "interactuar":
            if not self._get_partner(user_id):
                await interaction.response.send_message("❌ Necesitas pareja para esto.", ephemeral=True)
                return
            
            tipo = texto.lower() if texto else ""
            validos = ["besar", "abrazar", "cita"]
            
            if tipo not in validos:
                await interaction.response.send_message("⚠️ Tipos válidos en 'texto': besar, abrazar, cita", ephemeral=True)
                return
            
            data = self.data[user_id]
            last = data.get("last_interact", 0)
            now = time.time()
            
            # Cooldown global de 5 min para no spamear
            if now - last < 300:
                await interaction.response.send_message("⏳ ¡Hey, tranquilos! Esperen unos minutos.", ephemeral=True)
                return
            
            points = 0
            msg = ""
            
            if tipo == "besar":
                points = 5
                msg = f"💋 **{interaction.user.display_name}** besó apasionadamente a su pareja. (+5 Amor)"
            elif tipo == "abrazar":
                points = 2
                msg = f"🤗 **{interaction.user.display_name}** le dio un cálido abrazo a su pareja. (+2 Amor)"
            elif tipo == "cita":
                cost = 200
                if monedas:
                    if not monedas.remove_balance(interaction.user.id, cost):
                        await interaction.response.send_message(f"❌ Una cita cuesta 💰 {cost}.", ephemeral=True)
                        return
                points = 50
                msg = f"🍷 **{interaction.user.display_name}** llevó a su pareja a una cita romántica. (+50 Amor)"

            # Sync points
            data["love_points"] = data.get("love_points", 0) + points
            data["last_interact"] = now
            
            pid = str(data["partner"])
            if pid in self.data:
                self.data[pid]["love_points"] = data["love_points"]
                self.data[pid]["last_interact"] = now
            
            self._save_data()
            await interaction.response.send_message(msg)

        elif accion == "banco":
            if not self._get_partner(user_id): return
            
            try:
                amount = int(texto) if texto else 0
            except:
                await interaction.response.send_message("⚠️ Ingresa la cantidad en 'texto'.", ephemeral=True)
                return
            
            if amount == 0:
                await interaction.response.send_message(f"💰 Saldo conjunto: {self.data[user_id].get('bank', 0)}", ephemeral=True)
                return
            
            # Si amount > 0 depositar, si < 0 retirar
            if amount > 0:
                if monedas:
                    if not monedas.remove_balance(interaction.user.id, amount):
                        await interaction.response.send_message("❌ No tienes suficiente dinero.", ephemeral=True)
                        return
                
                self.data[user_id]["bank"] = self.data[user_id].get("bank", 0) + amount
                pid = str(self.data[user_id]["partner"])
                if pid in self.data: self.data[pid]["bank"] = self.data[user_id]["bank"]
                
                self._save_data()
                await interaction.response.send_message(f"💰 Depositaste {amount} en la cuenta conjunta.")
            else:
                withdraw = abs(amount)
                current = self.data[user_id].get("bank", 0)
                if current < withdraw:
                    await interaction.response.send_message("❌ No hay suficientes fondos en la cuenta conjunta.", ephemeral=True)
                    return
                
                self.data[user_id]["bank"] = current - withdraw
                pid = str(self.data[user_id]["partner"])
                if pid in self.data: self.data[pid]["bank"] = self.data[user_id]["bank"]
                
                if monedas: monedas.add_balance(interaction.user.id, withdraw)
                
                self._save_data()
                await interaction.response.send_message(f"💸 Retiraste {withdraw} de la cuenta conjunta.")

        elif accion == "ship":
            if not objetivo:
                await interaction.response.send_message("⚠️ Menciona a alguien para calcular compatibilidad.", ephemeral=True)
                return
            
            target_id = str(objetivo.id)
            if target_id == user_id:
                percentage = 100
                msg = "💖 ¡El amor propio es lo más importante!"
            else:
                # Deterministic percentage based on day
                day_seed = int(time.strftime("%j")) # Day of year 1-366
                seed = int(user_id) + int(target_id) + day_seed
                random.seed(seed)
                percentage = random.randint(0, 100)
                random.seed() # Reset seed
                
                if percentage >= 90: msg = "🔥 ¡Es el destino! Almas gemelas."
                elif percentage >= 70: msg = "❤️ Hay mucha química aquí."
                elif percentage >= 40: msg = "🤔 Podría funcionar con esfuerzo."
                else: msg = "❄️ Mejor sean solo amigos..."
            
            # Progress bar
            blocks = percentage // 10
            bar = "🟥" * blocks + "⬜" * (10 - blocks)
            
            embed = discord.Embed(title="🔮 Compatibilidad Amorosa", description=f"{interaction.user.mention} ❤️ {objetivo.mention}", color=Theme.get_color(interaction.guild.id, 'secondary'))
            embed.add_field(name=f"{percentage}% {bar}", value=msg)
            await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Matrimonio(bot))
