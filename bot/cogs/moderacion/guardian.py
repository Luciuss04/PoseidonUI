import asyncio
import secrets
import time
from datetime import datetime
from collections import deque
import discord
from discord.ext import commands
from discord import app_commands

WELCOME_CHANNEL = "📜-puertas-del-olimpo"
FAREWELL_CHANNEL = "🏺-el-umbral-de-hades"
ALERT_CHANNEL = "⚔️-alertas"
VERIFY_ROLE = "🧍Humanos"

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

    @discord.ui.button(label="Jurar ante los dioses", style=discord.ButtonStyle.primary, emoji="🦉", custom_id="verify_button")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name=VERIFY_ROLE)
        if role:
            await interaction.user.add_roles(role, reason="Juramento ritual aceptado")
            await interaction.response.send_message(
                f"🦉 {interaction.user.mention} ha jurado ante los dioses y ahora es parte del Olimpo.",
                ephemeral=True
            )
            try:
                self.bot.dispatch("user_verified", interaction.guild, interaction.user)
            except Exception:
                pass
        else:
            await interaction.response.send_message(
                f"⚠️ No existe el rol {VERIFY_ROLE}.",
                ephemeral=True
            )

class Guardian(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._joins = {}
        self._raid_locks = {}
        self._verify_msg_ids = {}
        self._recent_verifies = {}
        self._verify_panel_id = {}

    async def cog_load(self):
        self.bot.add_view(VerifyView(self.bot))

    @commands.Cog.listener()
    async def on_member_join(self, member):
        canal = discord.utils.get(member.guild.text_channels, name=WELCOME_CHANNEL)
        if canal:
            ch_general = discord.utils.get(member.guild.text_channels, name="chat-general")
            ch_acceso = discord.utils.get(member.guild.text_channels, name="acceso")
            ch_directo = discord.utils.get(member.guild.text_channels, name="directo-ahora")
            g_mention = ch_general.mention if ch_general else "#chat-general"
            a_mention = ch_acceso.mention if ch_acceso else "#acceso"
            d_mention = ch_directo.mention if ch_directo else "#directo-ahora"
            desc = (
                "╔══════════════════════════════╗\n"
                "Has ascendido al Olimpo: comunidad, streaming y buen rollo ⚡🎮\n"
                "╚══════════════════════════════╝\n\n"
                "🔱 **Primeros pasos** — sigue estas tres rutas y estarás listo:"
            )
            embed = discord.Embed(
                title=f"⚡👑 {member.display_name}, los dioses te reciben en el Olimpo",
                description=desc,
                color=discord.Color.gold()
            )
            embed.add_field(name="🫂 Presentación", value=f"Saluda en {g_mention}", inline=True)
            embed.add_field(name="🛡 Roles", value=f"Elige tus roles en {a_mention}", inline=True)
            embed.add_field(name="🎙 Directos", value=f"Mira cuándo hay stream en {d_mention}", inline=True)
            try:
                vrole = discord.utils.get(member.guild.roles, name=VERIFY_ROLE)
                vtxt = f"Pulsa el botón para recibir {vrole.mention}" if vrole else "Pulsa el botón para verificarte"
            except Exception:
                vtxt = "Pulsa el botón para verificarte"
            embed.add_field(name="🦉 Verificación", value=vtxt, inline=False)
            try:
                embed.add_field(name="👥 Población", value=str(member.guild.member_count), inline=True)
            except Exception:
                pass
            try:
                if member.guild.icon:
                    embed.set_thumbnail(url=member.guild.icon.url)
            except Exception:
                pass
            try:
                embed.set_image(url="https://cdn.discordapp.com/attachments/1425781431682076682/1440115588746706984/Imagen_para_el_bot_d.png")
            except Exception:
                pass
            embed.set_footer(text="Los dioses observan tu llegada...")
            await canal.send(embed=embed, view=VerifyView(self.bot))
        try:
            e2 = discord.Embed(title="Bienvenido al Olimpo", description="Pulsa el botón del canal de bienvenida para recibir acceso.", color=discord.Color.gold())
            await member.send(embed=e2)
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
                alert = discord.utils.get(member.guild.text_channels, name=ALERT_CHANNEL)
                rol_staff = discord.utils.get(member.guild.roles, name="Staff")
                mention = rol_staff.mention if rol_staff else None
                canales_bloqueo = []
                for n in ["chat-general", "acceso", "directo-ahora"]:
                    ch = discord.utils.get(member.guild.text_channels, name=n)
                    if ch:
                        canales_bloqueo.append(ch)
                if canales_bloqueo:
                    await self._apply_raid_lock(member.guild, canales_bloqueo, duration_secs=600)
                if alert:
                    tit = "Posible raid"
                    desc = f"{len(dq)} ingresos en 60s"
                    if canales_bloqueo:
                        desc += "\nCanales bloqueados: " + ", ".join([c.mention for c in canales_bloqueo])
            await alert.send(content=mention, embed=discord.Embed(title=tit, description=desc, color=discord.Color.red()))
        except Exception:
            pass
        try:
            age_days = 999
            try:
                age_days = (datetime.utcnow() - member.created_at.replace(tzinfo=None)).days
            except Exception:
                age_days = 999
            if age_days < 7:
                alert = discord.utils.get(member.guild.text_channels, name=ALERT_CHANNEL)
                rol_staff = discord.utils.get(member.guild.roles, name="Staff")
                mention = rol_staff.mention if rol_staff else None
                if alert:
                    e = discord.Embed(title="Cuenta reciente", description=f"{member.mention} creada hace {age_days} día(s)", color=discord.Color.orange())
                    try:
                        e.set_thumbnail(url=member.display_avatar.url)
                    except Exception:
                        pass
                    await alert.send(content=mention, embed=e)
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        try:
            gid = payload.guild_id
            if not gid:
                return
            g = self.bot.get_guild(gid)
            if not g:
                return
            ch = g.get_channel(payload.channel_id)
            if not isinstance(ch, discord.TextChannel):
                return
            if ch.name != WELCOME_CHANNEL:
                return
            if payload.user_id == self.bot.user.id:
                return
            target_id = self._verify_msg_ids.get(gid)
            if not target_id:
                try:
                    pins = await ch.pins()
                    for m in pins:
                        if m.author == self.bot.user and m.embeds:
                            e = m.embeds[0]
                            if e.title == "🦉 Verificación de acceso":
                                target_id = m.id
                                self._verify_msg_ids[gid] = target_id
                                break
                except Exception:
                    target_id = None
            if target_id and payload.message_id != target_id:
                return
            emoji = str(payload.emoji)
            if emoji not in {"🛡️", "🦉"}:
                return
            m = g.get_member(payload.user_id) or await g.fetch_member(payload.user_id)
            role = discord.utils.get(g.roles, name=VERIFY_ROLE)
            if role and m:
                try:
                    await m.add_roles(role, reason="Verificación por reacción")
                except Exception:
                    pass
                try:
                    msg = await ch.fetch_message(payload.message_id)
                    await msg.remove_reaction(payload.emoji, m)
                except Exception:
                    pass
                try:
                    e = discord.Embed(title="Acceso concedido", description=f"{m.mention} verificado", color=discord.Color.green())
                    await ch.send(embed=e, delete_after=5)
                except Exception:
                    pass
                try:
                    self.bot.dispatch("user_verified", g, m)
                except Exception:
                    pass
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            ch = discord.utils.get(guild.text_channels, name=WELCOME_CHANNEL)
            if not ch:
                continue
            msg_id = None
            try:
                pins = await ch.pins()
                for m in pins:
                    if m.author == self.bot.user and m.embeds:
                        e = m.embeds[0]
                        if e.title == "🦉 Verificación de acceso":
                            msg_id = m.id
                            break
            except Exception:
                pass
            if not msg_id:
                try:
                    e = discord.Embed(title="🦉 Verificación de acceso", description="Reacciona con 🛡️ o usa el botón para verificar.", color=discord.Color.blurple())
                    m = await ch.send(embed=e, view=VerifyView(self.bot))
                    try:
                        await m.add_reaction("🛡️")
                        await m.add_reaction("🦉")
                        await m.pin()
                    except Exception:
                        pass
                    msg_id = m.id
                except Exception:
                    pass
            if msg_id:
                self._verify_msg_ids[guild.id] = msg_id

    @commands.Cog.listener()
    async def on_user_verified(self, guild: discord.Guild, member: discord.Member):
        try:
            dq = self._recent_verifies.get(guild.id)
            if dq is None:
                dq = deque(maxlen=10)
                self._recent_verifies[guild.id] = dq
            dq.append((member.id, time.time()))
            await self._update_verify_panel(guild)
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
                        age_days = (datetime.utcnow() - m.created_at.replace(tzinfo=None)).days
                    except Exception:
                        age_days = "?"
                    lines.append(f"{hora} — {m.mention} (cuenta {age_days} días)")
                else:
                    lines.append(f"{hora} — <@{uid}>")
            if not lines:
                lines = ["Sin verificaciones recientes"]
            e = discord.Embed(title="🛡️ Accesos recientes", description="\n".join(lines[:10]), color=discord.Color.blurple())
            try:
                if guild.icon:
                    e.set_thumbnail(url=guild.icon.url)
            except Exception:
                pass
            if msg_id:
                try:
                    msg = await ch.fetch_message(msg_id)
                    await msg.edit(embed=e)
                    return
                except Exception:
                    pass
            msg = await ch.send(embed=e)
            try:
                await msg.pin()
            except Exception:
                pass
            self._verify_panel_id[guild.id] = msg.id
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
                color=discord.Color.dark_gold()
            )
            try:
                embed.set_image(url="https://cdn.discordapp.com/attachments/1425781431682076682/1440115588746706984/Imagen_para_el_bot_d.png")
            except Exception:
                pass
            embed.set_footer(text="El Oráculo guarda silencio ante su partida")
            await canal.send(embed=embed)

    @app_commands.command(name="juicio", description="Invoca el Juicio de los Dioses sobre un usuario")
    async def juicio(self, interaction: discord.Interaction, usuario: discord.Member):
        titulo = secrets.choice(list(JUICIO_ROLES.keys()))
        mensaje = {
            "⚡ Favor divino": "Los dioses sonríen sobre ti. Que tus pasos sean firmes.",
            "🗡️ Prueba del destino": "Camina sin miedo: cada sombra guarda un aprendizaje.",
            "🌫️ Silencio ritual": "Hoy calla y observa. En el silencio se revelan los hilos del destino.",
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
            color=discord.Color.purple()
        )
        embed.set_footer(text=f"Invocado por {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

        if rol:
            await usuario.add_roles(rol, reason="Juicio divino otorgado")
            await interaction.followup.send(f"🕯️ {usuario.mention} ha recibido el rol **{rol_nombre}** por 24 horas.", ephemeral=True)
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

    async def _apply_raid_lock(self, guild: discord.Guild, channels: list[discord.TextChannel], duration_secs: int = 600):
        try:
            if self._raid_locks.get(guild.id):
                return
            until = time.time() + max(60, duration_secs)
            self._raid_locks[guild.id] = {"until": until, "channels": [c.id for c in channels]}
            dr = guild.default_role
            for ch in channels:
                try:
                    await ch.set_permissions(dr, send_messages=False)
                except Exception:
                    pass
            asyncio.create_task(self._release_raid_lock(guild.id))
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
                    await alert.send(embed=discord.Embed(title="Fin de bloqueo anti‑raid", description="Permisos restaurados", color=discord.Color.green()))
                except Exception:
                    pass
        except Exception:
            pass

async def setup(bot):
    await bot.add_cog(Guardian(bot))
