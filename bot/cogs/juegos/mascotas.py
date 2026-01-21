import discord
from discord import app_commands
from discord.ext import commands
import random
import time

class Mascotas(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Estructura simple en memoria: {user_id: {"name": str, "type": str, "level": int, "xp": int, "hunger": int, "happiness": int, "last_feed": float}}
        # En un bot real, esto iría a base de datos.
        self.pets = {}
        
        self.pet_types = {
            "perro": {"emoji": "🐶", "desc": "Un compañero leal.", "food": "Hueso"},
            "gato": {"emoji": "🐱", "desc": "Independiente pero cariñoso.", "food": "Pescado"},
            "dragon": {"emoji": "🐲", "desc": "Mítico y poderoso.", "food": "Gemas"},
            "robot": {"emoji": "🤖", "desc": "El futuro es hoy.", "food": "Baterías"},
            "hamster": {"emoji": "🐹", "desc": "Pequeño y veloz.", "food": "Semillas"}
        }

    def _get_pet(self, user_id):
        return self.pets.get(user_id)

    def _save_pet(self, user_id, pet_data):
        self.pets[user_id] = pet_data

    @app_commands.command(name="mascota", description="Sistema de mascotas virtuales")
    @app_commands.describe(accion="adoptar, ver, alimentar, jugar, liberar", nombre="Nombre para tu mascota (solo al adoptar)", tipo="Tipo de mascota (solo al adoptar)")
    @app_commands.choices(tipo=[
        app_commands.Choice(name="Perro 🐶", value="perro"),
        app_commands.Choice(name="Gato 🐱", value="gato"),
        app_commands.Choice(name="Dragón 🐲", value="dragon"),
        app_commands.Choice(name="Robot 🤖", value="robot"),
        app_commands.Choice(name="Hámster 🐹", value="hamster")
    ])
    @app_commands.choices(accion=[
        app_commands.Choice(name="Ver estado", value="ver"),
        app_commands.Choice(name="Adoptar nueva", value="adoptar"),
        app_commands.Choice(name="Alimentar", value="alimentar"),
        app_commands.Choice(name="Jugar", value="jugar"),
        app_commands.Choice(name="Entrenar (XP)", value="entrenar"),
        app_commands.Choice(name="Dormir (Recuperar)", value="dormir"),
        app_commands.Choice(name="Liberar (Borrar)", value="liberar")
    ])
    async def mascota(self, interaction: discord.Interaction, accion: str, nombre: str = None, tipo: str = None):
        user_id = interaction.user.id
        pet = self._get_pet(user_id)

        if accion == "adoptar":
            if pet:
                await interaction.response.send_message("❌ Ya tienes una mascota. Usa `/mascota liberar` si quieres otra.", ephemeral=True)
                return
            
            if not tipo or not nombre:
                await interaction.response.send_message("⚠️ Debes especificar un `tipo` y un `nombre` para adoptar.", ephemeral=True)
                return

            self._save_pet(user_id, {
                "name": nombre,
                "type": tipo,
                "level": 1,
                "xp": 0,
                "hunger": 100, # 100 = lleno, 0 = hambriento
                "happiness": 100,
                "energy": 100,
                "last_interaction": time.time()
            })
            
            info = self.pet_types.get(tipo, {"emoji": "❓"})
            await interaction.response.send_message(f"🎉 ¡Felicidades! Has adoptado a **{nombre}** el {info['emoji']} ({tipo}).")

        elif accion == "ver":
            if not pet:
                await interaction.response.send_message("😢 No tienes mascota. Usa `/mascota adoptar`.", ephemeral=True)
                return
            
            info = self.pet_types.get(pet["type"], {"emoji": "❓"})
            
            # Ensure energy exists for old pets
            if "energy" not in pet: pet["energy"] = 100
            
            embed = discord.Embed(title=f"Estado de {pet['name']} {info['emoji']}", color=discord.Color.green())
            embed.add_field(name="Nivel", value=str(pet['level']), inline=True)
            embed.add_field(name="Experiencia", value=f"{pet['xp']}/100", inline=True)
            
            # Barras visuales
            h_bar = "🍖" * (pet['hunger'] // 10) + "⚫" * ((100 - pet['hunger']) // 10)
            hap_bar = "❤️" * (pet['happiness'] // 10) + "⚫" * ((100 - pet['happiness']) // 10)
            en_bar = "⚡" * (pet['energy'] // 10) + "⚫" * ((100 - pet['energy']) // 10)
            
            embed.add_field(name="Hambre", value=f"{pet['hunger']}%\n{h_bar}", inline=False)
            embed.add_field(name="Felicidad", value=f"{pet['happiness']}%\n{hap_bar}", inline=False)
            embed.add_field(name="Energía", value=f"{pet['energy']}%\n{en_bar}", inline=False)
            embed.set_footer(text=f"Tipo: {pet['type'].capitalize()}")
            
            await interaction.response.send_message(embed=embed)

        elif accion == "alimentar":
            if not pet:
                await interaction.response.send_message("😢 No tienes mascota.", ephemeral=True)
                return
            
            if pet['hunger'] >= 100:
                await interaction.response.send_message(f"🤢 **{pet['name']}** está llenísimo. No quiere comer más.", ephemeral=True)
                return
            
            pet['hunger'] = min(100, pet['hunger'] + 20)
            pet['xp'] += 5
            if "energy" not in pet: pet["energy"] = 100
            pet['energy'] = min(100, pet['energy'] + 5)
            
            self._save_pet(user_id, pet)
            
            info = self.pet_types.get(pet["type"], {"emoji": "❓"})
            await interaction.response.send_message(f"😋 Le diste de comer a **{pet['name']}**. ¡Se ve feliz! (+5 XP)")

        elif accion == "jugar":
            if not pet:
                await interaction.response.send_message("😢 No tienes mascota.", ephemeral=True)
                return
            
            if pet['hunger'] < 20:
                await interaction.response.send_message(f"😟 **{pet['name']}** tiene mucha hambre para jugar. Aliméntalo primero.", ephemeral=True)
                return
            
            if "energy" not in pet: pet["energy"] = 100
            if pet['energy'] < 10:
                await interaction.response.send_message(f"😴 **{pet['name']}** está muy cansado. Déjalo dormir un poco.", ephemeral=True)
                return

            pet['happiness'] = min(100, pet['happiness'] + 15)
            pet['hunger'] -= 10
            pet['energy'] -= 10
            pet['xp'] += 10
            
            # Level up check
            msg_extra = ""
            if pet['xp'] >= 100:
                pet['level'] += 1
                pet['xp'] = 0
                msg_extra = f"\n🆙 **¡SUBIÓ DE NIVEL!** Ahora es nivel {pet['level']}."
            
            self._save_pet(user_id, pet)
            await interaction.response.send_message(f"🎾 Jugaste con **{pet['name']}**. ¡Se divirtió mucho! (+10 XP){msg_extra}")

        elif accion == "entrenar":
            if not pet:
                await interaction.response.send_message("😢 No tienes mascota.", ephemeral=True)
                return
            
            if "energy" not in pet: pet["energy"] = 100
            if pet['energy'] < 30:
                await interaction.response.send_message(f"😴 **{pet['name']}** está demasiado cansado para entrenar.", ephemeral=True)
                return
            
            if pet['hunger'] < 30:
                await interaction.response.send_message(f"😟 **{pet['name']}** tiene hambre. No puede entrenar bien.", ephemeral=True)
                return

            pet['energy'] -= 30
            pet['hunger'] -= 20
            pet['xp'] += 25 # Más XP que jugar
            
            msg_extra = ""
            if pet['xp'] >= 100:
                pet['level'] += 1
                pet['xp'] = 0
                msg_extra = f"\n🆙 **¡SUBIÓ DE NIVEL!** Ahora es nivel {pet['level']}."
            
            self._save_pet(user_id, pet)
            await interaction.response.send_message(f"🏋️ **{pet['name']}** ha entrenado duro. ¡Se vuelve más fuerte! (+25 XP){msg_extra}")

        elif accion == "dormir":
            if not pet:
                await interaction.response.send_message("😢 No tienes mascota.", ephemeral=True)
                return
            
            if "energy" not in pet: pet["energy"] = 100
            if pet['energy'] >= 90:
                await interaction.response.send_message(f"👀 **{pet['name']}** no tiene sueño.", ephemeral=True)
                return
            
            pet['energy'] = 100
            pet['hunger'] -= 10 # Dormir da hambre al despertar
            pet['happiness'] += 5
            
            self._save_pet(user_id, pet)
            await interaction.response.send_message(f"💤 **{pet['name']}** ha dormido una siesta reparadora. ¡Energía al máximo!")


        elif accion == "liberar":
            if not pet:
                await interaction.response.send_message("No tienes mascota para liberar.", ephemeral=True)
                return
            
            del self.pets[user_id]
            await interaction.response.send_message(f"👋 Has liberado a tu mascota. Esperamos que encuentre un buen hogar.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Mascotas(bot))
