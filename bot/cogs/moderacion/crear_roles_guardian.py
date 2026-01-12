import random

import discord
from discord import app_commands
from discord.ext import commands

JUICIO_ROLES = {
    "⚡ Favor divino": "Bendecido",
    "🗡️ Prueba del destino": "Probado",
    "🌫️ Silencio ritual": "Silenciado",
    "🔥 Forja del espíritu": "Forjado",
    "🌌 Visión del Oráculo": "Visionario",
    "🛡️ Bendición de Atenea": "Protegido",
    "🌪️ Viento de cambio": "Transformado",
    "🌊 Purificación": "Purificado",
}


def generar_color_unico():
    return discord.Color.from_rgb(
        random.randint(50, 255), random.randint(50, 255), random.randint(50, 255)
    )


class CrearRolesGuardian(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="crear_roles_guardian",
        description="Crea automáticamente los roles del Guardian con colores dinámicos",
    )
    async def crear_roles_guardian(self, interaction: discord.Interaction):
        creados = []
        ya_existentes = []

        for titulo, rol_nombre in JUICIO_ROLES.items():
            rol = discord.utils.get(interaction.guild.roles, name=rol_nombre)
            if rol:
                ya_existentes.append(rol_nombre)
            else:
                try:
                    color = generar_color_unico()
                    await interaction.guild.create_role(
                        name=rol_nombre, color=color, reason="Roles del Guardian"
                    )
                    creados.append(f"{rol_nombre} ({color})")
                except discord.Forbidden:
                    await interaction.response.send_message(
                        "⚠️ No tengo permisos para crear roles.", ephemeral=True
                    )
                    return

        embed = discord.Embed(
            title="🛡️ Roles del Guardian",
            description="Los roles rituales han sido revisados.",
            color=discord.Color.blurple(),
        )
        if creados:
            embed.add_field(
                name="✅ Roles creados", value="\n".join(creados), inline=False
            )
        if ya_existentes:
            embed.add_field(
                name="ℹ️ Ya existentes", value=", ".join(ya_existentes), inline=False
            )

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(CrearRolesGuardian(bot))
