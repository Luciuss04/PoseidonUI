import json
import os
import discord

THEME_FILE = "theme_config.json"

# Definición de temas
THEMES = {
    "olimpo": {
        "name": "Olimpo (Default)",
        "colors": {
            "primary": 0x00FFFF,      # Cyan/Aqua
            "secondary": 0xFFD700,    # Gold
            "success": 0x00FF00,      # Green
            "error": 0xFF0000,        # Red
            "warning": 0xFFA500,      # Orange
            "info": 0x00BFFF         # Deep Sky Blue
        },
        "footer": "🔱 PoseidonUI • El Poder del Olimpo"
    },
    "hades": {
        "name": "Reino de Hades",
        "colors": {
            "primary": 0xFF0000,      # Red
            "secondary": 0x2C2F33,    # Dark Gray
            "success": 0x8B0000,      # Dark Red
            "error": 0x550000,        # Darker Red
            "warning": 0xFF4500,      # Orange Red
            "info": 0x808080          # Gray
        },
        "footer": "🔥 PoseidonUI • El Reino de las Sombras"
    },
    "atenea": {
        "name": "Sabiduría de Atenea",
        "colors": {
            "primary": 0xFFFFFF,      # White
            "secondary": 0xC0C0C0,    # Silver
            "success": 0xE6E6FA,      # Lavender
            "error": 0xCD5C5C,        # Indian Red
            "warning": 0xF0E68C,      # Khaki
            "info": 0xF0F8FF          # Alice Blue
        },
        "footer": "🦉 PoseidonUI • La Sabiduría Eterna"
    },
    "oceano": {
        "name": "Profundidades del Océano",
        "colors": {
            "primary": 0x00008B,      # Dark Blue
            "secondary": 0x008B8B,    # Dark Cyan
            "success": 0x2E8B57,      # Sea Green
            "error": 0x8B0000,        # Dark Red
            "warning": 0xFF8C00,      # Dark Orange
            "info": 0x4682B4          # Steel Blue
        },
        "footer": "🌊 PoseidonUI • Las Profundidades"
    }
}

class ThemeManager:
    def __init__(self):
        self.global_theme = "olimpo"
        self.guild_themes = {}  # guild_id -> theme_name
        self.custom_themes = {} # theme_name -> theme_data
        self.load_config()

    def load_config(self):
        if os.path.exists(THEME_FILE):
            try:
                with open(THEME_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.global_theme = data.get("global_theme", "olimpo")
                    # Convertir claves a int para guild_ids
                    self.guild_themes = {int(k): v for k, v in data.get("guild_themes", {}).items() if k.isdigit()}
                    self.custom_themes = data.get("custom_themes", {})
            except Exception:
                self.global_theme = "olimpo"
                self.guild_themes = {}
                self.custom_themes = {}
        else:
            self.global_theme = "olimpo"
            self.guild_themes = {}
            self.custom_themes = {}
            self.save_config()

    def save_config(self):
        try:
            with open(THEME_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "global_theme": self.global_theme,
                    "guild_themes": {str(k): v for k, v in self.guild_themes.items()},
                    "custom_themes": self.custom_themes
                }, f, indent=4)
        except Exception:
            pass

    def set_theme(self, theme_name, guild_id=None):
        # Verifica si el tema existe en los predefinidos o en los personalizados
        if theme_name not in THEMES and theme_name not in self.custom_themes:
            return False
        
        if guild_id:
            self.guild_themes[int(guild_id)] = theme_name
        else:
            self.global_theme = theme_name
            
        self.save_config()
        return True

    def create_custom_theme(self, name, display_name, colors, footer):
        """
        Crea o actualiza un tema personalizado.
        """
        self.custom_themes[name] = {
            "name": display_name,
            "colors": colors,
            "footer": footer
        }
        self.save_config()
        return True

    def delete_custom_theme(self, theme_name):
        """
        Elimina un tema personalizado.
        Retorna True si se eliminó, False si no existía o es built-in.
        """
        if theme_name in THEMES:
            return False # No se pueden borrar los built-in
            
        if theme_name in self.custom_themes:
            del self.custom_themes[theme_name]
            
            # Revertir uso si está activo
            if self.global_theme == theme_name:
                self.global_theme = "olimpo"
            
            # Revertir en guilds que lo usen
            for gid, t in list(self.guild_themes.items()):
                if t == theme_name:
                    self.guild_themes[gid] = "olimpo"
            
            self.save_config()
            return True
        return False

    def get_theme_name(self, guild_id=None):
        if guild_id and int(guild_id) in self.guild_themes:
            return self.guild_themes[int(guild_id)]
        return self.global_theme

    def get_data(self, guild_id=None):
        theme_name = self.get_theme_name(guild_id)
        if theme_name in self.custom_themes:
            return self.custom_themes[theme_name]
        return THEMES.get(theme_name, THEMES["olimpo"])

    def get_all_themes(self):
        """Retorna todos los temas disponibles (built-in + custom)"""
        all_themes = THEMES.copy()
        all_themes.update(self.custom_themes)
        return all_themes

    def get_color(self, guild_id, key):
        """
        Obtiene un color discord.Color para un servidor y clave específica.
        Keys: primary, secondary, success, error, warning, info
        """
        data = self.get_data(guild_id)
        hex_val = data["colors"].get(key, THEMES["olimpo"]["colors"].get(key, 0x000000))
        return discord.Color(hex_val)

    def get_footer_text(self, guild_id):
        """
        Obtiene el texto del footer para un servidor.
        """
        data = self.get_data(guild_id)
        return data.get("footer", THEMES["olimpo"]["footer"])

    @property
    def color(self):
        # Propiedad legacy/global para compatibilidad simple si se usa sin guild_id
        # Retorna los colores del tema global
        class ColorProxy:
            def __init__(self, manager):
                self.manager = manager
            
            def __getattr__(self, name):
                return self.manager.get_color(None, name)
                
        return ColorProxy(self)

    @property
    def footer_text(self):
        return self.get_footer_text(None)

# Instancia global
Theme = ThemeManager()
