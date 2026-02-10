import discord
from discord.ext import commands
from discord import app_commands
import random
from bot.themes import Theme

WORDS = {
    "ANIMALES": ["LEON", "TIGRE", "ELEFANTE", "JIRAFA", "HIPOPOTAMO", "AGUILA", "TIBURON", "PANTERA", "LOBO", "OSO"],
    "PAISES": ["ESPAÑA", "MEXICO", "ARGENTINA", "COLOMBIA", "FRANCIA", "ITALIA", "JAPON", "ALEMANIA", "BRASIL", "CHILE"],
    "TECNOLOGIA": ["PYTHON", "DISCORD", "ROBOT", "INTERNET", "WIFI", "PROGRAMACION", "COMPUTADORA", "SERVIDOR", "CODIGO"],
    "COMIDA": ["PIZZA", "HAMBURGUESA", "SUSHI", "TACOS", "PASTA", "CHOCOLATE", "HELADO", "ENSALADA", "POLLO"],
    "HOGAR": ["MESA", "SILLA", "CAMA", "SOFA", "LAMPARA", "ESPEJO", "COCINA", "BAÑO", "PUERTA", "VENTANA"]
}

STAGES = [
    """
      +---+
      |   |
          |
          |
          |
          |
    =========
    """,
    """
      +---+
      |   |
      O   |
          |
          |
          |
    =========
    """,
    """
      +---+
      |   |
      O   |
      |   |
          |
          |
    =========
    """,
    """
      +---+
      |   |
      O   |
     /|   |
          |
          |
    =========
    """,
    """
      +---+
      |   |
      O   |
     /|\\  |
          |
          |
    =========
    """,
    """
      +---+
      |   |
      O   |
     /|\\  |
     /    |
          |
    =========
    """,
    """
      +---+
      |   |
      O   |
     /|\\  |
     / \\  |
          |
    =========
    """
]

class GuessModal(discord.ui.Modal, title="Adivina una letra"):
    letter = discord.ui.TextInput(label="Letra", min_length=1, max_length=1, placeholder="Escribe una sola letra...")

    def __init__(self, view):
        super().__init__()
        self.view_ref = view

    async def on_submit(self, interaction: discord.Interaction):
        char = self.letter.value.upper()
        if not char.isalpha():
            await interaction.response.send_message("Solo letras, por favor.", ephemeral=True)
            return
        
        await self.view_ref.process_guess(interaction, char)

class SolveModal(discord.ui.Modal, title="Adivina la palabra"):
    word = discord.ui.TextInput(label="Palabra completa", min_length=2, placeholder="Escribe la palabra completa...")

    def __init__(self, view):
        super().__init__()
        self.view_ref = view

    async def on_submit(self, interaction: discord.Interaction):
        text = self.word.value.upper()
        await self.view_ref.process_solve(interaction, text)

class AhorcadoView(discord.ui.View):
    def __init__(self, category, word):
        super().__init__(timeout=180)
        self.category = category
        self.word = word
        self.guesses = set()
        self.mistakes = 0
        self.max_mistakes = len(STAGES) - 1
        self.solved = False

    def get_display_word(self):
        return " ".join([c if c in self.guesses else "_" for c in self.word])

    def get_embed(self, guild_id):
        color = Theme.get_color(guild_id, 'success') if self.solved else (
            Theme.get_color(guild_id, 'error') if self.mistakes >= self.max_mistakes else Theme.get_color(guild_id, 'primary')
        )
        
        desc = f"```\n{STAGES[self.mistakes]}\n```\n"
        desc += f"**Categoría:** {self.category}\n"
        desc += f"**Palabra:** `{self.get_display_word()}`\n\n"
        desc += f"**Letras usadas:** {', '.join(sorted(self.guesses)) if self.guesses else 'Ninguna'}"

        if self.solved:
            title = "¡Ganaste! 🎉"
        elif self.mistakes >= self.max_mistakes:
            title = "¡Perdiste! 💀"
            desc += f"\n\nLa palabra era: **{self.word}**"
        else:
            title = "Ahorcado"

        embed = discord.Embed(title=title, description=desc, color=color)
        return embed

    async def process_guess(self, interaction: discord.Interaction, char):
        if char in self.guesses:
            await interaction.response.send_message(f"Ya usaste la letra **{char}**.", ephemeral=True)
            return

        self.guesses.add(char)
        if char not in self.word:
            self.mistakes += 1
        
        if all(c in self.guesses for c in self.word):
            self.solved = True
            self.stop()
            for child in self.children:
                child.disabled = True
        elif self.mistakes >= self.max_mistakes:
            self.stop()
            for child in self.children:
                child.disabled = True

        await interaction.response.edit_message(embed=self.get_embed(interaction.guild.id), view=self)

    async def process_solve(self, interaction: discord.Interaction, text):
        if text == self.word:
            self.solved = True
            self.guesses.update(list(self.word)) # Reveal all
            self.stop()
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(embed=self.get_embed(interaction.guild.id), view=self)
        else:
            self.mistakes += 1
            if self.mistakes >= self.max_mistakes:
                self.stop()
                for child in self.children:
                    child.disabled = True
                await interaction.response.edit_message(embed=self.get_embed(interaction.guild.id), view=self)
            else:
                await interaction.response.edit_message(embed=self.get_embed(interaction.guild.id), view=self)
                await interaction.followup.send(f"**{text}** no es la palabra correcta. Pierdes un intento.", ephemeral=True)

    @discord.ui.button(label="Adivinar Letra", style=discord.ButtonStyle.primary, emoji="🔤")
    async def guess_letter(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GuessModal(self))

    @discord.ui.button(label="Resolver Palabra", style=discord.ButtonStyle.secondary, emoji="⚡")
    async def solve_word(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SolveModal(self))

class Ahorcado(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ahorcado", description="Juega al clásico ahorcado")
    async def ahorcado(self, interaction: discord.Interaction):
        cat = random.choice(list(WORDS.keys()))
        word = random.choice(WORDS[cat])
        
        view = AhorcadoView(cat, word)
        await interaction.response.send_message(embed=view.get_embed(interaction.guild.id), view=view)

async def setup(bot):
    await bot.add_cog(Ahorcado(bot))
