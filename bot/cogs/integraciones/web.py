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
            except Exception as e:
                # Log del error real pero respuesta genérica al cliente
                print(f"🔥 [API Error] {request.path}: {e}")
                response = web.json_response({"error": "Internal Server Error"}, status=500)
            
            # Añadir headers CORS a todas las respuestas
            response.headers['Access-Control-Allow-Origin'] = origin or '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            # Headers de seguridad adicionales
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            return response

        app.middlewares.append(custom_middleware)

        # --- API ENDPOINTS ---
        
        # Diccionario para rate limit básico de login
        self.login_attempts = {}

        async def login(request):
            # Rate limit básico por IP
            peername = request.transport.get_extra_info('peername')
            if peername:
                ip = peername[0]
                now = time.time()
                last_attempt, count = self.login_attempts.get(ip, (0, 0))
                
                # Bloquear 1 minuto si hay más de 5 intentos fallidos en 5 minutos
                if count >= 5 and now - last_attempt < 60:
                    return web.json_response({"error": "Too many attempts. Try again in 1 minute."}, status=429)
                
                if now - last_attempt > 300: # Reset cada 5 mins
                    count = 0
                self.login_attempts[ip] = (now, count + 1)

            try:
                data = await request.json()
            except Exception:
                return web.json_response({"error": "Invalid JSON"}, status=400)

            username = data.get('username')
            password = data.get('password')
            
            if verify_login(username, password):
                # Reset intentos tras login exitoso
                if peername: self.login_attempts[ip] = (0, 0)
                
                token = secrets.token_hex(32)
                self.sessions.add(token)
                return web.json_response({"token": token})
            
            return web.json_response({"error": "Invalid credentials"}, status=401)

        async def get_bot_stats(request):
            """Retorna estadísticas globales del bot (Público)."""
            uptime_secs = int(time.time() - self.start_time)
            stats = {
                "status": "online",
                "version": BOT_VERSION,
                "uptime_secs": uptime_secs,
                "guilds_count": len(self.bot.guilds),
                "users_count": sum(g.member_count for g in self.bot.guilds if g.member_count),
                "latency": round(self.bot.latency * 1000, 2)
            }
            return web.json_response(stats)

        async def get_guilds_list(request):
            """Retorna lista de servidores con detalles básicos (Privado)."""
            guilds = []
            for g in self.bot.guilds:
                guilds.append({
                    "id": str(g.id),
                    "name": g.name,
                    "icon": str(g.icon.url) if g.icon else None,
                    "members": g.member_count,
                    "owner": str(g.owner),
                    "config": get_guild_config(g.id)
                })
            return web.json_response(guilds)

        async def get_guild_settings(request):
            """Retorna la configuración detallada de un servidor (Privado)."""
            guild_id = request.match_info.get('guild_id')
            if not guild_id:
                return web.json_response({"error": "guild_id required"}, status=400)
            
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                return web.json_response({"error": "Guild not found"}, status=404)

            config = get_guild_config(guild.id)
            
            # Obtener canales de texto y roles para los selects del dashboard
            channels = [{"id": str(c.id), "name": c.name} for c in guild.text_channels]
            roles = [{"id": str(r.id), "name": r.name} for r in guild.roles if not r.is_default()]

            return web.json_response({
                "config": config,
                "channels": channels,
                "roles": roles,
                "name": guild.name
            })

        async def update_guild_config(request):
            """Actualiza ajustes del servidor vía API (Privado)."""
            try:
                data = await request.json()
            except Exception:
                return web.json_response({"error": "Invalid JSON"}, status=400)
                
            guild_id = data.get('guild_id')
            updates = data.get('updates', {}) # Diccionario con {key: value}
            
            if not guild_id:
                return web.json_response({"error": "Missing guild_id"}, status=400)
            
            # Validación de existencia de servidor
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                return web.json_response({"error": "Guild not found"}, status=404)

            # Lista blanca de configuraciones permitidas para evitar inyecciones en el JSON
            allowed_keys = ['log_channel_id', 'staff_role_id', 'theme', 'alert_channel_id']
            
            for key, value in updates.items():
                if key not in allowed_keys:
                    continue # Ignorar claves no permitidas
                
                # Convertir a int si son IDs de canales/roles y verificar que pertenecen al servidor
                if key in ['log_channel_id', 'staff_role_id', 'alert_channel_id']:
                    try:
                        if value:
                            val_int = int(value)
                            # Verificación extra: ¿El canal/rol existe en este servidor?
                            if key == 'log_channel_id' and not guild.get_channel(val_int):
                                continue
                            if key == 'staff_role_id' and not guild.get_role(val_int):
                                continue
                            value = val_int
                        else:
                            value = None
                    except ValueError:
                        continue
                
                # Validación de tema
                if key == 'theme' and value not in ['default', 'ocean', 'fire', 'nature']:
                    value = 'default'

                set_guild_setting(int(guild_id), key, value)
            
            return web.json_response({"status": "success"})

        async def get_logs(request):
            """Retorna los logs recientes filtrados por servidor (Privado)."""
            guild_id = request.match_info.get('guild_id')
            logs = getattr(self.bot, "recent_logs", [])
            
            if guild_id == "global":
                filtered = logs
            else:
                filtered = [l for l in logs if l.get('guild_id') == guild_id]
            
            return web.json_response(filtered[::-1]) # Invertir para ver lo más reciente primero

        async def reboot_bot(request):
            """Reinicia el bot (Privado)."""
            print("🚀 [WebServer] Petición de reinicio recibida.")
            # Respuesta rápida antes de cerrar
            response = web.json_response({"status": "rebooting"})
            
            async def shutdown():
                await asyncio.sleep(2)
                await self.bot.close()
                # El proceso se reiniciará por el .bat o el host
                os._exit(0)
            
            asyncio.create_task(shutdown())
            return response

        # --- RUTAS ---
        
        # API
        app.router.add_post('/api/login', login)
        app.router.add_get('/api/stats', get_bot_stats)
        app.router.add_get('/api/guilds', get_guilds_list)
        app.router.add_get('/api/config/{guild_id}', get_guild_settings)
        app.router.add_post('/api/config/update', update_guild_config)
        app.router.add_get('/api/logs/{guild_id}', get_logs)
        app.router.add_post('/api/reboot', reboot_bot)

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
