# -*- coding: utf-8 -*-
import importlib
import importlib.util
import sys
import threading
from typing import Iterable

import discord
from discord import app_commands
from discord.ext import commands

_RELOAD_LOCK = threading.Lock()


def _iter_tree_commands(tree: app_commands.CommandTree) -> Iterable[app_commands.Command]:
    for cmd in tree.get_commands():
        yield cmd


def _command_module(cmd: app_commands.Command) -> str | None:
    try:
        cb = getattr(cmd, "callback", None)
        return getattr(cb, "__module__", None)
    except Exception:
        return None


def _syntax_check(module_name: str) -> tuple[bool, str | None]:
    try:
        spec = importlib.util.find_spec(module_name)
        if not spec or not spec.origin or spec.origin == "built-in":
            return False, "Spec no encontrado"
        path = spec.origin
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        compile(source, path, "exec")
        return True, None
    except SyntaxError as e:
        try:
            return False, f"SyntaxError: {e.msg} (L{e.lineno}:{e.offset})"
        except Exception:
            return False, "SyntaxError"
    except Exception as e:
        return False, str(e)


class HotReload(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def cog_unload(self):
        try:
            self.bot.tree.remove_command("cog")
        except Exception:
            pass

    cog_group = app_commands.Group(name="cog", description="Gestión de cogs (hot-reload)")

    @cog_group.command(name="list", description="Lista cogs cargados y módulos permitidos")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def cog_list(self, interaction: discord.Interaction):
        allowed = getattr(self.bot, "allowed_cogs", None)
        if not isinstance(allowed, list):
            allowed = []
        loaded = sorted(set(getattr(self.bot, "extensions_loaded", [])))
        if not loaded:
            loaded = sorted({cog.__module__ for cog in self.bot.cogs.values()})

        text = f"Permitidos: {len(allowed)}\n" f"Cargados: {len(loaded)}\n\n" + "\n".join(
            f"- {m}" for m in loaded[:60]
        )
        if len(loaded) > 60:
            text += f"\n... +{len(loaded) - 60} más"
        await interaction.response.send_message(f"```text\n{text}\n```", ephemeral=True)

    async def _allowed_modules(self) -> list[str]:
        allowed = getattr(self.bot, "allowed_cogs", None)
        if isinstance(allowed, list) and allowed:
            return [str(x) for x in allowed]
        return sorted({cog.__module__ for cog in self.bot.cogs.values()})

    @cog_group.command(name="reload", description="Recarga un cog por módulo")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(modulo="Ej: bot.cogs.comunidad.musica", sync="guild|global")
    async def cog_reload(
        self,
        interaction: discord.Interaction,
        modulo: str,
        sync: str = "guild",
    ):
        await interaction.response.defer(ephemeral=True, thinking=True)

        allowed = await self._allowed_modules()
        if modulo not in allowed:
            await interaction.followup.send("⛔ Módulo no permitido.", ephemeral=True)
            return

        ok, err = _syntax_check(modulo)
        if not ok:
            await interaction.followup.send(f"⛔ Pre-check falló: {err}", ephemeral=True)
            return

        with _RELOAD_LOCK:
            removed_cogs = []
            for name, cog in list(self.bot.cogs.items()):
                if getattr(cog, "__module__", None) == modulo:
                    try:
                        removed = self.bot.remove_cog(name)
                        if removed:
                            removed_cogs.append(name)
                    except Exception:
                        pass

            removed_cmds = 0
            for cmd in list(_iter_tree_commands(self.bot.tree)):
                if _command_module(cmd) == modulo:
                    try:
                        self.bot.tree.remove_command(cmd.name, type=cmd.type)
                        removed_cmds += 1
                    except Exception:
                        pass

            try:
                if modulo in sys.modules:
                    module_obj = sys.modules[modulo]
                    importlib.reload(module_obj)
                else:
                    importlib.import_module(modulo)
                m = sys.modules[modulo]
                setup = getattr(m, "setup", None)
                if not setup:
                    raise RuntimeError("No existe setup() en el módulo")
                res = setup(self.bot)
                if hasattr(res, "__await__"):
                    await res
            except Exception as e:
                try:
                    await self.bot.log(
                        embed=self.bot.build_log_embed(
                            "HotReload",
                            "Recarga fallida",
                            user=interaction.user,
                            guild=interaction.guild,
                            extra={"Módulo": modulo, "Error": str(e)[:900]},
                        ),
                        guild=interaction.guild,
                    )
                except Exception:
                    pass
                await interaction.followup.send(
                    f"⛔ Recarga fallida.\n\n```text\n{type(e).__name__}: {e}\n```",
                    ephemeral=True,
                )
                return

        try:
            if sync == "guild" and interaction.guild:
                await self.bot.tree.sync(guild=interaction.guild)
            elif sync == "global":
                await self.bot.tree.sync()
        except Exception:
            pass

        try:
            await self.bot.log(
                embed=self.bot.build_log_embed(
                    "HotReload",
                    "Recarga completada",
                    user=interaction.user,
                    guild=interaction.guild,
                    extra={
                        "Módulo": modulo,
                        "Cogs removidos": ", ".join(removed_cogs) or "-",
                        "Cmds removidos": str(removed_cmds),
                        "Sync": sync,
                    },
                ),
                guild=interaction.guild,
            )
        except Exception:
            pass

        await interaction.followup.send(
            f"✅ Recargado: `{modulo}`\nCogs removidos: {len(removed_cogs)} | Cmds removidos: {removed_cmds}",
            ephemeral=True,
        )

    @cog_reload.autocomplete("modulo")
    async def cog_reload_autocomplete(self, interaction: discord.Interaction, current: str):
        allowed = await self._allowed_modules()
        current_low = (current or "").lower()
        items = [m for m in allowed if current_low in m.lower()]
        return [app_commands.Choice(name=m, value=m) for m in items[:25]]


async def setup(bot: commands.Bot):
    await bot.add_cog(HotReload(bot))
