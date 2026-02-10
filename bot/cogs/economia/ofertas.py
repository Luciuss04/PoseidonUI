import asyncio
import os
from datetime import datetime
from typing import Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv
from bot.themes import Theme

load_dotenv()
CANAL_OFERTAS_ID = os.getenv("CANAL_OFERTAS_ID")
CANAL_OFERTAS_ID = int(CANAL_OFERTAS_ID) if CANAL_OFERTAS_ID else None

CHEAPSHARK_URL = "https://www.cheapshark.com/api/1.0/deals"

STORE_MAP = {
    "1": "Steam",
    "7": "Fanatical",
    "11": "Humble Store",
    "15": "GOG",
    "23": "Epic Games",
}

TIENDA_ALIAS = {
    "steam": "Steam",
    "epic": "Epic Games",
    "epic games": "Epic Games",
    "gog": "GOG",
    "humble": "Humble Store",
    "humble store": "Humble Store",
    "fanatical": "Fanatical",
}


class Ofertas(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        if CANAL_OFERTAS_ID is not None:
            self.publicar_ofertas.start()
        self.cache: dict[int, list] = {}

    def cog_unload(self):
        self.publicar_ofertas.cancel()

    @app_commands.command(
        name="ofertas", description="Muestra al menos 30 ofertas de juegos de PC"
    )
    @app_commands.describe(
        tienda="Filtra por tienda (Steam, Epic, GOG, Humble, Fanatical)",
        descuento_min="Mínimo descuento (0-90)",
    )
    async def ofertas(
        self,
        interaction: discord.Interaction,
        tienda: Optional[str] = None,
        descuento_min: Optional[int] = None,
    ):
        await interaction.response.defer()
        fecha = datetime.now().strftime("%d-%m-%Y")
        nombre_thread = f"🌌 Profecías del Olimpo — {fecha}"
        try:
            existentes = [
                t for t in interaction.channel.threads if t.name == nombre_thread
            ]
            if existentes:
                await interaction.followup.send(
                    "🕒 Ya se han publicado las ofertas de hoy en este canal.",
                    ephemeral=True,
                )
                return
        except Exception:
            pass
        juegos = await self.obtener_ofertas()
        # Aplicar filtros
        tienda_norm = None
        if tienda:
            key = tienda.strip().lower()
            tienda_norm = TIENDA_ALIAS.get(key)
            if not tienda_norm:
                # Intentar coincidir con STORE_MAP values
                vals = set(STORE_MAP.values())
                for v in vals:
                    if v.lower() == key:
                        tienda_norm = v
                        break
        if descuento_min is not None:
            try:
                descuento_min = max(0, min(90, int(descuento_min)))
            except Exception:
                descuento_min = None
        if tienda_norm:
            juegos = [
                d
                for d in juegos
                if (
                    d.get("storeName") or STORE_MAP.get(str(d.get("storeID")), "")
                ).strip()
                == tienda_norm
            ]
        if descuento_min is not None:
            juegos = [
                d for d in juegos if int(float(d.get("savings", 0))) >= descuento_min
            ]
        if not juegos:
            await interaction.followup.send(
                "⚡ Hoy el Olimpo no encontró tesoros.", ephemeral=True
            )
            return

        juegos.sort(key=lambda j: float(j.get("savings", 0)), reverse=True)
        try:
            thread = await interaction.channel.create_thread(
                name=nombre_thread, type=discord.ChannelType.public_thread
            )
        except Exception:
            await interaction.followup.send(
                "⚠️ No se pudo crear el thread en este canal.", ephemeral=True
            )
            return

        try:
            top30 = juegos[:30]
            dist: dict[str, int] = {}
            for j in top30:
                sid = str(j.get("storeID"))
                st = j.get("storeName") or STORE_MAP.get(sid, "Desconocido")
                dist[st] = dist.get(st, 0) + 1
            mejor = max((int(float(j.get("savings", 0))) for j in top30), default=0)
            resumen = discord.Embed(
                title=f"✨ Ofertas del día — {fecha}",
                description="Selección curada de 30 ofertas destacadas",
                color=Theme.get_color(interaction.guild.id, 'primary'),
            )
            resumen.set_footer(text=Theme.get_footer_text(interaction.guild.id))
            if dist:
                resumen.add_field(
                    name="Tiendas",
                    value=" · ".join(f"{k}: {v}" for k, v in dist.items()),
                    inline=False,
                )
            resumen.add_field(name="Mejor descuento", value=f"−{mejor}%", inline=True)
            resumen.add_field(name="Fuente", value="CheapShark", inline=True)
            if tienda_norm or descuento_min is not None:
                filtros = []
                if tienda_norm:
                    filtros.append(f"Tienda: {tienda_norm}")
                if descuento_min is not None:
                    filtros.append(f"Min desc: −{descuento_min}%")
                resumen.add_field(
                    name="Filtros", value=" · ".join(filtros), inline=False
                )
            # cache y vista interactiva
            self.cache[thread.id] = juegos
            msg_head = await thread.send(
                embed=resumen, view=OfertasFilterView(self, thread.id)
            )
            try:
                e = interaction.client.build_log_embed(
                    "Economía/Ofertas",
                    f"Ofertas publicadas en {thread.mention}",
                    user=interaction.user,
                    guild=interaction.guild,
                )
                await interaction.client.log(embed=e, guild=interaction.guild)
            except Exception:
                pass
            try:
                await msg_head.pin()
            except Exception:
                pass
        except Exception:
            pass

        for idx, j in enumerate(juegos[:30], start=1):
            await thread.send(embed=self.crear_embed(j, idx, interaction.guild.id))

        asyncio.create_task(self.cerrar_thread(thread, horas=24))
        await interaction.followup.send(
            "✨ Se ha abierto un pergamino con las 30 profecías en un thread (cerrará en 24h).",
            ephemeral=True,
        )

    @tasks.loop(hours=24)
    async def publicar_ofertas(self):
        await self.bot.wait_until_ready()
        canal = self.bot.get_channel(CANAL_OFERTAS_ID)
        if not canal:
            return
        fecha = datetime.now().strftime("%d-%m-%Y")
        nombre_thread = f"🌌 Profecías del Olimpo — {fecha}"
        try:
            existentes = [t for t in canal.threads if t.name == nombre_thread]
            if existentes:
                return
        except Exception:
            pass

        juegos = await self.obtener_ofertas()
        if not juegos:
            await canal.send("⚡ Hoy el Olimpo no encontró tesoros.")
            try:
                e = self.bot.build_log_embed(
                    "Economía/Ofertas",
                    "No se encontraron ofertas hoy",
                    guild=canal.guild,
                )
                await self.bot.log(embed=e, guild=canal.guild)
            except Exception:
                pass
            return

        juegos.sort(key=lambda j: float(j.get("savings", 0)), reverse=True)
        try:
            thread = await canal.create_thread(
                name=nombre_thread, type=discord.ChannelType.public_thread
            )
        except Exception:
            return

        try:
            top30 = juegos[:30]
            dist: dict[str, int] = {}
            for j in top30:
                sid = str(j.get("storeID"))
                st = j.get("storeName") or STORE_MAP.get(sid, "Desconocido")
                dist[st] = dist.get(st, 0) + 1
            mejor = max((int(float(j.get("savings", 0))) for j in top30), default=0)
            resumen = discord.Embed(
                title=f"✨ Ofertas del día — {fecha}",
                description="Selección curada de 30 ofertas destacadas",
                color=Theme.get_color(canal.guild.id, 'primary'),
            )
            resumen.set_footer(text=Theme.get_footer_text(canal.guild.id))
            if dist:
                resumen.add_field(
                    name="Tiendas",
                    value=" · ".join(f"{k}: {v}" for k, v in dist.items()),
                    inline=False,
                )
            resumen.add_field(name="Mejor descuento", value=f"−{mejor}%", inline=True)
            resumen.add_field(name="Fuente", value="CheapShark", inline=True)
            # cache y vista interactiva
            self.cache[thread.id] = juegos
            msg_head = await thread.send(
                embed=resumen, view=OfertasFilterView(self, thread.id)
            )
            try:
                e = self.bot.build_log_embed(
                    "Economía/Ofertas",
                    f"Ofertas publicadas en {thread.mention}",
                    guild=thread.guild,
                )
                await self.bot.log(embed=e, guild=thread.guild)
            except Exception:
                pass
            try:
                await msg_head.pin()
            except Exception:
                pass
        except Exception:
            pass

        for idx, j in enumerate(juegos[:30], start=1):
            await thread.send(embed=self.crear_embed(j, idx, canal.guild.id))

        asyncio.create_task(self.cerrar_thread(thread, horas=24))

    async def cerrar_thread(self, thread, horas=24):
        await asyncio.sleep(horas * 3600)
        try:
            await thread.edit(archived=True, locked=True)
        except Exception:
            pass

    async def obtener_ofertas(self):
        params = {"storeID": "1,7,11,15,23", "pageSize": "50", "sortBy": "savings"}
        async with aiohttp.ClientSession() as session:
            async with session.get(CHEAPSHARK_URL, params=params) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()

        filtrados = []
        for d in data:
            title = d.get("title", "").lower()
            if any(x in title for x in ["dlc", "bundle", "soundtrack"]):
                continue
            filtrados.append(d)

        return filtrados

    def crear_embed(self, j, idx, guild_id: int, compact: bool = False):
        title = j.get("title")
        store_id = str(j.get("storeID"))
        store = j.get("storeName") or STORE_MAP.get(store_id, "Desconocido")
        price_new = j.get("salePrice")
        price_old = j.get("normalPrice")
        cut = int(float(j.get("savings", 0)))
        link = f"https://www.cheapshark.com/redirect?dealID={j.get('dealID')}"
        thumb = j.get("thumb")

        if cut >= 75:
            emoji = "🔥"
            color = Theme.get_color(guild_id, 'warning')
        elif cut >= 60:
            emoji = "💎"
            color = Theme.get_color(guild_id, 'success')
        elif cut >= 45:
            emoji = "⭐"
            color = Theme.get_color(guild_id, 'primary')
        else:
            emoji = "🌙"
            color = Theme.get_color(guild_id, 'secondary')

        numeros = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
        contador = "".join(numeros[int(d)] for d in str(idx))

        embed = discord.Embed(
            title=f"{contador} {emoji} {title}", color=color, url=link
        )
        if compact:
            embed.add_field(
                name="Precio", value=f"~~{price_old}€~~ → **{price_new}€**", inline=True
            )
            embed.add_field(name="−%", value=f"{cut}%", inline=True)
            embed.add_field(name="Tienda", value=store, inline=True)
        else:
            embed.add_field(
                name="Precio", value=f"~~{price_old}€~~ → **{price_new}€**", inline=True
            )
            embed.add_field(name="Descuento", value=f"−{cut}%", inline=True)
            embed.add_field(name="Tienda", value=store, inline=True)
            meta = j.get("metacriticScore")
            steam_pct = j.get("steamRatingPercent")
            steam_txt = j.get("steamRatingText")
            extra = []
            if meta:
                extra.append(f"Metacritic {meta}")
            if steam_pct:
                extra.append(f"Steam {steam_pct}%")
            if steam_txt:
                extra.append(str(steam_txt))
            if extra:
                embed.add_field(name="Reseñas", value=" · ".join(extra), inline=False)
            if thumb:
                embed.set_thumbnail(url=thumb)
            if cut >= 75:
                embed.add_field(name="Destacado", value="TOP oferta", inline=False)
        embed.set_footer(text=Theme.get_footer_text(guild_id))
        return embed

    @ofertas.autocomplete("tienda")
    async def auto_tienda(self, interaction: discord.Interaction, current: str):
        cur = (current or "").lower().strip()
        bases = list(set(list(TIENDA_ALIAS.values()) + list(STORE_MAP.values())))
        out = []
        for n in bases:
            if not cur or cur in n.lower():
                out.append(app_commands.Choice(name=n, value=n))
            if len(out) >= 25:
                break
        return out


class OfertasDescuentoModal(discord.ui.Modal, title="Descuento mínimo"):
    valor = discord.ui.TextInput(label="% mínimo (0-90)", required=False, max_length=3)

    def __init__(self, parent_view: "OfertasFilterView"):
        super().__init__()
        self.parent_view = parent_view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            v = str(self.valor.value or "").strip()
            self.parent_view.descuento_min = int(v) if v.isdigit() else None
        except Exception:
            self.parent_view.descuento_min = None
        await self.parent_view.publicar_filtradas(interaction)


class OfertasFilterView(discord.ui.View):
    def __init__(self, ofertas_cog: Ofertas, thread_id: int):
        super().__init__(timeout=None)
        self.cog = ofertas_cog
        self.thread_id = thread_id
        self.tienda_norm: Optional[str] = None
        self.descuento_min: Optional[int] = None
        self.clean_before: bool = False
        self.sort_by: str = "savings"
        self.compact: bool = False
        self.offset: int = 0

    @discord.ui.select(
        placeholder="Filtrar por tienda",
        options=[
            discord.SelectOption(label="Todas", description="No filtrar", emoji="🧭"),
            discord.SelectOption(label="Steam", emoji="🚂"),
            discord.SelectOption(label="Epic Games", emoji="🕹️"),
            discord.SelectOption(label="GOG", emoji="📚"),
            discord.SelectOption(label="Humble Store", emoji="🤝"),
            discord.SelectOption(label="Fanatical", emoji="🎮"),
        ],
        custom_id="ofertas_tienda_select",
    )
    async def seleccionar_tienda(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        val = select.values[0]
        if val == "Todas":
            self.tienda_norm = None
        else:
            self.tienda_norm = val
        await self.publicar_filtradas(interaction)

    @discord.ui.button(
        label="Descuento mínimo",
        style=discord.ButtonStyle.primary,
        custom_id="ofertas_min_desc",
    )
    async def set_min_desc(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(OfertasDescuentoModal(self))

    @discord.ui.button(
        label="Limpiar antes",
        style=discord.ButtonStyle.secondary,
        custom_id="ofertas_clean_toggle",
    )
    async def toggle_clean(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.clean_before = not self.clean_before
        await interaction.response.send_message(
            (
                "🧹 Limpieza: activada"
                if self.clean_before
                else "🧹 Limpieza: desactivada"
            ),
            ephemeral=True,
        )

    @discord.ui.select(
        placeholder="Ordenar por",
        options=[
            discord.SelectOption(
                label="Descuento", description="Mayor primero", emoji="🔥"
            ),
            discord.SelectOption(
                label="Precio", description="Menor primero", emoji="💰"
            ),
            discord.SelectOption(
                label="Metacritic", description="Mayor primero", emoji="📊"
            ),
            discord.SelectOption(
                label="Steam rating", description="Mayor primero", emoji="🧪"
            ),
        ],
        custom_id="ofertas_sort_select",
    )
    async def seleccionar_orden(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        val = select.values[0]
        self.offset = 0
        if val == "Descuento":
            self.sort_by = "savings"
        elif val == "Precio":
            self.sort_by = "price"
        elif val == "Metacritic":
            self.sort_by = "metacritic"
        else:
            self.sort_by = "steam"
        await self.publicar_filtradas(interaction)

    @discord.ui.button(
        label="Ver más", style=discord.ButtonStyle.success, custom_id="ofertas_more"
    )
    async def ver_mas(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.offset += 10
        await self.publicar_filtradas(interaction)

    @discord.ui.button(
        label="Ver anteriores",
        style=discord.ButtonStyle.secondary,
        custom_id="ofertas_prev",
    )
    async def ver_prev(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.offset = max(0, int(self.offset) - 10)
        await self.publicar_filtradas(interaction)

    @discord.ui.button(
        label="Modo compacto",
        style=discord.ButtonStyle.secondary,
        custom_id="ofertas_compact_toggle",
    )
    async def toggle_compact(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.compact = not self.compact
        await interaction.response.send_message(
            "🗜️ Compacto: activado" if self.compact else "🗜️ Compacto: desactivado",
            ephemeral=True,
        )

    async def publicar_filtradas(self, interaction: discord.Interaction):
        juegos = self.cog.cache.get(self.thread_id, [])
        if not juegos:
            await interaction.response.send_message(
                "⚠️ No hay datos para filtrar.", ephemeral=True
            )
            return
        if self.clean_before:
            try:
                bot_user = interaction.client.user
                thread = interaction.channel
                async for m in thread.history(limit=200):
                    if m.author == bot_user and not m.pinned:
                        try:
                            await m.delete()
                        except Exception:
                            pass
                try:
                    await interaction.response.send_message(
                        "🧹 Mensajes anteriores del bot eliminados.", ephemeral=True
                    )
                except Exception:
                    pass
            except Exception:
                pass
        else:
            try:
                bot_user = interaction.client.user
                thread = interaction.channel
                msgs = []
                async for m in thread.history(limit=300, oldest_first=True):
                    if m.author == bot_user and not m.pinned:
                        msgs.append(m)
                if len(msgs) > 40:
                    for m in msgs[: len(msgs) - 40]:
                        try:
                            await m.delete()
                        except Exception:
                            pass
            except Exception:
                pass
        filtrados = list(juegos)
        if self.tienda_norm:
            filtrados = [
                d
                for d in filtrados
                if (
                    d.get("storeName") or STORE_MAP.get(str(d.get("storeID")), "")
                ).strip()
                == self.tienda_norm
            ]
        if self.descuento_min is not None:
            try:
                m = max(0, min(90, int(self.descuento_min)))
            except Exception:
                m = None
            if m is not None:
                filtrados = [
                    d for d in filtrados if int(float(d.get("savings", 0))) >= m
                ]
        if self.sort_by == "savings":
            filtrados.sort(key=lambda j: float(j.get("savings", 0)), reverse=True)
        elif self.sort_by == "price":
            filtrados.sort(key=lambda j: float(j.get("salePrice", 0)))
        elif self.sort_by == "metacritic":
            filtrados.sort(
                key=lambda j: int(j.get("metacriticScore") or 0), reverse=True
            )
        else:
            filtrados.sort(
                key=lambda j: int(j.get("steamRatingPercent") or 0), reverse=True
            )
        total = len(filtrados)
        start = max(0, min(int(self.offset), max(0, total - 10)))
        out = filtrados[start : start + 10]
        resumen = []
        if self.tienda_norm:
            resumen.append(f"Tienda: {self.tienda_norm}")
        if self.descuento_min is not None:
            resumen.append(f"Min desc: −{int(self.descuento_min)}%")
        resumen.append(f"Orden: {self.sort_by}")
        resumen.append(f"Página: {start//10 + 1}")
        head = "Filtros activos: " + (" · ".join(resumen) if resumen else "Ninguno")
        try:
            await interaction.response.send_message(head, ephemeral=True)
        except Exception:
            pass
        try:
            thread = interaction.channel
            last_msg = None
            for idx, j in enumerate(out, start=1):
                m = await thread.send(
                    embed=self.cog.crear_embed(j, idx, compact=self.compact)
                )
                last_msg = m
            if self.compact and last_msg:
                try:
                    await last_msg.pin()
                except Exception:
                    pass
        except Exception:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Ofertas(bot))
