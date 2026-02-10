import asyncio
import os
import sys
import logging
from discord.ext import commands
from discord import Intents

# Configurar logging
logging.basicConfig(level=logging.INFO)

# Add root to path
sys.path.insert(0, os.getcwd())

# Importar el Cog
from bot.cogs.integraciones.web import WebServer

async def main():
    print("🚀 Iniciando Servidor Web de Prueba...")
    
    # Configurar Bot dummy
    intents = Intents.default()
    bot = commands.Bot(command_prefix="!", intents=intents)
    
    # Instanciar y añadir el Cog
    cog = WebServer(bot)
    await bot.add_cog(cog)
    
    # El servidor se inicia en cog_load, que se llama al añadir el cog
    # Mantenemos el script vivo
    print("✅ Servidor iniciado. Manteniendo proceso vivo...")
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Deteniendo...")
