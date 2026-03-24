import asyncio
import json
import os
import time
import secrets
from datetime import datetime

from aiohttp import web
from discord.ext import commands

from bot.config import BOT_VERSION, get_guild_config, set_guild_setting
from bot.themes import Theme
from bot.auth import verify_login


class WebServer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.site = None
        self.runner = None
        self.port = int(os.getenv("SERVER_PORT", "8080"))
        self.start_time = time.time()
        self.sessions = set() # Tokens de sesión activos

    async def cog_load(self):
        loop = asyncio.get_running_loop()
        loop.create_task(self.start_server())

    async def cog_unload(self):
        await self.stop_server()

    async def stop_server(self):
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        print("🌍 [WebServer] Dashboard detenido.")

    async def start_server(self):
        website_path = os.path.join(os.getcwd(), "docs")
        if not os.path.exists(website_path):
            print(f"⚠️ [WebServer] No se encontró 'docs' en {website_path}")
            return

        app = web.Application()

        # --- MIDDLEWARE CORS Y AUTENTICACIÓN ---
        @web.middleware
        async def custom_middleware(request, handler):
            # 1. Manejo de CORS (Para permitir que luciuss04.github.io acceda al bot local)
            origin = request.headers.get('Origin')
            
            # Si es una petición OPTIONS (pre-flight), respondemos rápido con los headers
            if request.method == 'OPTIONS':
                response = web.Response(status=204)
                response.headers['Access-Control-Allow-Origin'] = origin or '*'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
                return response

            # 2. Lógica de Autenticación
            if request.path.startswith('/api/') and request.path not in ['/api/login', '/api/stats']:
                token = request.headers.get('Authorization')
                if not token or token not in self.sessions:
                    return web.json_response({"error": "Unauthorized"}, status=401)
            
            # Ejecutar el handler real
            try:
                response = await handler(request)
            except web.HTTPException as ex:
                response = ex
            
            # Añadir headers CORS a todas las respuestas
            response.headers['Access-Control-Allow-Origin'] = origin or '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            return response

        app.middlewares.append(custom_middleware)

        # --- API ENDPOINTS ---
        
        async def login(request):
            data = await request.json()
            username = data.get('username')
            password = data.get('password')
            
            if verify_login(username, password):
                token = secrets.token_hex(32)
                self.sessions.add(token)
                return web.json_response({"token": token})
            return web.json_response({"error": "Invalid credentials"}, status=401)

        async def get_bot_stats(request):
            """Retorna estadísticas globales del bot (Público)."""
            uptime = str(datetime.fromtimestamp(self.start_time).strftime("%Y-%m-%d %H:%M:%S"))
            stats = {
                "status": "online",
                "version": BOT_VERSION,
                "uptime_start": uptime,
                "guilds_count": len(self.bot.guilds),
                "users_count": sum(g.member_count for g in self.bot.guilds),
                "latency": round(self.bot.latency * 1000, 2)
            }
            return web.json_response(stats)

        async def get_guild_settings(request):
            """Retorna la configuración de un servidor específico (Privado)."""
            guild_id = request.match_info.get('guild_id')
            if not guild_id:
                return web.json_response({"error": "guild_id required"}, status=400)
            
            config = get_guild_config(int(guild_id))
            return web.json_response(config)

        async def update_theme(request):
            """Actualiza el tema de un servidor vía API (Privado)."""
            data = await request.json()
            guild_id = data.get('guild_id')
            theme_name = data.get('theme')
            
            if not guild_id or not theme_name:
                return web.json_response({"error": "Missing params"}, status=400)
            
            set_guild_setting(int(guild_id), "theme", theme_name)
            return web.json_response({"status": "success", "new_theme": theme_name})

        # --- RUTAS ---
        
        # API
        app.router.add_post('/api/login', login)
        app.router.add_get('/api/stats', get_bot_stats)
        app.router.add_get('/api/config/{guild_id}', get_guild_settings)
        app.router.add_post('/api/theme', update_theme)

        # Frontend
        async def index(request):
            return web.FileResponse(os.path.join(website_path, "index.html"))

        async def login_page(request):
            return web.FileResponse(os.path.join(website_path, "login.html"))

        async def admin_page(request):
            return web.FileResponse(os.path.join(website_path, "admin.html"))

        app.router.add_get('/', index)
        app.router.add_get('/login', login_page)
        app.router.add_get('/admin', admin_page)
        app.router.add_static('/', website_path)

        self.runner = web.AppRunner(app)
        await self.runner.setup()
        
        self.site = web.TCPSite(self.runner, '0.0.0.0', self.port)
        
        try:
            await self.site.start()
            print(f"🌍 [WebServer] Dashboard con login en http://localhost:{self.port}")
        except Exception as e:
            print(f"❌ [WebServer] Error: {e}")

async def setup(bot):
    await bot.add_cog(WebServer(bot))

async def setup(bot):
    await bot.add_cog(WebServer(bot))
