import json
import os
from typing import List

import discord
from discord import app_commands
from discord.ext import commands
from bot.themes import Theme

class Tienda(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.file_path = "shop.json"
        self.items: dict[str, int] = {}
        self.inv: dict[str, list[str]] = {} # Keys as str(user_id) for JSON
        self._load_tienda()

    def _load_tienda(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.items = data.get("items", {})
                    self.inv = data.get("inventory", {})
            except Exception:
                pass
    
    def _save_tienda(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump({"items": self.items, "inventory": self.inv}, f, indent=4, ensure_ascii=False)

    def _get_monedas(self):
        try:
            return self.bot.get_cog("Monedas")
        except Exception:
            return None

    def _saldo(self, uid: int) -> int:
        m = self._get_monedas()
        try:
            return int(getattr(m, "bal", {}).get(uid, 0)) if m else 0
        except Exception:
            return 0

    def _sumar(self, uid: int, amt: int):
        m = self._get_monedas()
        try:
            if m and hasattr(m, "_add"):
                m._add(uid, amt)
        except Exception:
            pass

    @app_commands.command(
        name="tienda_add", description="Añade un artículo a la tienda"
    )
    async def tienda_add(
        self, interaction: discord.Interaction, nombre: str, precio: int
    ):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "⛔ Solo administradores.", ephemeral=True
            )
            return
        if precio <= 0:
            await interaction.response.send_message(
                "⚠️ Precio inválido.", ephemeral=True
            )
            return
        self.items[nombre.lower()] = precio
        self._save_tienda()
        await interaction.response.send_message(f"✅ Añadido {nombre} por {precio}.")
        try:
            e = interaction.client.build_log_embed(
                "Economía/Tienda",
                f"Añadido artículo: {nombre} ({precio})",
                user=interaction.user,
                guild=interaction.guild,
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @app_commands.command(
        name="tienda_list", description="Lista artículos de la tienda"
    )
    async def tienda_list(self, interaction: discord.Interaction):
        if not self.items:
            await interaction.response.send_message("⚠️ La tienda está vacía.")
            return
        embed = discord.Embed(
            title="🛍️ Tienda",
            description="Catálogo disponible",
            color=Theme.get_color(interaction.guild.id, 'primary'),
        )
        for n, p in self.items.items():
            embed.add_field(name=n, value=f"{p} monedas", inline=True)
        embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
        await interaction.response.send_message(embed=embed)
        try:
            e = interaction.client.build_log_embed(
                "Economía/Tienda",
                "Listado de tienda mostrado",
                user=interaction.user,
                guild=interaction.guild,
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @app_commands.command(
        name="tienda_remove", description="Elimina un artículo de la tienda"
    )
    async def tienda_remove(self, interaction: discord.Interaction, nombre: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "⛔ Solo administradores.", ephemeral=True
            )
            return
        if self.items.pop(nombre.lower(), None) is None:
            await interaction.response.send_message("⚠️ No existe.", ephemeral=True)
            return
        self._save_tienda()
        await interaction.response.send_message("✅ Eliminado.")
        try:
            e = interaction.client.build_log_embed(
                "Economía/Tienda",
                f"Eliminado artículo: {nombre}",
                user=interaction.user,
                guild=interaction.guild,
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @app_commands.command(name="comprar", description="Compra un artículo de la tienda")
    async def comprar(self, interaction: discord.Interaction, nombre: str):
        key = nombre.lower()
        precio = self.items.get(key)
        if precio is None:
            await interaction.response.send_message(
                "⚠️ No existe el artículo.", ephemeral=True
            )
            return
        uid = str(interaction.user.id)
        saldo = self._saldo(interaction.user.id)
        if saldo < precio:
            await interaction.response.send_message(
                f"⚠️ Saldo insuficiente. Tienes {saldo}, cuesta {precio}.",
                ephemeral=True,
            )
            return
        inv = self.inv.setdefault(uid, [])
        inv.append(key)
        self._sumar(interaction.user.id, -precio)
        self._save_tienda()
        await interaction.response.send_message(
            f"🛒 Compraste {nombre} por {precio}. Saldo restante: {self._saldo(interaction.user.id)}"
        )
        try:
            e = interaction.client.build_log_embed(
                "Economía/Tienda",
                f"Compra: {nombre} por {precio}",
                user=interaction.user,
                guild=interaction.guild,
                extra={"Saldo": str(self._saldo(uid))},
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @app_commands.command(name="inventario", description="Muestra inventario")
    async def inventario(
        self, interaction: discord.Interaction, usuario: discord.User | None = None
    ):
        uid = str((usuario or interaction.user).id)
        inv = self.inv.get(uid, [])
        if not inv:
            await interaction.response.send_message("📦 Vacío.")
            return
        target = usuario.mention if usuario else interaction.user.mention
        embed = discord.Embed(
            title="📦 Inventario",
            description=f"Artículos de {target}",
            color=Theme.get_color(interaction.guild.id, 'secondary'),
        )
        for it in inv:
            embed.add_field(name=it, value="Poseído", inline=True)
        embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
        await interaction.response.send_message(embed=embed)
        try:
            e = interaction.client.build_log_embed(
                "Economía/Tienda",
                "Inventario mostrado",
                user=interaction.user,
                guild=interaction.guild,
                extra={
                    "Usuario": (
                        usuario.mention if usuario else interaction.user.mention
                    )
                },
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @app_commands.command(name="regalar", description="Regala un artículo a un usuario")
    async def regalar(
        self, interaction: discord.Interaction, usuario: discord.User, nombre: str
    ):
        uid = interaction.user.id
        inv = self.inv.get(uid, [])
        key = nombre.lower()
        if key not in inv:
            await interaction.response.send_message(
                "⚠️ No tienes ese artículo.", ephemeral=True
            )
            return
        inv.remove(key)
        self.inv.setdefault(usuario.id, []).append(key)
        await interaction.response.send_message(
            f"🎁 Regalaste {nombre} a {usuario.mention}."
        )
        try:
            e = interaction.client.build_log_embed(
                "Economía/Tienda",
                f"Regalo: {nombre}",
                user=interaction.user,
                guild=interaction.guild,
                extra={"Para": f"{usuario} ({usuario.id})"},
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @app_commands.command(name="tienda_clear", description="Limpia la tienda")
    async def tienda_clear(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "⛔ Solo administradores.", ephemeral=True
            )
            return
        self.items.clear()
        await interaction.response.send_message("🧹 Tienda vaciada.")
        try:
            e = interaction.client.build_log_embed(
                "Economía/Tienda",
                "Tienda vaciada",
                user=interaction.user,
                guild=interaction.guild,
            )
            await interaction.client.log(embed=e, guild=interaction.guild)
        except Exception:
            pass

    @tienda_remove.autocomplete("nombre")
    async def auto_remove(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        cur = (current or "").lower().strip()
        out = []
        for n in self.items.keys():
            if cur in n:
                out.append(app_commands.Choice(name=n, value=n))
            if len(out) >= 25:
                break
        return out

    @comprar.autocomplete("nombre")
    async def auto_comprar(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        cur = (current or "").lower().strip()
        out = []
        for n, p in self.items.items():
            if cur in n:
                out.append(app_commands.Choice(name=f"{n} ({p})", value=n))
            if len(out) >= 25:
                break
        return out

    @regalar.autocomplete("nombre")
    async def auto_regalar(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        uid = str(interaction.user.id)
        inv = self.inv.get(uid, [])
        cur = (current or "").lower().strip()
        out = []
        for n in inv:
            if cur in n:
                out.append(app_commands.Choice(name=n, value=n))
            if len(out) >= 25:
                break
        return out


class TiendaView(discord.ui.View):
    def __init__(self, tienda: Tienda):
        super().__init__(timeout=None)
        self.tienda = tienda
        opts = []
        for n, p in self.tienda.items.items():
            opts.append(discord.SelectOption(label=n, description=f"{p} monedas"))
        if not opts:
            opts = [discord.SelectOption(label="(vacío)", description="Sin artículos")]
        self.selector = discord.ui.Select(
            placeholder="Selecciona artículo", options=opts, custom_id="tienda_select"
        )
        self.selector.callback = self.on_select
        self.add_item(self.selector)

    async def on_select(self, interaction: discord.Interaction):
        val = self.selector.values[0]
        precio = self.tienda.items.get(val.lower())
        if precio is None:
            await interaction.response.send_message(
                "⚠️ Artículo no disponible.", ephemeral=True
            )
            return
        uid = interaction.user.id
        saldo = self.tienda._saldo(uid)
        if saldo < precio:
            await interaction.response.send_message(
                f"⚠️ Saldo insuficiente. Tienes {saldo}, cuesta {precio}.",
                ephemeral=True,
            )
            return
        inv = self.tienda.inv.setdefault(uid, [])
        inv.append(val.lower())
        self.tienda._sumar(uid, -precio)
        await interaction.response.send_message(
            f"🛒 Compraste {val} por {precio}. Saldo restante: {self.tienda._saldo(uid)}"
        )

    @discord.ui.button(
        label="Actualizar",
        style=discord.ButtonStyle.secondary,
        custom_id="tienda_refresh",
    )
    async def refresh(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.clear_items()
        opts = []
        for n, p in self.tienda.items.items():
            opts.append(discord.SelectOption(label=n, description=f"{p} monedas"))
        if not opts:
            opts = [discord.SelectOption(label="(vacío)", description="Sin artículos")]
        sel = discord.ui.Select(
            placeholder="Selecciona artículo", options=opts, custom_id="tienda_select"
        )
        sel.callback = self.on_select
        self.selector = sel
        self.add_item(sel)
        await interaction.response.send_message(
            "♻️ Catálogo actualizado.", ephemeral=True
        )

    @discord.ui.button(
        label="Cerrar", style=discord.ButtonStyle.danger, custom_id="tienda_close"
    )
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.edit(view=None)
        await interaction.response.send_message("🔒 Panel cerrado.", ephemeral=True)

    @discord.ui.button(
        label="Mi saldo", style=discord.ButtonStyle.primary, custom_id="tienda_saldo"
    )
    async def saldo(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = interaction.user.id
        await interaction.response.send_message(
            f"💰 Tu saldo: {self.tienda._saldo(uid)}", ephemeral=True
        )

    @discord.ui.button(
        label="Mi inventario", style=discord.ButtonStyle.success, custom_id="tienda_inv"
    )
    async def inv(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = interaction.user.id
        inv = self.tienda.inv.get(uid, [])
        if not inv:
            await interaction.response.send_message("📦 Vacío.", ephemeral=True)
            return
        await interaction.response.send_message("\n".join(inv), ephemeral=True)

    @discord.ui.button(
        label="Ayuda", style=discord.ButtonStyle.secondary, custom_id="tienda_help"
    )
    async def help(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Usa el selector para comprar. Admin: /tienda_add, /tienda_remove, /tienda_clear",
            ephemeral=True,
        )

    @discord.ui.button(
        label="Reset catálogo",
        style=discord.ButtonStyle.danger,
        custom_id="tienda_reset",
    )
    async def reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "⛔ Solo administradores.", ephemeral=True
            )
            return
        self.tienda.items.clear()
        await interaction.response.send_message("🧹 Catálogo vaciado.", ephemeral=True)

    @discord.ui.button(
        label="Refrescar panel",
        style=discord.ButtonStyle.secondary,
        custom_id="tienda_panel_refresh",
    )
    async def panel_refresh(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        try:
            await interaction.message.edit(view=TiendaView(self.tienda))
            await interaction.response.send_message(
                "♻️ Panel refrescado.", ephemeral=True
            )
        except Exception:
            await interaction.response.send_message(
                "⚠️ No se pudo refrescar.", ephemeral=True
            )

    @discord.ui.button(
        label="Cerrar thread",
        style=discord.ButtonStyle.secondary,
        custom_id="tienda_thread_close",
    )
    async def thread_close(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        try:
            if isinstance(interaction.channel, discord.Thread):
                await interaction.channel.edit(archived=True, locked=True)
                await interaction.response.send_message(
                    "📜 Thread archivado.", ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "⚠️ No estás en un thread.", ephemeral=True
                )
        except Exception:
            await interaction.response.send_message(
                "⚠️ No se pudo archivar.", ephemeral=True
            )

    @discord.ui.button(
        label="Fijar", style=discord.ButtonStyle.secondary, custom_id="tienda_pin"
    )
    async def pin(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.message.pin()
            await interaction.response.send_message("📌 Panel fijado.", ephemeral=True)
        except Exception:
            await interaction.response.send_message(
                "⚠️ No se pudo fijar.", ephemeral=True
            )

    @discord.ui.button(
        label="Desfijar", style=discord.ButtonStyle.secondary, custom_id="tienda_unpin"
    )
    async def unpin(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.message.unpin()
            await interaction.response.send_message(
                "📌 Panel desfijado.", ephemeral=True
            )
        except Exception:
            await interaction.response.send_message(
                "⚠️ No se pudo desfijar.", ephemeral=True
            )

    @discord.ui.button(
        label="Borrar panel",
        style=discord.ButtonStyle.danger,
        custom_id="tienda_delete",
    )
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "⛔ Solo administradores.", ephemeral=True
            )
            return
        try:
            await interaction.message.delete()
        except Exception:
            pass
        try:
            await interaction.response.send_message(
                "🗑️ Panel eliminado.", ephemeral=True
            )
        except Exception:
            pass

    @discord.ui.button(
        label="Reacciones",
        style=discord.ButtonStyle.secondary,
        custom_id="tienda_react",
    )
    async def react(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.message.add_reaction("🛍️")
            await interaction.response.send_message(
                "🛍️ Reacción añadida.", ephemeral=True
            )
        except Exception:
            await interaction.response.send_message(
                "⚠️ No se pudo reaccionar.", ephemeral=True
            )

    @discord.ui.button(
        label="Copiar link",
        style=discord.ButtonStyle.secondary,
        custom_id="tienda_copy_link",
    )
    async def copy_link(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        try:
            url = interaction.message.jump_url
            await interaction.response.send_message(f"🔗 {url}", ephemeral=True)
        except Exception:
            await interaction.response.send_message(
                "⚠️ No se pudo obtener el link.", ephemeral=True
            )

    @discord.ui.button(
        label="Abrir en thread",
        style=discord.ButtonStyle.secondary,
        custom_id="tienda_open_thread",
    )
    async def open_thread(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        try:
            t = await interaction.channel.create_thread(
                name="🛍️ Tienda", type=discord.ChannelType.public_thread
            )
            embed = discord.Embed(
                title="🛍️ Tienda", description="Usa el selector para comprar", color=Theme.get_color(interaction.guild.id, 'secondary')
            )
            embed.set_footer(text=Theme.get_footer_text(interaction.guild.id))
            await t.send(
                embed=embed,
                view=TiendaView(self.tienda),
            )
            await interaction.response.send_message(
                "🧵 Panel abierto en thread.", ephemeral=True
            )
        except Exception:
            await interaction.response.send_message(
                "⚠️ No se pudo crear el thread.", ephemeral=True
            )

    @discord.ui.button(
        label="Top compradores",
        style=discord.ButtonStyle.secondary,
        custom_id="tienda_top",
    )
    async def top_buyers(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        counts: dict[int, int] = {}
        for uid, arr in self.tienda.inv.items():
            counts[uid] = counts.get(uid, 0) + len(arr)
        top = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]
        lines = []
        for uid, c in top:
            try:
                u = await interaction.client.fetch_user(uid)
                lines.append(f"{u.mention}: {c}")
            except Exception:
                lines.append(f"{uid}: {c}")
        if not lines:
            await interaction.response.send_message("⚠️ No hay datos.", ephemeral=True)
            return
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @discord.ui.button(
        label="Recargar saldo (+100)",
        style=discord.ButtonStyle.secondary,
        custom_id="tienda_recarga",
    )
    async def recarga(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        uid = interaction.user.id
        self.tienda._sumar(uid, 100)
        await interaction.response.send_message(
            f"💳 Recarga: 100. Nuevo saldo {self.tienda._saldo(uid)}", ephemeral=True
        )

    @discord.ui.button(
        label="Saldo servidor",
        style=discord.ButtonStyle.secondary,
        custom_id="tienda_saldo_srv",
    )
    async def saldo_srv(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        m = self.tienda._get_monedas()
        if not m:
            await interaction.response.send_message(
                "⚠️ Monedas no disponible.", ephemeral=True
            )
            return
        datos = sorted(getattr(m, "bal", {}).items(), key=lambda x: x[1], reverse=True)[
            :10
        ]
        lines = []
        for uid, val in datos:
            try:
                u = await interaction.client.fetch_user(uid)
                lines.append(f"{u.mention}: {val}")
            except Exception:
                lines.append(f"{uid}: {val}")
        if not lines:
            await interaction.response.send_message("⚠️ No hay datos.", ephemeral=True)
            return
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @discord.ui.button(
        label="Publicar guía",
        style=discord.ButtonStyle.secondary,
        custom_id="tienda_post_panel",
    )
    async def post_panel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        try:
            e = discord.Embed(
                title="🛍️ Tienda",
                description="Usa el selector para comprar",
                color=Theme.get_color(interaction.guild.id, 'primary'),
            )
            for n, p in self.tienda.items.items():
                e.add_field(name=n, value=f"{p} monedas", inline=True)
            msg = await interaction.channel.send(embed=e, view=TiendaView(self.tienda))
            try:
                await msg.pin()
            except Exception:
                pass
            await interaction.response.send_message(
                "✅ Panel publicado.", ephemeral=True
            )
        except Exception:
            await interaction.response.send_message(
                "⚠️ No se pudo publicar el panel.", ephemeral=True
            )

    @app_commands.command(
        name="tienda_panel", description="Publica un panel interactivo de la tienda"
    )
    async def tienda_panel(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        e = discord.Embed(
            title="🛍️ Tienda",
            description="Usa el selector para comprar",
            color=Theme.get_color(interaction.guild.id, 'primary'),
        )
        for n, p in self.items.items():
            e.add_field(name=n, value=f"{p} monedas", inline=True)
        msg = await interaction.channel.send(embed=e, view=TiendaView(self))
        try:
            await msg.pin()
        except Exception:
            pass
        await interaction.followup.send("✅ Panel publicado.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Tienda(bot))
