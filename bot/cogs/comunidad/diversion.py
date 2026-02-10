import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
from bot.themes import Theme

class PiedraPapelTijeras(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(label="Piedra", style=discord.ButtonStyle.blurple, emoji="🪨")
    async def piedra(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.play(interaction, "Piedra")

    @discord.ui.button(label="Papel", style=discord.ButtonStyle.green, emoji="📄")
    async def papel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.play(interaction, "Papel")

    @discord.ui.button(label="Tijeras", style=discord.ButtonStyle.red, emoji="✂️")
    async def tijeras(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.play(interaction, "Tijeras")

    async def play(self, interaction: discord.Interaction, user_choice):
        bot_choice = random.choice(["Piedra", "Papel", "Tijeras"])
        
        # Lógica de ganador
        if user_choice == bot_choice:
            result = "🤝 ¡Empate!"
            color = Theme.get_color(interaction.guild.id, 'warning')
        elif (user_choice == "Piedra" and bot_choice == "Tijeras") or \
             (user_choice == "Papel" and bot_choice == "Piedra") or \
             (user_choice == "Tijeras" and bot_choice == "Papel"):
            result = "🎉 ¡Ganaste!"
            color = Theme.get_color(interaction.guild.id, 'success')
        else:
            result = "🤖 ¡Gané yo!"
            color = Theme.get_color(interaction.guild.id, 'error')

        embed = discord.Embed(title="Piedra, Papel o Tijeras", color=color)
        embed.add_field(name="Tu elección", value=f"**{user_choice}**", inline=True)
        embed.add_field(name="Mi elección", value=f"**{bot_choice}**", inline=True)
        embed.add_field(name="Resultado", value=result, inline=False)
        embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
        
        # Deshabilitar botones
        for child in self.children:
            child.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)

class Diversion(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="dado", description="Lanza un dado de N caras")
    async def dado(self, interaction: discord.Interaction, caras: int = 6):
        if caras < 2:
            await interaction.response.send_message("⚠️ El dado debe tener al menos 2 caras.", ephemeral=True)
            return
        res = random.randint(1, caras)
        embed = discord.Embed(title="🎲 Lanzamiento de Dado", color=Theme.get_color(interaction.guild.id, 'primary'))
        embed.add_field(name="Caras", value=str(caras), inline=True)
        embed.add_field(name="Resultado", value=f"**{res}**", inline=True)
        embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="moneda", description="Lanza una moneda al aire")
    async def moneda(self, interaction: discord.Interaction):
        res = random.choice(["Cara", "Cruz"])
        embed = discord.Embed(title="🪙 Lanzamiento de Moneda", color=Theme.get_color(interaction.guild.id, 'primary'))
        embed.description = f"La moneda cayó en: **{res}**"
        embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ppt", description="Juega Piedra, Papel o Tijeras contra el bot")
    async def ppt(self, interaction: discord.Interaction):
        view = PiedraPapelTijeras()
        embed = discord.Embed(title="Piedra, Papel o Tijeras", description="Elige tu jugada:", color=Theme.get_color(interaction.guild.id, 'primary'))
        embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="eleccion", description="Elige aleatoriamente entre varias opciones")
    async def eleccion(self, interaction: discord.Interaction, opciones: str):
        """Separa las opciones por comas. Ejemplo: Pizza, Hamburguesa, Tacos"""
        lista = [x.strip() for x in opciones.split(",") if x.strip()]
        if len(lista) < 2:
            await interaction.response.send_message("⚠️ Dame al menos 2 opciones separadas por comas.", ephemeral=True)
            return
        
        elegido = random.choice(lista)
        embed = discord.Embed(title="🤔 Decisión Difícil", color=Theme.get_color(interaction.guild.id, 'primary'))
        embed.add_field(name="Opciones", value=", ".join(lista), inline=False)
        embed.add_field(name="Elijo...", value=f"✨ **{elegido}** ✨", inline=False)
        embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="buscaminas", description="Genera un tablero de buscaminas jugable")
    async def buscaminas(self, interaction: discord.Interaction, minas: int = 8):
        if minas > 20: minas = 20
        if minas < 1: minas = 1
        
        rows, cols = 8, 8
        grid = [[0 for _ in range(cols)] for _ in range(rows)]
        mines_placed = 0
        
        while mines_placed < minas:
            r, c = random.randint(0, rows-1), random.randint(0, cols-1)
            if grid[r][c] != -1:
                grid[r][c] = -1
                mines_placed += 1
        
        for r in range(rows):
            for c in range(cols):
                if grid[r][c] == -1: continue
                count = 0
                for i in range(max(0, r-1), min(rows, r+2)):
                    for j in range(max(0, c-1), min(cols, c+2)):
                        if grid[i][j] == -1: count += 1
                grid[r][c] = count

        emojis = {
            0: "🟦", 1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 
            5: "5️⃣", 6: "6️⃣", 7: "7️⃣", 8: "8️⃣", -1: "💥"
        }
        
        text = ""
        for r in range(rows):
            for c in range(cols):
                val = grid[r][c]
                text += f"||{emojis.get(val, '🟦')}||"
            text += "\n"
        
        embed = discord.Embed(title="💣 Buscaminas", description=f"**Minas:** {minas}\n¡Haz clic en los spoilers para revelar!", color=Theme.get_color(interaction.guild.id, 'secondary'))
        embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
        await interaction.response.send_message(content=text, embed=embed)

    @app_commands.command(name="ship", description="Calcula el porcentaje de amor entre usuarios")
    async def ship(self, interaction: discord.Interaction, usuario1: discord.User, usuario2: discord.User = None):
        u2 = usuario2 or interaction.user
        if usuario1.id == u2.id:
            await interaction.response.send_message("💔 No puedes hacer ship contigo mismo (amor propio es importante, pero...).", ephemeral=True)
            return

        # Seed based on IDs so it's consistent for the same pair
        random.seed(usuario1.id + u2.id)
        percent = random.randint(0, 100)
        random.seed() # Reset seed

        bar_len = 10
        filled = int(percent / 10)
        bar = "💖" * filled + "🖤" * (bar_len - filled)
        
        msg = ""
        if percent < 20: msg = "💔 Ni lo intenten..."
        elif percent < 50: msg = "😐 Solo amigos."
        elif percent < 80: msg = "😏 Hay química."
        elif percent < 100: msg = "🔥 ¡Son tal para cual!"
        else: msg = "💍 ¡Boda inminente!"

        embed = discord.Embed(title="💘 Love Calculator", description=f"{usuario1.mention} ❤️ {u2.mention}", color=Theme.get_color(interaction.guild.id, 'primary'))
        embed.add_field(name="Compatibilidad", value=f"**{percent}%**\n{bar}\n\n{msg}")
        embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="hack", description="Simula un hackeo a un usuario (Fake)")
    async def hack(self, interaction: discord.Interaction, usuario: discord.User):
        await interaction.response.send_message(f"💻 Iniciando ataque a {usuario.name}...", ephemeral=False)
        msg = await interaction.original_response()
        
        pasos = [
            "🔍 Buscando dirección IP...",
            "🔓 IP Encontrada: 192.168.1.XX",
            "🔑 Descifrando contraseñas...",
            "📂 Descargando historial de búsqueda...",
            "😳 ¡Madre mía! Qué historial...",
            "📤 Subiendo datos a la Dark Web...",
            "✅ Hackeo completado. Se han robado 0 monedas."
        ]
        
        for paso in pasos:
            await asyncio.sleep(2)
            try:
                await msg.edit(content=f"💻 {paso}")
            except:
                pass
        
        await msg.edit(content=f"💀 Hackeo a {usuario.mention} finalizado con éxito. (Es broma 🤡)")

    @app_commands.command(name="meme_txt", description="Genera un meme de texto aleatorio")
    async def meme_txt(self, interaction: discord.Interaction):
        memes = [
            "Cuando el código compila a la primera:\nWait, that's illegal.",
            "Yo: *arregla un bug*\nEl código: *crea 5 bugs nuevos*",
            "Cliente: ¿Y esto es difícil de hacer?\nYo: *Llora en stackoverflow*",
            "Mi código no funciona, no sé por qué.\nMi código funciona, no sé por qué.",
            "Git push --force\n*El equipo de desarrollo colapsa*",
            "Junior: Borré la base de datos de producción.\nSenior: ¿Que borraste QUÉ?",
            "Yo a las 3 AM programando:\nSoy un dios.\nYo al día siguiente leyendo mi código:\n¿Quién escribió esta basura?"
        ]
        meme = random.choice(memes)
        embed = discord.Embed(title="😂 Meme de Programador", description=meme, color=Theme.get_color(interaction.guild.id, 'secondary'))
        embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Diversion(bot))
