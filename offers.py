from discord.ext import commands
import discord

# ====== Cog de Ofertas ======
class OffersCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def oferta(self, ctx):
        """Muestra una oferta especial"""
        embed = discord.Embed(
            title="🎁 Oferta Especial",
            description="✨ ¡Has descubierto un cofre oculto con recompensas místicas!",
            color=discord.Color.green()
        )
        embed.add_field(name="Recompensa", value="100 XP extra ⚔️", inline=False)
        embed.set_footer(text="Atenea sonríe ante tu hallazgo 🌟")
        await ctx.send(embed=embed)

    @commands.command()
    async def ofertas(self, ctx):
        """Lista varias ofertas disponibles"""
        embed = discord.Embed(
            title="📜 Ofertas Disponibles",
            description="El Olimpo abre sus tesoros para ti:",
            color=discord.Color.gold()
        )
        embed.add_field(name="⚔️ Espada de la Verdad", value="Duplica tu XP por 1 hora", inline=False)
        embed.add_field(name="🏛️ Bendición de Atenea", value="Acceso a un Oráculo privado", inline=False)
        embed.add_field(name="🌌 Estrella del Destino", value="Un rol exclusivo en el servidor", inline=False)
        embed.set_footer(text="Elige con sabiduría, mortal ✨")
        await ctx.send(embed=embed)

# ====== Setup obligatorio para main.py ======
async def setup(bot):
    await bot.add_cog(OffersCog(bot))
