import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
from bot.themes import Theme

# Constantes de cartas
SUITS = ["♠️", "♥️", "♦️", "♣️"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
VALUES = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10,
    "J": 10, "Q": 10, "K": 10, "A": 11
}

class Deck:
    def __init__(self):
        self.cards = [(r, s) for s in SUITS for r in RANKS]
        random.shuffle(self.cards)

    def draw(self):
        return self.cards.pop()

def calculate_hand(hand):
    value = sum(VALUES[card[0]] for card in hand)
    aces = sum(1 for card in hand if card[0] == "A")
    
    while value > 21 and aces:
        value -= 10
        aces -= 1
    return value

def format_hand(hand, hide_second=False):
    if hide_second:
        return f"[{hand[0][0]}{hand[0][1]}] [??]"
    return " ".join([f"[{r}{s}]" for r, s in hand])

class BlackjackView(discord.ui.View):
    def __init__(self, bot, user, bet, deck, player_hand, dealer_hand):
        super().__init__(timeout=120)
        self.bot = bot
        self.user = user
        self.bet = bet
        self.deck = deck
        self.player_hand = player_hand
        self.dealer_hand = dealer_hand
        self.finished = False
        self.first_turn = True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("⛔ No es tu partida.", ephemeral=True)
            return False
        return True

    async def update_message(self, interaction, result_msg=None, color=None, final=False):
        if color is None:
            color = Theme.get_color(interaction.guild.id, 'primary')
            
        player_val = self.calculate_hand(self.player_hand)
        dealer_val = self.calculate_hand(self.dealer_hand)
        
        desc = f"🃏 **Tu Mano:** {self.format_hand(self.player_hand)} (Valor: {player_val})\n"
        
        if result_msg:
            desc += f"**{result_msg}**"

        embed = discord.Embed(
            title=f"🎰 Blackjack - Apuesta: {self.bet}",
            description=desc,
            color=color
        )
        embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
        
        if final:
            self.clear_items()
            self.finished = True
            self.stop()
        else:
            # Actualizar estado de botones Doblar/Rendirse
            for child in self.children:
                if isinstance(child, discord.ui.Button) and child.label in ["Doblar", "Rendirse"]:
                    child.disabled = not self.first_turn
        
        if interaction.response.is_done():
            await interaction.message.edit(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Pedir", style=discord.ButtonStyle.success, emoji="🃏", row=0)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.first_turn = False
        self.player_hand.append(self.deck.draw())
        val = calculate_hand(self.player_hand)
        
        if val > 21:
            await self.update_message(interaction, "💥 ¡Te pasaste! Pierdes.", Theme.get_color(interaction.guild.id, 'error'), final=True)
        elif val == 21:
            # Auto-plantarse si llega a 21
            await self.stand_logic(interaction)
        else:
            await self.update_message(interaction)

    @discord.ui.button(label="Plantarse", style=discord.ButtonStyle.danger, emoji="🛑", row=0)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.stand_logic(interaction)

    @discord.ui.button(label="Doblar", style=discord.ButtonStyle.primary, emoji="💰", row=1)
    async def double(self, interaction: discord.Interaction, button: discord.ui.Button):
        monedas = self.bot.get_cog("Monedas")
        if not monedas:
            await interaction.response.send_message("⚠️ Error de economía.", ephemeral=True)
            return

        if not monedas.remove_balance(self.user.id, self.bet):
            await interaction.response.send_message("❌ No tienes suficientes monedas para doblar.", ephemeral=True)
            return

        self.bet *= 2
        self.player_hand.append(self.deck.draw())
        val = calculate_hand(self.player_hand)
        
        if val > 21:
            await self.update_message(interaction, f"💥 Doblaste y te pasaste ({val}). Pierdes {self.bet}.", Theme.get_color(interaction.guild.id, 'error'), final=True)
        else:
            # Doblar implica pedir una carta y plantarse automáticamente
            await self.stand_logic(interaction)

    @discord.ui.button(label="Rendirse", style=discord.ButtonStyle.secondary, emoji="🏳️", row=1)
    async def surrender(self, interaction: discord.Interaction, button: discord.ui.Button):
        monedas = self.bot.get_cog("Monedas")
        refund = int(self.bet / 2)
        if monedas:
            monedas.add_balance(self.user.id, refund)
            
        await self.update_message(interaction, f"🏳️ Te rendiste. Recuperas {refund} (50%).", Theme.get_color(interaction.guild.id, 'secondary'), final=True)

    async def stand_logic(self, interaction):
        # Turno del dealer
        while calculate_hand(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deck.draw())
        
        p_val = calculate_hand(self.player_hand)
        d_val = calculate_hand(self.dealer_hand)
        
        monedas = self.bot.get_cog("Monedas")
        
        if d_val > 21:
            winnings = self.bet * 2
            if monedas: monedas.add_balance(self.user.id, winnings)
            msg = f"🎉 Dealer se pasó. ¡Ganas {winnings}!"
            col = Theme.get_color(interaction.guild.id, 'success')
        elif p_val > d_val:
            winnings = self.bet * 2
            if monedas: monedas.add_balance(self.user.id, winnings)
            msg = f"🎉 ¡Ganaste! Tienes {p_val} vs {d_val}. (+{winnings})"
            col = Theme.get_color(interaction.guild.id, 'success')
        elif p_val == d_val:
            if monedas: monedas.add_balance(self.user.id, self.bet) # Devolver apuesta
            msg = f"🤝 Empate. Recuperas tu apuesta."
            col = Theme.get_color(interaction.guild.id, 'secondary')
        else:
            msg = f"💀 Dealer gana con {d_val} vs {p_val}. Pierdes {self.bet}."
            col = Theme.get_color(interaction.guild.id, 'error')
            
        await self.update_message(interaction, msg, col, final=True)

class Casino(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Grupo principal /casino
    casino_group = app_commands.Group(name="casino", description="Juegos de azar y apuestas")

    @casino_group.command(name="blackjack", description="Juega al Blackjack y apuesta monedas")
    @app_commands.describe(apuesta="Cantidad de monedas a apostar")
    async def blackjack(self, interaction: discord.Interaction, apuesta: int):
        if apuesta < 10:
            await interaction.response.send_message("⚠️ Apuesta mínima: 10 monedas.", ephemeral=True)
            return

        monedas = self.bot.get_cog("Monedas")
        if not monedas:
            await interaction.response.send_message("⚠️ Sistema de economía no disponible.", ephemeral=True)
            return

        if not monedas.remove_balance(interaction.user.id, apuesta):
            await interaction.response.send_message("❌ No tienes suficientes monedas.", ephemeral=True)
            return

        deck = Deck()
        player_hand = [deck.draw(), deck.draw()]
        dealer_hand = [deck.draw(), deck.draw()]

        # Verificar Blackjack natural inmediato
        p_val = calculate_hand(player_hand)
        d_val = calculate_hand(dealer_hand)
        
        if p_val == 21:
            if d_val == 21:
                monedas.add_balance(interaction.user.id, apuesta)
                embed = discord.Embed(
                    title=f"🎰 Blackjack - Apuesta: {apuesta}",
                    description=f"**Tu mano:** {format_hand(player_hand)} (21)\n**Dealer:** {format_hand(dealer_hand)} (21)\n\n🤝 **Empate de Blackjacks.** Recuperas apuesta.",
                    color=Theme.get_color(interaction.guild.id, 'secondary')
                )
                embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
                await interaction.response.send_message(embed=embed)
                return
            else:
                winnings = int(apuesta * 2.5) # Pago 3:2 (apuesta + 1.5*apuesta)
                monedas.add_balance(interaction.user.id, winnings)
                embed = discord.Embed(
                    title=f"🎰 Blackjack - Apuesta: {apuesta}",
                    description=f"**Tu mano:** {format_hand(player_hand)} (21)\n**Dealer:** {format_hand(dealer_hand)} ({d_val})\n\n🎉 **¡BLACKJACK!** Ganas {winnings} (Pago 3:2).",
                    color=Theme.get_color(interaction.guild.id, 'primary')
                )
                embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
                await interaction.response.send_message(embed=embed)
                return

        view = BlackjackView(self.bot, interaction.user, apuesta, deck, player_hand, dealer_hand)
        
        embed = discord.Embed(
            title=f"🎰 Blackjack - Apuesta: {apuesta}",
            description=f"**Tu mano:** {format_hand(player_hand)} ({p_val})\n**Dealer:** {format_hand(dealer_hand, hide_second=True)} (?)\n\n¿Pedir o Plantarse?",
            color=Theme.get_color(interaction.guild.id, 'primary')
        )
        embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
        await interaction.response.send_message(embed=embed, view=view)

    @casino_group.command(name="ruleta", description="Apuesta en la ruleta: Número (0-36), Color (rojo/negro) o Paridad (par/impar)")
    @app_commands.describe(apuesta="Cantidad de monedas a apostar", eleccion="Tu apuesta: 0-36, rojo, negro, par, impar")
    async def ruleta(self, interaction: discord.Interaction, apuesta: int, eleccion: str):
        if apuesta < 10:
            await interaction.response.send_message("⚠️ Apuesta mínima: 10 monedas.", ephemeral=True)
            return

        monedas = self.bot.get_cog("Monedas")
        if not monedas:
            await interaction.response.send_message("⚠️ Sistema de economía no disponible.", ephemeral=True)
            return

        if not monedas.remove_balance(interaction.user.id, apuesta):
            await interaction.response.send_message("❌ No tienes suficientes monedas.", ephemeral=True)
            return

        # Normalizar elección
        eleccion = eleccion.lower().strip()
        
        # Definir datos de la ruleta
        red_numbers = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
        black_numbers = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}
        
        # Validar apuesta
        bet_type = None # "number", "color", "parity"
        target_value = None
        
        if eleccion in ["rojo", "negro"]:
            bet_type = "color"
            target_value = eleccion
        elif eleccion in ["par", "impar"]:
            bet_type = "parity"
            target_value = eleccion
        elif eleccion.isdigit():
            val = int(eleccion)
            if 0 <= val <= 36:
                bet_type = "number"
                target_value = val
            else:
                monedas.add_balance(interaction.user.id, apuesta)
                await interaction.response.send_message("⚠️ El número debe estar entre 0 y 36.", ephemeral=True)
                return
        else:
            monedas.add_balance(interaction.user.id, apuesta)
            await interaction.response.send_message("⚠️ Opción no válida. Usa: número (0-36), 'rojo', 'negro', 'par' o 'impar'.", ephemeral=True)
            return

        # Girar la ruleta
        result_number = random.randint(0, 36)
        
        # Determinar atributos del resultado
        result_color = "verde" # 0
        if result_number in red_numbers:
            result_color = "rojo"
        elif result_number in black_numbers:
            result_color = "negro"
            
        result_parity = "ninguno" # 0
        if result_number != 0:
            result_parity = "par" if result_number % 2 == 0 else "impar"

        # Verificar victoria
        won = False
        payout = 0
        
        if bet_type == "number":
            if target_value == result_number:
                won = True
                payout = apuesta * 36 # Pago 35:1 (más la apuesta original implícita si no se hubiera quitado, aquí devolvemos total 36x)
        elif bet_type == "color":
            if target_value == result_color:
                won = True
                payout = apuesta * 2
        elif bet_type == "parity":
            if target_value == result_parity:
                won = True
                payout = apuesta * 2
        
        # Mensaje resultado
        color_map = {"rojo": "🟥", "negro": "⬛", "verde": "🟩"}
        emoji_color = color_map.get(result_color, "⬜")
        
        desc = f"La bola cayó en: **{emoji_color} {result_number} ({result_color.upper()})**"
        
        if won:
            monedas.add_balance(interaction.user.id, payout)
            embed = discord.Embed(title="🎰 Ruleta - ¡Ganaste!", description=f"{desc}\n\n🎉 **¡Felicidades!** Ganaste **{payout}** monedas.", color=Theme.get_color(interaction.guild.id, 'success'))
        else:
            embed = discord.Embed(title="🎰 Ruleta - Perdiste", description=f"{desc}\n\n💸 Perdiste {apuesta} monedas. ¡Suerte para la próxima!", color=Theme.get_color(interaction.guild.id, 'error'))
            
        embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
        await interaction.response.send_message(embed=embed)

    @casino_group.command(name="slots", description="Apuesta tus monedas en la tragaperras")
    @app_commands.describe(apuesta="Cantidad de monedas a apostar")
    async def slots(self, interaction: discord.Interaction, apuesta: int):
        uid = interaction.user.id
        if apuesta <= 0:
            await interaction.response.send_message("⚠️ La apuesta debe ser mayor a 0.", ephemeral=True)
            return
        
        monedas = self.bot.get_cog("Monedas")
        if not monedas:
            await interaction.response.send_message("⚠️ Sistema de economía no disponible.", ephemeral=True)
            return

        if not monedas.remove_balance(uid, apuesta):
            await interaction.response.send_message(f"⚠️ No tienes suficientes monedas.", ephemeral=True)
            return
        
        emojis = ["🍒", "🍋", "🔔", "💎", "7️⃣"]
        a = random.choice(emojis)
        b = random.choice(emojis)
        c = random.choice(emojis)
        
        resultado = f"🎰 | {a} | {b} | {c} |"
        
        ganancia = 0
        if a == b == c:
            if a == "7️⃣":
                ganancia = apuesta * 10
                msg = f"🎉 ¡JACKPOT! Ganaste {ganancia} monedas."
            else:
                ganancia = apuesta * 5
                msg = f"🎉 ¡Tres iguales! Ganaste {ganancia} monedas."
        elif a == b or b == c or a == c:
            ganancia = int(apuesta * 1.5)
            msg = f"✨ ¡Dos iguales! Recuperas {ganancia} monedas."
        else:
            msg = "😢 Perdiste. Inténtalo de nuevo."
            
        if ganancia > 0:
            monedas.add_balance(uid, ganancia)
            
        color = Theme.get_color(interaction.guild.id, 'success') if ganancia > 0 else Theme.get_color(interaction.guild.id, 'error')
        embed = discord.Embed(title="Tragaperras 🎰", description=f"{resultado}\n\n{msg}", color=color)
        embed.set_footer(text=f"{Theme.get_footer_text(interaction.guild.id)}")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Casino(bot))
