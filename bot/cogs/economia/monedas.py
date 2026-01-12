import time
import random

import discord
from discord import app_commands
from discord.ext import commands


class Monedas(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bal: dict[int, int] = {}
        self.daily_ts: dict[int, int] = {}

    def _add(self, uid: int, amt: int):
        self.bal[uid] = self.bal.get(uid, 0) + amt

    @app_commands.command(name="balance", description="Muestra tu saldo")
    async def balance(
        self, interaction: discord.Interaction, usuario: discord.User | None = None
    ):
        uid = (usuario or interaction.user).id
        val = self.bal.get(uid, 0)
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

    @app_commands.command(name="daily", description="Reclama tu recompensa diaria")
    async def daily(self, interaction: discord.Interaction):
        uid = interaction.user.id
        now = int(time.time())
        last = self.daily_ts.get(uid, 0)
        if now - last < 86400:
            await interaction.response.send_message(
                "⚠️ Ya reclamaste hoy.", ephemeral=True
            )
            return
        self.daily_ts[uid] = now
        self._add(uid, 100)
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

    @app_commands.command(name="work", description="Trabaja para ganar monedas")
    async def work(self, interaction: discord.Interaction):
        uid = interaction.user.id
        self._add(uid, 50)
        await interaction.response.send_message("🛠️ Ganaste 50 monedas.")
        try:
            e = interaction.client.build_log_embed(
                "Economía/Monedas",
                "Work ejecutado",
                user=interaction.user,
                guild=interaction.guild,
                extra={"Cantidad": "50"},
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @app_commands.command(name="dar", description="Da monedas a un usuario (Admin)")
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

    @app_commands.command(name="transferir", description="Transfiere monedas de tu saldo a otro usuario")
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

    @app_commands.command(name="slots", description="Apuesta tus monedas en la tragaperras")
    async def slots(self, interaction: discord.Interaction, apuesta: int):
        uid = interaction.user.id
        if apuesta <= 0:
            await interaction.response.send_message("⚠️ La apuesta debe ser mayor a 0.", ephemeral=True)
            return
        
        saldo = self.bal.get(uid, 0)
        if saldo < apuesta:
            await interaction.response.send_message(f"⚠️ No tienes suficientes monedas (Tienes: {saldo}).", ephemeral=True)
            return

        self._add(uid, -apuesta)
        
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
            self._add(uid, ganancia)
            
        embed = discord.Embed(title="Tragaperras 🎰", description=f"{resultado}\n\n{msg}", color=discord.Color.gold() if ganancia > 0 else discord.Color.red())
        embed.set_footer(text=f"Saldo actual: {self.bal.get(uid, 0)}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="quitar", description="Quita monedas a un usuario")
    async def quitar(
        self, interaction: discord.Interaction, usuario: discord.User, cantidad: int
    ):
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

    @app_commands.command(name="top", description="Top de usuarios por saldo")
    async def top(self, interaction: discord.Interaction):
        datos = sorted(self.bal.items(), key=lambda x: x[1], reverse=True)[:10]
        lines = []
        for uid, val in datos:
            try:
                u = await self.bot.fetch_user(uid)
                lines.append(f"{u.mention}: {val}")
            except Exception:
                lines.append(f"{uid}: {val}")
        if not lines:
            await interaction.response.send_message("⚠️ No hay datos.", ephemeral=True)
            return
        await interaction.response.send_message("\n".join(lines))
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
