import discord
from discord import app_commands
from discord.ext import commands
from bot.themes import Theme

MAX_OPTIONS = 5


class EncuestaView(discord.ui.View):
    def __init__(self, autor_id: int, opciones: list[str]):
        super().__init__(timeout=None)
        self.autor_id = autor_id
        self.opciones = opciones
        self.votos: dict[str, set[int]] = {opt: set() for opt in opciones}
        for i, opt in enumerate(opciones):
            self.add_item(self._make_button(label=opt, custom_id=f"poll_opt_{i}"))
        self.add_item(self._make_close())

    def _make_button(self, label: str, custom_id: str) -> discord.ui.Button:
        btn = discord.ui.Button(
            label=label, style=discord.ButtonStyle.primary, custom_id=custom_id
        )

        async def on_click(interaction: discord.Interaction):
            opt = label
            uid = interaction.user.id
            # alternar voto
            if uid in self.votos[opt]:
                self.votos[opt].remove(uid)
            else:
                # quitar de otras opciones
                for o in self.opciones:
                    self.votos[o].discard(uid)
                self.votos[opt].add(uid)
            await interaction.response.defer(ephemeral=True)

        btn.callback = on_click
        return btn

    def _make_close(self) -> discord.ui.Button:
        btn = discord.ui.Button(
            label="Cerrar encuesta",
            style=discord.ButtonStyle.danger,
            custom_id="poll_close",
        )

        async def on_click(interaction: discord.Interaction):
            if interaction.user.id != self.autor_id:
                await interaction.response.send_message(
                    "⚠️ Solo el creador puede cerrar la encuesta.", ephemeral=True
                )
                return
            resumen = "\n".join(
                [f"• {o}: {len(self.votos[o])} votos" for o in self.opciones]
            )
            embed = discord.Embed(
                title="📊 Resultados de la encuesta",
                description=resumen,
                color=Theme.get_color(interaction.guild.id, 'primary'),
            )
            embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
            await interaction.message.edit(view=None)
            await interaction.response.send_message(embed=embed)

        btn.callback = on_click
        return btn


class Encuestas(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="encuesta",
        description="Crea una encuesta con opciones (separadas por ';')",
    )
    async def encuesta(
        self, interaction: discord.Interaction, pregunta: str, opciones: str
    ):
        opts = [o.strip() for o in opciones.split(";") if o.strip()]
        if len(opts) < 2 or len(opts) > MAX_OPTIONS:
            await interaction.response.send_message(
                f"⚠️ Debes indicar entre 2 y {MAX_OPTIONS} opciones.", ephemeral=True
            )
            return
        embed = discord.Embed(
            title="📊 Encuesta", description=pregunta, color=Theme.get_color(interaction.guild.id, 'primary')
        )
        embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
        view = EncuestaView(interaction.user.id, opts)
        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(Encuestas(bot))
