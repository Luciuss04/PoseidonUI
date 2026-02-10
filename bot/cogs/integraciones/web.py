import os
import asyncio
from aiohttp import web
from discord.ext import commands

class WebServer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.site = None
        self.runner = None
        self.port = int(os.getenv("SERVER_PORT", "8080")) # Puerto configurable

    async def cog_load(self):
        # En versiones recientes de d.py, bot.loop puede no estar disponible si no se ha iniciado el login
        # Usamos asyncio.get_running_loop() para mayor seguridad
        loop = asyncio.get_running_loop()
        loop.create_task(self.start_server())

    async def cog_unload(self):
        await self.stop_server()

    async def stop_server(self):
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        print("🌍 Web server detenido.")

    async def start_server(self):
        # Ruta a la carpeta docs (GitHub Pages)
        website_path = os.path.join(os.getcwd(), "docs")
        
        if not os.path.exists(website_path):
            print(f"⚠️ [WebServer] No se encontró la carpeta 'docs' en {website_path}")
            return

        app = web.Application()

        # Handler para la página principal
        async def index(request):
            return web.FileResponse(os.path.join(website_path, "index.html"))

        # Rutas
        app.router.add_get('/', index)
        # Servir archivos estáticos (css, js, images) desde la misma raíz para que style.css funcione
        app.router.add_static('/', website_path)

        self.runner = web.AppRunner(app)
        await self.runner.setup()
        
        # Escuchar en todas las interfaces (0.0.0.0) para que sea accesible desde fuera
        self.site = web.TCPSite(self.runner, '0.0.0.0', self.port)
        
        try:
            await self.site.start()
            print(f"🌍 [WebServer] Landing page activa en http://0.0.0.0:{self.port}")
            print(f"🌍 [WebServer] Ruta local: {website_path}")
        except Exception as e:
            print(f"❌ [WebServer] Error al iniciar en puerto {self.port}: {e}")

async def setup(bot):
    await bot.add_cog(WebServer(bot))
