import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import time
from datetime import datetime

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
        accion="proponer, aceptar, divorcio, info, anillo, adoptar",
        usuario="Usuario objetivo (para proponer/adoptar)",
        extra="Nombre del anillo o hijo"
    )
    @app_commands.choices(accion=[
        app_commands.Choice(name="Proponer Matrimonio", value="proponer"),
        app_commands.Choice(name="Aceptar Propuesta", value="aceptar"),
        app_commands.Choice(name="Divorciarse", value="divorcio"),
        app_commands.Choice(name="Ver Estado (Info)", value="info"),
        app_commands.Choice(name="Comprar Anillo", value="anillo"),
        app_commands.Choice(name="Adoptar Hijo (NPC)", value="adoptar")
    ])
    async def love(self, interaction: discord.Interaction, accion: str, usuario: discord.User = None, extra: str = None):
        user_id = str(interaction.user.id)
        
        if accion == "proponer":
            if not usuario:
                await interaction.response.send_message("⚠️ Debes mencionar a quien quieres proponerle matrimonio.", ephemeral=True)
                return
            
            target_id = str(usuario.id)
            if target_id == user_id:
                await interaction.response.send_message("❌ No puedes casarte contigo mismo (aunque te quieras mucho).", ephemeral=True)
                return
            
            if usuario.bot:
                await interaction.response.send_message("❌ No puedes casarte con un bot.", ephemeral=True)
                return

            if self._get_partner(user_id):
                await interaction.response.send_message("❌ ¡Ya estás casado! Infiel...", ephemeral=True)
                return
            
            if self._get_partner(target_id):
                await interaction.response.send_message(f"❌ **{usuario.display_name}** ya está casado con otra persona.", ephemeral=True)
                return
            
            self.proposals[target_id] = user_id
            await interaction.response.send_message(f"💍 **{interaction.user.mention}** le ha propuesto matrimonio a **{usuario.mention}**.\nUsa `/love aceptar` para decir que sí.")

        elif accion == "aceptar":
            if user_id not in self.proposals:
                await interaction.response.send_message("😢 Nadie te ha propuesto matrimonio recientemente.", ephemeral=True)
                return
            
            proposer_id = self.proposals[user_id]
            # Verificar que el proponente no se haya casado mientras tanto
            if self._get_partner(proposer_id):
                 await interaction.response.send_message("❌ El proponente ya se casó con alguien más. ¡Qué rápido!", ephemeral=True)
                 del self.proposals[user_id]
                 return

            # Crear vínculo
            match_data = {
                "partner": proposer_id,
                "date": time.time(),
                "ring": "Anillo de Hojalata",
                "children": [],
                "level": 1
            }
            # Guardamos para ambos (o referencia cruzada).
            # Simplificación: Guardamos entrada para ambos apuntando al otro.
            self.data[user_id] = match_data
            self.data[proposer_id] = {
                "partner": user_id,
                "date": time.time(),
                "ring": "Anillo de Hojalata",
                "children": [],
                "level": 1
            }
            
            del self.proposals[user_id]
            self._save_data()
            
            await interaction.response.send_message(f"💒 **¡VIVAN LOS NOVIOS!** 💒\n<@{user_id}> y <@{proposer_id}> ahora están casados.")

        elif accion == "divorcio":
            partner_id = self._get_partner(user_id)
            if not partner_id:
                await interaction.response.send_message("❌ No estás casado.", ephemeral=True)
                return
            
            # Borrar datos de ambos
            if user_id in self.data: del self.data[user_id]
            if str(partner_id) in self.data: del self.data[str(partner_id)]
            
            self._save_data()
            await interaction.response.send_message(f"💔 **{interaction.user.mention}** se ha divorciado. El amor ha muerto.")

        elif accion == "info":
            # Ver info propia o del usuario mencionado
            target = usuario if usuario else interaction.user
            target_id = str(target.id)
            
            if target_id not in self.data:
                partner_id = self._get_partner(target_id) # Intento búsqueda inversa
                if not partner_id:
                    await interaction.response.send_message(f"ℹ️ **{target.display_name}** está soltero/a.", ephemeral=True)
                    return
                # Si encontramos partner pero no entrada directa (caso raro si borramos simétrico), recuperamos
                data = self.data[str(partner_id)] # Usamos la data del partner
            else:
                data = self.data[target_id]
                partner_id = data["partner"]

            partner_obj = interaction.guild.get_member(int(partner_id))
            partner_name = partner_obj.display_name if partner_obj else "Desconocido"
            
            days = int((time.time() - data["date"]) / 86400)
            
            embed = discord.Embed(title=f"💖 Estado Civil de {target.display_name}", color=discord.Color.pink())
            embed.add_field(name="💍 Cónyuge", value=partner_name, inline=True)
            embed.add_field(name="📅 Tiempo juntos", value=f"{days} días", inline=True)
            embed.add_field(name="💎 Anillo", value=data.get("ring", "Ninguno"), inline=True)
            
            children = data.get("children", [])
            if children:
                embed.add_field(name="👶 Hijos", value=", ".join(children), inline=False)
            
            await interaction.response.send_message(embed=embed)

        elif accion == "anillo":
            if not self._get_partner(user_id):
                await interaction.response.send_message("❌ Cásate primero antes de comprar anillos.", ephemeral=True)
                return
            
            if not extra:
                await interaction.response.send_message("⚠️ Especifica el nombre del nuevo anillo en 'extra'.", ephemeral=True)
                return
            
            # Aquí se cobraría dinero
            self.data[user_id]["ring"] = extra
            partner_id = self.data[user_id]["partner"]
            if str(partner_id) in self.data:
                self.data[str(partner_id)]["ring"] = extra # Comparten anillo visualmente
            
            self._save_data()
            await interaction.response.send_message(f"💎 Has actualizado vuestro anillo a: **{extra}**.")

        elif accion == "adoptar":
            if not self._get_partner(user_id):
                await interaction.response.send_message("❌ Debes estar casado para adoptar (por ahora).", ephemeral=True)
                return
            
            if not extra:
                await interaction.response.send_message("⚠️ Especifica el nombre de tu hijo/a en 'extra'.", ephemeral=True)
                return
            
            # Añadir hijo a ambos
            if "children" not in self.data[user_id]: self.data[user_id]["children"] = []
            self.data[user_id]["children"].append(extra)
            
            partner_id = self.data[user_id]["partner"]
            if str(partner_id) in self.data:
                if "children" not in self.data[str(partner_id)]: self.data[str(partner_id)]["children"] = []
                self.data[str(partner_id)]["children"].append(extra)
            
            self._save_data()
            await interaction.response.send_message(f"👶 ¡Felicidades! **{extra}** ahora es parte de la familia.")

async def setup(bot: commands.Bot):
    await bot.add_cog(Matrimonio(bot))
