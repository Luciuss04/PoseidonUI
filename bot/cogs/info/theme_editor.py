import random
import re

import discord
from discord import app_commands
from discord.ext import commands

from bot.themes import Theme

# Presets de colores para facilitar el diseño
PRESETS = {
    "ocean": {
        "name": "Océano Profundo",
        "colors": {
            "primary": 0x006994,
            "secondary": 0x00BCD4,
            "success": 0x4CAF50,
            "error": 0xF44336,
            "warning": 0xFF9800,
            "info": 0x2196F3,
        },
        "footer": "🌊 Navegando los mares de Discord",
    },
    "forest": {
        "name": "Bosque Encantado",
        "colors": {
            "primary": 0x2E7D32,
            "secondary": 0x81C784,
            "success": 0x66BB6A,
            "error": 0xE57373,
            "warning": 0xFFA726,
            "info": 0x29B6F6,
        },
        "footer": "🍃 La naturaleza te protege",
    },
    "cyber": {
        "name": "Cyberpunk 2077",
        "colors": {
            "primary": 0xFCEE0A,
            "secondary": 0x00F0FF,
            "success": 0x00FF9F,
            "error": 0xFF003C,
            "warning": 0xF9F9F9,
            "info": 0x711C91,
        },
        "footer": "🤖 Wake up, Samurai",
    },
    "pastel": {
        "name": "Sueño Pastel",
        "colors": {
            "primary": 0xFFB7B2,
            "secondary": 0xFFDAC1,
            "success": 0xE2F0CB,
            "error": 0xFF9AA2,
            "warning": 0xFFD3B6,
            "info": 0xB5EAD7,
        },
        "footer": "✨ Dulces sueños",
    },
    "dark": {
        "name": "Modo Oscuro Pro",
        "colors": {
            "primary": 0x2B2D31,
            "secondary": 0x1E1F22,
            "success": 0x57F287,
            "error": 0xED4245,
            "warning": 0xFEE75C,
            "info": 0x5865F2,
        },
        "footer": "🌑 Elegancia y simplicidad",
    },
    "dracula": {
        "name": "Dracula",
        "colors": {
            "primary": 0xBD93F9,
            "secondary": 0x6272A4,
            "success": 0x50FA7B,
            "error": 0xFF5555,
            "warning": 0xFFB86C,
            "info": 0x8BE9FD,
        },
        "footer": "🧛 La noche es joven",
    },
}


class HexInputModal(discord.ui.Modal):
    def __init__(self, color_key, current_hex, view_parent):
        super().__init__(title=f"🎨 Color: {color_key.capitalize()}")
        self.color_key = color_key
        self.view_parent = view_parent

        self.hex_input = discord.ui.TextInput(
            label="Código Hex (ej. #FF0000)",
            default=current_hex,
            placeholder="#RRGGBB",
            min_length=6,
            max_length=7,
        )
        self.add_item(self.hex_input)

    async def on_submit(self, interaction: discord.Interaction):
        hex_val = self.hex_input.value.strip()
        # Validar hex
        match = re.search(r"^#?(?:[0-9a-fA-F]{3}){1,2}$", hex_val)

        if not match:
            await interaction.response.send_message("❌ Código Hex inválido.", ephemeral=True)
            return

        if not hex_val.startswith("#"):
            hex_val = "#" + hex_val

        # Convertir a int
        try:
            color_int = int(hex_val.replace("#", ""), 16)
        except ValueError:
            await interaction.response.send_message(
                "❌ Error al procesar el color.", ephemeral=True
            )
            return

        self.view_parent.draft_colors[self.color_key] = color_int
        await self.view_parent.update_message(interaction)


class InfoInputModal(discord.ui.Modal):
    def __init__(self, current_name, current_footer, view_parent):
        super().__init__(title="📝 Detalles del Tema")
        self.view_parent = view_parent

        self.name_input = discord.ui.TextInput(
            label="Nombre del Tema",
            default=current_name,
            placeholder="Mi Tema Increíble",
            max_length=30,
        )
        self.footer_input = discord.ui.TextInput(
            label="Texto del Footer",
            default=current_footer,
            placeholder="Texto al pie de los embeds",
            style=discord.TextStyle.paragraph,
            max_length=100,
        )
        self.add_item(self.name_input)
        self.add_item(self.footer_input)

    async def on_submit(self, interaction: discord.Interaction):
        self.view_parent.draft_name = self.name_input.value
        self.view_parent.draft_footer = self.footer_input.value
        await self.view_parent.update_message(interaction)


class ThemeEditorView(discord.ui.View):
    def __init__(self, interaction_user, initial_data=None):
        super().__init__(timeout=900)
        self.user = interaction_user

        if initial_data:
            self.draft_name = initial_data.get("name", "Custom Theme")
            self.draft_colors = initial_data.get("colors", {}).copy()
            self.draft_footer = initial_data.get("footer", "Footer Personalizado")
        else:
            self.draft_name = "Mi Tema Nuevo"
            self.draft_colors = {
                "primary": 0x00FFFF,
                "secondary": 0xFFD700,
                "success": 0x00FF00,
                "error": 0xFF0000,
                "warning": 0xFFA500,
                "info": 0x00BFFF,
            }
            self.draft_footer = "Texto de pie de página personalizado"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("⛔ No puedes usar este panel.", ephemeral=True)
            return False
        return True

    def build_embed(self):
        c = self.draft_colors

        # ANSI Format helpers
        # 31 Red, 32 Green, 33 Yellow, 34 Blue, 35 Pink/Magenta, 36 Cyan, 37 White

        def to_ansi(key, hex_val):
            hex_s = f"#{hex_val:06x}".upper()

            # Map semantic keys to ANSI colors for visual distinction
            ansi_code = "37"  # White default
            if key == "primary":
                ansi_code = "36"  # Cyan
            elif key == "secondary":
                ansi_code = "35"  # Magenta
            elif key == "success":
                ansi_code = "32"  # Green
            elif key == "error":
                ansi_code = "31"  # Red
            elif key == "warning":
                ansi_code = "33"  # Yellow
            elif key == "info":
                ansi_code = "34"  # Blue

            # Format: [1;3XmKEY      [0m #HEX
            # Padding for alignment
            key_padded = f"{key.capitalize():<10}"
            return f"\u001b[1;{ansi_code}m{key_padded}\u001b[0m {hex_s}"

        desc = "🛠️ **Estudio de Diseño**\n" "Personaliza la identidad visual de tu servidor.\n"

        e = discord.Embed(
            title=f"🎨 {self.draft_name}", description=desc, color=c.get("primary", 0x000000)
        )

        # ANSI Block
        ansi_lines = []
        for k in ["primary", "secondary", "success", "error", "warning", "info"]:
            ansi_lines.append(to_ansi(k, c.get(k, 0)))

        e.add_field(
            name="🎨 Configuración de Color (ANSI)",
            value="```ansi\n" + "\n".join(ansi_lines) + "\n```",
            inline=False,
        )

        e.add_field(name="📝 Footer Activo", value=f"```\n{self.draft_footer}\n```", inline=False)

        e.set_footer(text=f"Vista Previa: {self.draft_footer}")
        if self.user.avatar:
            e.set_thumbnail(url=self.user.avatar.url)

        return e

    async def update_message(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.select(
        placeholder="📂 Plantillas (Presets)...",
        row=0,
        options=[
            discord.SelectOption(
                label="🌊 Océano Profundo", value="ocean", description="Azul / Cian"
            ),
            discord.SelectOption(
                label="🍃 Bosque Encantado", value="forest", description="Verde / Naturaleza"
            ),
            discord.SelectOption(
                label="🤖 Cyberpunk 2077", value="cyber", description="Amarillo / Neón"
            ),
            discord.SelectOption(
                label="✨ Sueño Pastel", value="pastel", description="Colores suaves"
            ),
            discord.SelectOption(
                label="🌑 Modo Oscuro", value="dark", description="Gris / Minimalista"
            ),
            discord.SelectOption(
                label="🧛 Dracula", value="dracula", description="Púrpura / Oscuro"
            ),
        ],
    )
    async def select_preset(self, interaction: discord.Interaction, select: discord.ui.Select):
        preset_key = select.values[0]
        if preset_key in PRESETS:
            data = PRESETS[preset_key]
            self.draft_name = f"{data['name']} (Editado)"
            self.draft_colors = data["colors"].copy()
            self.draft_footer = data["footer"]
            await self.update_message(interaction)

    @discord.ui.select(
        placeholder="🎨 Editar un Color...",
        row=1,
        options=[
            discord.SelectOption(
                label="Primary",
                value="primary",
                description="Color principal de los embeds",
                emoji="🟦",
            ),
            discord.SelectOption(
                label="Secondary", value="secondary", description="Detalles secundarios", emoji="🟪"
            ),
            discord.SelectOption(
                label="Success", value="success", description="Operaciones exitosas", emoji="🟩"
            ),
            discord.SelectOption(
                label="Error", value="error", description="Errores y fallos", emoji="🟥"
            ),
            discord.SelectOption(
                label="Warning", value="warning", description="Advertencias", emoji="🟧"
            ),
            discord.SelectOption(
                label="Info", value="info", description="Información general", emoji="ℹ️"
            ),
        ],
    )
    async def select_color(self, interaction: discord.Interaction, select: discord.ui.Select):
        key = select.values[0]
        current_val = self.draft_colors.get(key, 0x000000)
        current_hex = f"#{current_val:06x}".upper()
        await interaction.response.send_modal(HexInputModal(key, current_hex, self))

    @discord.ui.button(label="📝 Info", style=discord.ButtonStyle.secondary, row=2, emoji="✏️")
    async def edit_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            InfoInputModal(self.draft_name, self.draft_footer, self)
        )

    @discord.ui.button(label="🎲 Random", style=discord.ButtonStyle.secondary, row=2, emoji="🎲")
    async def random_palette(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Generate random pleasant colors
        def rand_color():
            return random.randint(0, 0xFFFFFF)

        self.draft_colors = {
            "primary": rand_color(),
            "secondary": rand_color(),
            "success": 0x00FF00,  # Keep functional colors somewhat standard or random? Let's random all
            "error": 0xFF0000,
            "warning": 0xFFA500,
            "info": rand_color(),
        }
        self.draft_name = f"Random Theme #{random.randint(100,999)}"
        await self.update_message(interaction)

    @discord.ui.button(label="👁️ Test", style=discord.ButtonStyle.primary, row=2, emoji="👁️")
    async def preview_theme(self, interaction: discord.Interaction, button: discord.ui.Button):
        c = self.draft_colors
        e_success = discord.Embed(
            title="✅ Éxito", description="Operación completada.", color=c.get("success", 0x00FF00)
        )
        e_error = discord.Embed(
            title="❌ Error", description="Algo salió mal.", color=c.get("error", 0xFF0000)
        )
        e_success.set_footer(text=self.draft_footer)

        await interaction.response.send_message(
            content="**Vista Previa Rápida:**", embeds=[e_success, e_error], ephemeral=True
        )

    @discord.ui.button(label="Guardar", style=discord.ButtonStyle.success, row=3, emoji="💾")
    async def save_theme(self, interaction: discord.Interaction, button: discord.ui.Button):
        safe_name = "".join(c for c in self.draft_name.lower() if c.isalnum() or c == "_")
        if not safe_name:
            safe_name = f"custom_{interaction.guild.id}"

        theme_id = f"custom_{interaction.guild.id}_{safe_name}"

        Theme.create_custom_theme(
            name=theme_id,
            display_name=self.draft_name,
            colors=self.draft_colors,
            footer=self.draft_footer,
        )

        Theme.set_theme(theme_id, guild_id=interaction.guild.id)

        embed = discord.Embed(
            title="🎨 Tema Aplicado",
            description=f"El tema **{self.draft_name}** está activo.",
            color=self.draft_colors["success"],
        )
        embed.set_footer(text=self.draft_footer)

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.danger, row=3, emoji="✖️")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Cancelado.", embed=None, view=None)


class ThemeEditor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="crear_tema", description="Abre el estudio de diseño para crear un tema personalizado"
    )
    async def crear_tema(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "⛔ Solo administradores pueden crear temas.", ephemeral=True
            )
            return

        # Cargar datos del tema actual para empezar a editar desde ahí
        current_data = Theme.get_data(interaction.guild.id)

        # Si es un tema built-in, cambiamos el nombre para que no parezca que editamos el original
        initial_data = current_data.copy()
        if "name" in initial_data:
            initial_data["name"] = f"Copia de {initial_data['name']}"

        view = ThemeEditorView(interaction.user, initial_data=initial_data)
        await interaction.response.send_message(embed=view.build_embed(), view=view)

    @app_commands.command(
        name="borrar_tema", description="Elimina un tema personalizado creado en este servidor"
    )
    @app_commands.describe(nombre="Nombre del tema a eliminar")
    async def borrar_tema(self, interaction: discord.Interaction, nombre: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "⛔ Solo administradores pueden eliminar temas.", ephemeral=True
            )
            return

        # Verificar si es un tema custom
        if not nombre.startswith("custom_"):
            await interaction.response.send_message(
                "❌ Solo se pueden borrar temas personalizados.", ephemeral=True
            )
            return

        # Intentar borrar
        if Theme.delete_custom_theme(nombre):
            await interaction.response.send_message(
                f"🗑️ Tema `{nombre}` eliminado correctamente.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"❌ No se encontró el tema `{nombre}`.", ephemeral=True
            )

    @borrar_tema.autocomplete("nombre")
    async def borrar_tema_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        # Obtener solo temas custom
        # Theme.custom_themes es un dict
        choices = []
        for key, data in Theme.custom_themes.items():
            # Filtrar por búsqueda
            if current.lower() in data["name"].lower() or current.lower() in key.lower():
                choices.append(app_commands.Choice(name=f"{data['name']} ({key})", value=key))

        return choices[:25]


async def setup(bot: commands.Bot):
    await bot.add_cog(ThemeEditor(bot))
