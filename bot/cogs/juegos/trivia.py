import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
import json
import os
import time
from bot.themes import Theme

# Base de datos de preguntas (Local para estabilidad)
QUESTIONS = [
    {"q": "¿Cuál es el comando para ver el ping en Discord?", "o": ["/ping", "/pong", "/test", "/ms"], "a": 0, "cat": "Discord"},
    {"q": "¿En qué año se lanzó Discord?", "o": ["2015", "2016", "2014", "2013"], "a": 0, "cat": "Discord"},
    {"q": "¿Cuál es la mascota oficial de Discord?", "o": ["Wumpus", "Clyde", "Nelly", "Phibi"], "a": 0, "cat": "Discord"},
    {"q": "¿Qué lenguaje de programación usa este bot?", "o": ["Python", "JavaScript", "C#", "Java"], "a": 0, "cat": "Tech"},
    {"q": "¿Cuál es el Pokémon inicial de tipo Fuego en Kanto?", "o": ["Charmander", "Squirtle", "Bulbasaur", "Pikachu"], "a": 0, "cat": "Anime"},
    {"q": "¿Cómo se llama el protagonista de Dragon Ball?", "o": ["Goku", "Vegeta", "Gohan", "Piccolo"], "a": 0, "cat": "Anime"},
    {"q": "¿Cuál es el juego más vendido de la historia?", "o": ["Minecraft", "Tetris", "GTA V", "Wii Sports"], "a": 0, "cat": "Gaming"},
    {"q": "¿Quién es el hermano de Mario?", "o": ["Luigi", "Wario", "Yoshi", "Toad"], "a": 0, "cat": "Gaming"},
    {"q": "¿Cuál es la capital de Francia?", "o": ["París", "Londres", "Madrid", "Roma"], "a": 0, "cat": "Geografía"},
    {"q": "¿Cuántos planetas tiene el Sistema Solar?", "o": ["8", "9", "7", "10"], "a": 0, "cat": "Ciencia"},
    {"q": "¿Qué es H2O?", "o": ["Agua", "Oxígeno", "Hidrógeno", "Sal"], "a": 0, "cat": "Ciencia"},
    {"q": "¿Quién pintó la Mona Lisa?", "o": ["Da Vinci", "Picasso", "Van Gogh", "Dalí"], "a": 0, "cat": "Arte"},
    {"q": "¿Cuál es el río más largo del mundo?", "o": ["Amazonas", "Nilo", "Yangtsé", "Misisipi"], "a": 0, "cat": "Geografía"},
    {"q": "¿En qué año llegó el hombre a la luna?", "o": ["1969", "1959", "1979", "1960"], "a": 0, "cat": "Historia"},
    {"q": "¿Quién escribió 'Don Quijote'?", "o": ["Cervantes", "Shakespeare", "Dante", "García Márquez"], "a": 0, "cat": "Literatura"},
    {"q": "¿Cuál es el símbolo químico del Oro?", "o": ["Au", "Ag", "Fe", "Cu"], "a": 0, "cat": "Ciencia"},
    {"q": "¿Qué compañía creó el iPhone?", "o": ["Apple", "Samsung", "Microsoft", "Google"], "a": 0, "cat": "Tech"},
    {"q": "¿Cómo se llama el fundador de Facebook?", "o": ["Mark Zuckerberg", "Bill Gates", "Elon Musk", "Jeff Bezos"], "a": 0, "cat": "Tech"},
    {"q": "¿Qué animal es Sonic?", "o": ["Erizo", "Gato", "Perro", "Zorro"], "a": 0, "cat": "Gaming"},
    {"q": "¿De qué color es la pastilla que toma Neo en Matrix?", "o": ["Roja", "Azul", "Verde", "Amarilla"], "a": 0, "cat": "Cine"}
]

class TriviaView(discord.ui.View):
    def __init__(self, question_data, correct_idx, timeout=15):
        super().__init__(timeout=timeout)
        self.correct_idx = correct_idx
        self.question_data = question_data
        self.answered_users = set()
        self.results = {} # {user_id: (points, time_taken)}
        self.start_time = time.time()
        
        # Setup Buttons
        labels = ["A", "B", "C", "D"]
        for i, option in enumerate(question_data["o"]):
            button = discord.ui.Button(label=option, custom_id=str(i), style=discord.ButtonStyle.secondary)
            button.callback = self.callback_wrapper(i)
            self.add_item(button)

    def callback_wrapper(self, index):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id in self.answered_users:
                await interaction.response.send_message("❌ Ya respondiste.", ephemeral=True)
                return
            
            self.answered_users.add(interaction.user.id)
            time_taken = time.time() - self.start_time
            
            if index == self.correct_idx:
                points = max(10, int(100 - (time_taken * 5))) # Más rápido = más puntos
                self.results[interaction.user.id] = points
                await interaction.response.send_message(f"✅ ¡Correcto! (+{points} pts)", ephemeral=True)
            else:
                self.results[interaction.user.id] = 0
                await interaction.response.send_message("❌ Incorrecto.", ephemeral=True)
        return callback

class Trivia(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.scores_file = "trivia_scores.json"
        self.scores = self._load_scores()

    def _load_scores(self):
        if os.path.exists(self.scores_file):
            try:
                with open(self.scores_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_scores(self):
        with open(self.scores_file, "w", encoding="utf-8") as f:
            json.dump(self.scores, f, indent=4)

    @app_commands.command(name="trivia", description="Inicia una ronda rápida de preguntas")
    async def trivia(self, interaction: discord.Interaction):
        q = random.choice(QUESTIONS)
        
        embed = discord.Embed(
            title=f"🧠 Trivia: {q['cat']}",
            description=f"**{q['q']}**\n\n" + "\n".join([f"**{chr(65+i)}.** {opt}" for i, opt in enumerate(q['o'])]),
            color=Theme.get_color(interaction.guild.id, 'primary')
        )
        embed.set_footer(text="Tienes 15 segundos para responder. ¡La velocidad cuenta!")
        
        view = TriviaView(q, q['a'])
        await interaction.response.send_message(embed=embed, view=view)
        
        # Esperar a que termine el tiempo
        await view.wait()
        
        # Calcular resultados
        if not view.results:
            result_text = "⏰ Tiempo agotado. Nadie respondió correctamente."
        else:
            winners = sorted([(uid, pts) for uid, pts in view.results.items() if pts > 0], key=lambda x: x[1], reverse=True)
            if not winners:
                result_text = f"⏰ Tiempo agotado. La respuesta correcta era: **{q['o'][q['a']]}**"
            else:
                result_text = f"✅ La respuesta correcta era: **{q['o'][q['a']]}**\n\n🏆 **Ganadores:**\n"
                for uid, pts in winners:
                    user = interaction.guild.get_member(uid)
                    name = user.display_name if user else "Usuario"
                    result_text += f"🥇 {name}: +{pts} pts\n"
                    
                    # Guardar score global
                    sid = str(uid)
                    self.scores[sid] = self.scores.get(sid, 0) + pts
                self._save_scores()

                # Dar monedas si existe el cog
                monedas = self.bot.get_cog("Monedas")
                if monedas:
                    for uid, pts in winners:
                        coins = pts // 2 # 50% de los puntos en monedas
                        monedas.add_balance(uid, coins)
                        result_text += f"\n💰 Se repartieron monedas."

        # Desactivar botones
        for item in view.children:
            item.disabled = True
            if int(item.custom_id) == q['a']:
                item.style = discord.ButtonStyle.success
            else:
                item.style = discord.ButtonStyle.secondary
        
        embed.description += f"\n\n**RESULTADOS:**\n{result_text}"
        await interaction.edit_original_response(embed=embed, view=view)

    @app_commands.command(name="ranking_trivia", description="Top 10 genios de la Trivia")
    async def ranking(self, interaction: discord.Interaction):
        sorted_scores = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)[:10]
        
        desc = ""
        for i, (uid, score) in enumerate(sorted_scores, 1):
            user = interaction.guild.get_member(int(uid))
            name = user.display_name if user else f"Usuario {uid}"
            medal = "🥇" if i==1 else ("🥈" if i==2 else ("🥉" if i==3 else "🔹"))
            desc += f"{medal} **{name}**: {score} pts\n"
            
        embed = discord.Embed(title="🏆 Ranking Global de Trivia", description=desc or "Nadie ha jugado aún.", color=Theme.get_color(interaction.guild.id, 'warning'))
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Trivia(bot))
