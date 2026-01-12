import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio

# --- Constantes y "Sprites" (Emojis) ---
SPRITE_PLAYER = "🧙‍♂️"
SPRITE_GRASS = "🟩"
SPRITE_TREE = "🌲"
SPRITE_WALL = "🧱"
SPRITE_WATER = "🟦"
SPRITE_CHEST = "🎁"
SPRITE_ENEMY = "👹"
SPRITE_BOSS = "🐉"
SPRITE_TOWN = "🏰"
SPRITE_MOUNTAIN = "⛰️"

# Mapas predefinidos o generación
MAP_SIZE = 9  # 9x9 grid

class RPGGame:
    def __init__(self, player_id):
        self.player_id = player_id
        self.x = 4
        self.y = 4
        self.level = 1
        self.hp = 100
        self.max_hp = 100
        self.xp = 0
        self.gold = 0
        self.inventory = []
        self.map_data = self.generate_map()
        self.in_combat = False
        self.current_enemy = None
        self.state = "EXPLORING" # EXPLORING, COMBAT, EVENT

    def generate_map(self):
        # Generar un mapa simple con bordes y obstáculos aleatorios
        grid = [[SPRITE_GRASS for _ in range(MAP_SIZE)] for _ in range(MAP_SIZE)]
        
        # Bordes
        for i in range(MAP_SIZE):
            grid[0][i] = SPRITE_TREE
            grid[MAP_SIZE-1][i] = SPRITE_TREE
            grid[i][0] = SPRITE_TREE
            grid[i][MAP_SIZE-1] = SPRITE_TREE

        # Obstáculos aleatorios
        for _ in range(10):
            rx, ry = random.randint(1, MAP_SIZE-2), random.randint(1, MAP_SIZE-2)
            if (rx, ry) != (4, 4):
                grid[ry][rx] = random.choice([SPRITE_MOUNTAIN, SPRITE_WATER, SPRITE_TREE])

        # Cofres
        for _ in range(3):
            rx, ry = random.randint(1, MAP_SIZE-2), random.randint(1, MAP_SIZE-2)
            if (rx, ry) != (4, 4) and grid[ry][rx] == SPRITE_GRASS:
                grid[ry][rx] = SPRITE_CHEST

        # Enemigos visibles (opcional, aunque usaremos encuentros aleatorios)
        # Ciudad central
        grid[4][4] = SPRITE_TOWN
        return grid

    def render_map(self):
        # Renderiza el mapa centrando al jugador o mostrando todo si es pequeño
        # Aquí mostramos todo el grid 9x9
        display = ""
        for y in range(MAP_SIZE):
            row = ""
            for x in range(MAP_SIZE):
                if x == self.x and y == self.y:
                    row += SPRITE_PLAYER
                else:
                    row += self.map_data[y][x]
            display += row + "\n"
        return display

    def move(self, dx, dy):
        nx, ny = self.x + dx, self.y + dy
        if 0 <= nx < MAP_SIZE and 0 <= ny < MAP_SIZE:
            tile = self.map_data[ny][nx]
            if tile in [SPRITE_TREE, SPRITE_WALL, SPRITE_WATER, SPRITE_MOUNTAIN]:
                return "BLOCKED"
            self.x, self.y = nx, ny
            return self.check_tile(tile)
        return "BLOCKED"

    def check_tile(self, tile):
        if tile == SPRITE_CHEST:
            self.map_data[self.y][self.x] = SPRITE_GRASS
            loot = random.randint(10, 50)
            self.gold += loot
            return f"CHEST:{loot}"
        elif tile == SPRITE_TOWN:
            self.hp = self.max_hp
            return "TOWN"
        elif tile == SPRITE_GRASS:
            if random.random() < 0.2: # 20% chance encounter
                return "ENCOUNTER"
        return "MOVE"

class RPGView(discord.ui.View):
    def __init__(self, game: RPGGame, user_id: int):
        super().__init__(timeout=300)
        self.game = game
        self.user_id = user_id
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        if self.game.state == "EXPLORING":
            # Movement Buttons
            self.add_item(RPGButton("⬆️", 0, -1, 1))
            self.add_item(RPGButton("⬅️", -1, 0, 2))
            self.add_item(RPGButton("⬇️", 0, 1, 3))
            self.add_item(RPGButton("➡️", 1, 0, 4))
            self.add_item(RPGActionButton("🎒 Info", "INFO", discord.ButtonStyle.secondary, 2))
        elif self.game.state == "COMBAT":
            self.add_item(RPGActionButton("⚔️ Atacar", "ATTACK", discord.ButtonStyle.danger, 1))
            self.add_item(RPGActionButton("🛡️ Defender", "DEFEND", discord.ButtonStyle.primary, 1))
            self.add_item(RPGActionButton("🏃 Huir", "FLEE", discord.ButtonStyle.secondary, 2))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⛔ Esta no es tu partida.", ephemeral=True)
            return False
        return True

class RPGButton(discord.ui.Button):
    def __init__(self, label, dx, dy, row):
        super().__init__(label=label, style=discord.ButtonStyle.primary, row=row)
        self.dx = dx
        self.dy = dy

    async def callback(self, interaction: discord.Interaction):
        view: RPGView = self.view
        res = view.game.move(self.dx, self.dy)
        
        msg_content = ""
        if res == "BLOCKED":
            msg_content = "🚫 Camino bloqueado."
        elif res.startswith("CHEST"):
            amount = res.split(":")[1]
            msg_content = f"🎁 ¡Encontraste un cofre con {amount} monedas!"
        elif res == "TOWN":
            msg_content = "🏰 Descansaste en la ciudad. HP restaurado."
        elif res == "ENCOUNTER":
            view.game.state = "COMBAT"
            view.game.current_enemy = {"name": "Goblin", "hp": 30, "max_hp": 30, "atk": 5, "sprite": "https://i.imgur.com/8l6D0i3.png"} # Placeholder sprite
            msg_content = "⚔️ ¡Un enemigo salvaje apareció!"
            view.update_buttons()
        
        embed = create_rpg_embed(view.game, msg_content)
        await interaction.response.edit_message(embed=embed, view=view)

class RPGActionButton(discord.ui.Button):
    def __init__(self, label, action, style, row):
        super().__init__(label=label, style=style, row=row)
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        view: RPGView = self.view
        game = view.game
        msg_content = ""

        if self.action == "INFO":
            msg_content = f"📊 Nivel: {game.level} | XP: {game.xp} | Oro: {game.gold}"
        
        elif self.action == "ATTACK":
            enemy = game.current_enemy
            dmg = random.randint(5, 15)
            enemy["hp"] -= dmg
            msg_content = f"⚔️ Atacaste al {enemy['name']} e hiciste **{dmg}** de daño."
            
            if enemy["hp"] <= 0:
                xp_gain = 20
                gold_gain = 10
                game.xp += xp_gain
                game.gold += gold_gain
                game.state = "EXPLORING"
                game.current_enemy = None
                view.update_buttons()
                msg_content += f"\n💀 ¡Derrotaste al enemigo! Ganaste {xp_gain} XP y {gold_gain} oro."
            else:
                # Enemy turn
                enemy_dmg = max(0, enemy["atk"] - random.randint(0, 2))
                game.hp -= enemy_dmg
                msg_content += f"\n👹 El {enemy['name']} contraataca e inflige **{enemy_dmg}** de daño."
                if game.hp <= 0:
                    game.state = "GAME_OVER"
                    view.clear_items()
                    msg_content += "\n💀 **¡Has muerto!** Fin del juego."

        elif self.action == "DEFEND":
            game.hp = min(game.max_hp, game.hp + 5)
            msg_content = "🛡️ Te defendiste y recuperaste un poco de salud."
            # Enemy attacks with reduced damage
            enemy = game.current_enemy
            enemy_dmg = max(0, int(enemy["atk"] * 0.5))
            game.hp -= enemy_dmg
            msg_content += f"\n👹 El {enemy['name']} ataca pero bloqueas parte del daño (-{enemy_dmg} HP)."
            if game.hp <= 0:
                game.state = "GAME_OVER"
                view.clear_items()
                msg_content += "\n💀 **¡Has muerto!**"

        elif self.action == "FLEE":
            if random.random() < 0.5:
                game.state = "EXPLORING"
                game.current_enemy = None
                view.update_buttons()
                msg_content = "🏃 Escapaste con éxito."
            else:
                enemy = game.current_enemy
                enemy_dmg = enemy["atk"]
                game.hp -= enemy_dmg
                msg_content = f"🚫 No lograste escapar. El enemigo te golpea por {enemy_dmg} HP."
                if game.hp <= 0:
                    game.state = "GAME_OVER"
                    view.clear_items()
                    msg_content += "\n💀 **¡Has muerto!**"

        embed = create_rpg_embed(game, msg_content)
        await interaction.response.edit_message(embed=embed, view=view)

def create_rpg_embed(game, status_msg=""):
    if game.state == "GAME_OVER":
        embed = discord.Embed(title="💀 GAME OVER", description=status_msg, color=discord.Color.red())
        return embed

    embed = discord.Embed(title="🗺️ Poseidon RPG", color=discord.Color.green())
    
    if game.state == "EXPLORING":
        map_str = game.render_map()
        embed.description = f"**Mundo Abierto**\n\n{map_str}\n\n{status_msg}"
        embed.add_field(name="Estado", value=f"❤️ HP: {game.hp}/{game.max_hp}\n💰 Oro: {game.gold}\n📍 Pos: ({game.x}, {game.y})")
    
    elif game.state == "COMBAT":
        enemy = game.current_enemy
        embed.title = "⚔️ ¡En Combate!"
        embed.color = discord.Color.red()
        # Sprite visual del enemigo (usando imagen real o emoji grande)
        if enemy.get("sprite"):
            embed.set_thumbnail(url=enemy["sprite"])
        
        embed.description = f"**🆚 {enemy['name']}**\n{SPRITE_ENEMY*3}\n\n{status_msg}"
        
        embed.add_field(name="Tu Héroe", value=f"❤️ HP: {game.hp}/{game.max_hp}", inline=True)
        embed.add_field(name="Enemigo", value=f"❤️ HP: {enemy['hp']}/{enemy['max_hp']}", inline=True)

    return embed

class RPG(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.games = {} # user_id -> RPGGame

    @app_commands.command(name="rpg", description="Inicia una aventura RPG gráfica")
    async def start_rpg(self, interaction: discord.Interaction):
        # Iniciar nueva partida
        game = RPGGame(interaction.user.id)
        self.games[interaction.user.id] = game
        
        view = RPGView(game, interaction.user.id)
        embed = create_rpg_embed(game, "¡Bienvenido al mundo de Poseidon! Usa los botones para moverte.")
        
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(RPG(bot))
