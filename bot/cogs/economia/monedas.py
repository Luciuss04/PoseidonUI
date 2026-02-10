import time
import random
import json
import os

import discord
from discord import app_commands
from discord.ext import commands
from bot.themes import Theme

class Monedas(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.file_path = "economy.json"
        self.stock_file = "stocks.json"
        self.bal: dict[str, int] = {} # Keys as strings for JSON compatibility
        self.daily_ts: dict[str, int] = {}
        self.stocks: dict[str, dict] = {} # "TICKER": {"price": 100, "trend": 0.5}
        self.user_stocks: dict[str, dict] = {} # "user_id": {"TICKER": amount}
        self.jobs: dict[str, dict] = {} # "user_id": {"job": "name", "level": 1, "xp": 0}
        self._load_data()
        self._init_stocks()

    def _init_stocks(self):
        # Initialize default stocks if empty
        if not self.stocks:
            self.stocks = {
                "POSE": {"name": "Poseidon Inc.", "price": 100.0, "volatility": 2.0},
                "NECT": {"name": "Néctar Sagrado", "price": 50.0, "volatility": 1.5},
                "GOLD": {"name": "Minas de Oro", "price": 200.0, "volatility": 1.0},
                "FORG": {"name": "Fragua de Hefesto", "price": 150.0, "volatility": 3.0}
            }

    def _load_data(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.bal = data.get("balances", {})
                    self.daily_ts = data.get("daily_ts", {})
                    self.user_stocks = data.get("user_stocks", {})
                    self.jobs = data.get("jobs", {})
            except Exception:
                pass
        
        if os.path.exists(self.stock_file):
            try:
                with open(self.stock_file, "r", encoding="utf-8") as f:
                    self.stocks = json.load(f)
            except Exception:
                pass

    def _save_data(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump({
                "balances": self.bal, 
                "daily_ts": self.daily_ts,
                "user_stocks": self.user_stocks,
                "jobs": self.jobs
            }, f, indent=4)
        
        with open(self.stock_file, "w", encoding="utf-8") as f:
            json.dump(self.stocks, f, indent=4)

    def _update_stocks(self):
        # Simulate market movement
        for ticker, data in self.stocks.items():
            change = random.uniform(-data['volatility'], data['volatility'])
            # Market bias based on random event chance
            if random.random() < 0.1: # 10% chance of major swing
                change *= 3
            
            new_price = max(1.0, data['price'] + change)
            data['price'] = round(new_price, 2)
        self._save_data()

    def get_balance(self, user_id: int) -> int:
        return self.bal.get(str(user_id), 0)

    def add_balance(self, user_id: int, amount: int):
        uid = str(user_id)
        self.bal[uid] = self.bal.get(uid, 0) + amount
        self._save_data()

    def remove_balance(self, user_id: int, amount: int) -> bool:
        """Returns True if successful, False if insufficient funds"""
        uid = str(user_id)
        current = self.bal.get(uid, 0)
        if current < amount:
            return False
        self.bal[uid] = current - amount
        self._save_data()
        return True

    def _add(self, uid: int, amt: int):
        # Internal helper kept for backward compatibility with existing commands logic
        self.add_balance(uid, amt)

    # Grupo principal /eco
    eco_group = app_commands.Group(name="eco", description="Sistema de economía global")

    @eco_group.command(name="balance", description="Muestra tu saldo")
    async def balance(
        self, interaction: discord.Interaction, usuario: discord.User | None = None
    ):
        uid = (usuario or interaction.user).id
        val = self.get_balance(uid)
        await interaction.response.send_message(
            f"💰 Saldo de {usuario.mention if usuario else interaction.user.mention}: {val}"
        )
        try:
            e = interaction.client.build_log_embed(
                "Economía/Monedas",
                "Consulta de saldo",
                user=interaction.user,
                guild=interaction.guild,
                extra={"Usuario": str(uid), "Saldo": str(val)},
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @eco_group.command(name="daily", description="Reclama tu recompensa diaria")
    async def daily(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        now = int(time.time())
        last = self.daily_ts.get(uid, 0)
        if now - last < 86400:
            next_time = last + 86400
            wait = next_time - now
            hours = wait // 3600
            mins = (wait % 3600) // 60
            await interaction.response.send_message(
                f"⚠️ Ya reclamaste hoy. Vuelve en {hours}h {mins}m.", ephemeral=True
            )
            return
        self.daily_ts[uid] = now
        self.add_balance(interaction.user.id, 100)
        self._save_data()
        await interaction.response.send_message("✅ Recibiste 100 monedas.")
        try:
            e = interaction.client.build_log_embed(
                "Economía/Monedas",
                "Daily reclamado",
                user=interaction.user,
                guild=interaction.guild,
                extra={"Cantidad": "100"},
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @eco_group.command(name="work", description="Trabaja para ganar monedas")
    async def work(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        now = int(time.time())
        work_key = f"work_{uid}"
        last = self.daily_ts.get(work_key, 0)
        
        cooldown = 3600 # 1 hora
        if now - last < cooldown:
            wait = (last + cooldown) - now
            mins = wait // 60
            secs = wait % 60
            await interaction.response.send_message(f"⏳ Debes descansar. Vuelve en {mins}m {secs}s.", ephemeral=True)
            return

        self.daily_ts[work_key] = now
        
        # Job logic
        user_job = self.jobs.get(uid, {"job": "Desempleado", "level": 1, "xp": 0})
        base_earnings = random.randint(30, 80)
        
        # Level multiplier
        multiplier = 1.0 + (user_job['level'] * 0.1)
        earnings = int(base_earnings * multiplier)
        
        # XP gain
        level = user_job['level']
        xp_needed = level * 100
        user_job['xp'] += 10
        leveled_up = False

        if user_job['xp'] >= xp_needed:
            user_job['xp'] = 0
            user_job['level'] += 1
            leveled_up = True
            
        self.jobs[uid] = user_job
        self.add_balance(interaction.user.id, earnings)
        self._save_data()
        
        jobs_list = ["forjando armas", "limpiando el templo", "alimentando pegasos", "guiando almas", "puliendo estatuas"]
        job = random.choice(jobs_list)
        current_xp = user_job['xp']
        
        embed = discord.Embed(
            title="🔨 Trabajo Realizado", 
            description=f"Trabajaste como **{job}** (Nivel {level}) y ganaste **{earnings}** monedas.\nXP: {current_xp}/{xp_needed}", 
            color=Theme.get_color(interaction.guild.id, 'primary')
        )
        if leveled_up:
            embed.add_field(name="🎉 ¡Ascenso!", value=f"Has subido al nivel {level+1}. Tu sueldo base ha aumentado.", inline=False)
        embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
        await interaction.response.send_message(embed=embed)
        try:
            e = interaction.client.build_log_embed(
                "Economía/Monedas",
                "Work ejecutado",
                user=interaction.user,
                guild=interaction.guild,
                extra={"Cantidad": str(earnings), "Trabajo": job, "Nivel": str(user_job['level'])},
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @eco_group.command(name="bolsa", description="Mercado de valores")
    @app_commands.describe(accion="Ver, Comprar, Vender", ticker="Símbolo de la acción (ej. POSE)", cantidad="Cantidad de acciones")
    @app_commands.choices(accion=[
        app_commands.Choice(name="Ver Mercado", value="ver"),
        app_commands.Choice(name="Comprar Acciones", value="comprar"),
        app_commands.Choice(name="Vender Acciones", value="vender"),
        app_commands.Choice(name="Mi Portafolio", value="portfolio")
    ])
    async def bolsa(self, interaction: discord.Interaction, accion: str, ticker: str = None, cantidad: int = 1):
        self._update_stocks() # Refresh prices
        uid = str(interaction.user.id)
        
        if accion == "ver":
            embed = discord.Embed(title="📈 Mercado de Valores", color=Theme.get_color(interaction.guild.id, 'secondary'))
            for t, data in self.stocks.items():
                trend = "🟢" if random.random() > 0.5 else "🔴" # Visual trend for now
                embed.add_field(name=f"{t} - {data['name']}", value=f"Precio: **{data['price']}** 💰 {trend}", inline=False)
            embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
            await interaction.response.send_message(embed=embed)
            
        elif accion == "portfolio":
            user_portfolio = self.user_stocks.get(uid, {})
            if not user_portfolio:
                await interaction.response.send_message("❌ No tienes acciones.", ephemeral=True)
                return
            
            embed = discord.Embed(title=f"💼 Portafolio de {interaction.user.display_name}", color=Theme.get_color(interaction.guild.id, 'secondary'))
            total_value = 0
            for t, amt in user_portfolio.items():
                if amt > 0:
                    current_price = self.stocks.get(t, {}).get('price', 0)
                    value = amt * current_price
                    total_value += value
                    embed.add_field(name=t, value=f"Acciones: {amt}\nValor: {int(value)} 💰", inline=True)
            
            embed.description = f"**Valor Total:** {int(total_value)} 💰"
            embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
            await interaction.response.send_message(embed=embed)

        elif accion == "comprar":
            if not ticker or ticker not in self.stocks:
                await interaction.response.send_message("❌ Ticker inválido. Usa /bolsa ver para ver disponibles.", ephemeral=True)
                return
            if cantidad <= 0:
                await interaction.response.send_message("❌ Cantidad inválida.", ephemeral=True)
                return
                
            cost = self.stocks[ticker]['price'] * cantidad
            if not self.remove_balance(interaction.user.id, cost):
                await interaction.response.send_message(f"❌ No tienes suficientes monedas. Costo: {int(cost)}", ephemeral=True)
                return
            
            if uid not in self.user_stocks: self.user_stocks[uid] = {}
            self.user_stocks[uid][ticker] = self.user_stocks[uid].get(ticker, 0) + cantidad
            self._save_data()
            
            await interaction.response.send_message(f"✅ Compraste {cantidad} acciones de **{ticker}** por **{int(cost)}** monedas.")

        elif accion == "vender":
            if not ticker or ticker not in self.stocks:
                await interaction.response.send_message("❌ Ticker inválido.", ephemeral=True)
                return
            if cantidad <= 0:
                await interaction.response.send_message("❌ Cantidad inválida.", ephemeral=True)
                return
            
            user_portfolio = self.user_stocks.get(uid, {})
            current_amt = user_portfolio.get(ticker, 0)
            
            if current_amt < cantidad:
                await interaction.response.send_message(f"❌ No tienes suficientes acciones. Tienes: {current_amt}", ephemeral=True)
                return
                
            earnings = self.stocks[ticker]['price'] * cantidad
            self.add_balance(interaction.user.id, earnings)
            self.user_stocks[uid][ticker] -= cantidad
            self._save_data()
            
            await interaction.response.send_message(f"✅ Vendiste {cantidad} acciones de **{ticker}** por **{int(earnings)}** monedas.")

    @eco_group.command(name="dar", description="Da monedas a un usuario (Admin)")
    async def dar(
        self, interaction: discord.Interaction, usuario: discord.User, cantidad: int
    ):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("⛔ Solo administradores.", ephemeral=True)
            return

        if cantidad <= 0:
            await interaction.response.send_message(
                "⚠️ Cantidad inválida.", ephemeral=True
            )
            return
        # Admin genera dinero, no se resta de su saldo
        self._add(usuario.id, cantidad)
        await interaction.response.send_message(
            f"✅ Admin: Añadidos {cantidad} a {usuario.mention}."
        )

    @eco_group.command(name="transferir", description="Transfiere monedas de tu saldo a otro usuario")
    async def transferir(
        self, interaction: discord.Interaction, usuario: discord.User, cantidad: int
    ):
        if cantidad <= 0:
            await interaction.response.send_message("⚠️ Cantidad inválida.", ephemeral=True)
            return
        
        if usuario.id == interaction.user.id:
            await interaction.response.send_message("⚠️ No puedes transferirte a ti mismo.", ephemeral=True)
            return

        uid = interaction.user.id
        if self.bal.get(uid, 0) < cantidad:
            await interaction.response.send_message(
                f"⚠️ No tienes suficientes monedas (Tienes: {self.bal.get(uid, 0)}).", ephemeral=True
            )
            return

        self._add(uid, -cantidad)
        self._add(usuario.id, cantidad)
        await interaction.response.send_message(
            f"💸 Transferencia exitosa: {cantidad} monedas enviadas a {usuario.mention}."
        )
        try:
            e = interaction.client.build_log_embed(
                "Economía/Monedas",
                "Transferencia realizada",
                user=interaction.user,
                guild=interaction.guild,
                extra={"Destino": str(usuario.id), "Cantidad": str(cantidad)},
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @eco_group.command(name="quitar", description="Quita monedas a un usuario (Admin)")
    async def quitar(
        self, interaction: discord.Interaction, usuario: discord.User, cantidad: int
    ):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("⛔ Solo administradores.", ephemeral=True)
            return

        if cantidad <= 0:
            await interaction.response.send_message(
                "⚠️ Cantidad inválida.", ephemeral=True
            )
            return
        self._add(usuario.id, -cantidad)
        await interaction.response.send_message(
            f"⚠️ Se han restado {cantidad} a {usuario.mention}."
        )
        try:
            e = interaction.client.build_log_embed(
                "Economía/Monedas",
                "Quitar monedas",
                user=interaction.user,
                guild=interaction.guild,
                extra={"A": f"{usuario} ({usuario.id})", "Cantidad": str(cantidad)},
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @eco_group.command(name="top", description="Top de usuarios por saldo")
    async def top(self, interaction: discord.Interaction):
        datos = sorted(self.bal.items(), key=lambda x: x[1], reverse=True)[:10]
        
        embed = discord.Embed(title="🏆 Ranking de Riqueza", color=Theme.get_color(interaction.guild.id, 'secondary'))
        
        description = ""
        for i, (uid, val) in enumerate(datos, 1):
            try:
                u = await self.bot.fetch_user(uid)
                name = u.display_name
            except Exception:
                name = f"ID: {uid}"
            
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            description += f"**{medal} {name}** — 💰 {val}\n"
            
        if not description:
            description = "No hay datos registrados."
            
        embed.description = description
        embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
        await interaction.response.send_message(embed=embed)
        try:
            e = interaction.client.build_log_embed(
                "Economía/Monedas",
                "Top mostrado",
                user=interaction.user,
                guild=interaction.guild,
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass


async def setup(bot):
    await bot.add_cog(Monedas(bot))
