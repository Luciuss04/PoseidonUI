import asyncio
import os
import secrets
import time
from collections import deque
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks

import os

def _env_int(n: str, d: int) -> int:
    try:
        return max(0, int(os.getenv(n, str(d))))
    except Exception:
        return d

WELCOME_CHANNEL = "📜-puertas-del-olimpo"
FAREWELL_CHANNEL = "🏺-el-umbral-de-hades"
ALERT_CHANNEL = "⚔️-alertas"
VERIFY_ROLE = "🧍Humanos"
ORACULO_ABIERTOS_NAME = "Oráculos de Atenea"
ORACULO_CERRADOS_NAME = "Oráculos Sellados"
ORACULO_CLEANUP_MAX = _env_int("ORACULO_CLEANUP_MAX", 5)
ORACULO_CLEANUP_SLEEP = _env_int("ORACULO_CLEANUP_SLEEP", 2)
ORACULO_CLEANUP_ATTACH_MAX = _env_int("ORACULO_CLEANUP_ATTACH_MAX", 30)
ORACULO_CLEANUP_ATTACH_SLEEP = _env_int("ORACULO_CLEANUP_ATTACH_SLEEP", 1)
ORACULO_CLEANUP_THREAD_MAX = _env_int("ORACULO_CLEANUP_THREAD_MAX", 10)
ORACULO_CLEANUP_THREAD_SLEEP = _env_int("ORACULO_CLEANUP_THREAD_SLEEP", 1)
ORACULO_CLEANUP_ATTACH_PAGES = _env_int("ORACULO_CLEANUP_ATTACH_PAGES", 5)
ORACULO_CLEANUP_ATTACH_PAGE_SLEEP = _env_int("ORACULO_CLEANUP_ATTACH_PAGE_SLEEP", 1)
ORACULO_CLEANUP_START_HOUR = _env_int("ORACULO_CLEANUP_START_HOUR", 4)

ORACULO_SCORE_MSG = _env_int("ORACULO_SCORE_MSG", 1)
ORACULO_SCORE_ATTACH = _env_int("ORACULO_SCORE_ATTACH", 2)
ORACULO_SCORE_REACT = _env_int("ORACULO_SCORE_REACT", 1)

JUICIO_ROLES = {
    "⚡ Favor divino": "Bendecido",
    "🗡️ Prueba del destino": "Probado",
    "🌫️ Silencio ritual": "Silenciado",
    "🔥 Forja del espíritu": "Forjado",
    "🌌 Visión del Oráculo": "Visionario",
    "🛡️ Bendición de Atenea": "Protegido",
    "🌪️ Viento de cambio": "Transformado",
    "🌊 Purificación": "Purificado",
}
JUICIO_DURATION = 24 * 60 * 60


class VerifyView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="Jurar ante los dioses",
        style=discord.ButtonStyle.primary,
        emoji="🦉",
        custom_id="verify_button",
    )
    async def verify_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        role = discord.utils.get(interaction.guild.roles, name=VERIFY_ROLE)
        if role:
            await interaction.user.add_roles(role, reason="Juramento ritual aceptado")
            msg = (
                f"🦉 {interaction.user.mention} ha jurado ante los dioses "
                "y ahora es parte del Olimpo."
            )
            await interaction.response.send_message(msg, ephemeral=True)
            try:
                self.bot.dispatch("user_verified", interaction.guild, interaction.user)
            except Exception:
                pass
        else:
            await interaction.response.send_message(
                f"⚠️ No existe el rol {VERIFY_ROLE}.", ephemeral=True
            )


class Guardian(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._joins = {}
        self._raid_locks = {}
        self._recent_verifies = {}
        self._verify_panel_id = {}
        self._daily_counts = {}

    async def cog_load(self):
        self.bot.add_view(VerifyView(self.bot))
        try:
            self._daily_summary.start()
        except Exception:
            pass
        try:
            self._cleanup_oraculos.start()
        except Exception:
            pass

    async def _log(
        self,
        guild: discord.Guild,
        content: str | None = None,
        embed: discord.Embed | None = None,
    ):
        try:
            await self.bot.log(content=content, embed=embed, guild=guild)
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_member_join(self, member):
        canal = discord.utils.get(member.guild.text_channels, name=WELCOME_CHANNEL)
        if canal:
            ch_general = discord.utils.get(
                member.guild.text_channels, name="chat-general"
            )
            ch_zeus = discord.utils.get(
                member.guild.text_channels, name="📣-voz-de-zeus"
            )
            g_mention = ch_general.mention if ch_general else "#chat-general"
            dz_mention = ch_zeus.mention if ch_zeus else "#📣-voz-de-zeus"
            desc = (
                "╔══════════════════════════════════════════════════╗\n"
                "Has ascendido al Olimpo.\n"
                "Bienvenido a nuestra comunidad de streaming, juegos y buen rollo ⚡🎮\n"
                "Comparte tus ideas, participa en eventos y disfruta con todos.\n"
                "╚══════════════════════════════════════════════════╝\n\n"
                "🏛️ Lee las reglas para evitar la ira de Zeus.\n"
                "🦉 Consulta al Oráculo cuando necesites ayuda.\n\n"
                f"📣 Los anuncios de directo se publican en {dz_mention}.\n\n"
                "────────────────────────────────────────────────────\n"
                "🔱 **Primeros pasos** — sigue esta guía para empezar:"
            )
            embed = discord.Embed(
                title=f"⚡👑 {member.display_name}, los dioses te reciben en el Olimpo",
                description=desc,
                color=discord.Color.gold(),
            )
            embed.add_field(
                name="🫂 Presentación",
                value=f"Saluda en la sala de los mortales {g_mention}",
                inline=True,
            )
            try:
                ofans = discord.utils.get(member.guild.roles, name="Olimpofans")
                directos_txt = (
                    f"Para recibir la notificación debes tener el rol {ofans.mention}"
                    if ofans
                    else "Para recibir la notificación debes tener el rol Olimpofans"
                )
            except Exception:
                directos_txt = (
                    "Para recibir la notificación debes tener el rol Olimpofans"
                )
            embed.add_field(
                name="🎙 Directos",
                value=f"Anuncios en {dz_mention}. {directos_txt}",
                inline=True,
            )
            try:
                vrole = discord.utils.get(member.guild.roles, name=VERIFY_ROLE)
                vtxt = (
                    f"Pulsa el botón para recibir {vrole.mention}"
                    if vrole
                    else "Pulsa el botón para verificarte"
                )
            except Exception:
                vtxt = "Pulsa el botón para verificarte"
            embed.add_field(name="🦉 Verificación", value=vtxt, inline=False)
            try:
                embed.add_field(
                    name="👥 Población",
                    value=str(member.guild.member_count),
                    inline=True,
                )
            except Exception:
                pass
            try:
                if member.guild.icon:
                    embed.set_thumbnail(url=member.guild.icon.url)
            except Exception:
                pass
            try:
                embed.set_image(
                    url="https://cdn.discordapp.com/attachments/1425781431682076682/1440115588746706984/Imagen_para_el_bot_d.png"
                )
            except Exception:
                pass
            embed.set_footer(text="Los dioses observan tu llegada...")
            await canal.send(embed=embed, view=VerifyView(self.bot))
            try:
                await self._log(
                    member.guild,
                    embed=discord.Embed(
                        title="Log",
                        description=f"Bienvenida enviada a {member.mention}",
                        color=discord.Color.blurple(),
                    ),
                )
            except Exception:
                pass
        try:
            e2 = discord.Embed(
                title="Bienvenido al Olimpo",
                description="Pulsa el botón del canal de bienvenida para recibir acceso.",
                color=discord.Color.gold(),
            )
            await member.send(embed=e2)
            try:
                await self._log(
                    member.guild,
                    embed=discord.Embed(
                        title="Log",
                        description=f"DM de bienvenida enviado a {member.mention}",
                        color=discord.Color.blurple(),
                    ),
                )
            except Exception:
                pass
        except Exception:
            pass
        try:
            dq = self._joins.get(member.guild.id)
            if dq is None:
                dq = deque()
                self._joins[member.guild.id] = dq
            now = time.time()
            dq.append(now)
            while dq and now - dq[0] > 60:
                dq.popleft()
            if len(dq) >= 5:
                alert = discord.utils.get(
                    member.guild.text_channels, name=ALERT_CHANNEL
                )
                rol_staff = discord.utils.get(member.guild.roles, name="Staff")
                mention = rol_staff.mention if rol_staff else None
                canales_bloqueo = []
                for n in ["chat-general", "acceso", "directo-ahora"]:
                    ch = discord.utils.get(member.guild.text_channels, name=n)
                    if ch:
                        canales_bloqueo.append(ch)
                if canales_bloqueo:
                    await self._apply_raid_lock(
                        member.guild, canales_bloqueo, duration_secs=600
                    )
                if alert:
                    tit = "Posible raid"
                    desc = f"{len(dq)} ingresos en 60s"
                    if canales_bloqueo:
                        desc += "\nCanales bloqueados: " + ", ".join(
                            [c.mention for c in canales_bloqueo]
                        )
                    await alert.send(
                        content=mention,
                        embed=discord.Embed(
                            title=tit, description=desc, color=discord.Color.red()
                        ),
                    )
                try:
                    await self._log(
                        member.guild,
                        embed=discord.Embed(
                            title="Log",
                            description=f"Anti‑raid: {len(dq)} ingresos en 60s",
                            color=discord.Color.red(),
                        ),
                    )
                except Exception:
                    pass
                try:
                    c = self._daily_counts.setdefault(member.guild.id, {})
                    c["raids"] = c.get("raids", 0) + 1
                except Exception:
                    pass
                    try:
                        c = getattr(self, "_daily_counts", {}).setdefault(member.guild.id, {})
                        c["raids"] = c.get("raids", 0) + 1
                        self._daily_counts[member.guild.id] = c
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            age_days = 999
            try:
                age_days = (
                    datetime.utcnow() - member.created_at.replace(tzinfo=None)
                ).days
            except Exception:
                age_days = 999
            if age_days < 7:
                alert = discord.utils.get(
                    member.guild.text_channels, name=ALERT_CHANNEL
                )
                rol_staff = discord.utils.get(member.guild.roles, name="Staff")
                mention = rol_staff.mention if rol_staff else None
                if alert:
                    e = discord.Embed(
                        title="Cuenta reciente",
                        description=f"{member.mention} creada hace {age_days} día(s)",
                        color=discord.Color.orange(),
                    )
                    try:
                        e.set_thumbnail(url=member.display_avatar.url)
                    except Exception:
                        pass
                    await alert.send(content=mention, embed=e)
                try:
                    await self._log(
                        member.guild,
                        embed=discord.Embed(
                            title="Log",
                            description=f"Cuenta reciente: {member} ({age_days} días)",
                            color=discord.Color.orange(),
                        ),
                    )
                except Exception:
                    pass
                try:
                    c = self._daily_counts.setdefault(member.guild.id, {})
                    c["new_accounts"] = c.get("new_accounts", 0) + 1
                except Exception:
                    pass
                try:
                    c = getattr(self, "_daily_counts", {}).setdefault(member.guild.id, {})
                    c["new_accounts"] = c.get("new_accounts", 0) + 1
                    self._daily_counts[member.guild.id] = c
                except Exception:
                    pass
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        try:
            guild = self.bot.get_guild(payload.guild_id) if payload.guild_id else None
            if not guild:
                return
            ch = guild.get_channel(payload.channel_id)
            if isinstance(ch, discord.TextChannel):
                cat = ch.category
                if not cat or cat.name != ORACULO_ABIERTOS_NAME:
                    return
                key_id = ch.id
            elif isinstance(ch, discord.Thread):
                try:
                    parent = ch.parent
                    if not (isinstance(parent, discord.TextChannel) and parent.category and parent.category.name == ORACULO_ABIERTOS_NAME):
                        return
                    key_id = parent.id
                except Exception:
                    return
            else:
                return
            c = self._daily_counts.setdefault(guild.id, {})
            mc = c.setdefault("oraculo_msg_counts", {})
            mc[key_id] = mc.get(key_id, 0) + ORACULO_SCORE_REACT
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_user_verified(self, guild: discord.Guild, member: discord.Member):
        try:
            dq = self._recent_verifies.get(guild.id)
            if dq is None:
                dq = deque(maxlen=10)
                self._recent_verifies[guild.id] = dq
            dq.append((member.id, time.time()))
            await self._update_verify_panel(guild)
            try:
                await self._log(
                    guild,
                    embed=discord.Embed(
                        title="Log",
                        description=f"Verificado: {member.mention}",
                        color=discord.Color.green(),
                    ),
                )
            except Exception:
                pass
            try:
                c = self._daily_counts.setdefault(guild.id, {})
                c["verifies"] = c.get("verifies", 0) + 1
                vb = c.setdefault("verify_by_user", {})
                vb[member.id] = vb.get(member.id, 0) + 1
            except Exception:
                pass
            try:
                c = getattr(self, "_daily_counts", {}).setdefault(guild.id, {})
                c["verifies"] = c.get("verifies", 0) + 1
                self._daily_counts[guild.id] = c
            except Exception:
                pass
        except Exception:
            pass

    async def _update_verify_panel(self, guild: discord.Guild):
        try:
            ch = discord.utils.get(guild.text_channels, name=ALERT_CHANNEL)
            if not ch:
                return
            msg_id = self._verify_panel_id.get(guild.id)
            entries = list(self._recent_verifies.get(guild.id) or [])
            lines = []
            for uid, ts in reversed(entries):
                try:
                    m = guild.get_member(uid) or await guild.fetch_member(uid)
                except Exception:
                    m = None
                hora = datetime.utcfromtimestamp(ts).strftime("%H:%M UTC")
                if m:
                    try:
                        age_days = (
                            datetime.utcnow() - m.created_at.replace(tzinfo=None)
                        ).days
                    except Exception:
                        age_days = "?"
                    lines.append(f"{hora} — {m.mention} (cuenta {age_days} días)")
                else:
                    lines.append(f"{hora} — <@{uid}>")
            if not lines:
                lines = ["Sin verificaciones recientes"]
            e = discord.Embed(
                title="🛡️ Accesos recientes",
                description="\n".join(lines[:10]),
                color=discord.Color.blurple(),
            )
            try:
                if guild.icon:
                    e.set_thumbnail(url=guild.icon.url)
            except Exception:
                pass
            if msg_id:
                try:
                    msg = await ch.fetch_message(msg_id)
                    await msg.edit(embed=e)
                    try:
                        await self._log(
                            guild,
                            embed=discord.Embed(
                                title="Log",
                                description="Panel de accesos actualizado",
                                color=discord.Color.blurple(),
                            ),
                        )
                    except Exception:
                        pass
                    return
                except Exception:
                    pass
            msg = await ch.send(embed=e)
            try:
                await msg.pin()
            except Exception:
                pass
            self._verify_panel_id[guild.id] = msg.id
            try:
                await self._log(
                    guild,
                    embed=discord.Embed(
                        title="Log",
                        description="Panel de accesos creado",
                        color=discord.Color.blurple(),
                    ),
                )
            except Exception:
                pass
        except Exception:
            pass

    @app_commands.command(name="setup", description="Configurar canales y rol de verificación")
    async def setup(self, interaction: discord.Interaction):
        g = interaction.guild
        u = interaction.user
        if not g or not u.guild_permissions.administrator:
            await interaction.response.send_message("⛔ Solo administradores.", ephemeral=True)
            return
        created: list[str] = []
        adjusted: list[str] = []
        welcome = discord.utils.get(g.text_channels, name=WELCOME_CHANNEL)
        if not welcome:
            try:
                welcome = await g.create_text_channel(WELCOME_CHANNEL)
                created.append(welcome.mention)
            except Exception:
                pass
        alerts = discord.utils.get(g.text_channels, name=ALERT_CHANNEL)
        if not alerts:
            try:
                alerts = await g.create_text_channel(ALERT_CHANNEL)
                created.append(alerts.mention)
            except Exception:
                pass
        zeus = discord.utils.get(g.text_channels, name="📣-voz-de-zeus")
        if not zeus:
            try:
                zeus = await g.create_text_channel("📣-voz-de-zeus")
                created.append(zeus.mention)
            except Exception:
                pass
        vrole = discord.utils.get(g.roles, name=VERIFY_ROLE)
        if not vrole:
            try:
                vrole = await g.create_role(name=VERIFY_ROLE, color=discord.Color.green(), mentionable=True)
                created.append(vrole.mention)
            except Exception:
                pass
        if isinstance(welcome, discord.TextChannel):
            try:
                await welcome.set_permissions(g.default_role, send_messages=False)
                adjusted.append(welcome.mention)
            except Exception:
                pass
        e = discord.Embed(title="Configuración aplicada", color=discord.Color.blurple())
        if created:
            e.add_field(name="Creados", value="\n".join(created), inline=False)
        if adjusted:
            e.add_field(name="Ajustados", value="\n".join(adjusted), inline=False)
        await interaction.response.send_message(embed=e, ephemeral=True)
        try:
            le = self.bot.build_log_embed("Setup", "Configuración de canales y roles", user=u, guild=g, extra={"Creados": str(len(created)), "Ajustados": str(len(adjusted))})
            await self.bot.log(embed=le, guild=g)
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_oraculo_opened(self, guild: discord.Guild, channel: discord.TextChannel):
        try:
            c = self._daily_counts.setdefault(guild.id, {})
            c["oraculo_opened"] = c.get("oraculo_opened", 0) + 1
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_oraculo_closed(self, guild: discord.Guild, channel: discord.TextChannel):
        try:
            c = self._daily_counts.setdefault(guild.id, {})
            c["oraculo_closed"] = c.get("oraculo_closed", 0) + 1
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_oraculo_resolved(self, guild: discord.Guild, channel: discord.TextChannel):
        try:
            c = self._daily_counts.setdefault(guild.id, {})
            c["oraculo_resolved"] = c.get("oraculo_resolved", 0) + 1
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_oraculo_reopened(self, guild: discord.Guild, channel: discord.TextChannel):
        try:
            c = self._daily_counts.setdefault(guild.id, {})
            c["oraculo_reopened"] = c.get("oraculo_reopened", 0) + 1
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_mod_mute(self, guild: discord.Guild, member: discord.Member):
        try:
            c = self._daily_counts.setdefault(guild.id, {})
            c["mod_mute"] = c.get("mod_mute", 0) + 1
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_mod_unmute(self, guild: discord.Guild, member: discord.Member):
        try:
            c = self._daily_counts.setdefault(guild.id, {})
            c["mod_unmute"] = c.get("mod_unmute", 0) + 1
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_mod_warn(self, guild: discord.Guild, member: discord.Member):
        try:
            c = self._daily_counts.setdefault(guild.id, {})
            c["mod_warn"] = c.get("mod_warn", 0) + 1
        except Exception:
            pass

    @tasks.loop(hours=24)
    async def _daily_summary(self):
        try:
            for guild in self.bot.guilds:
                ch = discord.utils.get(guild.text_channels, name=ALERT_CHANNEL)
                if not ch:
                    continue
                c = self._daily_counts.get(guild.id) or {}
                verifies = c.get("verifies", 0)
                raids = c.get("raids", 0)
                new_acc = c.get("new_accounts", 0)
                locks = c.get("locks_applied", 0)
                o_open = c.get("oraculo_opened", 0)
                o_close = c.get("oraculo_closed", 0)
                o_res = c.get("oraculo_resolved", 0)
                o_reop = c.get("oraculo_reopened", 0)
                m_mute = c.get("mod_mute", 0)
                m_unmute = c.get("mod_unmute", 0)
                m_warn = c.get("mod_warn", 0)
                vb = c.get("verify_by_user", {})
                mc = c.get("oraculo_msg_counts", {})
                top_verifiers = []
                try:
                    for uid, cnt in sorted(vb.items(), key=lambda x: x[1], reverse=True)[:3]:
                        m = guild.get_member(uid)
                        top_verifiers.append(f"{m.mention if m else f'<@{uid}>'} ({cnt})")
                except Exception:
                    pass
                top_oraculos = []
                try:
                    for cid, cnt in sorted(mc.items(), key=lambda x: x[1], reverse=True)[:3]:
                        ch2 = guild.get_channel(cid)
                        if isinstance(ch2, discord.TextChannel):
                            top_oraculos.append(f"{ch2.mention} ({cnt})")
                except Exception:
                    pass
                lines = [
                    f"Verificados: {verifies}",
                    f"Posibles raids: {raids}",
                    f"Cuentas nuevas (<7d): {new_acc}",
                    f"Bloqueos aplicados: {locks}",
                    f"Oráculos abiertos: {o_open}",
                    f"Oráculos cerrados: {o_close}",
                    f"Oráculos resueltos: {o_res}",
                    f"Oráculos reabiertos: {o_reop}",
                    f"Mutes: {m_mute} • Unmutes: {m_unmute} • Warns: {m_warn}",
                ]
                if top_oraculos:
                    lines += [
                        "",
                        "Top Oráculos por actividad:",
                        "• " + ", ".join(top_oraculos),
                    ]
                if top_verifiers:
                    lines += [
                        "",
                        "Top verificadores:",
                        "• " + ", ".join(top_verifiers),
                    ]
                e = discord.Embed(title="Resumen diario del Olimpo", description="\n".join(lines), color=discord.Color.blurple())
                try:
                    e.add_field(name="Cálculo actividad", value="Mensajes + Adjuntos + Reacciones", inline=False)
                except Exception:
                    pass
                mention = None
                if raids > 0:
                    try:
                        rol_staff = discord.utils.get(guild.roles, name="Staff")
                        mention = rol_staff.mention if rol_staff else None
                    except Exception:
                        mention = None
                try:
                    await ch.send(content=mention, embed=e)
                except Exception:
                    pass
                try:
                    await self._log(guild, embed=self.bot.build_log_embed("Resumen diario", "Panel publicado", guild=guild, extra={"verificados": str(verifies), "raids": str(raids), "nuevas": str(new_acc), "bloqueos": str(locks)}))
                except Exception:
                    pass
                try:
                    getattr(self, "_daily_counts", {})[guild.id] = {}
                except Exception:
                    pass
        except Exception:
            pass

    @_daily_summary.before_loop
    async def _wait_ready(self):
        try:
            await self.bot.wait_until_ready()
        except Exception:
            pass

    @tasks.loop(hours=24)
    async def _cleanup_oraculos(self):
        try:
            now = int(time.time())
            for guild in self.bot.guilds:
                cat = discord.utils.get(guild.categories, name=ORACULO_CERRADOS_NAME)
                if not cat:
                    continue
                cleaned = 0
                threads_deleted = 0
                attach_deleted = 0
                for ch in cat.text_channels:
                    try:
                        topic = ch.topic or ""
                        closed_at = None
                        if "||" in topic:
                            try:
                                meta = topic.split("||", 1)[1]
                            except Exception:
                                meta = topic
                            for part in meta.split("|"):
                                if "=" in part:
                                    k, v = part.split("=", 1)
                                    if k.strip() == "closed_at":
                                        try:
                                            closed_at = int(v.strip())
                                        except Exception:
                                            closed_at = None
                        age = 0
                        if closed_at:
                            age = now - closed_at
                        else:
                            try:
                                age = now - int(ch.created_at.timestamp())
                            except Exception:
                                age = 0
                        if age < 7 * 24 * 60 * 60:
                            continue
                        t_deleted_channel = 0
                        for th in list(getattr(ch, "threads", []) or []):
                            try:
                                if ORACULO_CLEANUP_THREAD_MAX and t_deleted_channel >= ORACULO_CLEANUP_THREAD_MAX:
                                    break
                                await th.delete()
                                t_deleted_channel += 1
                                threads_deleted += 1
                                await asyncio.sleep(ORACULO_CLEANUP_THREAD_SLEEP)
                            except Exception:
                                pass
                        try:
                            a_deleted_channel = 0
                            pages = 0
                            before_msg = None
                            while True:
                                if ORACULO_CLEANUP_ATTACH_MAX and a_deleted_channel >= ORACULO_CLEANUP_ATTACH_MAX:
                                    break
                                if ORACULO_CLEANUP_ATTACH_PAGES and pages >= ORACULO_CLEANUP_ATTACH_PAGES:
                                    break
                                fetched_any = False
                                async for msg in ch.history(limit=100, before=before_msg):
                                    fetched_any = True
                                    before_msg = msg
                                    if ORACULO_CLEANUP_ATTACH_MAX and a_deleted_channel >= ORACULO_CLEANUP_ATTACH_MAX:
                                        break
                                    if msg.attachments:
                                        try:
                                            await msg.delete()
                                            a_deleted_channel += 1
                                            attach_deleted += 1
                                            await asyncio.sleep(ORACULO_CLEANUP_ATTACH_SLEEP)
                                        except Exception:
                                            pass
                                pages += 1
                                await asyncio.sleep(ORACULO_CLEANUP_ATTACH_PAGE_SLEEP)
                                if not fetched_any:
                                    break
                        except Exception:
                            pass
                        orig_name = ch.name
                        need_rename = not orig_name.startswith("archivado-")
                        new_name = orig_name
                        if need_rename:
                            raw = orig_name
                            for pref in ("sellado-", "auto-", "resuelto-", "cerrado-"):
                                if raw.startswith(pref):
                                    raw = raw[len(pref):]
                            new_name = f"archivado-{raw}"
                        tok = ch.topic or ""
                        base = tok.split("||", 1)[0].strip() or "oraculo"
                        new_meta = f"{base} || closed_at={closed_at or now}|archived_at={now}"
                        try:
                            if need_rename:
                                await ch.edit(name=new_name, topic=new_meta)
                            else:
                                await ch.edit(topic=new_meta)
                            await asyncio.sleep(ORACULO_CLEANUP_SLEEP)
                        except Exception:
                            pass
                        cleaned += 1
                    except Exception:
                        pass
                    if ORACULO_CLEANUP_MAX and cleaned >= ORACULO_CLEANUP_MAX:
                        break
                if cleaned:
                    try:
                        c = self._daily_counts.setdefault(guild.id, {})
                        c["oraculo_cleaned"] = c.get("oraculo_cleaned", 0) + cleaned
                        c["oraculo_threads_deleted"] = c.get("oraculo_threads_deleted", 0) + threads_deleted
                        c["oraculo_attachments_deleted"] = c.get("oraculo_attachments_deleted", 0) + attach_deleted
                    except Exception:
                        pass
                    alert = discord.utils.get(guild.text_channels, name=ALERT_CHANNEL)
                    if alert:
                        try:
                            await alert.send(
                                embed=discord.Embed(
                                    title="Limpieza de Oráculos",
                                    description=f"Canales archivados: {cleaned}\nHilos eliminados: {threads_deleted}\nAdjuntos eliminados: {attach_deleted}",
                                    color=discord.Color.orange(),
                                )
                            )
                        except Exception:
                            pass
        except Exception:
            pass

    @_cleanup_oraculos.before_loop
    async def _wait_ready_cleanup(self):
        try:
            await self.bot.wait_until_ready()
            try:
                while True:
                    now = datetime.now()
                    if now.hour == ORACULO_CLEANUP_START_HOUR:
                        break
                    await asyncio.sleep(60)
            except Exception:
                pass
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        canal = discord.utils.get(member.guild.text_channels, name=FAREWELL_CHANNEL)
        if canal:
            total = member.guild.member_count
            desc = (
                "╔══════════════════════════════╗\n"
                "Sus huellas quedan grabadas en la arena del Olimpo.\n"
                "Que los vientos le guíen hacia nuevos horizontes.\n"
                "╚══════════════════════════════╝\n\n"
                f"👤 {member.name} deja el templo.\n"
                f"👥 Población del Olimpo: {total} almas."
            )
            embed = discord.Embed(
                title="🏺 Despedida del templo",
                description=desc,
                color=discord.Color.dark_gold(),
            )
            try:
                embed.set_image(
                    url="https://cdn.discordapp.com/attachments/1425781431682076682/1440115588746706984/Imagen_para_el_bot_d.png"
                )
            except Exception:
                pass
            embed.set_footer(text="El Oráculo guarda silencio ante su partida")
            await canal.send(embed=embed)

    @app_commands.command(
        name="juicio", description="Invoca el Juicio de los Dioses sobre un usuario"
    )
    async def juicio(self, interaction: discord.Interaction, usuario: discord.Member):
        titulo = secrets.choice(list(JUICIO_ROLES.keys()))
        mensaje = {
            "⚡ Favor divino": "Los dioses sonríen sobre ti. Que tus pasos sean firmes.",
            "🗡️ Prueba del destino": "Camina sin miedo: cada sombra guarda un aprendizaje.",
            "🌫️ Silencio ritual": (
                "Hoy calla y observa. En el silencio se revelan "
                "los hilos del destino."
            ),
            "🔥 Forja del espíritu": "Acepta el calor de la prueba: saldrás templado.",
            "🌌 Visión del Oráculo": "Una estrella te guía. No la pierdas de vista.",
            "🛡️ Bendición de Atenea": "La sabiduría te cubre como un manto sagrado.",
            "🌪️ Viento de cambio": "Prepárate: lo que viene transforma lo que fue.",
            "🌊 Purificación": "Deja que la marea arrastre lo que ya no sirve.",
        }[titulo]

        rol_nombre = JUICIO_ROLES[titulo]
        rol = discord.utils.get(interaction.guild.roles, name=rol_nombre)

        embed = discord.Embed(
            title=f"🔱 Juicio de los Dioses: {titulo}",
            description=f"{usuario.mention}\n{mensaje}",
            color=discord.Color.purple(),
        )
        embed.set_footer(text=f"Invocado por {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

        if rol:
            await usuario.add_roles(rol, reason="Juicio divino otorgado")
            await interaction.followup.send(
                f"🕯️ {usuario.mention} ha recibido el rol **{rol_nombre}** por 24 horas.",
                ephemeral=True,
            )
            try:
                asyncio.create_task(self._expire_juicio(usuario, rol))
            except Exception:
                pass

    async def _expire_juicio(self, usuario: discord.Member, rol: discord.Role):
        try:
            await asyncio.sleep(JUICIO_DURATION)
            await usuario.remove_roles(rol, reason="Juicio expirado")
        except Exception:
            pass

    async def _apply_raid_lock(
        self,
        guild: discord.Guild,
        channels: list[discord.TextChannel],
        duration_secs: int = 600,
    ):
        try:
            if self._raid_locks.get(guild.id):
                return
            until = time.time() + max(60, duration_secs)
            self._raid_locks[guild.id] = {
                "until": until,
                "channels": [c.id for c in channels],
            }
            dr = guild.default_role
            for ch in channels:
                try:
                    await ch.set_permissions(dr, send_messages=False)
                except Exception:
                    pass
            asyncio.create_task(self._release_raid_lock(guild.id))
            try:
                await self._log(
                    guild,
                    embed=discord.Embed(
                        title="Log",
                        description="Bloqueo anti‑raid aplicado",
                        color=discord.Color.red(),
                    ),
                )
            except Exception:
                pass
            try:
                c = self._daily_counts.setdefault(guild.id, {})
                c["locks_applied"] = c.get("locks_applied", 0) + 1
            except Exception:
                pass
        except Exception:
            pass

    async def _release_raid_lock(self, gid: int):
        try:
            data = self._raid_locks.get(gid)
            if not data:
                return
            wait = max(0, int(data["until"] - time.time()))
            await asyncio.sleep(wait)
            guild = discord.utils.get(self.bot.guilds, id=gid)
            if not guild:
                self._raid_locks.pop(gid, None)
                return
            ids = data.get("channels", [])
            dr = guild.default_role
            for cid in ids:
                ch = guild.get_channel(cid)
                if isinstance(ch, discord.TextChannel):
                    try:
                        await ch.set_permissions(dr, send_messages=None)
                    except Exception:
                        pass
            self._raid_locks.pop(gid, None)
            alert = discord.utils.get(guild.text_channels, name=ALERT_CHANNEL)
            if alert:
                try:
                    await alert.send(
                        embed=discord.Embed(
                            title="Fin de bloqueo anti‑raid",
                            description="Permisos restaurados",
                            color=discord.Color.green(),
                        )
                    )
                except Exception:
                    pass
            try:
                await self._log(
                    guild,
                    embed=discord.Embed(
                        title="Log",
                        description="Bloqueo anti‑raid finalizado",
                        color=discord.Color.green(),
                    ),
                )
            except Exception:
                pass
        except Exception:
            pass


async def setup(bot):
    await bot.add_cog(Guardian(bot))
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            if not message.guild or message.author.bot:
                return
            ch = message.channel
            key_id = None
            if isinstance(ch, discord.TextChannel):
                cat = ch.category
                if cat and cat.name == ORACULO_ABIERTOS_NAME:
                    key_id = ch.id
            elif isinstance(ch, discord.Thread):
                try:
                    parent = ch.parent
                    if isinstance(parent, discord.TextChannel) and parent.category and parent.category.name == ORACULO_ABIERTOS_NAME:
                        key_id = parent.id
                except Exception:
                    key_id = None
            if key_id is None:
                return
            c = self._daily_counts.setdefault(message.guild.id, {})
            mc = c.setdefault("oraculo_msg_counts", {})
            inc = ORACULO_SCORE_MSG + ORACULO_SCORE_ATTACH * len(message.attachments or [])
            mc[key_id] = mc.get(key_id, 0) + inc
        except Exception:
            pass
