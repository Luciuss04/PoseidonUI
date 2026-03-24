import json
import os
import random
import time

import discord
from discord import app_commands
from discord.ext import commands

from bot.themes import Theme


class BattleView(discord.ui.View):
    def __init__(self, bot, user, pet, enemy_stats, stake, cog):
        super().__init__(timeout=120)
        self.bot = bot
        self.user = user
        self.pet = pet
        self.enemy = enemy_stats
        self.stake = stake
        self.cog = cog
        self.finished = False

        # Cargar datos base
        self.p_info = self.cog.pet_types.get(self.pet['type'], {})
        self.e_info = self.cog.pet_types.get(self.enemy['type'], {})

        # Calcular Stats
        # HP = (Nivel * 20) + (Defensa * 5)
        self.p_max_hp = (self.pet['level'] * 20) + (self.p_info.get('defense', 5) * 5)
        self.p_hp = self.p_max_hp
        self.p_energy = 100
        
        self.e_max_hp = (self.enemy['level'] * 20) + (self.e_info.get('defense', 5) * 5)
        self.e_hp = self.e_max_hp
        
        self.logs = [f"⚔️ **{self.pet['name']}** vs **{self.enemy['name']}**"]

    def _get_element_multiplier(self, atk_elem, def_elem):
        # Tabla simple de elementos
        weaknesses = {
            "fuego": "agua", "agua": "electrico", "electrico": "tierra", "tierra": "fuego",
            "viento": "hielo", "hielo": "fuego", "luz": "oscuridad", "oscuridad": "luz"
        }
        if weaknesses.get(def_elem) == atk_elem:
            return 1.5 # Super efectivo
        if weaknesses.get(atk_elem) == def_elem:
            return 0.5 # Poco efectivo
        return 1.0

    async def update_embed(self, interaction, final=False):
        color = Theme.get_color(interaction.guild.id, 'error' if final and self.p_hp <= 0 else 'success')
        
        # --- MEJORA VISUAL 2026 ---
        def make_bar(cur, max_v, color_emoji="🟩"):
            pct = max(0, min(1, cur / max_v))
            filled = int(pct * 10)
            bar = color_emoji * filled + "⬛" * (10 - filled)
            return f"`{bar}` {int(pct*100)}%"

        p_elem_icon = self.p_info.get('emoji_elem', '⚪')
        e_elem_icon = self.e_info.get('emoji_elem', '⚪')
        
        # Log formateado
        log_text = ""
        for l in self.logs[-4:]:
            if "atacó" in l: log_text += f"💢 {l}\n"
            elif "curó" in l: log_text += f"💚 {l}\n"
            elif "CRÍTICO" in l: log_text += f"🔥 **{l}**\n"
            else: log_text += f"{l}\n"

        embed = discord.Embed(
            title="🏟️ El Coliseo de Atenea", 
            description=f"```fix\nFase de Combate\n```\n{log_text}", 
            color=color
        )
        
        # Layout de batalla
        p_stats = f"❤️ HP: {make_bar(self.p_hp, self.p_max_hp, '🟩')}\n⚡ EN: {make_bar(self.p_energy, 100, '🟦')}"
        e_stats = f"❤️ HP: {make_bar(self.e_hp, self.e_max_hp, '🟥')}\n🤖 IA Nvl: {self.enemy['level']}"

        embed.add_field(
            name=f"{self.p_info['emoji']} {self.pet['name']} {p_elem_icon}",
            value=p_stats,
            inline=False
        )
        embed.add_field(
            name="⚡ VS ⚡", 
            value=f"**{self.enemy['name']}** {e_elem_icon}", 
            inline=False
        )
        embed.add_field(
            name=f"Estadísticas del Oponente",
            value=e_stats,
            inline=False
        )

        if final:
            self.stop()
            self.clear_items()
            if self.p_hp > 0:
                embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1425781431682076682/1440115588746706984/Imagen_para_el_bot_d.png")
            else:
                embed.set_footer(text="¡Derrota en el Coliseo! Entrena más a tu mascota.")
        else:
            embed.set_footer(text=f"Turno de: {self.user.display_name} • Usa tus habilidades sabiamente")

        if interaction.response.is_done():
            await interaction.message.edit(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    async def enemy_turn(self, interaction):
        if self.e_hp <= 0:
            return

        # IA Simple
        action = "attack"
        if self.e_hp < self.e_max_hp * 0.3 and random.random() < 0.3:
            action = "heal"
        
        msg = ""
        
        if action == "heal":
            heal = int(self.e_max_hp * 0.2)
            self.e_hp = min(self.e_max_hp, self.e_hp + heal)
            msg = f"🩹 **{self.enemy['name']}** se curó {heal} HP."
        else:
            # Attack
            base_dmg = self.e_info.get('attack', 10) + (self.enemy['level'] * 2)
            mult = self._get_element_multiplier(self.e_info.get('element', 'normal'), self.p_info.get('element', 'normal'))
            final_dmg = int(base_dmg * mult * random.uniform(0.8, 1.2))
            
            self.p_hp -= final_dmg
            eff_text = "💥" if mult > 1 else ("🛡️" if mult < 1 else "⚔️")
            msg = f"{eff_text} **{self.enemy['name']}** atacó: -{final_dmg} HP"
            if mult > 1:
                msg += " (¡Super efectivo!)"

        self.logs.append(msg)
        
        if self.p_hp <= 0:
            self.p_hp = 0
            self.logs.append(f"💀 **{self.pet['name']}** cayó debilitado...")
            
            # Penalización
            self.pet['losses'] = self.pet.get('losses', 0) + 1
            self.pet['happiness'] = max(0, self.pet['happiness'] - 10)
            self.cog._save_pet(self.user.id, self.pet)
            
            self.logs.append(f"💸 Perdiste la apuesta de {self.stake}.")
            await self.update_embed(interaction, final=True)
        else:
            await self.update_embed(interaction)

    async def _handle_victory(self, interaction):
        self.e_hp = 0
        self.logs.append(f"🏆 **¡{self.enemy['name']}** fue derrotado!")
        
        # Recompensa
        monedas = self.bot.get_cog("Monedas")
        winnings = self.stake * 2
        if monedas and self.stake > 0:
            monedas.add_balance(self.user.id, winnings)
            self.logs.append(f"💰 Ganaste {winnings} monedas.")
        
        xp_gain = 30 + (self.enemy['level'] * 5)
        xp_msg = self.cog._add_xp(self.pet, xp_gain)
        self.pet['wins'] = self.pet.get('wins', 0) + 1
        self.logs.append(f"🌟 Ganaste {xp_gain} XP.{xp_msg}")
        
        self.cog._save_pet(self.user.id, self.pet)
        await self.update_embed(interaction, final=True)

    @discord.ui.button(label="Atacar", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def attack(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            return
        
        base_dmg = self.p_info.get('attack', 10) + (self.pet['level'] * 2)
        mult = self._get_element_multiplier(self.p_info.get('element', 'normal'), self.e_info.get('element', 'normal'))
        
        # Crítico con animación
        is_crit = random.random() < 0.15 # 15% crit
        crit = 1.7 if is_crit else 1.0
        
        final_dmg = int(base_dmg * mult * crit * random.uniform(0.9, 1.1))
        self.e_hp -= final_dmg
        
        msg = f"⚔️ **{self.pet['name']}** atacó: -{final_dmg} HP"
        if is_crit:
            msg = f"🔥 **CRÍTICO DIVINO** 🔥 {msg}"
        elif mult > 1:
            msg += " (¡Efectivo!)"
        
        self.logs.append(msg)
        self.p_energy = min(100, self.p_energy + 15) # Recuperar más energía
        
        if self.e_hp <= 0:
            await self._handle_victory(interaction)
        else:
            await self.enemy_turn(interaction)

    @discord.ui.button(label="Especial (-40⚡)", style=discord.ButtonStyle.primary, emoji="✨")
    async def special(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            return
        
        if self.p_energy < 40:
            await interaction.response.send_message("⚠️ No tienes suficiente energía (40).", ephemeral=True)
            return
            
        self.p_energy -= 40
        
        # Nombre de habilidad especial según tipo
        habilidades = {
            "dragon": "🔥 Aliento de Fuego",
            "robot": "⚡ Descarga Voltáica",
            "fantasma": "🌑 Pesadilla Eterna",
            "alien": "🛸 Abducción Cuántica",
            "slime": "💧 Explosión Ácida",
            "dinosaurio": "🦖 Mordisco Ancestral",
            "unicornio": "✨ Rayo Purificador"
        }
        skill_name = habilidades.get(self.pet['type'], "✨ Ataque Especial")

        base_dmg = (self.p_info.get('attack', 10) * 1.6) + (self.pet['level'] * 3)
        mult = self._get_element_multiplier(self.p_info.get('element', 'normal'), self.e_info.get('element', 'normal'))
        
        final_dmg = int(base_dmg * mult * random.uniform(1.1, 1.4))
        self.e_hp -= final_dmg
        
        self.logs.append(f"🌟 **{self.pet['name']}** usó `{skill_name}`: -{final_dmg} HP!!")
        
        if self.e_hp <= 0:
            await self._handle_victory(interaction)
        else:
            await self.enemy_turn(interaction)

    @discord.ui.button(label="Curar (-30⚡)", style=discord.ButtonStyle.success, emoji="💊")
    async def heal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            return
        
        if self.p_energy < 30:
            await interaction.response.send_message("⚠️ No tienes suficiente energía (30).", ephemeral=True)
            return

        self.p_energy -= 30
        heal_amount = int(self.p_max_hp * 0.35)
        self.p_hp = min(self.p_max_hp, self.p_hp + heal_amount)
        
        self.logs.append(f"💊 **{self.pet['name']}** recuperó {heal_amount} HP.")
        await self.enemy_turn(interaction)

class Mascotas(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.file_path = "mascotas.json"
        self.pets = self._load_pets()
        
        self.pet_types = {
            "perro": {"emoji": "🐶", "desc": "Un compañero leal.", "food": "Hueso", "attack": 10, "defense": 5, "element": "tierra", "emoji_elem": "🪨"},
            "gato": {"emoji": "🐱", "desc": "Independiente pero cariñoso.", "food": "Pescado", "attack": 8, "defense": 8, "element": "normal", "emoji_elem": "⚪"},
            "dragon": {"emoji": "🐲", "desc": "Mítico y poderoso.", "food": "Gemas", "attack": 15, "defense": 10, "element": "fuego", "emoji_elem": "🔥"},
            "robot": {"emoji": "🤖", "desc": "El futuro es hoy.", "food": "Baterías", "attack": 12, "defense": 12, "element": "electrico", "emoji_elem": "⚡"},
            "hamster": {"emoji": "🐹", "desc": "Pequeño y veloz.", "food": "Semillas", "attack": 5, "defense": 20, "element": "normal", "emoji_elem": "⚪"},
            "alien": {"emoji": "👽", "desc": "Visitante de otro mundo.", "food": "Polvo Estelar", "attack": 14, "defense": 8, "element": "oscuridad", "emoji_elem": "🌑"},
            "fantasma": {"emoji": "👻", "desc": "Espíritu travieso.", "food": "Ectoplasma", "attack": 10, "defense": 15, "element": "oscuridad", "emoji_elem": "🌑"},
            "dinosaurio": {"emoji": "🦖", "desc": "Gigante prehistórico.", "food": "Carne", "attack": 18, "defense": 5, "element": "tierra", "emoji_elem": "🪨"},
            "unicornio": {"emoji": "🦄", "desc": "Magia pura.", "food": "Arcoíris", "attack": 8, "defense": 18, "element": "luz", "emoji_elem": "✨"},
            "slime": {"emoji": "💧", "desc": "Gelatinoso y amigable.", "food": "Agua", "attack": 5, "defense": 25, "element": "agua", "emoji_elem": "💧"},
            # Evoluciones (Nivel 10+)
            "lobo_mistico": {"emoji": "🐺", "desc": "Evolución de Perro. Un guardián espiritual.", "food": "Carne Sagrada", "attack": 25, "defense": 15, "element": "tierra", "emoji_elem": "🪨"},
            "leon_solar": {"emoji": "🦁", "desc": "Evolución de Gato. Brilla con luz propia.", "food": "Ambrosía", "attack": 20, "defense": 20, "element": "luz", "emoji_elem": "✨"},
            "bahamut": {"emoji": "🐉", "desc": "Evolución de Dragón. El rey de los dragones.", "food": "Cristales de Maná", "attack": 35, "defense": 25, "element": "fuego", "emoji_elem": "🔥"},
            "mecha_prime": {"emoji": "🦾", "desc": "Evolución de Robot. Tecnología suprema.", "food": "Núcleo de Fusión", "attack": 28, "defense": 28, "element": "electrico", "emoji_elem": "⚡"},
            "bestia_divina": {"emoji": "🐗", "desc": "Evolución de Hamster. Imparable.", "food": "Néctar", "attack": 15, "defense": 45, "element": "tierra", "emoji_elem": "🪨"},
            "invasor_cosmico": {"emoji": "🛸", "desc": "Evolución de Alien. Conquistador de mundos.", "food": "Materia Oscura", "attack": 30, "defense": 20, "element": "oscuridad", "emoji_elem": "🌑"},
            "espectro_real": {"emoji": "💀", "desc": "Evolución de Fantasma. Terror nocturno.", "food": "Almas", "attack": 25, "defense": 30, "element": "oscuridad", "emoji_elem": "🌑"},
            "t_rex_titan": {"emoji": "🦕", "desc": "Evolución de Dinosaurio. El depredador definitivo.", "food": "Meteorito", "attack": 40, "defense": 10, "element": "fuego", "emoji_elem": "🔥"},
            "alicornio_sagrado": {"emoji": "🌈", "desc": "Evolución de Unicornio. Luz de esperanza.", "food": "Luz Pura", "attack": 20, "defense": 35, "element": "luz", "emoji_elem": "✨"},
            "rey_slime": {"emoji": "👑", "desc": "Evolución de Slime. El más grande de todos.", "food": "Océano", "attack": 15, "defense": 50, "element": "agua", "emoji_elem": "💧"}
        }
        
        self.evolution_map = {
            "perro": "lobo_mistico",
            "gato": "leon_solar",
            "dragon": "bahamut",
            "robot": "mecha_prime",
            "hamster": "bestia_divina",
            "alien": "invasor_cosmico",
            "fantasma": "espectro_real",
            "dinosaurio": "t_rex_titan",
            "unicornio": "alicornio_sagrado",
            "slime": "rey_slime"
        }

    def _load_pets(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_pets(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.pets, f, indent=4, ensure_ascii=False)

    def _get_pet(self, user_id):
        return self.pets.get(str(user_id))

    def _save_pet(self, user_id, pet_data):
        self.pets[str(user_id)] = pet_data
        self._save_pets()

    def _add_xp(self, pet, amount):
        pet['xp'] += amount
        msg = ""
        # Level up logic
        while pet['xp'] >= 100:
            pet['xp'] -= 100
            pet['level'] += 1
            msg += f"\n🆙 **¡SUBIÓ DE NIVEL!** Ahora es nivel {pet['level']}."
        return msg

    def _check_vital_signs(self, pet):
        # Calculate time passed since last interaction
        last_seen = pet.get('last_interaction', time.time())
        now = time.time()
        hours_passed = (now - last_seen) / 3600
        
        # Decay rates per hour
        hunger_decay = 4 * hours_passed
        happiness_decay = 4 * hours_passed
        energy_decay = 2 * hours_passed
        
        pet['hunger'] = max(0, pet['hunger'] - hunger_decay)
        pet['happiness'] = max(0, pet['happiness'] - happiness_decay)
        pet['energy'] = max(0, pet['energy'] - energy_decay)
        
        # Update timestamp
        pet['last_interaction'] = now
        
        # Check death conditions
        if pet['hunger'] <= 0:
            return False, f"🪦 **{pet['name']}** ha muerto de hambre por falta de cuidados... 😔"
        
        if pet['happiness'] <= 0:
            return False, f"🏃 **{pet['name']}** se ha escapado de casa porque estaba muy triste... 💔"
            
        return True, ""

    @app_commands.command(name="mascota", description="Sistema de mascotas virtuales")
    @app_commands.describe(accion="Acción a realizar", nombre="Nombre (adoptar/renombrar) / Apuesta (duelo)", tipo="Tipo (adoptar)")
    @app_commands.choices(tipo=[
        app_commands.Choice(name="Perro 🐶", value="perro"),
        app_commands.Choice(name="Gato 🐱", value="gato"),
        app_commands.Choice(name="Dragón 🐲", value="dragon"),
        app_commands.Choice(name="Robot 🤖", value="robot"),
        app_commands.Choice(name="Hámster 🐹", value="hamster"),
        app_commands.Choice(name="Alien 👽", value="alien"),
        app_commands.Choice(name="Fantasma 👻", value="fantasma"),
        app_commands.Choice(name="Dinosaurio 🦖", value="dinosaurio"),
        app_commands.Choice(name="Unicornio 🦄", value="unicornio"),
        app_commands.Choice(name="Slime 💧", value="slime")
    ])
    @app_commands.choices(accion=[
        app_commands.Choice(name="Ver estado", value="ver"),
        app_commands.Choice(name="Adoptar nueva", value="adoptar"),
        app_commands.Choice(name="Alimentar (Cuesta monedas)", value="alimentar"),
        app_commands.Choice(name="Jugar", value="jugar"),
        app_commands.Choice(name="Entrenar (XP)", value="entrenar"),
        app_commands.Choice(name="Dormir (Recuperar)", value="dormir"),
        app_commands.Choice(name="Liberar (Borrar)", value="liberar"),
        app_commands.Choice(name="Explorar (Ganar items/dinero)", value="explorar"),
        app_commands.Choice(name="Duelo (Apostar)", value="duelo"),
        app_commands.Choice(name="Tienda de Mascotas", value="tienda"),
        app_commands.Choice(name="Comprar Item", value="comprar"),
        app_commands.Choice(name="Evolucionar (Nivel 10+)", value="evolucionar"),
        app_commands.Choice(name="Ranking Global", value="ranking"),
        app_commands.Choice(name="Renombrar", value="renombrar")
    ])
    async def mascota(self, interaction: discord.Interaction, accion: str, nombre: str = None, tipo: str = None):
        user_id = str(interaction.user.id)
        pet = self._get_pet(user_id)
        monedas = self.bot.get_cog("Monedas")

        # Vital signs check (Skip for adopt since no pet exists yet)
        if pet and accion != "adoptar":
            alive, msg = self._check_vital_signs(pet)
            if not alive:
                del self.pets[user_id]
                self._save_pets()
                await interaction.response.send_message(msg)
                return
            # If alive, save the updated stats (decay applied)
            self._save_pet(user_id, pet)

        if accion == "adoptar":
            if pet:
                await interaction.response.send_message("❌ Ya tienes una mascota. Usa `/mascota liberar` si quieres otra.", ephemeral=True)
                return
            
            if not tipo or not nombre:
                await interaction.response.send_message("⚠️ Debes especificar un `tipo` y un `nombre` para adoptar.", ephemeral=True)
                return

            costo = 500
            if monedas:
                if not monedas.remove_balance(interaction.user.id, costo):
                    await interaction.response.send_message(f"❌ Adoptar una mascota cuesta 💰 {costo}.", ephemeral=True)
                    return

            self._save_pet(user_id, {
                "name": nombre,
                "type": tipo,
                "level": 1,
                "xp": 0,
                "hunger": 100, # 100 = lleno, 0 = hambriento
                "happiness": 100,
                "energy": 100,
                "wins": 0,
                "losses": 0,
                "last_interaction": time.time(),
                "last_exploration": 0
            })
            
            info = self.pet_types.get(tipo, {"emoji": "❓"})
            await interaction.response.send_message(f"🎉 ¡Felicidades! Has adoptado a **{nombre}** el {info['emoji']} ({tipo}) por 💰 {costo}.")

        elif accion == "ver":
            if not pet:
                await interaction.response.send_message("😢 No tienes mascota. Usa `/mascota adoptar`.", ephemeral=True)
                return
            
            info = self.pet_types.get(pet["type"], {"emoji": "❓"})
            if "energy" not in pet:
                pet["energy"] = 100
            
            embed = discord.Embed(title=f"Estado de {pet['name']} {info['emoji']} ({pet['type'].capitalize()})", color=Theme.get_color(interaction.guild.id, 'primary'))
            embed.add_field(name="Nivel", value=str(pet['level']), inline=True)
            embed.add_field(name="Experiencia", value=f"{pet['xp']}/100", inline=True)
            embed.add_field(name="Récord", value=f"🏆 {pet.get('wins', 0)} - 💀 {pet.get('losses', 0)}", inline=True)
            
            # Barras visuales
            h_bar = "🍖" * (pet['hunger'] // 10) + "⚫" * ((100 - pet['hunger']) // 10)
            hap_bar = "❤️" * (pet['happiness'] // 10) + "⚫" * ((100 - pet['happiness']) // 10)
            en_bar = "⚡" * (pet['energy'] // 10) + "⚫" * ((100 - pet['energy']) // 10)
            
            embed.add_field(name="Hambre", value=f"{pet['hunger']}%\n{h_bar}", inline=False)
            embed.add_field(name="Felicidad", value=f"{pet['happiness']}%\n{hap_bar}", inline=False)
            embed.add_field(name="Energía", value=f"{pet['energy']}%\n{en_bar}", inline=False)
            embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
            
            await interaction.response.send_message(embed=embed)

        elif accion == "alimentar":
            if not pet:
                await interaction.response.send_message("😢 No tienes mascota.", ephemeral=True)
                return
            
            if pet['hunger'] >= 100:
                await interaction.response.send_message(f"🤢 **{pet['name']}** está llenísimo. No quiere comer más.", ephemeral=True)
                return
            
            costo_comida = 20
            if monedas:
                if not monedas.remove_balance(interaction.user.id, costo_comida):
                    await interaction.response.send_message(f"❌ No tienes 💰 {costo_comida} para comprar comida.", ephemeral=True)
                    return
            
            pet['hunger'] = min(100, pet['hunger'] + 30)
            msg_extra = self._add_xp(pet, 5)
            if "energy" not in pet:
                pet["energy"] = 100
            pet['energy'] = min(100, pet['energy'] + 10)
            
            self._save_pet(user_id, pet)
            
            info = self.pet_types.get(pet["type"], {"emoji": "❓"})
            await interaction.response.send_message(f"😋 Le diste de comer a **{pet['name']}** (Coste: 💰 {costo_comida}). ¡Se ve feliz! (+5 XP){msg_extra}")

        elif accion == "jugar":
            if not pet:
                await interaction.response.send_message("😢 No tienes mascota.", ephemeral=True)
                return
            
            if pet['hunger'] < 20:
                await interaction.response.send_message(f"😟 **{pet['name']}** tiene mucha hambre para jugar. Aliméntalo primero.", ephemeral=True)
                return
            
            if "energy" not in pet:
                pet["energy"] = 100
            if pet['energy'] < 10:
                await interaction.response.send_message(f"😴 **{pet['name']}** está muy cansado. Déjalo dormir un poco.", ephemeral=True)
                return

            pet['happiness'] = min(100, pet['happiness'] + 15)
            pet['hunger'] -= 10
            pet['energy'] -= 10
            msg_extra = self._add_xp(pet, 10)
            
            self._save_pet(user_id, pet)
            await interaction.response.send_message(f"🎾 Jugaste con **{pet['name']}**. ¡Se divirtió mucho! (+10 XP){msg_extra}")

        elif accion == "entrenar":
            if not pet:
                await interaction.response.send_message("😢 No tienes mascota.", ephemeral=True)
                return
            
            if "energy" not in pet:
                pet["energy"] = 100
            if pet['energy'] < 30:
                await interaction.response.send_message(f"😴 **{pet['name']}** está demasiado cansado para entrenar.", ephemeral=True)
                return
            
            if pet['hunger'] < 30:
                await interaction.response.send_message(f"😟 **{pet['name']}** tiene hambre. No puede entrenar bien.", ephemeral=True)
                return

            pet['energy'] -= 30
            pet['hunger'] -= 20
            msg_extra = self._add_xp(pet, 25)
            
            self._save_pet(user_id, pet)
            await interaction.response.send_message(f"🏋️ **{pet['name']}** ha entrenado duro. ¡Se vuelve más fuerte! (+25 XP){msg_extra}")

        elif accion == "dormir":
            if not pet:
                await interaction.response.send_message("😢 No tienes mascota.", ephemeral=True)
                return
            
            if "energy" not in pet:
                pet["energy"] = 100
            if pet['energy'] >= 90:
                await interaction.response.send_message(f"👀 **{pet['name']}** no tiene sueño.", ephemeral=True)
                return
            
            pet['energy'] = 100
            pet['hunger'] -= 15 
            pet['happiness'] += 5
            
            self._save_pet(user_id, pet)
            await interaction.response.send_message(f"💤 **{pet['name']}** ha dormido una siesta reparadora. ¡Energía al máximo!")

        elif accion == "explorar":
            if not pet:
                await interaction.response.send_message("😢 No tienes mascota.", ephemeral=True)
                return
            
            if "last_exploration" in pet and time.time() - pet["last_exploration"] < 300: # 5 min cooldown
                remaining = int(300 - (time.time() - pet["last_exploration"]))
                await interaction.response.send_message(f"⏳ **{pet['name']}** está descansando de su última aventura. Espera {remaining} segundos.", ephemeral=True)
                return
            
            if pet['energy'] < 20:
                await interaction.response.send_message(f"😴 **{pet['name']}** está muy cansado para salir.", ephemeral=True)
                return

            pet['energy'] -= 20
            pet['last_exploration'] = time.time()
            
            outcome = random.randint(1, 100)
            
            if outcome <= 25: # 25% dinero común
                amount = random.randint(10, 50) * pet['level']
                if monedas:
                    monedas.add_balance(interaction.user.id, amount)
                msg = f"🗺️ **{pet['name']}** encontró unas monedas tiradas: 💰 {amount}."
                
            elif outcome <= 35: # 10% TESORO
                amount = random.randint(100, 300) * pet['level']
                if monedas:
                    monedas.add_balance(interaction.user.id, amount)
                msg = f"💎 **{pet['name']}** descubrió un COFRE DEL TESORO: 💰 {amount}!!"
                
            elif outcome <= 50: # 15% nada
                msg = f"🍃 **{pet['name']}** paseó por el bosque pero no encontró nada interesante."
                
            elif outcome <= 80: # 30% experiencia
                xp_gain = random.randint(10, 30)
                msg_extra = self._add_xp(pet, xp_gain)
                msg = f"🌟 **{pet['name']}** aprendió mucho explorando el mundo. (+{xp_gain} XP){msg_extra}"
                
            elif outcome <= 90: # 10% Gran Experiencia
                xp_gain = random.randint(50, 100)
                msg_extra = self._add_xp(pet, xp_gain)
                msg = f"📜 **{pet['name']}** encontró un pergamino antiguo. (+{xp_gain} XP){msg_extra}"
                
            elif outcome <= 95: # 5% Encontrar comida
                pet['hunger'] = min(100, pet['hunger'] + 40)
                msg = f"🍎 **{pet['name']}** encontró frutas silvestres y se las comió. (+40 Hambre)"

            else: # 5% peligro
                pet['happiness'] = max(0, pet['happiness'] - 15)
                pet['energy'] = max(0, pet['energy'] - 10)
                msg = f"⚠️ **{pet['name']}** fue perseguido por un oso. Escapó, pero está asustado y cansado."
            
            self._save_pet(user_id, pet)
            await interaction.response.send_message(msg)

        elif accion == "duelo":
            if not pet: 
                await interaction.response.send_message("😢 No tienes mascota.", ephemeral=True)
                return
            
            # Validar apuesta
            bet = 0
            if nombre and nombre.isdigit():
                bet = int(nombre)
            else:
                await interaction.response.send_message("⚠️ Debes ingresar la cantidad a apostar en el campo 'nombre'.", ephemeral=True)
                return

            if bet < 0: 
                await interaction.response.send_message("⚠️ La apuesta debe ser positiva.", ephemeral=True)
                return

            if monedas:
                if not monedas.remove_balance(interaction.user.id, bet):
                    await interaction.response.send_message("❌ No tienes suficiente dinero para esa apuesta.", ephemeral=True)
                    return
            
            # Generar enemigo
            enemy_level = max(1, pet['level'] + random.randint(-2, 2))
            enemy_type = random.choice(list(self.pet_types.keys()))
            
            enemy_data = {
                "name": f"{enemy_type.capitalize()} Salvaje",
                "type": enemy_type,
                "level": enemy_level
            }
            
            # Iniciar Vista de Batalla
            view = BattleView(self.bot, interaction.user, pet, enemy_data, bet, self)
            
            # Mensaje inicial
            embed = discord.Embed(
                title="⚔️ ¡Duelo Encontrado!",
                description=f"**{pet['name']}** se enfrenta a un **{enemy_data['name']}** (Nvl {enemy_level}).\n¡Prepárate para luchar!",
                color=Theme.get_color(interaction.guild.id, 'warning')
            )
            await interaction.response.send_message(embed=embed, view=view)
            await view.update_embed(interaction)

        elif accion == "tienda":
            embed = discord.Embed(title="🏪 Tienda de Mascotas", description="Usa `/mascota comprar` + nombre_item", color=Theme.get_color(interaction.guild.id, 'primary'))
            embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
            embed.add_field(name="🍖 comida", value="💰 20\nRecupera 30 Hambre, +5 XP", inline=True)
            embed.add_field(name="🍎 superalimento", value="💰 50\nRecupera 50 Hambre, +20 XP", inline=True)
            embed.add_field(name="☕ cafe", value="� 30\nRecupera 30 Energía, +5 XP", inline=True)
            embed.add_field(name="🎾 pelota", value="💰 40\nRecupera 20 Felicidad, +10 XP", inline=True)
            embed.add_field(name="� medicina", value="💰 100\nRecupera Salud/Energía completa", inline=True)
            embed.add_field(name="🧪 pocion", value="💰 150\nOtorga +100 XP instantáneos", inline=True)
            embed.add_field(name="🧸 juguete", value="💰 500\n+50 Felicidad permanente", inline=True)
            embed.set_footer(text="¡Cuida bien de tu compañero!")
            await interaction.response.send_message(embed=embed)

        elif accion == "comprar":
            if not pet:
                await interaction.response.send_message("😢 No tienes mascota.", ephemeral=True)
                return
            
            if not nombre:
                await interaction.response.send_message("⚠️ Debes especificar el nombre del item (comida, superalimento, medicina, juguete).", ephemeral=True)
                return
            
            item = nombre.lower()
            cost = 0
            effect = ""
            
            if item == "comida":
                cost = 20
                if monedas and not monedas.remove_balance(interaction.user.id, cost):
                    await interaction.response.send_message(f"❌ No tienes 💰 {cost}.", ephemeral=True)
                    return
                pet['hunger'] = min(100, pet['hunger'] + 30)
                msg_extra = self._add_xp(pet, 5)
                effect = f"ha comido bien. (+30 Hambre, +5 XP){msg_extra}"
                
            elif item == "superalimento":
                cost = 50
                if monedas and not monedas.remove_balance(interaction.user.id, cost):
                    await interaction.response.send_message(f"❌ No tienes 💰 {cost}.", ephemeral=True)
                    return
                pet['hunger'] = min(100, pet['hunger'] + 50)
                msg_extra = self._add_xp(pet, 20)
                effect = f"ha disfrutado un manjar. (+50 Hambre, +20 XP){msg_extra}"

            elif item == "cafe":
                cost = 30
                if monedas and not monedas.remove_balance(interaction.user.id, cost):
                    await interaction.response.send_message(f"❌ No tienes 💰 {cost}.", ephemeral=True)
                    return
                if "energy" not in pet:
                    pet["energy"] = 100
                pet['energy'] = min(100, pet['energy'] + 30)
                msg_extra = self._add_xp(pet, 5)
                effect = f"se siente energizado. (+30 Energía, +5 XP){msg_extra}"

            elif item == "pelota":
                cost = 40
                if monedas and not monedas.remove_balance(interaction.user.id, cost):
                    await interaction.response.send_message(f"❌ No tienes 💰 {cost}.", ephemeral=True)
                    return
                pet['happiness'] = min(100, pet['happiness'] + 20)
                msg_extra = self._add_xp(pet, 10)
                effect = f"jugó un rato. (+20 Felicidad, +10 XP){msg_extra}"

            elif item == "pocion":
                cost = 150
                if monedas and not monedas.remove_balance(interaction.user.id, cost):
                    await interaction.response.send_message(f"❌ No tienes 💰 {cost}.", ephemeral=True)
                    return
                msg_extra = self._add_xp(pet, 100)
                effect = f"bebió la poción mágica. (+100 XP){msg_extra}"
                
            elif item == "medicina":
                cost = 100
                if monedas and not monedas.remove_balance(interaction.user.id, cost):
                    await interaction.response.send_message(f"❌ No tienes 💰 {cost}.", ephemeral=True)
                    return
                pet['energy'] = 100
                pet['happiness'] = min(100, pet['happiness'] + 10)
                effect = "se siente renovado. (Energía restaurada)"
                
            elif item == "juguete":
                cost = 500
                if monedas and not monedas.remove_balance(interaction.user.id, cost):
                    await interaction.response.send_message(f"❌ No tienes 💰 {cost}.", ephemeral=True)
                    return
                pet['happiness'] = min(100, pet['happiness'] + 50)
                msg_extra = self._add_xp(pet, 50)
                effect = f"está eufórico con su nuevo juguete. (+50 Felicidad, +50 XP){msg_extra}"
                
            else:
                await interaction.response.send_message("❌ Item no encontrado. Mira la `/mascota tienda`.", ephemeral=True)
                return

            self._save_pet(user_id, pet)
            await interaction.response.send_message(f"🛍️ Compraste **{item}** por 💰 {cost}.\n**{pet['name']}** {effect}")

        elif accion == "liberar":
            if not pet:
                await interaction.response.send_message("No tienes mascota para liberar.", ephemeral=True)
                return
            
            del self.pets[user_id]
            self._save_pets()
            await interaction.response.send_message("👋 Has liberado a tu mascota. Esperamos que encuentre un buen hogar.", ephemeral=True)

        elif accion == "evolucionar":
            if not pet:
                await interaction.response.send_message("❌ No tienes mascota.", ephemeral=True)
                return

            current_type = pet["type"]
            if current_type not in self.evolution_map:
                await interaction.response.send_message(f"❌ Tu **{current_type}** no puede evolucionar más (o no tiene evolución conocida).", ephemeral=True)
                return
            
            if pet["level"] < 10:
                await interaction.response.send_message(f"❌ **{pet['name']}** necesita ser Nivel 10 para evolucionar (Actual: {pet['level']}).", ephemeral=True)
                return
            
            cost = 1000
            if monedas and not monedas.remove_balance(interaction.user.id, cost):
                await interaction.response.send_message(f"❌ La evolución cuesta 💰 {cost}.", ephemeral=True)
                return

            new_type_key = self.evolution_map[current_type]
            new_type_info = self.pet_types[new_type_key]
            
            pet["type"] = new_type_key
            # Boost stats indirectly by changing type (which has higher base stats)
            
            self._save_pet(user_id, pet)
            await interaction.response.send_message(f"✨🔮 **¡EVOLUCIÓN!** 🔮✨\n**{pet['name']}** ha evolucionado a **{new_type_key.upper().replace('_', ' ')}** {new_type_info['emoji']}!\n{new_type_info['desc']}")

        elif accion == "ranking":
            if not self.pets:
                await interaction.response.send_message("❌ No hay mascotas registradas aún.", ephemeral=True)
                return
            
            # Ordenar por nivel (desc) y luego XP (desc)
            sorted_pets = sorted(self.pets.items(), key=lambda item: (item[1]['level'], item[1]['xp']), reverse=True)
            top_10 = sorted_pets[:10]
            
            desc = ""
            for i, (uid, p) in enumerate(top_10, 1):
                try:
                    # Intentar obtener nombre del usuario (puede ser lento si no está en caché)
                    user = self.bot.get_user(int(uid))
                    user_name = user.display_name if user else f"Usuario {uid}"
                except Exception:
                    user_name = f"Usuario {uid}"
                
                info = self.pet_types.get(p["type"], {"emoji": "❓"})
                desc += f"**{i}. {p['name']}** {info['emoji']} (Dueño: {user_name})\n   Nivel {p['level']} | {p['xp']} XP | {p.get('wins', 0)} Victorias\n"
            
            embed = discord.Embed(title="🏆 Ranking Global de Mascotas", description=desc, color=Theme.get_color(interaction.guild.id, 'primary'))
            embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
            await interaction.response.send_message(embed=embed)

        elif accion == "renombrar":
            if not pet:
                await interaction.response.send_message("❌ No tienes mascota para renombrar.", ephemeral=True)
                return
            
            if not nombre:
                await interaction.response.send_message("⚠️ Debes especificar el nuevo nombre en el campo `nombre`.", ephemeral=True)
                return
            
            old_name = pet['name']
            pet['name'] = nombre
            self._save_pet(user_id, pet)
            
            await interaction.response.send_message(f"✏️ Has renombrado a tu mascota.\nDe **{old_name}** a **{nombre}**.")

async def setup(bot: commands.Bot):
    await bot.add_cog(Mascotas(bot))
