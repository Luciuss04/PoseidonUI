import asyncio
import datetime
import os
import secrets
import time

import discord
import psutil
from aiohttp import web
from discord import app_commands
from discord.ext import commands

from bot.auth import add_web_user, get_user_data, verify_login
from bot.config import BOT_VERSION, get_guild_config, get_guild_setting, set_guild_setting
from bot.themes import Theme


class WebServer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.site = None
        self.runner = None
        self.port = int(os.getenv("SERVER_PORT", "8080"))
        self.start_time = time.time()
        self.sessions = set()  # Tokens de sesión activos

    @app_commands.command(
        name="web-register",
        description="Registra una cuenta para el panel web (Solo para administradores del servidor)",
    )
    @app_commands.describe(
        usuario="Nombre de usuario para el panel",
        contrasena="Contraseña para el panel",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def web_register(
        self, interaction: discord.Interaction, usuario: str, contrasena: str
    ):
        # Diferir la respuesta inmediatamente para evitar que el comando expire
        await interaction.response.defer(ephemeral=True)

        # Asegurarnos de que estamos en un servidor
        if not interaction.guild:
            return await interaction.followup.send("❌ Este comando solo se puede usar en servidores.", ephemeral=True)

        # Verificar si el usuario ya existe
        try:
            existing = get_user_data(usuario)
            if existing:
                return await interaction.followup.send(
                    f"❌ El usuario `{usuario}` ya existe.", ephemeral=True
                )

            # Crear el nuevo usuario vinculado a este servidor
            is_global = False
            owner_id = getattr(self.bot.config, "OWNER_ID", None)
            if owner_id and str(interaction.user.id) == str(owner_id):
                is_global = True

            add_web_user(
                username=usuario,
                password=contrasena,
                guild_id=str(interaction.guild_id) if not is_global else None,
                discord_id=str(interaction.user.id),
                avatar_url=str(interaction.user.display_avatar.url),
                is_global_admin=is_global
            )

            await interaction.followup.send(
                f"✅ **Cuenta Creada Correctamente**\n\n"
                f"👤 **Usuario:** `{usuario}`\n"
                f"🔑 **Contraseña:** `••••••••` (la que elegiste)\n"
                f"🌐 **Servidor:** {interaction.guild.name}\n\n"
                f"Ya puedes entrar aquí: https://luciuss04.github.io/PoseidonUI/login.html",
                ephemeral=True,
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Error al crear la cuenta: {e}", ephemeral=True)

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
            origin = request.headers.get("Origin")

            # Si es una petición OPTIONS (pre-flight), respondemos rápido con los headers
            if request.method == "OPTIONS":
                response = web.Response(status=204)
                response.headers["Access-Control-Allow-Origin"] = origin or "*"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
                response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
                return response

            # 2. Lógica de Autenticación
            if request.path.startswith("/api/") and request.path not in [
                "/api/login",
                "/api/stats",
                "/api/health",
            ]:
                token = request.headers.get("Authorization")
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
            response.headers["Access-Control-Allow-Origin"] = origin or "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            # Headers de seguridad adicionales
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            return response

        app.middlewares.append(custom_middleware)

        # --- API ENDPOINTS ---

        # Diccionario para rate limit básico de login
        self.login_attempts = {}

        async def login(request):
            # Rate limit básico por IP
            peername = request.transport.get_extra_info("peername")
            if peername:
                ip = peername[0]
                now = time.time()
                last_attempt, count = self.login_attempts.get(ip, (0, 0))

                # Bloquear 1 minuto si hay más de 5 intentos fallidos en 5 minutos
                if count >= 5 and now - last_attempt < 60:
                    return web.json_response(
                        {"error": "Too many attempts. Try again in 1 minute."}, status=429
                    )

                if now - last_attempt > 300:  # Reset cada 5 mins
                    count = 0
                self.login_attempts[ip] = (now, count + 1)

            try:
                data = await request.json()
            except Exception:
                return web.json_response({"error": "Invalid JSON"}, status=400)

            username = data.get("username")
            password = data.get("password")

            if verify_login(username, password):
                # Reset intentos tras login exitoso
                if peername:
                    self.login_attempts[ip] = (0, 0)

                # Obtener datos del usuario para el token y la respuesta
                user_data = get_user_data(username)
                token = secrets.token_hex(32)
                self.sessions.add(token)

                # Vincular token con datos del usuario para filtrar después
                if not hasattr(self, "token_data"):
                    self.token_data = {}

                if user_data:
                    self.token_data[token] = {
                        "username": user_data["username"],
                        "guild_id": user_data.get("guild_id"),
                        "is_global_admin": user_data.get("is_global_admin", False),
                    }

                    return web.json_response(
                        {
                            "token": token,
                            "user": {
                                "username": user_data["username"],
                                "avatar": user_data.get("avatar_url", ""),
                                "is_global_admin": user_data.get("is_global_admin", False),
                                "guild_id": user_data.get("guild_id"),
                            },
                        }
                    )

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
                "latency": round(self.bot.latency * 1000, 2),
            }
            return web.json_response(stats)

        async def get_health(request):
            uptime_secs = int(time.time() - self.start_time)
            latency_ms = round(self.bot.latency * 1000, 2)
            cpu_percent = psutil.cpu_percent(interval=None)
            memory_percent = psutil.virtual_memory().percent

            now = datetime.datetime.utcnow()
            errors_5m = 0
            logs = getattr(self.bot, "recent_logs", [])
            for entry in logs:
                try:
                    if entry.get("level") != "error":
                        continue
                    ts = entry.get("timestamp")
                    if not isinstance(ts, str) or not ts:
                        continue
                    dt = datetime.datetime.fromisoformat(ts)
                    if (now - dt).total_seconds() <= 300:
                        errors_5m += 1
                except Exception:
                    continue

            status = "ok"
            reasons = []
            if latency_ms >= 400:
                reasons.append("latency_high")
            if cpu_percent >= 85:
                reasons.append("cpu_high")
            if memory_percent >= 85:
                reasons.append("memory_high")
            if errors_5m >= 10:
                reasons.append("errors_spike")

            if reasons:
                status = "degraded"
            if latency_ms >= 900 or cpu_percent >= 95 or memory_percent >= 95 or errors_5m >= 30:
                status = "critical"

            return web.json_response(
                {
                    "status": status,
                    "version": BOT_VERSION,
                    "uptime_secs": uptime_secs,
                    "latency_ms": latency_ms,
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "errors_5m": errors_5m,
                    "reasons": reasons,
                }
            )

        async def get_guilds_list(request):
            """Retorna lista de servidores con detalles básicos (Privado)."""
            token = request.headers.get("Authorization")
            user_info = getattr(self, "token_data", {}).get(token, {})
            is_global = user_info.get("is_global_admin", False)
            restricted_guild = user_info.get("guild_id")

            guilds = []
            for g in self.bot.guilds:
                # Si es admin global, ve todo. Si no, solo ve su servidor restringido.
                if is_global or (restricted_guild and str(g.id) == restricted_guild):
                    guilds.append(
                        {
                            "id": str(g.id),
                            "name": g.name,
                            "icon": str(g.icon.url) if g.icon else None,
                            "members": g.member_count,
                            "owner": str(g.owner),
                            "config": get_guild_config(g.id),
                        }
                    )
            return web.json_response(guilds)

        async def get_guild_settings(request):
            """Retorna la configuración detallada de un servidor (Privado)."""
            guild_id = request.match_info.get("guild_id")
            if not guild_id:
                return web.json_response({"error": "guild_id required"}, status=400)

            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                return web.json_response({"error": "Guild not found"}, status=404)

            config = get_guild_config(guild.id)

            # Obtener canales de texto y roles para los selects del dashboard
            channels = [{"id": str(c.id), "name": c.name} for c in guild.text_channels]
            roles = [{"id": str(r.id), "name": r.name} for r in guild.roles if not r.is_default()]

            # --- ESTADÍSTICAS REALES ---
            stats = {
                "pets": {"total": 0, "avg_level": 0},
                "economy": {"total_bal": 0, "avg_bal": 0},
                "moderation": {"total_logs": 0},
            }

            # RPG Stats
            mascotas_cog = self.bot.get_cog("Mascotas")
            if mascotas_cog:
                guild_pets = []
                for member in guild.members:
                    p = mascotas_cog.pets.get(str(member.id))
                    if p:
                        guild_pets.append(p)
                if guild_pets:
                    stats["pets"]["total"] = len(guild_pets)
                    stats["pets"]["avg_level"] = round(
                        sum(p["level"] for p in guild_pets) / len(guild_pets), 1
                    )

            # Economy Stats
            monedas_cog = self.bot.get_cog("Monedas")
            if monedas_cog:
                guild_bals = []
                for member in guild.members:
                    b = monedas_cog.bal.get(str(member.id), 0)
                    if b > 0:
                        guild_bals.append(b)
                if guild_bals:
                    stats["economy"]["total_bal"] = sum(guild_bals)
                    stats["economy"]["avg_bal"] = round(sum(guild_bals) / len(guild_bals), 1)

            # Moderation Stats
            logs = getattr(self.bot, "recent_logs", [])
            stats["moderation"]["total_logs"] = len(
                [l for l in logs if l.get("guild_id") == str(guild.id)]
            )

            return web.json_response(
                {
                    "config": config,
                    "channels": channels,
                    "roles": roles,
                    "name": guild.name,
                    "stats": stats,
                }
            )

        async def update_guild_config(request):
            """Actualiza ajustes del servidor vía API (Privado)."""
            try:
                data = await request.json()
            except Exception:
                return web.json_response({"error": "Invalid JSON"}, status=400)

            guild_id = data.get("guild_id")
            updates = data.get("updates", {})  # Diccionario con {key: value}

            if not guild_id:
                return web.json_response({"error": "Missing guild_id"}, status=400)

            # Validación de existencia de servidor
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                return web.json_response({"error": "Guild not found"}, status=404)

            # Lista blanca de configuraciones permitidas para evitar inyecciones en el JSON
            allowed_keys = [
                "log_channel_id",
                "staff_role_id",
                "staff_role_ids",
                "theme",
                "alert_channel_id",
                "license_plan",
                "confesiones_channel_id",
                "moderacion_logs_channel_id",
                "enabled_modules",
            ]

            for key, value in updates.items():
                if key not in allowed_keys:
                    continue  # Ignorar claves no permitidas

                # Convertir a int si son IDs de canales/roles y verificar que pertenecen al servidor
                if key in ["log_channel_id", "staff_role_id", "alert_channel_id"]:
                    try:
                        if value:
                            val_int = int(value)
                            # Verificación extra: ¿El canal/rol existe en este servidor?
                            if key == "log_channel_id" and not guild.get_channel(val_int):
                                continue
                            if key == "staff_role_id" and not guild.get_role(val_int):
                                continue
                            if key == "alert_channel_id" and not guild.get_channel(val_int):
                                continue
                            value = val_int
                        else:
                            value = None
                    except ValueError:
                        continue

                    if key == "staff_role_id":
                        set_guild_setting(int(guild_id), "staff_role_ids", [value] if value else [])
                        continue

                if key == "staff_role_ids":
                    if value is None:
                        set_guild_setting(int(guild_id), "staff_role_ids", [])
                        continue
                    if isinstance(value, (str, int)):
                        try:
                            rid = int(value)
                        except Exception:
                            continue
                        if not guild.get_role(rid):
                            continue
                        set_guild_setting(int(guild_id), "staff_role_ids", [rid])
                        continue
                    if isinstance(value, list):
                        normalized = []
                        ok = True
                        for item in value:
                            try:
                                rid = int(item)
                            except Exception:
                                ok = False
                                break
                            if not guild.get_role(rid):
                                ok = False
                                break
                            normalized.append(rid)
                        if not ok:
                            continue
                        set_guild_setting(int(guild_id), "staff_role_ids", normalized)
                        continue

                # Validación de tema
                if key == "theme" and value not in ["default", "ocean", "fire", "nature"]:
                    value = "default"

                if key == "license_plan":
                    if value is None:
                        value = None
                    else:
                        v = str(value).strip().lower()
                        if v not in ["basic", "pro", "elite", "custom"]:
                            continue
                        value = v

                if key in ["confesiones_channel_id", "moderacion_logs_channel_id"]:
                    if value:
                        try:
                            val_int = int(value)
                        except Exception:
                            continue
                        if not guild.get_channel(val_int):
                            continue
                        value = val_int
                    else:
                        value = None

                set_guild_setting(int(guild_id), key, value)

            return web.json_response({"status": "success"})

        async def get_logs(request):
            """Retorna los logs recientes filtrados por servidor (Privado)."""
            guild_id = request.match_info.get("guild_id")
            logs = getattr(self.bot, "recent_logs", [])

            if guild_id == "global":
                filtered = logs
            else:
                filtered = [entry for entry in logs if entry.get("guild_id") == guild_id]

            return web.json_response(filtered[::-1])  # Invertir para ver lo más reciente primero

        async def get_analytics(request):
            """Retorna las analíticas de actividad por servidor (Privado)."""
            guild_id = request.match_info.get("guild_id")
            analytics_cog = self.bot.get_cog("Analytics")
            if not analytics_cog:
                return web.json_response({"error": "Analytics module not loaded"}, status=503)

            data = analytics_cog.get_guild_analytics(guild_id)
            return web.json_response(data)

        async def get_streaming_config(request):
            """Retorna la configuración de streaming de un servidor (Privado)."""
            guild_id = request.match_info.get("guild_id")
            if not guild_id:
                return web.json_response({"error": "Missing guild_id"}, status=400)

            config = get_guild_setting(
                int(guild_id),
                "streaming_config",
                {
                    "enabled": False,
                    "target_ids": [],
                    "target_role_id": None,
                    "channel_id": None,
                    "message": "¡@everyone **{user}** está en directo en {platform}! 🔴",
                },
            )
            return web.json_response(config)

        async def update_streaming_config(request):
            """Actualiza la configuración de streaming (Privado)."""
            # ... existing logic ...
            try:
                data = await request.json()
            except Exception:
                return web.json_response({"error": "Invalid JSON"}, status=400)

            guild_id = data.get("guild_id")
            config = data.get("config", {})

            if not guild_id:
                return web.json_response({"error": "Missing guild_id"}, status=400)

            # Limpiar IDs de texto a números
            if "target_ids" in config:
                config["target_ids"] = [
                    int(tid) for tid in config["target_ids"] if str(tid).isdigit()
                ]
            if config.get("target_role_id"):
                config["target_role_id"] = int(config["target_role_id"])
            if config.get("channel_id"):
                config["channel_id"] = int(config["channel_id"])

            set_guild_setting(int(guild_id), "streaming_config", config)
            return web.json_response({"status": "success"})

        async def get_custom_cmds(request):
            """Retorna los comandos personalizados de un servidor (Privado)."""
            guild_id = request.match_info.get("guild_id")
            if not guild_id:
                return web.json_response({"error": "Missing guild_id"}, status=400)

            cmds = get_guild_setting(int(guild_id), "custom_commands", {})
            return web.json_response(cmds)

        async def update_custom_cmds(request):
            """Actualiza la lista de comandos personalizados (Privado)."""
            # ... logic ...
            try:
                data = await request.json()
            except Exception:
                return web.json_response({"error": "Invalid JSON"}, status=400)

            guild_id = data.get("guild_id")
            cmds = data.get("cmds", {})  # {name: {response: "..."}}

            if not guild_id:
                return web.json_response({"error": "Missing guild_id"}, status=400)

            set_guild_setting(int(guild_id), "custom_commands", cmds)
            return web.json_response({"status": "success"})

        async def get_gaming_profiles(request):
            """Retorna todos los perfiles gaming vinculados (Privado)."""
            gaming_cog = self.bot.get_cog("GamingProfiles")
            if not gaming_cog:
                return web.json_response({"error": "Gaming module not loaded"}, status=503)

            # Formatear datos para el frontend
            formatted = []
            for user_id, games in gaming_cog.profiles.items():
                user = self.bot.get_user(int(user_id))
                formatted.append(
                    {
                        "user_id": user_id,
                        "username": str(user) if user else f"Usuario {user_id}",
                        "avatar": str(user.avatar.url) if user and user.avatar else None,
                        "games": games,
                    }
                )
            return web.json_response(formatted)

        async def update_theme(request):
            """Actualiza el tema personalizado de un servidor (Privado)."""
            try:
                data = await request.json()
            except Exception:
                return web.json_response({"error": "Invalid JSON"}, status=400)

            guild_id = data.get("guild_id")
            colors = data.get("colors", {})  # {primary: 0x..., secondary: 0x...}
            footer = data.get("footer", "PoseidonUI")

            if not guild_id:
                return web.json_response({"error": "Missing guild_id"}, status=400)

            theme_name = f"custom_{guild_id}"
            Theme.create_custom_theme(theme_name, f"Tema Personalizado {guild_id}", colors, footer)
            Theme.set_theme(theme_name, guild_id)

            return web.json_response({"status": "success"})

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
        app.router.add_post("/api/login", login)
        app.router.add_get("/api/stats", get_bot_stats)
        app.router.add_get("/api/health", get_health)
        app.router.add_get("/api/guilds", get_guilds_list)
        app.router.add_get("/api/config/{guild_id}", get_guild_settings)
        app.router.add_post("/api/config/update", update_guild_config)
        app.router.add_get("/api/logs/{guild_id}", get_logs)
        app.router.add_get("/api/analytics/{guild_id}", get_analytics)
        app.router.add_get("/api/streaming/{guild_id}", get_streaming_config)
        app.router.add_post("/api/streaming/update", update_streaming_config)
        app.router.add_get("/api/custom_cmds/{guild_id}", get_custom_cmds)
        app.router.add_post("/api/custom_cmds/update", update_custom_cmds)
        app.router.add_get("/api/gaming/profiles", get_gaming_profiles)
        app.router.add_post("/api/theme/update", update_theme)
        app.router.add_post("/api/reboot", reboot_bot)

        # Frontend
        async def index(request):
            return web.FileResponse(os.path.join(website_path, "index.html"))

        async def login_page(request):
            return web.FileResponse(os.path.join(website_path, "login.html"))

        async def admin_page(request):
            return web.FileResponse(os.path.join(website_path, "admin.html"))

        app.router.add_get("/", index)
        app.router.add_get("/login", login_page)
        app.router.add_get("/admin", admin_page)
        app.router.add_static("/", website_path)

        self.runner = web.AppRunner(app)
        await self.runner.setup()

        self.site = web.TCPSite(self.runner, "0.0.0.0", self.port)

        try:
            await self.site.start()
            print(f"🌍 [WebServer] Dashboard con login en http://localhost:{self.port}")
        except Exception as e:
            print(f"❌ [WebServer] Error: {e}")


async def setup(bot):
    cog = WebServer(bot)
    await bot.add_cog(cog)
    # Sincronizar comandos de barra para este cog
    try:
        await bot.tree.sync()
        print("✅ [WebServer] Comandos de barra sincronizados.")
    except Exception as e:
        print(f"❌ [WebServer] Error al sincronizar comandos: {e}")
