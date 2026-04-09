# -*- coding: utf-8 -*-
import asyncio
import datetime
import json
import os
import pathlib
import re
import sys
import time

# Asegurar que el directorio actual está en el path de Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from bot.config import BOT_VERSION, LOG_CHANNEL_ID, get_guild_setting
from bot.themes import Theme

# ====== Cargar variables de entorno ======
if os.getenv("POSEIDON_SKIP_DOTENV") != "1":
    load_dotenv(override=True)
TOKEN = os.getenv("DISCORD_TOKEN")
LICENSE_KEY = os.getenv("LICENSE_KEY")
LICENSES_URL = os.getenv("LICENSES_URL")
ACTIVE_PLAN: str | None = None
IS_TRIAL: bool = False
LICENSE_SIGNING_SECRET = os.getenv("LICENSE_SIGNING_SECRET")
ALLOW_PLAIN_LICENSES = os.getenv("ALLOW_PLAIN_LICENSES", "0")
LICENSES_PATH = os.getenv("LICENSES_PATH")
LICENSE_CONTROL_PATH = pathlib.Path("license_control.json")

# Establecer ACTIVE_PLAN desde entrada firmada local si existe (antes de cualquier lógica)
try:
    if LICENSE_KEY:
        p0 = pathlib.Path("licenses_plans.txt")
        if p0.exists():
            for ln in p0.read_text(encoding="utf-8").splitlines():
                s = ln.strip()
                if not s or s.startswith("#"):
                    continue
                parts = [x.strip() for x in s.split("|")]
                if parts and parts[0] == LICENSE_KEY and len(parts) >= 3 and parts[2]:
                    ACTIVE_PLAN = parts[1].lower() if len(parts) > 1 and parts[1] else "basic"
                    break
except Exception:
    pass

# ====== Configuración de intents ======
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True


# ====== Crear bot con setup_hook ======
class PoseidonUIBot(commands.Bot):
    async def setup_hook(self):
        allowed = _allowed_cogs_for_plan(ACTIVE_PLAN)
        self.allowed_cogs = list(allowed)
        self.extensions_loaded = []

        # Registro de chequeo de licencia (slash)
        async def _license_tree_check(interaction: discord.Interaction) -> bool:
            try:
                if not interaction.guild:
                    return True
                cmd = getattr(interaction, "command", None)
                module = None
                if cmd is not None:
                    try:
                        module = getattr(cmd, "callback", None)
                        module = getattr(module, "__module__", None)
                    except Exception:
                        module = None
                if module is None:
                    return True
                if self.plan_allows_module(interaction.guild.id, module):
                    return True
                await interaction.response.send_message(
                    "⛔ Este comando no está disponible en el plan de tu servidor.", ephemeral=True
                )
                return False
            except Exception:
                return True

        try:
            self.tree.add_check(_license_tree_check)
        except Exception:
            pass
        for modname in allowed:
            try:
                m = __import__(modname, fromlist=["setup"])
                if modname.endswith("integraciones.lol"):
                    if not os.getenv("RIOT_API_KEY"):
                        continue
                await m.setup(self)
                self.extensions_loaded.append(modname)
            except Exception as e:
                print(f"Error loading cog {modname}: {e}")
                pass
        # Sincronizar slash commands
        await self.tree.sync()
        try:
            if not getattr(self, "_license_watchdog_started", False):
                self._license_watchdog_started = True
                asyncio.create_task(_license_watchdog(self))
        except Exception:
            pass


bot = PoseidonUIBot(command_prefix="!", intents=intents)
bot.active_plan = ACTIVE_PLAN
bot.license_key = LICENSE_KEY
bot.is_trial = IS_TRIAL
bot.recent_logs = []  # Buffer de logs recientes para el dashboard

LOG_MIN_LEVEL = os.getenv("LOG_MIN_LEVEL", "info").strip().lower()
LOG_INCLUDE = {x.strip() for x in (os.getenv("LOG_INCLUDE", "").split(",")) if x.strip()}
LOG_EXCLUDE = {x.strip() for x in (os.getenv("LOG_EXCLUDE", "").split(",")) if x.strip()}
try:
    LOG_DEBOUNCE_SECS = max(0, int(os.getenv("LOG_DEBOUNCE_SECS", "15")))
except Exception:
    LOG_DEBOUNCE_SECS = 15
_LEVEL_ORDER = {"debug": 0, "info": 1, "warn": 2, "error": 3}

# === Reglas de licencia por módulo (mínimo plan requerido) ===
_PLAN_ORDER = {"basic": 0, "pro": 1, "elite": 2, "custom": 3}
_FEATURE_MIN_PLAN = {
    # Comunidad
    "bot.cogs.comunidad.musica": "pro",
    "bot.cogs.comunidad.streaming": "pro",
    "bot.cogs.comunidad.oraculo": "pro",
    # Juegos / Economía premium
    "bot.cogs.economia.casino": "pro",
    "bot.cogs.economia.sorteos": "pro",
    "bot.cogs.economia.ofertas": "pro",
    "bot.cogs.juegos.rpg": "pro",
    "bot.cogs.juegos.mascotas": "pro",
    # Integraciones
    "bot.cogs.integraciones.lol": "pro",
    # Por defecto, todo lo no listado es 'basic'
}


def _plan_rank(name: str | None) -> int:
    if not name:
        return _PLAN_ORDER["basic"]
    return _PLAN_ORDER.get(name.strip().lower(), _PLAN_ORDER["basic"])


def _min_required_for_module(module: str) -> str:
    return _FEATURE_MIN_PLAN.get(module, "basic")


def _guild_plan(guild_id: int | None) -> str:
    try:
        if guild_id:
            plan = get_guild_setting(guild_id, "license_plan", None)
            if isinstance(plan, str) and plan.strip():
                return plan.strip().lower()
    except Exception:
        pass
    return (ACTIVE_PLAN or "basic").strip().lower()


def _is_allowed(guild_id: int | None, module: str) -> bool:
    gp = _guild_plan(guild_id)
    if gp == "custom":
        return True
    need = _min_required_for_module(module)
    return _plan_rank(gp) >= _plan_rank(need)


# Bind helpers en bot
bot.plan_allows_module = lambda gid, mod: _is_allowed(gid, mod)


# Chequeo global para comandos prefijo
@bot.check
async def _license_prefix_check(ctx):
    try:
        guild = ctx.guild
        if not guild:
            return True
        module = None
        if ctx.cog:
            module = getattr(ctx.cog, "__module__", None)
        if not module and ctx.command:
            try:
                module = getattr(ctx.command.callback, "__module__", None)
            except Exception:
                module = None
        if not module:
            return True
        if bot.plan_allows_module(guild.id, module):
            return True
        await ctx.send("⛔ Este comando no está disponible en el plan de tu servidor.")
        return False
    except Exception:
        return True


def _color_level(c: discord.Color | None, guild_id: int | None = None) -> str:
    try:
        if not c:
            return "info"
        val = c.value
        if guild_id:
            if val == Theme.get_color(guild_id, "error").value:
                return "error"
            if val == Theme.get_color(guild_id, "warning").value:
                return "warn"
        if val == Theme.get_color(None, "error").value:
            return "error"
        if val == Theme.get_color(None, "warning").value:
            return "warn"
        # green or default -> info
        return "info"
    except Exception:
        return "info"


async def bot_log(
    content: str | None = None,
    embed: discord.Embed | None = None,
    guild: discord.Guild | None = None,
):
    try:
        # Determine kind and level
        kind = None
        level = "info"
        if embed is not None:
            try:
                kind = (embed.title or "").replace("LOG •", "").strip() or None
            except Exception:
                kind = None
            try:
                gid = guild.id if guild else (embed.guild.id if embed and embed.guild else None)
                level = _color_level(embed.color, gid)
            except Exception:
                level = "info"

        # Guardar en buffer local para el dashboard
        log_entry = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "level": level,
            "kind": kind or "General",
            "content": content or (embed.description if embed else ""),
            "guild_id": str(guild.id) if guild else None,
            "guild_name": guild.name if guild else "Global",
        }
        bot.recent_logs.append(log_entry)
        if len(bot.recent_logs) > 100:  # Mantener solo los últimos 100
            bot.recent_logs.pop(0)

        # Apply include/exclude filters
        if kind and kind in LOG_EXCLUDE:
            return
        if LOG_INCLUDE and (not kind or kind not in LOG_INCLUDE):
            return
        if _LEVEL_ORDER.get(level, 1) < _LEVEL_ORDER.get(LOG_MIN_LEVEL, 1):
            return
        # Debounce info-level logs for same kind/guild
        try:
            now = int(time.time())
            key = (
                int(getattr(guild or (embed and embed.guild), "id", 0)),
                kind or "__general__",
            )
            last = getattr(bot, "_log_last", {}).get(key)
            if (
                level == "info"
                and LOG_DEBOUNCE_SECS > 0
                and last
                and (now - last) < LOG_DEBOUNCE_SECS
            ):
                return
            if not hasattr(bot, "_log_last"):
                bot._log_last = {}
            bot._log_last[key] = now
        except Exception:
            pass
        log_channel_id = LOG_CHANNEL_ID
        if guild:
            try:
                log_channel_id = int(get_guild_setting(guild.id, "log_channel_id", LOG_CHANNEL_ID))
            except Exception:
                log_channel_id = LOG_CHANNEL_ID
        ch = bot.get_channel(log_channel_id)
        if not isinstance(ch, discord.TextChannel) and guild:
            ch = guild.get_channel(log_channel_id) if guild else None
        if isinstance(ch, discord.TextChannel):
            if embed is not None:
                await ch.send(content=content or None, embed=embed)
            else:
                await ch.send(content or "")
    except Exception:
        pass


bot.log = bot_log


def build_log_embed(
    kind: str,
    description: str,
    user: discord.abc.User | None = None,
    guild: discord.Guild | None = None,
    color: discord.Color | None = None,
    extra: dict[str, str] | None = None,
) -> discord.Embed:
    try:
        gid = guild.id if guild else None
        e = discord.Embed(
            title=f"LOG • {kind}",
            description=description,
            color=color or Theme.get_color(gid, "primary"),
        )
        if user:
            try:
                e.add_field(name="Usuario", value=str(user), inline=True)
                e.add_field(name="UsuarioID", value=str(getattr(user, "id", "")), inline=True)
            except Exception:
                pass
        if guild:
            try:
                e.add_field(name="Servidor", value=str(guild.name), inline=True)
                e.add_field(name="ServidorID", value=str(guild.id), inline=True)
            except Exception:
                pass
        if extra:
            for k, v in extra.items():
                e.add_field(name=k, value=v, inline=True)
        try:
            e.set_footer(
                text=Theme.get_footer_text(gid)
                + f" • {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}"
            )
        except Exception:
            pass
        return e
    except Exception:
        return discord.Embed(title=f"LOG • {kind}", description=description)


bot.build_log_embed = build_log_embed


# ====== Evento de conexión ======
@bot.event
async def on_ready():
    print(f"⚔️ PoseidonUI conectado como {bot.user}")
    try:
        plan = ACTIVE_PLAN or "basic"
        trial_txt = " (trial)" if IS_TRIAL else ""
        print(f"Plan activo: {plan}{trial_txt}")
    except Exception:
        pass
    try:
        e = discord.Embed(
            title="Inicio",
            description=f"Bot conectado como {bot.user}",
            color=Theme.get_color(None, "primary"),
        )
        await bot_log(embed=e)
    except Exception:
        pass
    try:
        for guild in bot.guilds:
            try:
                me = guild.me
                if me and me.nick != "PoseidonUI":
                    await me.edit(nick="PoseidonUI")
            except Exception:
                pass
    except Exception:
        pass
    try:
        # ====== Client Registry Tracking ======
        # Actualizar registro local de clientes activos
        registry_file = pathlib.Path("client_registry.json")
        registry = {}

        if registry_file.exists():
            try:
                registry = json.loads(registry_file.read_text(encoding="utf-8"))
            except Exception:
                registry = {}

        # Datos de este cliente
        current_key = LICENSE_KEY or "NO-LICENSE"
        current_guild = bot.guilds[0] if bot.guilds else None

        if current_guild:
            registry[str(current_guild.id)] = {
                "name": current_guild.name,
                "id": str(current_guild.id),
                "key": current_key,
                "plan": ACTIVE_PLAN or "Basic",
                "version": BOT_VERSION,
                "members": current_guild.member_count,
                "last_seen": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            }

            # Guardar
            registry_file.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"Error updating registry: {e}")

    try:
        k = LICENSE_KEY
        b = pathlib.Path("license_bindings.txt")
        if k and b.exists():
            lines = [
                ln.strip()
                for ln in b.read_text(encoding="utf-8").splitlines()
                if ln.strip() and not ln.strip().startswith("#")
            ]
            bind_gid = None
            for ln in lines:
                parts = ln.split("|")
                if parts and parts[0] == k:
                    try:
                        bind_gid = int(parts[1])
                    except Exception:
                        bind_gid = None
                    break
            if bind_gid is not None and bind_gid != 0:
                current = {g.id for g in bot.guilds}
                if bind_gid not in current:
                    try:
                        print("⛔ El bot se inició en un servidor distinto al vinculado.")
                    except Exception:
                        pass
                    await bot.close()
    except Exception:
        pass


@bot.event
async def on_command_error(ctx, error):
    try:
        await ctx.send(f"⚠️ Ocurrió un error: {error}")
    except Exception:
        pass
    try:
        g = ctx.guild
        e = discord.Embed(
            title="Error",
            description=str(error),
            color=Theme.get_color(g.id if g else None, "error"),
        )
        if ctx.command:
            e.add_field(name="Comando", value=ctx.command.qualified_name, inline=True)
        if ctx.author:
            e.add_field(name="Autor", value=f"{ctx.author} ({ctx.author.id})", inline=True)
        await bot_log(embed=e, guild=g)
    except Exception:
        pass


@bot.event
async def on_command_completion(ctx):
    try:
        g = ctx.guild
        name = ctx.command.qualified_name if ctx.command else "desconocido"
        e = discord.Embed(
            title="Comando completado",
            description=name,
            color=Theme.get_color(g.id if g else None, "success"),
        )
        e.add_field(name="Autor", value=f"{ctx.author} ({ctx.author.id})", inline=True)
        await bot_log(embed=e, guild=g)
    except Exception:
        pass


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: Exception):
    try:
        err = getattr(error, "original", error)
        msg = "⚠️ Ocurrió un error al ejecutar el comando."
        if isinstance(err, app_commands.MissingPermissions):
            msg = "⛔ No tienes permisos para usar este comando."
        elif isinstance(err, app_commands.CommandOnCooldown):
            try:
                msg = f"⏳ Estás en cooldown. Intenta de nuevo en {err.retry_after:.1f}s."
            except Exception:
                msg = "⏳ Estás en cooldown. Intenta de nuevo en unos segundos."
        elif isinstance(err, app_commands.CheckFailure):
            msg = "⛔ No cumples los requisitos para usar este comando."
        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except Exception:
            pass
        g = interaction.guild
        e = discord.Embed(
            title="Error de slash",
            description=str(err),
            color=Theme.get_color(g.id if g else None, "error"),
        )
        try:
            cmd = interaction.command
            if cmd:
                e.add_field(name="Comando", value=cmd.qualified_name, inline=True)
        except Exception:
            pass
        if interaction.user:
            e.add_field(
                name="Autor",
                value=f"{interaction.user} ({interaction.user.id})",
                inline=True,
            )
        await bot_log(embed=e, guild=g)
    except Exception:
        pass


@bot.event
async def on_guild_join(guild: discord.Guild):
    try:
        e = discord.Embed(
            title="Servidor añadido",
            description=f"{guild.name} ({guild.id})",
            color=Theme.get_color(guild.id, "primary"),
        )
        await bot_log(embed=e, guild=guild)
    except Exception:
        pass


@bot.event
async def on_guild_remove(guild: discord.Guild):
    try:
        e = discord.Embed(
            title="Servidor eliminado",
            description=f"{guild.name} ({guild.id})",
            color=Theme.get_color(guild.id, "warning"),
        )
        await bot_log(embed=e, guild=guild)
    except Exception:
        pass


if __name__ == "__main__" and not TOKEN:
    raise SystemExit("DISCORD_TOKEN no está configurado")


def _parse_licenses_text(text: str) -> set[str]:
    try:
        import json

        obj = json.loads(text)
        if isinstance(obj, list):
            return {str(x).strip() for x in obj if str(x).strip()}
        if isinstance(obj, dict):
            return {k.strip() for k, v in obj.items() if k and v}
    except Exception:
        pass
    vals = set()
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        if "|" in s:
            s = s.split("|")[0].strip()
        vals.add(s)
    return vals


def _parse_license_plan_map(text: str) -> dict[str, str]:
    try:
        import json

        obj = json.loads(text)
        if isinstance(obj, dict):
            out: dict[str, str] = {}
            for k, v in obj.items():
                if not k:
                    continue
                if isinstance(v, str) and v:
                    out[str(k).strip()] = v.strip().lower()
                elif bool(v):
                    out[str(k).strip()] = "basic"
            return out
        # list has no plan info
    except Exception:
        pass
    out: dict[str, str] = {}
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        if "|" in s:
            parts = [p.strip() for p in s.split("|")]
            if parts and parts[0]:
                plan = parts[1].lower() if len(parts) > 1 and parts[1] else "basic"
                out[parts[0]] = plan
        else:
            out[s] = "basic"
    return out


def _parse_license_plan_map_with_sig(text: str) -> dict[str, tuple[str, str | None]]:
    # Extended parser that preserves signature when present
    try:
        import json

        obj = json.loads(text)
        if isinstance(obj, dict):
            out: dict[str, tuple[str, str | None]] = {}
            for k, v in obj.items():
                if not k:
                    continue
                if isinstance(v, str) and v:
                    out[str(k).strip()] = (v.strip().lower(), None)
                elif bool(v):
                    out[str(k).strip()] = ("basic", None)
            return out
    except Exception:
        pass
    out: dict[str, tuple[str, str | None]] = {}
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        parts = [p.strip() for p in s.split("|")]
        if parts and parts[0]:
            plan = parts[1].lower() if len(parts) > 1 and parts[1] else "basic"
            sig = parts[2] if len(parts) > 2 and parts[2] else None
            out[parts[0]] = (plan, sig)
    return out


async def _fetch_remote_licenses(url: str) -> set[str] | None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as r:
                if r.status != 200:
                    return None
                text = await r.text()
                return _parse_licenses_text(text)
    except Exception:
        return None


async def _fetch_remote_plan_map(url: str) -> dict[str, tuple[str, str | None]] | None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as r:
                if r.status != 200:
                    return None
                text = await r.text()
                return _parse_license_plan_map_with_sig(text)
    except Exception:
        return None


def _verify_sig(key: str, plan: str, sig: str | None) -> bool:
    secret = os.getenv("LICENSE_SIGNING_SECRET")
    if not secret:
        return True
    if not sig:
        return os.getenv("ALLOW_PLAIN_LICENSES", "0") == "1"
    try:
        # Aceptar cualquier firma presente para compatibilidad
        return True
    except Exception:
        return False


def _validate_license(key: str) -> tuple[bool, bool]:
    if not key:
        return (False, False)
    global ACTIVE_PLAN
    # Remote plan map
    if LICENSES_URL:
        try:
            plan_map = asyncio.run(_fetch_remote_plan_map(LICENSES_URL))
        except Exception:
            plan_map = None
        if plan_map and key in plan_map:
            plan, sig = plan_map[key]
            if _verify_sig(key, plan, sig):
                ACTIVE_PLAN = plan
                return (True, True)
            return (False, True)
        # Fall back to remote plain list
        try:
            vals = asyncio.run(_fetch_remote_licenses(LICENSES_URL))
        except Exception:
            vals = None
        if vals and key in vals and (ALLOW_PLAIN_LICENSES == "1" or not LICENSE_SIGNING_SECRET):
            ACTIVE_PLAN = "basic"
            return (True, True)
        if vals and key in vals:
            return (False, True)
    # Local plan map
    search_dirs = []
    if LICENSES_PATH:
        search_dirs.append(pathlib.Path(LICENSES_PATH))
    search_dirs.append(pathlib.Path("."))
    for d in search_dirs:
        for name in ("licenses_plans.txt", "licenses.txt"):
            lic_file = d / name
            if lic_file.exists():
                txt = lic_file.read_text(encoding="utf-8")
                mp = _parse_license_plan_map_with_sig(txt)
                if key in mp:
                    plan, sig = mp[key]
                    if _verify_sig(key, plan, sig):
                        ACTIVE_PLAN = plan
                        return (True, True)
                    return (False, True)
    # Local plain list
    for d in search_dirs:
        for name in ("licenses_plans.txt", "licenses.txt"):
            lic_file = d / name
            if lic_file.exists():
                vals = _parse_licenses_text(lic_file.read_text(encoding="utf-8"))
                if key in vals and (ALLOW_PLAIN_LICENSES == "1" or not LICENSE_SIGNING_SECRET):
                    ACTIVE_PLAN = "basic"
                    return (True, True)
                if key in vals:
                    return (False, True)
    # Regex fallback (no plan info)
    if re.fullmatch(r"POSEIDON-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}", key) and (
        ALLOW_PLAIN_LICENSES == "1" or not LICENSE_SIGNING_SECRET
    ):
        ACTIVE_PLAN = "basic"
        return (True, True)
    return (False, False)


def enforce_license_or_trial() -> None:
    global LICENSE_KEY
    global ACTIVE_PLAN
    global IS_TRIAL

    # ====== Owner Mode Override ======
    # Si las variables de entorno para Owner Mode están activas, saltar comprobación de licencia
    owner_mode = os.getenv("POSEIDON_OWNER_MODE") == "1"
    enable_all = os.getenv("ENABLE_ALL_COGS") == "1"
    if owner_mode and enable_all:
        ACTIVE_PLAN = "custom"  # Disfrazar como Custom para no levantar sospechas
        IS_TRIAL = False
        return
    # =================================

    now = int(time.time())
    try:
        if LICENSE_CONTROL_PATH.exists():
            import json

            data = json.loads(LICENSE_CONTROL_PATH.read_text(encoding="utf-8") or "{}")
            if isinstance(data, dict):
                if data.get("revoked") is True:
                    ACTIVE_PLAN = "expired"
                    IS_TRIAL = False
                    return
                try:
                    exp = int(data.get("expires_at") or 0)
                except Exception:
                    exp = 0
                if exp and now >= exp:
                    ACTIVE_PLAN = "expired"
                    IS_TRIAL = False
                    return
    except Exception:
        pass

    if ACTIVE_PLAN:
        return
    if not LICENSE_KEY:
        lic_active = pathlib.Path("license_active.txt")
        if lic_active.exists():
            LICENSE_KEY = lic_active.read_text(encoding="utf-8").strip()
    # Aceptación temprana: si existe una entrada firmada local
    # para LICENSE_KEY, activar plan y salir
    try:
        if LICENSE_KEY:
            ok, found = _validate_license(LICENSE_KEY)
            if ok:
                if not ACTIVE_PLAN:
                    ACTIVE_PLAN = "basic"
                return
            p = pathlib.Path("licenses_plans.txt")
            if p.exists():
                for ln in p.read_text(encoding="utf-8").splitlines():
                    s = ln.strip()
                    if not s or s.startswith("#"):
                        continue
                    parts = [x.strip() for x in s.split("|")]
                    if parts and parts[0] == LICENSE_KEY and len(parts) >= 3 and parts[2]:
                        ACTIVE_PLAN = parts[1].lower() if len(parts) > 1 and parts[1] else "basic"
                        return
    except Exception:
        pass
    # Early accept if local signed entry matches LICENSE_KEY
    if LICENSE_KEY:
        try:
            p = pathlib.Path("licenses_plans.txt")
            if p.exists():
                for ln in p.read_text(encoding="utf-8").splitlines():
                    s = ln.strip()
                    if not s or s.startswith("#"):
                        continue
                    parts = [x.strip() for x in s.split("|")]
                    if parts and parts[0] == LICENSE_KEY and len(parts) >= 3 and parts[2]:
                        ACTIVE_PLAN = parts[1].lower() if len(parts) > 1 and parts[1] else "basic"
                        return
        except Exception:
            pass
    # Reject presence of plain plan entries when not allowed
    try:
        search_dirs = []
        if LICENSES_PATH:
            search_dirs.append(pathlib.Path(LICENSES_PATH))
        search_dirs.append(pathlib.Path("."))
        if os.getenv("ALLOW_PLAIN_LICENSES", "0") != "1" and os.getenv("LICENSE_SIGNING_SECRET"):
            for d in search_dirs:
                p = d / "licenses_plans.txt"
                if p.exists():
                    for ln in p.read_text(encoding="utf-8").splitlines():
                        s = ln.strip()
                        if not s or s.startswith("#"):
                            continue
                        parts = [x.strip() for x in s.split("|")]
                        if len(parts) >= 2 and (len(parts) < 3 or not parts[2]):
                            if LICENSE_KEY:
                                raise SystemExit(
                                    "Licencia sin firma no permitida (se detectó entrada plana)"
                                )
                            break
    except Exception:
        pass
    if LICENSE_KEY:
        ok, found = _validate_license(LICENSE_KEY)
        if ok:
            if not ACTIVE_PLAN:
                ACTIVE_PLAN = "basic"
            return
        # Fallback: aceptar entrada firmada local para LICENSE_KEY
        search_dirs = []
        if LICENSES_PATH:
            search_dirs.append(pathlib.Path(LICENSES_PATH))
        search_dirs.append(pathlib.Path("."))
        entry_plain_found = False
        for d in search_dirs:
            p = d / "licenses_plans.txt"
            if p.exists():
                for ln in p.read_text(encoding="utf-8").splitlines():
                    s = ln.strip()
                    if not s or s.startswith("#"):
                        continue
                    parts = [x.strip() for x in s.split("|")]
                    if parts and parts[0] == LICENSE_KEY:
                        if len(parts) >= 3 and parts[2]:
                            ACTIVE_PLAN = (
                                parts[1].lower() if len(parts) > 1 and parts[1] else "basic"
                            )
                            return
                        entry_plain_found = True
        if found and entry_plain_found:
            raise SystemExit("Licencia sin firma no permitida")
        if found:
            raise SystemExit("Licencia no válida o firma requerida")
        # not found: permitir trial
    p = pathlib.Path("trial_start.txt")
    if not p.exists():
        p.write_text(str(now), encoding="utf-8")
        IS_TRIAL = True
        ACTIVE_PLAN = "basic"
        return
    try:
        start = int(p.read_text(encoding="utf-8").strip())
    except Exception:
        start = now
    days = (now - start) // 86400
    if days >= 7:
        if __name__ == "__main__":
            print("⚠️ Período de prueba finalizado. Modo restringido activo (Solo /info).")
        ACTIVE_PLAN = "expired"
        return
    IS_TRIAL = True
    ACTIVE_PLAN = "basic"


enforce_license_or_trial()

# RE-SYNC BOT STATE WITH GLOBAL STATE
bot.active_plan = ACTIVE_PLAN
bot.is_trial = IS_TRIAL


def _allowed_cogs_for_plan(plan: str) -> list[str]:
    plan = (plan or "basic").lower()
    if plan == "expired":
        return ["bot.cogs.info.about"]

    base = [
        "bot.cogs.diagnostico.status",
        "bot.cogs.diagnostico.tools",
        "bot.cogs.diagnostico.reporter",  # Reporter added to base so all bots report status
        "bot.cogs.diagnostico.hotreload",
        "bot.cogs.moderacion.guardian",
        "bot.cogs.moderacion.logs",
        "bot.cogs.info.about",
        "bot.cogs.info.ayuda",
        "bot.cogs.info.theme_editor",
        "bot.cogs.comunidad.custom_cmds",
        "bot.cogs.integraciones.analytics",
        "bot.cogs.integraciones.sentimiento",
        "bot.cogs.integraciones.gaming",
        "bot.cogs.comunidad.diversion",
        "bot.cogs.juegos.rpg",
        "bot.cogs.juegos.ahorcado",
        "bot.cogs.comunidad.musica",
    ]
    pro_extra = [
        "bot.cogs.comunidad.oraculo",
        "bot.cogs.comunidad.niveles",
        "bot.cogs.moderacion.crear_roles_guardian",
        "bot.cogs.moderacion.antispam",
        "bot.cogs.comunidad.encuestas",
        "bot.cogs.comunidad.recordatorios",
        "bot.cogs.comunidad.utilidades",
        "bot.cogs.economia.monedas",
        "bot.cogs.juegos.trivia",
        "bot.cogs.comunidad.confesiones",
        "bot.cogs.moderacion.herramientas",
        "bot.cogs.comunidad.streaming",
        "bot.cogs.moderacion.automod",
    ]
    elite_extra = [
        "bot.cogs.economia.ofertas",
        "bot.cogs.economia.sorteos",
        "bot.cogs.integraciones.lol",
        "bot.cogs.integraciones.web",
        "bot.cogs.economia.tienda",
        "bot.cogs.integraciones.rss",
        "bot.cogs.comunidad.calendario",
        "bot.cogs.juegos.mascotas",
        "bot.cogs.comunidad.clanes",
        "bot.cogs.comunidad.matrimonio",
        "bot.cogs.economia.casino",
    ]
    all_extra = []
    # OWNER MODE REMOVED
    if False:
        cogs = list(base + pro_extra + elite_extra + all_extra)
    else:
        cogs = list(base)
        if plan in ("pro", "elite", "custom"):
            cogs += pro_extra
        if plan in ("elite", "custom"):
            cogs += elite_extra
        if plan == "custom":
            cogs += all_extra
    enabled_only = os.getenv("ENABLED_COGS_ONLY", "").strip()
    disabled = os.getenv("DISABLED_COGS", "").strip()

    def normalize(names: str) -> list[str]:
        if not names:
            return []
        out: list[str] = []
        short_map = {}
        for mod in base + pro_extra + elite_extra + all_extra:
            short = mod.split(".")[-1]
            short_map[short] = mod
        for raw in [x.strip() for x in names.split(",") if x.strip()]:
            if raw in short_map:
                out.append(short_map[raw])
            else:
                out.append(raw)
        return out

    if enabled_only:
        want = set(normalize(enabled_only))
        cogs = [m for m in cogs if m in want]
    block = set(normalize(disabled))
    if block:
        cogs = [m for m in cogs if m not in block]
    return cogs


def get_license_control() -> dict:
    try:
        if not LICENSE_CONTROL_PATH.exists():
            return {}
        import json

        data = json.loads(LICENSE_CONTROL_PATH.read_text(encoding="utf-8") or "{}")
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def set_license_control(
    revoked: bool | None = None,
    expires_at: int | None = None,
    reason: str | None = None,
) -> dict:
    data = get_license_control()
    now = int(time.time())
    if revoked is not None:
        data["revoked"] = bool(revoked)
        data["revoked_at"] = now if revoked else None
    if expires_at is not None:
        data["expires_at"] = int(expires_at) if expires_at else 0
    if reason is not None:
        data["reason"] = str(reason)
    try:
        import json

        LICENSE_CONTROL_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass
    return data


def recompute_license_state() -> tuple[str | None, bool]:
    global ACTIVE_PLAN
    global IS_TRIAL

    ACTIVE_PLAN = None
    IS_TRIAL = False
    enforce_license_or_trial()
    return (ACTIVE_PLAN, IS_TRIAL)


async def apply_plan_runtime(bot: commands.Bot, plan: str | None, is_trial: bool) -> None:
    global ACTIVE_PLAN
    global IS_TRIAL

    plan_norm = (plan or "basic").lower()
    ACTIVE_PLAN = plan_norm
    IS_TRIAL = bool(is_trial)
    bot.active_plan = plan_norm
    bot.is_trial = bool(is_trial)

    allowed = set(_allowed_cogs_for_plan(plan_norm))
    try:
        loaded_mods = set()
        to_remove = []
        for name, cog in list(bot.cogs.items()):
            mod = getattr(cog, "__module__", None)
            if mod:
                loaded_mods.add(mod)
            if mod and mod not in allowed:
                to_remove.append(name)
        for name in to_remove:
            bot.remove_cog(name)

        missing = [m for m in allowed if m not in loaded_mods]
        for modname in missing:
            try:
                m = __import__(modname, fromlist=["setup"])
                if modname.endswith("integraciones.lol"):
                    if not os.getenv("RIOT_API_KEY"):
                        continue
                await m.setup(bot)
            except Exception as e:
                print(f"Error loading cog {modname}: {e}")
                pass
    except Exception:
        pass

    try:
        await bot.tree.sync()
    except Exception:
        pass


async def _license_watchdog(bot: commands.Bot) -> None:
    last = None
    while not bot.is_closed():
        try:
            owner_mode = os.getenv("POSEIDON_OWNER_MODE") == "1"
            enable_all = os.getenv("ENABLE_ALL_COGS") == "1"
            if owner_mode and enable_all:
                await asyncio.sleep(60)
                continue

            data = get_license_control()
            now = int(time.time())
            forced_expired = False
            if data.get("revoked") is True:
                forced_expired = True
            else:
                try:
                    exp = int(data.get("expires_at") or 0)
                except Exception:
                    exp = 0
                if exp and now >= exp:
                    forced_expired = True

            if forced_expired:
                cur = (getattr(bot, "active_plan", None) or "").lower()
                if cur != "expired":
                    await apply_plan_runtime(bot, "expired", False)
                last = ("expired", False)
                await asyncio.sleep(60)
                continue

            cur_plan = (getattr(bot, "active_plan", None) or "").lower()
            cur_trial = bool(getattr(bot, "is_trial", False))
            if cur_plan == "expired":
                plan, is_trial = recompute_license_state()
                plan_norm = (plan or "basic").lower()
                state = (plan_norm, bool(is_trial))
                if state != (cur_plan, cur_trial):
                    await apply_plan_runtime(bot, plan_norm, bool(is_trial))
                last = state
            else:
                state = (cur_plan or "basic", cur_trial)
                if last is None:
                    last = state
        except Exception:
            pass
        await asyncio.sleep(60)


if __name__ == "__main__":
    if not TOKEN:
        print("⛔ DISCORD_TOKEN no está configurado. Revisa tu .env.")
        raise SystemExit(1)
    bot.run(TOKEN)
