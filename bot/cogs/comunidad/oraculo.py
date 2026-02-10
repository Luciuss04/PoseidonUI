import io
import json
import os
import random
import time
from datetime import datetime

import discord
import asyncio
from discord import app_commands
from discord.ext import commands, tasks
from bot.themes import Theme

LOG_FILE = "oraculos.json"
PANEL_CHANNEL_NAME = "📩-oráculo-de-ayuda"
ALERT_CHANNEL_NAME = "⚔️-alertas de atenea"
ALERT_CHANNEL_ID = 1445911157289259140
CATEGORIA_ABIERTOS = "Oráculos de Atenea"
CATEGORIA_CERRADOS = "Oráculos Sellados"
STAFF_ROLE_NAME = "Staff"
STAFF_ROLE_ID = 1425967833229033562
MAX_PARTICIPANTS = int(os.getenv("ORACULO_MAX_PARTICIPANTS", "5"))

FRASES_APERTURA = {
    "general": [
        "🌟 *Atenea escucha tu llamado y abre las puertas del Olimpo.*",
        "✨ *La sabiduría desciende sobre ti, expón tu duda con valor.*",
        "🏛️ *El Oráculo se enciende con la luz de la verdad.*",
        "⚡ *Los dioses han atendido tu invocación, habla mortal.*",
        "🌌 *El cosmos se abre para escuchar tu voz.*",
    ],
    "urgente": [
        "⚡ *Los dioses han atendido tu invocación con premura.*",
        "🔥 *El Oráculo arde con la urgencia de tu consulta.*",
        "🚨 *El Olimpo se estremece ante tu clamor.*",
        "💥 *La verdad se precipita con fuerza hacia ti.*",
    ],
    "creativo": [
        "🎨 *Las musas inspiran tu Oráculo, deja fluir tu visión.*",
        "🌌 *La imaginación se abre como un cosmos infinito.*",
        "🪄 *La magia del arte envuelve tu consulta.*",
        "🎭 *El teatro de los dioses se abre para ti.*",
    ],
    "soporte": [
        "🛠️ *Los artesanos del Olimpo afinan sus herramientas para tu causa.*",
        "⚙️ *El Oráculo se abre para reparar y guiar.*",
        "🔧 *Las manos divinas ajustan los engranajes de tu destino.*",
        "💻 *La sabiduría técnica desciende desde los cielos.*",
    ],
    "administrativo": [
        "📑 *Los escribas del Olimpo preparan los registros sagrados.*",
        "🏛️ *El Oráculo abre sus archivos divinos para tu gestión.*",
        "🖋️ *Las plumas doradas redactan tu petición en los pergaminos celestiales.*",
        "⚖️ *La justicia de Atenea guía tu trámite.*",
    ],
    "denuncia": [
        "🚨 *El Oráculo escucha tu clamor y convoca a los guardianes.*",
        "⚔️ *Los dioses se preparan para impartir justicia.*",
        "🛡️ *La verdad será protegida por el Olimpo.*",
        "🔥 *La voz de Atenea arde contra la injusticia.*",
    ],
    "colaboración": [
        "🤝 *Los lazos divinos se entretejen en tu consulta.*",
        "🌐 *El Oráculo abre caminos de unión y alianza.*",
        "🏛️ *Atenea convoca a los mortales a trabajar juntos.*",
        "✨ *La cooperación se convierte en fuerza celestial.*",
    ],
    "místico": [
        "🔮 *El velo del misterio se levanta ante tu consulta.*",
        "🌌 *El cosmos susurra secretos ancestrales.*",
        "🕯️ *La luz de las velas guía tu pregunta.*",
        "🌙 *La luna revela símbolos ocultos en tu destino.*",
    ],
}

FRASES_CIERRE = [
    "⚖️ *El Oráculo ha hablado, y su voz queda sellada en la eternidad.*",
    "🔒 *Atenea guarda silencio, tu consulta ha sido archivada.*",
    "📜 *Las palabras se desvanecen, pero la sabiduría permanece.*",
    "🏛️ *El Olimpo cierra sus puertas hasta tu próxima invocación.*",
]


def guardar_log(oraculo_data):
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = []
    except Exception:
        data = []
    data.append(oraculo_data)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def normalizar_tipo(valor_label: str) -> str:
    t = valor_label.lower().strip()
    if t in FRASES_APERTURA.keys():
        return t
    m = {"colaboracion": "colaboración", "mistico": "místico"}
    return m.get(t, "general")


def color_por_tipo(tipo: str, guild_id: int = None) -> discord.Color:
    tipo = tipo.lower()
    if tipo == "urgente":
        return Theme.get_color(guild_id, 'error')
    if tipo == "creativo":
        return Theme.get_color(guild_id, 'primary')
    if tipo == "soporte":
        return Theme.get_color(guild_id, 'success')
    if tipo == "administrativo":
        return Theme.get_color(guild_id, 'warning')
    if tipo == "denuncia":
        return Theme.get_color(guild_id, 'error')
    if tipo == "colaboración":
        return Theme.get_color(guild_id, 'success')
    if tipo == "místico":
        return Theme.get_color(guild_id, 'secondary')
    return Theme.get_color(guild_id, 'secondary')


def guia_por_tipo(tipo: str) -> str:
    t = tipo.lower()
    if t == "soporte":
        return (
            "• Indica versión y plataforma\n"
            "• Describe pasos para reproducir\n"
            "• Explica lo esperado y lo obtenido\n"
            "• Añade capturas o logs"
        )
    if t == "urgente":
        return (
            "• Resume el contexto\n"
            "• Explica por qué es prioritario\n"
            "• Añade datos clave y evidencia"
        )
    if t == "creativo":
        return (
            "• Cuenta la idea\n"
            "• Define el objetivo\n"
            "• Lista recursos y referencias"
        )
    if t == "administrativo":
        return (
            "• Especifica trámite\n"
            "• Incluye ID de referencia si aplica\n"
            "• Explica detalles relevantes"
        )
    if t == "denuncia":
        return (
            "• Indica implicados\n"
            "• Aporta evidencia (links)\n"
            "• Detalla lo ocurrido"
        )
    if t == "colaboración":
        return (
            "• Expón tu propuesta\n"
            "• Define alcance\n"
            "• Añade notas y requisitos"
        )
    if t == "místico":
        return (
            "• Describe símbolos\n"
            "• Expón tu consulta\n"
            "• Añade contexto"
        )
    return "• Expón tu consulta\n• Añade contexto\n• Adjunta material útil"


TIPOS_ORACULO = list(FRASES_APERTURA.keys())


def _topic_tokens(canal: discord.TextChannel) -> dict[str, str]:
    s = canal.topic or ""
    meta = s
    if "||" in s:
        try:
            meta = s.split("||", 1)[1]
        except Exception:
            meta = s
    out: dict[str, str] = {}
    for part in meta.split("|"):
        if "=" in part:
            k, v = part.split("=", 1)
            if k:
                out[k.strip()] = v.strip()
    return out


async def _topic_set(canal: discord.TextChannel, **updates):
    toks = _topic_tokens(canal)
    for k, v in updates.items():
        if v is not None:
            toks[str(k)] = str(v)
    base = "oraculo"
    tokens = [base] + [f"{k}={toks[k]}" for k in toks if k]
    tipo = (toks.get("tipo") or "general").capitalize()
    owner = toks.get("owner")
    staff = toks.get("staff")
    pretty = f"🏛️ Oráculo en curso • Tipo: {tipo}"
    if owner:
        pretty += f" • Autor: <@{owner}>"
    if staff:
        pretty += f" • Asignado: <@{staff}>"
    spacer = "\u2003" * 40
    topic_text = f"{pretty} {spacer} || " + "|".join(tokens)
    await _edit_channel(canal, topic=topic_text)


async def _rename_channel(canal: discord.TextChannel, name: str):
    await _edit_channel(canal, name=name)


async def _update_pinned_embed_followup(canal: discord.TextChannel):
    try:
        toks = _topic_tokens(canal)
        tid = toks.get("alert_thread")
        if not tid:
            return
        tipo_norm = "general"
        try:
            t = toks.get("tipo")
            if t:
                tipo_norm = normalizar_tipo(t)
        except Exception:
            tipo_norm = "general"
        urgent = False
        try:
            urgent = canal.name.startswith("urgente-")
        except Exception:
            urgent = False
        raw_name = canal.name
        try:
            if raw_name.startswith("urgente-"):
                raw_name = raw_name[len("urgente-") :]
        except Exception:
            pass
        hold = False
        try:
            hold = raw_name.startswith("espera-")
        except Exception:
            hold = False
        pins = await canal.pins()
        for msg in pins:
            if msg.author == canal.guild.me and msg.embeds:
                emb = msg.embeds[0]
                if emb.title and emb.title.startswith("🏛️ Oráculo de Atenea"):
                    title = emb.title
                    if urgent and not title.startswith("⚠️ "):
                        title = "⚠️ " + title
                    if (not urgent) and title.startswith("⚠️ "):
                        title = title[3:]
                    try:
                        base_color = color_por_tipo(tipo_norm, canal.guild.id)
                    except Exception:
                        base_color = emb.color
                    nuevo_color = Theme.get_color(canal.guild.id, 'error') if urgent else base_color
                    nuevo = discord.Embed(
                        title=title, description=emb.description, color=nuevo_color
                    )
                    # Reordenar campos y actualizar/insertar "Estado"
                    # Colocar "Seguimiento" debajo de "Staff"
                    fields = [
                        f
                        for f in emb.fields
                        if f.name not in {"Seguimiento", "Estado", "Progreso"}
                    ]
                    seg_val = f"<#${tid}>".replace("$", "")
                    estado_val = "URGENTE" if urgent else "Normal"
                    progreso_val = "En espera" if hold else "En curso"
                    staff_idx = None
                    for i, f in enumerate(fields):
                        if f.name == "Staff":
                            staff_idx = i
                            break
                    for i, f in enumerate(fields):
                        nuevo.add_field(name=f.name, value=f.value, inline=f.inline)
                        if f.name == "Tipo":
                            nuevo.add_field(
                                name="Estado", value=estado_val, inline=True
                            )
                            nuevo.add_field(
                                name="Progreso", value=progreso_val, inline=True
                            )
                        if staff_idx is not None and i == staff_idx:
                            nuevo.add_field(
                                name="Seguimiento", value=seg_val, inline=False
                            )
                    if staff_idx is None:
                        nuevo.add_field(name="Seguimiento", value=seg_val, inline=False)
                    nuevo.set_footer(text=Theme.get_footer_text(canal.guild.id))
                    try:
                        await msg.edit(embed=nuevo)
                    except Exception:
                        pass
                    break
    except Exception:
        pass


class OraculoOpenView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="Invoca un Oráculo por tipo",
        options=[
            discord.SelectOption(
                label="General", description="Consulta general", emoji="🌟"
            ),
            discord.SelectOption(
                label="Soporte", description="Asistencia técnica", emoji="🛠️"
            ),
            discord.SelectOption(
                label="Urgente", description="Atención prioritaria", emoji="⚡"
            ),
            discord.SelectOption(
                label="Creativo", description="Ideas y proyectos", emoji="🎨"
            ),
            discord.SelectOption(
                label="Administrativo", description="Gestión y trámites", emoji="📑"
            ),
            discord.SelectOption(
                label="Denuncia", description="Reportes y evidencias", emoji="🚨"
            ),
            discord.SelectOption(
                label="Colaboración", description="Propuestas y alianzas", emoji="🤝"
            ),
            discord.SelectOption(
                label="Místico", description="Simbolismo y rol", emoji="🔮"
            ),
        ],
        custom_id="tipo_oraculo_rapido",
    )
    async def seleccionar_rapido(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        tipo = normalizar_tipo(select.values[0])
        modal = QuickOraculoModal(tipo)
        await interaction.response.send_modal(modal)


class OraculoUserView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=None)
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if (
            interaction.user.id == self.owner_id
            or interaction.user.guild_permissions.administrator
        ):
            return True
        try:
            await interaction.response.send_message(
                "⛔ Solo el autor del Oráculo puede usar este panel.", ephemeral=True
            )
        except Exception:
            pass
        return False

    @discord.ui.select(
        placeholder="Elige el tipo del Oráculo",
        options=[
            discord.SelectOption(
                label="General", description="Consulta general", emoji="🌟"
            ),
            discord.SelectOption(
                label="Urgente", description="Atención prioritaria", emoji="⚡"
            ),
            discord.SelectOption(
                label="Creativo", description="Ideas y proyectos", emoji="🎨"
            ),
            discord.SelectOption(
                label="Soporte", description="Asistencia técnica", emoji="🛠️"
            ),
            discord.SelectOption(
                label="Administrativo", description="Gestión y trámites", emoji="📑"
            ),
            discord.SelectOption(
                label="Denuncia", description="Reportes y evidencias", emoji="🚨"
            ),
            discord.SelectOption(
                label="Colaboración", description="Propuestas y alianzas", emoji="🤝"
            ),
            discord.SelectOption(
                label="Místico", description="Simbolismo y rol", emoji="🔮"
            ),
        ],
        custom_id="elige_motivo",
    )
    async def elegir_motivo(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        canal = interaction.channel
        tipo = normalizar_tipo(select.values[0])
        await _topic_set(canal, tipo=tipo)
        try:
            pins = await canal.pins()
            for msg in pins:
                if msg.author == interaction.client.user and msg.embeds:
                    emb = msg.embeds[0]
                    if emb.title and emb.title.startswith("🏛️ Oráculo de Atenea"):
                        urg = False
                        try:
                            urg = interaction.channel.name.startswith("urgente-")
                        except Exception:
                            urg = False
                        base_color = color_por_tipo(tipo, interaction.guild.id)
                        nuevo_color = Theme.get_color(interaction.guild.id, 'error') if urg else base_color
                        nuevo = discord.Embed(
                            title=f"🏛️ Oráculo de Atenea ({tipo.capitalize()})",
                            description=emb.description,
                            color=nuevo_color,
                        )
                        for f in emb.fields:
                            if f.name == "Tipo":
                                nuevo.add_field(
                                    name="Tipo", value=tipo.capitalize(), inline=True
                                )
                            elif f.name == "Estado":
                                nuevo.add_field(
                                    name="Estado",
                                    value=("URGENTE" if urg else "Normal"),
                                    inline=True,
                                )
                            elif f.name == "Guía":
                                nuevo.add_field(
                                    name="Guía", value=guia_por_tipo(tipo), inline=False
                                )
                            else:
                                nuevo.add_field(
                                    name=f.name, value=f.value, inline=f.inline
                                )
                        nuevo.set_footer(text=Theme.get_footer_text(interaction.guild.id))
                        try:
                            await msg.edit(embed=nuevo)
                        except Exception:
                            pass
                        break
        except Exception:
            pass
        await interaction.response.send_message(
            f"✅ Motivo actualizado a {tipo.capitalize()}.", ephemeral=True
        )

    @discord.ui.select(
        placeholder="Checklist rápido por tipo",
        options=[
            discord.SelectOption(
                label="General", description="Checklist breve", emoji="🌟"
            ),
            discord.SelectOption(
                label="Soporte",
                description="Versión, pasos, esperado, obtenido",
                emoji="🛠️",
            ),
            discord.SelectOption(
                label="Urgente", description="Contexto y prioridad", emoji="⚡"
            ),
            discord.SelectOption(
                label="Creativo", description="Idea, objetivo, recursos", emoji="🎨"
            ),
            discord.SelectOption(
                label="Administrativo", description="Trámite, id, detalles", emoji="📑"
            ),
            discord.SelectOption(
                label="Denuncia",
                description="Implicados, evidencia, detalle",
                emoji="🚨",
            ),
            discord.SelectOption(
                label="Colaboración", description="Propuesta y alcance", emoji="🤝"
            ),
            discord.SelectOption(
                label="Místico", description="Símbolos y consulta", emoji="🔮"
            ),
        ],
        custom_id="user_checklist",
    )
    async def checklist_rapido(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        tipo = normalizar_tipo(select.values[0])
        modal = QuickOraculoModal(tipo)
        await interaction.response.send_modal(modal)


class OraculoChannelView(discord.ui.View):
    def __init__(self, channel: discord.TextChannel | None = None):
        super().__init__(timeout=None)
        if channel is None:
            return
        self._channel = channel
        try:
            is_closed = bool(
                channel.category and channel.category.name == CATEGORIA_CERRADOS
            )
        except Exception:
            is_closed = False
        if not is_closed:
            for item in list(self.children):
                try:
                    if (
                        isinstance(item, discord.ui.Button)
                        and getattr(item, "custom_id", "") == "reopen_oraculo"
                    ):
                        self.remove_item(item)
                except Exception:
                    pass
        else:
            for item in list(self.children):
                try:
                    if isinstance(item, discord.ui.Button) and getattr(
                        item, "custom_id", ""
                    ) in {
                        "close_oraculo",
                        "resolve_oraculo",
                        "add_participant",
                        "toggle_urgent",
                        "ping_staff",
                        "assign_self",
                    }:
                        self.remove_item(item)
                except Exception:
                    pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        guild = interaction.guild
        rol_staff = guild.get_role(STAFF_ROLE_ID) or discord.utils.get(
            guild.roles, name=STAFF_ROLE_NAME
        )
        if interaction.user.guild_permissions.administrator or (
            rol_staff and rol_staff in interaction.user.roles
        ):
            return True
        try:
            await interaction.response.send_message(
                "⛔ Controles disponibles solo para Staff.", ephemeral=True
            )
        except Exception:
            pass
        return False

    @discord.ui.button(
        label="❌ Sellar Oráculo",
        style=discord.ButtonStyle.danger,
        custom_id="close_oraculo",
    )
    async def cerrar_oraculo(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        miembro = interaction.user

        # Solo administradores pueden cerrar Oráculos
        if not miembro.guild_permissions.administrator:
            await interaction.response.send_message(
                "⛔ Solo administradores pueden sellar Oráculos.", ephemeral=True
            )
            return
        modal = CloseOraculoModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="➕ Añadir participante",
        style=discord.ButtonStyle.secondary,
        custom_id="add_participant",
    )
    async def add_participant(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        miembro = interaction.user
        guild = interaction.guild
        rol_staff = guild.get_role(STAFF_ROLE_ID) or discord.utils.get(
            guild.roles, name=STAFF_ROLE_NAME
        )
        owner_ok = False
        try:
            toks = _topic_tokens(interaction.channel)
            owner_ok = toks.get("owner") == str(miembro.id)
        except Exception:
            owner_ok = False
        if not (
            miembro.guild_permissions.administrator
            or owner_ok
            or (rol_staff and rol_staff in miembro.roles)
        ):
            await interaction.response.send_message(
                "⛔ Solo administradores o Staff pueden añadir participantes.",
                ephemeral=True,
            )
            return
        await interaction.response.send_modal(AddParticipantModal())

    @discord.ui.button(
        label="🔓 Reabrir Oráculo",
        style=discord.ButtonStyle.success,
        custom_id="reopen_oraculo",
    )
    async def reopen_oraculo(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        miembro = interaction.user
        guild = interaction.guild
        canal = interaction.channel
        rol_staff = guild.get_role(STAFF_ROLE_ID) or discord.utils.get(
            guild.roles, name=STAFF_ROLE_NAME
        )
        owner_ok = False
        try:
            toks = _topic_tokens(canal)
            owner_ok = toks.get("owner") == str(miembro.id)
        except Exception:
            owner_ok = False
        if not (
            miembro.guild_permissions.administrator
            or owner_ok
            or (rol_staff and rol_staff in miembro.roles)
        ):
            await interaction.response.send_message(
                "⛔ Solo administradores o Staff pueden reabrir Oráculos.",
                ephemeral=True,
            )
            return
        categoria_abiertos = discord.utils.get(
            guild.categories, name=CATEGORIA_ABIERTOS
        )
        if not categoria_abiertos:
            categoria_abiertos = await guild.create_category(CATEGORIA_ABIERTOS)
        nuevo_nombre = canal.name
        was_cerrado = nuevo_nombre.startswith("cerrado-")
        for pref in ("sellado-", "auto-", "resuelto-", "cerrado-"):
            if nuevo_nombre.startswith(pref):
                nuevo_nombre = nuevo_nombre[len(pref) :]
                break
            await _edit_channel(canal, category=categoria_abiertos, name=nuevo_nombre)
            try:
                interaction.client.dispatch("oraculo_reopened", interaction.guild, canal)
            except Exception:
                pass
        for overwrite_target in list(canal.overwrites):
            if isinstance(overwrite_target, discord.Member):
                await _set_permissions(
                    canal, overwrite_target, send_messages=True, view_channel=True
                )
        embed = discord.Embed(
            title="🔓 Oráculo Reabierto",
            description="El Oráculo ha sido reabierto. Puedes continuar la conversación.",
            color=Theme.get_color(guild.id, 'success'),
        )
        await canal.send(embed=embed)
        # Controles disponibles para Staff mediante /oraculo_controles
        try:
            lista = []
            if was_cerrado:
                toks = _topic_tokens(canal)
                owner = toks.get("owner")
                if owner:
                    lista.append(f"<@{owner}>")
            else:
                for t, ow in canal.overwrites.items():
                    if isinstance(t, discord.Member):
                        lista.append(t.mention)
            rol_staff = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)
            if rol_staff:
                lista.append(rol_staff.mention)
            if lista:
                await canal.send("🔔 Participantes y Staff: " + " ".join(lista[:10]))
        except Exception:
            pass
        guardar_log(
            {
                "canal": canal.name,
                "reabierto_por": f"{miembro} ({miembro.id})",
                "fecha_reapertura": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            }
        )
        await interaction.response.send_message("✅ Oráculo reabierto.", ephemeral=True)

    @discord.ui.button(
        label="🧭 Asignarme", style=discord.ButtonStyle.primary, custom_id="assign_self"
    )
    async def assign_self(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        miembro = interaction.user
        guild = interaction.guild
        canal = interaction.channel
        rol_staff = guild.get_role(STAFF_ROLE_ID) or discord.utils.get(
            guild.roles, name=STAFF_ROLE_NAME
        )
        if not (
            miembro.guild_permissions.administrator
            or (rol_staff and rol_staff in miembro.roles)
        ):
            await interaction.response.send_message(
                "⛔ Solo Staff o administradores pueden asignarse el Oráculo.",
                ephemeral=True,
            )
            return
        toks = _topic_tokens(canal)
        ya = toks.get("staff")
        if ya and ya != str(miembro.id) and not miembro.guild_permissions.administrator:
            try:
                u = await guild.fetch_member(int(ya))
                await interaction.response.send_message(
                    f"⚠️ El Oráculo ya está asignado a {u.mention}.", ephemeral=True
                )
            except Exception:
                await interaction.response.send_message(
                    "⚠️ El Oráculo ya está asignado.", ephemeral=True
                )
            return
        try:
            if rol_staff:
                await _set_permissions(
                    canal, rol_staff, view_channel=True, send_messages=True, attach_files=True
                )
        except Exception:
            pass
        await _topic_set(canal, staff=str(miembro.id), assignedat=str(int(time.time())))
        await canal.send(f"🧭 {miembro.mention} se ha asignado este Oráculo.")
        try:
            e = discord.Embed(
                title="Asignación registrada",
                description=f"Asignado: {miembro.mention}",
                color=Theme.get_color(guild.id, 'success'),
            )
            await _alert_thread_post(guild, canal, embed=e)
        except Exception:
            pass
        try:
            raw = (miembro.display_name or miembro.name or "staff").lower()
            raw = raw.replace(" ", "-")
            slug = "".join([c for c in raw if c.isalnum() or c == "-"])
            name = canal.name
            urgent = False
            if name.startswith("urgente-"):
                name = name[len("urgente-") :]
                urgent = True
            if name.startswith("atendido-"):
                idx = name.find("-", len("atendido-"))
                if idx != -1:
                    name = name[idx + 1 :]
                else:
                    name = name[len("atendido-") :]
            new_name = ("urgente-" if urgent else "") + f"atendido-{slug}-" + name
            await _rename_channel(canal, new_name)
        except Exception:
            pass
        await interaction.response.send_message(
            "✅ Asignación registrada.", ephemeral=True
        )

    @discord.ui.button(
        label="🛡️ Llamar Staff",
        style=discord.ButtonStyle.primary,
        custom_id="ping_staff",
    )
    async def ping_staff(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        canal = interaction.channel
        guild = interaction.guild
        rol_staff = guild.get_role(STAFF_ROLE_ID) or discord.utils.get(
            guild.roles, name=STAFF_ROLE_NAME
        )
        if not rol_staff:
            await interaction.response.send_message(
                "⚠️ No hay rol Staff configurado.", ephemeral=True
            )
            return
        toks = _topic_tokens(canal)
        last = 0
        try:
            last = int(toks.get("laststaff", "0") or "0")
        except Exception:
            last = 0
        now = int(time.time())
        if now - last < 900:
            rem = 900 - (now - last)
            await interaction.response.send_message(
                f"⏱️ Espera {rem}s antes de volver a llamar al Staff.", ephemeral=True
            )
            return
        await canal.send(f"🛡️ {rol_staff.mention}")
        await _topic_set(canal, laststaff=str(now))
        await interaction.response.send_message(
            "✅ Se ha notificado al Staff.", ephemeral=True
        )
        try:
            e = discord.Embed(
                title="Llamada al Staff",
                description=f"Notificado: {rol_staff.mention}",
                color=Theme.get_color(guild.id, 'primary'),
            )
            await _alert_thread_post(guild, canal, embed=e)
            try:
                await interaction.client.log(embed=e, guild=guild)
            except Exception:
                pass
        except Exception:
            pass

    @discord.ui.button(
        label="⚠️ Marcar urgente",
        style=discord.ButtonStyle.danger,
        custom_id="toggle_urgent",
    )
    async def toggle_urgent(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        canal = interaction.channel
        miembro = interaction.user
        guild = interaction.guild
        rol_staff = guild.get_role(STAFF_ROLE_ID) or discord.utils.get(
            guild.roles, name=STAFF_ROLE_NAME
        )
        if not (
            miembro.guild_permissions.administrator
            or (rol_staff and rol_staff in miembro.roles)
        ):
            await interaction.response.send_message(
                "⛔ Solo administradores o Staff pueden marcar urgente.", ephemeral=True
            )
            return
        name = canal.name
        if name.startswith("urgente-"):
            new = name[len("urgente-") :]
        else:
            new = f"urgente-{name}"
        try:
            await _rename_channel(canal, new)
            await interaction.response.send_message(
                "✅ Estado de urgencia actualizado.", ephemeral=True
            )
        except Exception:
            await interaction.response.send_message(
                "⚠️ No se pudo cambiar el nombre.", ephemeral=True
            )
        try:
            await _update_pinned_embed_followup(canal)
        except Exception:
            pass
        try:
            urg = new.startswith("urgente-")
            e = discord.Embed(
                title="Cambio de urgencia",
                description=("URGENTE" if urg else "Modo normal"),
                color=(Theme.get_color(guild.id, 'error') if urg else Theme.get_color(guild.id, 'primary')),
            )
            await _alert_thread_post(guild, canal, embed=e)
        except Exception:
            pass

    @discord.ui.button(
        label="🧊 En espera",
        style=discord.ButtonStyle.secondary,
        custom_id="toggle_hold",
    )
    async def toggle_hold(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        canal = interaction.channel
        guild = interaction.guild
        rol_staff = guild.get_role(STAFF_ROLE_ID) or discord.utils.get(
            guild.roles, name=STAFF_ROLE_NAME
        )
        if not (
            interaction.user.guild_permissions.administrator
            or (rol_staff and rol_staff in interaction.user.roles)
        ):
            await interaction.response.send_message(
                "⛔ Solo administradores o Staff pueden cambiar el estado de espera.",
                ephemeral=True,
            )
            return
        name = canal.name
        prefix = ""
        raw = name
        if raw.startswith("urgente-"):
            prefix = "urgente-"
            raw = raw[len("urgente-") :]
        if raw.startswith("espera-"):
            raw = raw[len("espera-") :]
            new = prefix + raw
            progreso_txt = "En curso"
            color = Theme.get_color(guild.id, 'primary')
        else:
            new = prefix + "espera-" + raw
            progreso_txt = "En espera"
            color = Theme.get_color(guild.id, 'secondary')
        try:
            await _rename_channel(canal, new)
            await interaction.response.send_message(
                "✅ Estado de progreso actualizado.", ephemeral=True
            )
        except Exception:
            await interaction.response.send_message(
                "⚠️ No se pudo cambiar el nombre.", ephemeral=True
            )
        try:
            await _update_pinned_embed_followup(canal)
        except Exception:
            pass
        try:
            e = discord.Embed(
                title="Cambio de progreso", description=progreso_txt, color=color
            )
            await _alert_thread_post(guild, canal, embed=e)
        except Exception:
            pass

    @discord.ui.button(
        label="�� Completar checklist",
        style=discord.ButtonStyle.secondary,
        custom_id="complete_checklist",
    )
    async def complete_checklist(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        tipo = "general"
        try:
            toks = _topic_tokens(interaction.channel)
            t = toks.get("tipo")
            if t:
                tipo = normalizar_tipo(t)
        except Exception:
            pass
        await interaction.response.send_modal(QuickOraculoModal(tipo))

    @discord.ui.button(
        label="✅ Resolver",
        style=discord.ButtonStyle.success,
        custom_id="resolve_oraculo",
    )
    async def resolve_oraculo(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        miembro = interaction.user
        if not miembro.guild_permissions.administrator:
            await interaction.response.send_message(
                "⛔ Solo administradores pueden resolver Oráculos.", ephemeral=True
            )
            return
        await interaction.response.send_modal(ResolveOraculoModal())


class CloseOraculoModal(discord.ui.Modal, title="Sellar Oráculo"):
    resumen = discord.ui.TextInput(
        label="Resumen del cierre",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500,
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
        except Exception:
            pass
        try:
            guild = interaction.guild
            canal = interaction.channel
            miembro = interaction.user
            categoria_cerrados = discord.utils.get(
                guild.categories, name=CATEGORIA_CERRADOS
            )
            if not categoria_cerrados:
                categoria_cerrados = await guild.create_category(CATEGORIA_CERRADOS)
            try:
                await _edit_channel(
                    canal,
                    category=categoria_cerrados,
                    name=f"sellado-{canal.name}",
                )
            except Exception:
                pass
            try:
                await _topic_set(canal, closed_at=str(int(__import__("time").time())))
            except Exception:
                pass
            try:
                interaction.client.dispatch("oraculo_closed", interaction.guild, canal)
            except Exception:
                pass
            try:
                for overwrite_target in list(canal.overwrites):
                    if isinstance(overwrite_target, discord.Member):
                        await _set_permissions(
                            canal, overwrite_target, send_messages=False
                        )
            except Exception:
                pass
            frase = random.choice(FRASES_CIERRE)
            desc = frase
            if str(self.resumen.value).strip():
                desc = f"{frase}\n\n📝 Resumen: {self.resumen.value.strip()}"
            embed = discord.Embed(
                title="⚖️ Oráculo Sellado",
                description=desc,
                color=Theme.get_color(guild.id, 'warning'),
            )
            embed.set_footer(text=Theme.get_footer_text(guild.id))
            await canal.send(embed=embed)
            try:
                pins = await canal.pins()
                for msg in pins:
                    if msg.author == interaction.client.user and msg.embeds:
                        e0 = msg.embeds[0]
                        if e0.title == "Checklist":
                            try:
                                await msg.unpin()
                            except Exception:
                                pass
            except Exception:
                pass
            # Controles disponibles para Staff mediante /oraculo_controles
            try:
                lines = []
                async for msg in canal.history(limit=200, oldest_first=True):
                    ts = msg.created_at.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M")
                    content = (msg.content or "").replace("\n", " ")
                    lines.append(f"[{ts}] {msg.author}: {content}")
                if lines:
                    buf = io.BytesIO("\n".join(lines).encode("utf-8"))
                    await canal.send(file=discord.File(buf, "oraculo-transcript.txt"))
            except Exception:
                pass
            guardar_log(
                {
                    "canal": canal.name,
                    "cerrado_por": f"{miembro} ({miembro.id})",
                    "fecha_cierre": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "resumen": self.resumen.value.strip(),
                }
            )
            try:
                await interaction.followup.send(
                    "✅ El Oráculo ha sido sellado correctamente.", ephemeral=True
                )
            except Exception:
                pass
            try:
                txt = self.resumen.value.strip()
                e = discord.Embed(
                    title="Oráculo sellado",
                    description=(txt or ""),
                    color=Theme.get_color(guild.id, 'warning'),
                )
                await _alert_thread_post(guild, canal, embed=e)
            except Exception:
                pass
        except Exception:
            try:
                await interaction.followup.send(
                    "⚠️ No se pudo sellar el Oráculo.", ephemeral=True
                )
            except Exception:
                pass


class ResolveOraculoModal(discord.ui.Modal, title="Resolver Oráculo"):
    resumen = discord.ui.TextInput(label="Resumen breve", required=True, max_length=200)
    cierre_total = discord.ui.TextInput(
        label="Cerrar definitivamente (sí/no)", required=False, max_length=3
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Responder inmediatamente para evitar el error del modal
        try:
            await interaction.response.send_message(
                "Procesando resolución...", ephemeral=True
            )
        except Exception:
            pass

        async def _do_resolver():
            try:
                guild = interaction.guild
                canal = interaction.channel
                miembro = interaction.user
                categoria_cerrados = discord.utils.get(
                    guild.categories, name=CATEGORIA_CERRADOS
                )
                if not categoria_cerrados:
                    try:
                        categoria_cerrados = await guild.create_category(
                            CATEGORIA_CERRADOS
                        )
                    except Exception:
                        categoria_cerrados = None
                close_def = str(self.cierre_total.value or "").strip().lower() in {
                    "si",
                    "sí",
                    "yes",
                    "true",
                    "1",
                }
                base_name = canal.name
                nuevo_nombre = (
                    f"resuelto-{base_name}" if not close_def else f"cerrado-{base_name}"
                )
                try:
                    if len(nuevo_nombre) > 90:
                        nuevo_nombre = nuevo_nombre[:90]
                    if categoria_cerrados:
                        await _edit_channel(canal, category=categoria_cerrados, name=nuevo_nombre)
                    else:
                        await _rename_channel(canal, nuevo_nombre)
                except Exception:
                    pass
                if close_def:
                    try:
                        for overwrite_target in list(canal.overwrites):
                            if isinstance(overwrite_target, discord.Member):
                                try:
                                    await _set_permissions(
                                        canal, overwrite_target, overwrite=None
                                    )
                                except Exception:
                                    pass
                        try:
                            dr = canal.overwrites_for(guild.default_role)
                            dr.view_channel = False
                            dr.send_messages = False
                            await _set_permissions(
                                canal, guild.default_role, overwrite=dr
                            )
                        except Exception:
                            pass
                        rol_staff = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)
                        if rol_staff:
                            try:
                                await _set_permissions(
                                    canal, rol_staff, view_channel=True, send_messages=True
                                )
                            except Exception:
                                pass
                    except Exception:
                        pass
                else:
                    try:
                        for overwrite_target in list(canal.overwrites):
                            if isinstance(overwrite_target, discord.Member):
                                try:
                                    await _set_permissions(
                                        canal,
                                        overwrite_target,
                                        send_messages=False,
                                        view_channel=True,
                                    )
                                except Exception:
                                    pass
                    except Exception:
                        pass
                embed = discord.Embed(
                    title=(
                        "✅ Oráculo Resuelto"
                        if not close_def
                        else "🔒 Oráculo Resuelto y Cerrado"
                    ),
                    description=f"📝 Solución: {self.resumen.value.strip()}",
                    color=Theme.get_color(guild.id, 'success'),
                )
                try:
                    await canal.send(embed=embed)
                except Exception:
                    pass
                try:
                    interaction.client.dispatch("oraculo_resolved", guild, canal)
                    if close_def:
                        interaction.client.dispatch("oraculo_closed", guild, canal)
                except Exception:
                    pass
                if close_def:
                    try:
                        await _topic_set(canal, closed_at=str(int(__import__("time").time())))
                    except Exception:
                        pass
                try:
                    pins = await canal.pins()
                    for msg in pins:
                        if msg.author == interaction.client.user and msg.embeds:
                            e0 = msg.embeds[0]
                            if e0.title == "Checklist":
                                try:
                                    await msg.unpin()
                                except Exception:
                                    pass
                except Exception:
                    pass
                # Controles disponibles para Staff mediante /oraculo_controles
                try:
                    lines = []
                    async for msg in canal.history(limit=200, oldest_first=True):
                        ts = msg.created_at.replace(tzinfo=None).strftime(
                            "%Y-%m-%d %H:%M"
                        )
                        content = (msg.content or "").replace("\n", " ")
                        lines.append(f"[{ts}] {msg.author}: {content}")
                    if lines:
                        buf = io.BytesIO("\n".join(lines).encode("utf-8"))
                        await canal.send(
                            file=discord.File(buf, "oraculo-transcript.txt")
                        )
                except Exception:
                    pass
                guardar_log(
                    {
                        "canal": canal.name,
                        "resuelto_por": f"{miembro} ({miembro.id})",
                        "fecha_resuelto": datetime.utcnow().strftime(
                            "%Y-%m-%d %H:%M:%S UTC"
                        ),
                        "resumen": self.resumen.value.strip(),
                    }
                )
                try:
                    await interaction.followup.send(
                        "✅ Oráculo marcado como resuelto.", ephemeral=True
                    )
                except Exception:
                    pass
            except Exception:
                try:
                    await interaction.followup.send(
                        "⚠️ No se pudo resolver el Oráculo.", ephemeral=True
                    )
                except Exception:
                    pass

        try:
            await _do_resolver()
        except Exception:
            pass


class AddParticipantModal(discord.ui.Modal, title="Añadir participante"):
    usuario = discord.ui.TextInput(
        label="Usuario (mención o ID)", required=True, max_length=64
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        canal = interaction.channel
        val = str(self.usuario.value).strip()
        uid = None
        try:
            if val.startswith("<@") and val.endswith(">"):
                import re

                m = re.search(r"\d+", val)
                if m:
                    uid = int(m.group(0))
            elif val.isdigit():
                uid = int(val)
        except Exception:
            uid = None
        miembro_obj = guild.get_member(uid) if uid else None
        if not miembro_obj:
            await interaction.response.send_message(
                "⚠️ Usuario inválido. Usa mención o ID.", ephemeral=True
            )
            return
        miembros_actuales = [
            t for t in canal.overwrites if isinstance(t, discord.Member)
        ]
        if len(miembros_actuales) >= MAX_PARTICIPANTS:
            await interaction.response.send_message(
                f"⛔ Límite de participantes alcanzado ({MAX_PARTICIPANTS}).",
                ephemeral=True,
            )
            return
        await _set_permissions(
            canal, miembro_obj, view_channel=True, send_messages=True, attach_files=True
        )
        await canal.send(f"➕ {miembro_obj.mention} añadido al Oráculo.")
        await interaction.response.send_message(
            "✅ Participante añadido.", ephemeral=True
        )


class AperturaOraculoModal(discord.ui.Modal, title="Apertura del Oráculo"):
    titulo = discord.ui.TextInput(label="Título", required=False, max_length=100)
    detalle = discord.ui.TextInput(
        label="Detalle",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=1000,
    )
    urgente = discord.ui.TextInput(
        label="Urgente (si/no)", required=False, max_length=3
    )

    def __init__(
        self,
        tipo: str,
        participante: discord.User | None,
        adjuntos: list[discord.Attachment | None],
    ):
        super().__init__()
        self.tipo = tipo
        self.participante = participante
        self.adjuntos = [a for a in adjuntos if a]

    async def on_submit(self, interaction: discord.Interaction):
        canal = await crear_oraculo(interaction, self.tipo)
        if not canal:
            return
        try:
            interaction.client.dispatch("oraculo_opened", interaction.guild, canal)
        except Exception:
            pass
        titulo = str(self.titulo.value or "").strip()
        detalle = str(self.detalle.value or "").strip()
        urg = str(self.urgente.value or "").strip().lower()
        if urg in {"si", "sí", "yes", "true"}:
            try:
                guild = interaction.guild
                rol_staff = guild.get_role(STAFF_ROLE_ID) or discord.utils.get(
                    guild.roles, name=STAFF_ROLE_NAME
                )
                if interaction.user.guild_permissions.administrator or (
                    rol_staff and rol_staff in interaction.user.roles
                ):
                    name = canal.name
                    if not name.startswith("urgente-"):
                        await _rename_channel(canal, f"urgente-{name}")
            except Exception:
                pass
        if self.participante:
            try:
                await _set_permissions(
                    canal,
                    self.participante,
                    view_channel=True,
                    send_messages=True,
                    attach_files=True,
                )
                await canal.send(f"➕ {self.participante.mention} añadido al Oráculo.")
            except Exception:
                pass
        try:
            if titulo or detalle:
                emb = discord.Embed(
                    title=titulo or "📜 Detalles",
                    description=detalle or "",
                    color=Theme.get_color(interaction.guild.id, 'primary'),
                )
                await canal.send(embed=emb)
        except Exception:
            pass
        try:
            mt = ((titulo + "\n") if titulo else "") + (detalle or "")
            if mt:
                await _topic_set(canal, motivo=mt[:1024])
            guild = interaction.guild
            alert = _find_alert_channel(guild)
            if alert:
                rol_staff = guild.get_role(STAFF_ROLE_ID) or discord.utils.get(
                    guild.roles, name=STAFF_ROLE_NAME
                )
                tipo_norm = normalizar_tipo(self.tipo)
                urg = False
                try:
                    urg = canal.name.startswith("urgente-")
                except Exception:
                    urg = False
                base_color = color_por_tipo(tipo_norm)
                alert_color = Theme.get_color(guild.id, 'error') if urg else base_color
                e = discord.Embed(
                    title=f"🛡️ Nuevo Oráculo — {tipo_norm.capitalize()}",
                    description=f"Canal: {canal.mention}",
                    color=alert_color,
                )
                e.add_field(name="Autor", value=interaction.user.mention, inline=True)
                if mt:
                    e.add_field(name="Motivo", value=mt[:1024], inline=False)
                e.add_field(name="Guía", value=guia_por_tipo(tipo_norm), inline=False)
                try:
                    e.set_image(
                        url="https://cdn.discordapp.com/attachments/1425781431682076682/1440115588746706984/Imagen_para_el_bot_d.png"
                    )
                except Exception:
                    pass
                files_alert = []
                try:
                    for a in self.adjuntos:
                        if a:
                            files_alert.append(await a.to_file())
                    if files_alert:
                        names = ", ".join(
                            [
                                getattr(a, "filename", "archivo")
                                for a in self.adjuntos
                                if a
                            ]
                        )
                        e.add_field(name="Adjuntos", value=names, inline=False)
                except Exception:
                    files_alert = []
                uid = 0
                try:
                    uid = int(os.getenv("ORACULO_ALERT_USER_ID", "0") or "0")
                except Exception:
                    uid = 0
                content = None
                if uid > 0:
                    content = f"<@{uid}>"
                elif rol_staff:
                    content = rol_staff.mention
                if files_alert:
                    msg = await alert.send(content=content, embed=e, files=files_alert)
                else:
                    msg = await alert.send(content=content, embed=e)
                try:
                    await interaction.client.log(embed=e, guild=interaction.guild)
                except Exception:
                    pass
                try:
                    thr = await msg.create_thread(
                        name=f"Seguimiento • {canal.name}", auto_archive_duration=1440
                    )
                    await _topic_set(canal, alert_thread=str(thr.id))
                    await _update_pinned_embed_followup(canal)
                except Exception:
                    pass
        except Exception:
            pass
        for a in self.adjuntos:
            try:
                f = await a.to_file()
                await canal.send(file=f)
            except Exception:
                pass
        try:
            guild = interaction.guild
            files = []
            names = []
            for a in self.adjuntos:
                if a:
                    try:
                        files.append(await a.to_file())
                        names.append(getattr(a, "filename", "archivo"))
                    except Exception:
                        pass
            if files:
                max_per = 5
                total = len(files)
                for i in range(0, total, max_per):
                    chunk_files = files[i : i + max_per]
                    chunk_names = names[i : i + max_per]
                    title = (
                        "Nuevos adjuntos"
                        if total <= max_per
                        else f"Nuevos adjuntos ({i//max_per+1})"
                    )
                    e2 = discord.Embed(
                        title=title,
                        description=f"Autor: {interaction.user.mention}",
                        color=Theme.get_color(guild.id, 'primary'),
                    )
                    e2.add_field(
                        name="Lista", value=", ".join(chunk_names)[:1024], inline=False
                    )
                    e2.add_field(
                        name="Resumen",
                        value=f"{len(chunk_files)} de {total} archivos",
                        inline=True,
                    )
                    await _alert_thread_post(guild, canal, embed=e2, files=chunk_files)
        except Exception:
            pass


class QuickOraculoModal(discord.ui.Modal):
    def __init__(self, tipo: str):
        super().__init__(title=f"Oráculo rápido ({tipo.capitalize()})")
        self.tipo = tipo
        if tipo == "soporte":
            self.add_item(
                discord.ui.TextInput(label="Versión", required=False, max_length=50)
            )
            self.add_item(
                discord.ui.TextInput(
                    label="Pasos",
                    style=discord.TextStyle.paragraph,
                    required=False,
                    max_length=500,
                )
            )
            self.add_item(
                discord.ui.TextInput(label="Esperado", required=False, max_length=200)
            )
            self.add_item(
                discord.ui.TextInput(label="Obtenido", required=False, max_length=200)
            )
        elif tipo == "creativo":
            self.add_item(
                discord.ui.TextInput(label="Idea", required=False, max_length=200)
            )
            self.add_item(
                discord.ui.TextInput(label="Objetivo", required=False, max_length=200)
            )
            self.add_item(
                discord.ui.TextInput(
                    label="Recursos",
                    style=discord.TextStyle.paragraph,
                    required=False,
                    max_length=500,
                )
            )
        elif tipo == "administrativo":
            self.add_item(
                discord.ui.TextInput(label="Trámite", required=False, max_length=100)
            )
            self.add_item(
                discord.ui.TextInput(
                    label="ID referencia", required=False, max_length=100
                )
            )
            self.add_item(
                discord.ui.TextInput(
                    label="Detalles",
                    style=discord.TextStyle.paragraph,
                    required=False,
                    max_length=500,
                )
            )
        elif tipo == "denuncia":
            self.add_item(
                discord.ui.TextInput(label="Implicados", required=False, max_length=200)
            )
            self.add_item(
                discord.ui.TextInput(
                    label="Evidencia (links)",
                    style=discord.TextStyle.paragraph,
                    required=False,
                    max_length=500,
                )
            )
            self.add_item(
                discord.ui.TextInput(
                    label="Detalle",
                    style=discord.TextStyle.paragraph,
                    required=False,
                    max_length=500,
                )
            )
        elif tipo == "colaboración":
            self.add_item(
                discord.ui.TextInput(label="Propuesta", required=False, max_length=200)
            )
            self.add_item(
                discord.ui.TextInput(label="Alcance", required=False, max_length=200)
            )
            self.add_item(
                discord.ui.TextInput(
                    label="Notas",
                    style=discord.TextStyle.paragraph,
                    required=False,
                    max_length=500,
                )
            )
        elif tipo == "místico":
            self.add_item(
                discord.ui.TextInput(label="Símbolos", required=False, max_length=200)
            )
            self.add_item(
                discord.ui.TextInput(
                    label="Consulta",
                    style=discord.TextStyle.paragraph,
                    required=False,
                    max_length=500,
                )
            )
        else:
            self.add_item(
                discord.ui.TextInput(label="Pregunta", required=False, max_length=200)
            )
            self.add_item(
                discord.ui.TextInput(
                    label="Contexto",
                    style=discord.TextStyle.paragraph,
                    required=False,
                    max_length=500,
                )
            )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
        except Exception:
            pass
        canal = interaction.channel
        usar_actual = False
        creado_nuevo = False
        try:
            toks = _topic_tokens(canal)
            usar_actual = bool(toks.get("owner"))
        except Exception:
            usar_actual = False
        if not usar_actual:
            canal = await crear_oraculo(interaction, self.tipo)
            if not canal:
                return
            creado_nuevo = True
        try:
            campos = []
            for comp in self.children:
                if isinstance(comp, discord.ui.TextInput) and (
                    comp.label and comp.value
                ):
                    campos.append((comp.label, comp.value))
            datos = {k: v for k, v in campos}
            urg = False
            try:
                urg = canal.name.startswith("urgente-")
            except Exception:
                urg = False
            faltan = []
            if urg:
                if self.tipo == "soporte":
                    if not datos.get("Pasos"):
                        faltan.append("Pasos")
                    if not datos.get("Obtenido"):
                        faltan.append("Obtenido")
                elif self.tipo == "administrativo":
                    if not (datos.get("Trámite") or datos.get("ID referencia")):
                        faltan.append("Trámite o ID referencia")
                elif self.tipo == "denuncia":
                    if not datos.get("Evidencia (links)"):
                        faltan.append("Evidencia (links)")
                elif self.tipo == "creativo":
                    if not (datos.get("Idea") or datos.get("Objetivo")):
                        faltan.append("Idea u Objetivo")
                elif self.tipo == "general":
                    if not datos.get("Pregunta"):
                        faltan.append("Pregunta")
            if faltan:
                try:
                    await interaction.followup.send(
                        "⚠️ Faltan campos obligatorios: " + ", ".join(faltan),
                        ephemeral=True,
                    )
                except Exception:
                    pass
                return
            if campos:
                e = discord.Embed(title="Checklist", color=Theme.get_color(interaction.guild.id, 'primary'))
                if urg:
                    e.add_field(name="Estado", value="URGENTE", inline=True)
                for label, val in campos:
                    e.add_field(name=label, value=val[:1024], inline=False)
                e.set_footer(text=f"{Theme.get_footer_text(interaction.guild.id)} • Añade capturas o archivos en este canal")
                last = None
                try:
                    async for m in canal.history(limit=30, oldest_first=False):
                        if m.author == interaction.client.user and m.embeds:
                            emb = m.embeds[0]
                            if emb.title == "Checklist":
                                last = m
                                break
                except Exception:
                    pass
                if last:
                    try:
                        await last.edit(embed=e)
                        if urg:
                            try:
                                await last.pin()
                            except Exception:
                                pass
                    except Exception:
                        m = await canal.send(embed=e)
                        if urg:
                            try:
                                await m.pin()
                            except Exception:
                                pass
                else:
                    m = await canal.send(embed=e)
                    if urg:
                        try:
                            await m.pin()
                        except Exception:
                            pass
            # Aviso para Staff si se acaba de crear el Oráculo
            try:
                if creado_nuevo:
                    mt = (
                        "\n".join([f"{lbl}: {val}" for lbl, val in campos])
                        if campos
                        else ""
                    )
                    if mt:
                        await _topic_set(canal, motivo=mt[:1024])
                    guild = interaction.guild
                    alert = _find_alert_channel(guild)
                    if alert:
                        rol_staff = guild.get_role(STAFF_ROLE_ID) or discord.utils.get(
                            guild.roles, name=STAFF_ROLE_NAME
                        )
                        tipo_norm = normalizar_tipo(self.tipo)
                        urg2 = False
                        try:
                            urg2 = canal.name.startswith("urgente-")
                        except Exception:
                            urg2 = False
                        base_color2 = color_por_tipo(tipo_norm)
                        alert_color2 = Theme.get_color(guild.id, 'error') if urg2 else base_color2
                        ee = discord.Embed(
                            title=f"🛡️ Nuevo Oráculo — {tipo_norm.capitalize()}",
                            description=f"Canal: {canal.mention}",
                            color=alert_color2,
                        )
                        ee.add_field(
                            name="Autor", value=interaction.user.mention, inline=True
                        )
                        if mt:
                            ee.add_field(name="Motivo", value=mt[:1024], inline=False)
                        ee.add_field(
                            name="Guía", value=guia_por_tipo(tipo_norm), inline=False
                        )
                        try:
                            ee.set_image(
                                url="https://cdn.discordapp.com/attachments/1425781431682076682/1440115588746706984/Imagen_para_el_bot_d.png"
                            )
                        except Exception:
                            pass
                        uid = 0
                        try:
                            uid = int(os.getenv("ORACULO_ALERT_USER_ID", "0") or "0")
                        except Exception:
                            uid = 0
                        content = None
                        if uid > 0:
                            content = f"<@{uid}>"
                        elif rol_staff:
                            content = rol_staff.mention
                        msg = await alert.send(content=content, embed=ee)
                        try:
                            await interaction.client.log(
                                embed=ee, guild=interaction.guild
                            )
                        except Exception:
                            pass
                        try:
                            thr = await msg.create_thread(
                                name=f"Seguimiento • {canal.name}",
                                auto_archive_duration=1440,
                            )
                            await _topic_set(canal, alert_thread=str(thr.id))
                            await _update_pinned_embed_followup(canal)
                        except Exception:
                            pass
            except Exception:
                pass
            try:
                await interaction.followup.send(
                    "✅ Checklist publicado/actualizado.", ephemeral=True
                )
            except Exception:
                pass
        except Exception:
            try:
                await interaction.followup.send(
                    "⚠️ No se pudo publicar el checklist.", ephemeral=True
                )
            except Exception:
                pass


async def crear_oraculo(interaction: discord.Interaction, tipo: str = "general"):
    guild = interaction.guild
    miembro = interaction.user

    categoria_abiertos = discord.utils.get(guild.categories, name=CATEGORIA_ABIERTOS)
    if not categoria_abiertos:
        categoria_abiertos = await guild.create_category(CATEGORIA_ABIERTOS)

    nombre_base = miembro.name.lower().replace(" ", "-")
    nombre_canal = f"oraculo-{nombre_base}"
    existentes = [
        c for c in categoria_abiertos.text_channels if c.name.startswith(nombre_canal)
    ]
    if existentes:
        await interaction.response.send_message(
            f"ℹ️ Ya tienes un Oráculo abierto: {existentes[0].mention}", ephemeral=True
        )
        return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        miembro: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, attach_files=True
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, manage_channels=True
        ),
    }
    rol_staff = guild.get_role(STAFF_ROLE_ID) or discord.utils.get(
        guild.roles, name=STAFF_ROLE_NAME
    )
    if rol_staff:
        overwrites[rol_staff] = discord.PermissionOverwrite(
            view_channel=True, send_messages=True
        )

    canal = await guild.create_text_channel(
        nombre_canal,
        overwrites=overwrites,
        category=categoria_abiertos,
        reason=f"Oráculo abierto por {miembro}",
    )
    await _topic_set(canal, owner=miembro.id, tipo=normalizar_tipo(tipo))
    try:
        await canal.edit(slowmode_delay=2)
    except Exception:
        pass

    tipo_norm = normalizar_tipo(tipo)
    frases = FRASES_APERTURA.get(tipo_norm, FRASES_APERTURA["general"])
    frase = random.choice(frases)
    color = color_por_tipo(tipo_norm)

    embed = discord.Embed(
        title=f"🏛️ Oráculo de Atenea ({tipo_norm.capitalize()})",
        description=(
            "╔══════════════════════════════╗\n"
            f"{frase}\n"
            "╚══════════════════════════════╝\n\n"
            "📜 Expón tu consulta con claridad para que la sabiduría descienda."
        ),
        color=color,
    )
    embed.set_footer(text=Theme.get_footer_text(guild.id))
    embed.add_field(name="Tipo", value=tipo_norm.capitalize(), inline=True)
    embed.add_field(
        name="Apertura",
        value=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        inline=True,
    )
    embed.add_field(name="Estado", value="Normal", inline=True)
    embed.add_field(name="Progreso", value="En curso", inline=True)
    if rol_staff:
        embed.add_field(name="Staff", value=rol_staff.mention, inline=False)
    embed.add_field(name="Guía", value=guia_por_tipo(tipo_norm), inline=False)

    content = f"{miembro.mention}"
    if rol_staff:
        content += f" {rol_staff.mention}"
    msg = await canal.send(
        content=content + ", tu Oráculo ha sido abierto.", embed=embed
    )
    try:
        await msg.pin()
    except Exception:
        pass

    try:
        if not interaction.response.is_done():
            await interaction.response.send_message(
                f"✅ Tu Oráculo ha sido abierto: {canal.mention}", ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"✅ Tu Oráculo ha sido abierto: {canal.mention}", ephemeral=True
            )
    except Exception:
        pass

    guardar_log(
        {
            "canal": canal.name,
            "tipo": tipo_norm,
            "abierto_por": f"{miembro} ({miembro.id})",
            "fecha_apertura": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        }
    )
    return canal


class OraculoPanel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            canal = discord.utils.get(guild.text_channels, name=PANEL_CHANNEL_NAME)
            if canal:
                ya_existe = False
                try:
                    pins = await canal.pins()
                    for msg in pins:
                        if msg.author == self.bot.user and msg.embeds:
                            e = msg.embeds[0]
                            if e.title == "📩 Panel del Oráculo de Atenea":
                                ya_existe = True
                                break
                except Exception:
                    pass
                if not ya_existe:
                    try:
                        async for msg in canal.history(limit=50):
                            if msg.author == self.bot.user and msg.embeds:
                                e = msg.embeds[0]
                                if e.title == "📩 Panel del Oráculo de Atenea":
                                    ya_existe = True
                                    break
                    except Exception:
                        pass
                if not ya_existe:
                    embed = discord.Embed(
                        title="📩 Panel del Oráculo de Atenea",
                        description=(
                            "╔══════════════════════════════╗\n"
                            "Pulsa el selector para abrir un Oráculo según tu necesidad.\n"
                            "╚══════════════════════════════╝\n\n"
                            "Tipos disponibles:\n"
                            "🌟 General\n⚡ Urgente\n🎨 Creativo\n"
                            "🛠️ Soporte\n📑 Administrativo\n🚨 Denuncia\n"
                            "🤝 Colaboración\n🔮 Místico"
                        ),
                        color=Theme.get_color(guild.id, 'secondary'),
                    )
                    embed.set_image(
                        url="https://cdn.discordapp.com/attachments/1425781431682076682/1440115588746706984/Imagen_para_el_bot_d.png"
                    )
                    embed.set_footer(text=Theme.get_footer_text(g.id))
                    msg = await canal.send(embed=embed, view=OraculoOpenView())
                    try:
                        await msg.pin()
                    except Exception:
                        pass

    @app_commands.command(
        name="oraculos_abiertos", description="Lista Oráculos abiertos"
    )
    async def oraculos_abiertos(self, interaction: discord.Interaction):
        g = interaction.guild
        categoria_abiertos = discord.utils.get(g.categories, name=CATEGORIA_ABIERTOS)
        if not categoria_abiertos or not categoria_abiertos.text_channels:
            await interaction.response.send_message(
                "No hay Oráculos abiertos.", ephemeral=True
            )
            return
        items = []
        for c in categoria_abiertos.text_channels:
            toks = _topic_tokens(c)
            owner = toks.get("owner")
            om = f"<@{owner}>" if owner else "?"
            items.append(f"{c.mention} — {om}")
        await interaction.response.send_message("\n".join(items), ephemeral=True)

    @app_commands.command(
        name="oraculo_transferir", description="Transfiere el Oráculo a un Staff"
    )
    async def oraculo_transferir(
        self, interaction: discord.Interaction, staff: discord.User
    ):
        canal = interaction.channel
        guild = interaction.guild
        rol_staff = guild.get_role(STAFF_ROLE_ID) or discord.utils.get(
            guild.roles, name=STAFF_ROLE_NAME
        )
        if not (
            interaction.user.guild_permissions.administrator
            or (rol_staff and rol_staff in interaction.user.roles)
        ):
            await interaction.response.send_message(
                "⛔ Solo administradores o Staff.", ephemeral=True
            )
            return
        try:
            miembro = guild.get_member(staff.id) or await guild.fetch_member(staff.id)
        except Exception:
            miembro = None
        if not miembro:
            await interaction.response.send_message(
                "⚠️ Usuario inválido.", ephemeral=True
            )
            return
        try:
            await _set_permissions(
                canal, miembro, view_channel=True, send_messages=True, attach_files=True
            )
        except Exception:
            pass
        try:
            raw = (
                (miembro.display_name or miembro.name or "staff")
                .lower()
                .replace(" ", "-")
            )
            slug = "".join([c for c in raw if c.isalnum() or c == "-"])
            name = canal.name
            urgent = False
            if name.startswith("urgente-"):
                name = name[len("urgente-") :]
                urgent = True
            if name.startswith("atendido-"):
                idx = name.find("-", len("atendido-"))
                if idx != -1:
                    name = name[idx + 1 :]
                else:
                    name = name[len("atendido-") :]
            new_name = ("urgente-" if urgent else "") + f"atendido-{slug}-" + name
            await _rename_channel(canal, new_name)
        except Exception:
            pass
        await _topic_set(canal, staff=str(miembro.id), assignedat=str(int(time.time())))
        await canal.send(f"🧭 {miembro.mention} ha tomado este Oráculo.")
        await interaction.response.send_message(
            "✅ Transferencia realizada.", ephemeral=True
        )

    @app_commands.command(
        name="oraculo_exportar", description="Exporta transcript del Oráculo"
    )
    async def oraculo_exportar(self, interaction: discord.Interaction):
        canal = interaction.channel
        lines = []
        try:
            async for msg in canal.history(limit=500, oldest_first=True):
                ts = msg.created_at.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M")
                content = (msg.content or "").replace("\n", " ")
                lines.append(f"[{ts}] {msg.author}: {content}")
        except Exception:
            pass
        if not lines:
            await interaction.response.send_message(
                "⚠️ No hay mensajes.", ephemeral=True
            )
            return
        buf = io.BytesIO("\n".join(lines).encode("utf-8"))
        await canal.send(file=discord.File(buf, "oraculo-transcript.txt"))
        await interaction.response.send_message(
            "✅ Transcript exportado al canal.", ephemeral=True
        )

    @app_commands.command(
        name="oraculo_slowmode", description="Ajusta slowmode del Oráculo"
    )
    async def oraculo_slowmode(self, interaction: discord.Interaction, segundos: int):
        canal = interaction.channel
        guild = interaction.guild
        rol_staff = guild.get_role(STAFF_ROLE_ID) or discord.utils.get(
            guild.roles, name=STAFF_ROLE_NAME
        )
        if not (
            interaction.user.guild_permissions.administrator
            or (rol_staff and rol_staff in interaction.user.roles)
        ):
            await interaction.response.send_message(
                "⛔ Solo administradores o Staff.", ephemeral=True
            )
            return
        if segundos < 0 or segundos > 21600:
            await interaction.response.send_message(
                "⚠️ Segundos inválidos (0-21600).", ephemeral=True
            )
            return
        try:
            await canal.edit(slowmode_delay=segundos)
            await interaction.response.send_message(
                f"⏱️ Slowmode: {segundos}s.", ephemeral=True
            )
        except Exception:
            await interaction.response.send_message(
                "⚠️ No se pudo aplicar slowmode.", ephemeral=True
            )

    @app_commands.command(name="oraculo_help", description="Guía de uso del Oráculo")
    async def oraculo_help(self, interaction: discord.Interaction):
        e = discord.Embed(
            title="🏛️ Guía del Oráculo",
            description="Consejos para abrir y gestionar tu Oráculo",
            color=Theme.get_color(interaction.guild.id, 'secondary'),
        )
        e.add_field(
            name="Apertura",
            value="Usa /oraculo_abrir y completa el formulario. Puedes adjuntar archivos.",
            inline=False,
        )
        e.add_field(
            name="Participantes",
            value="Añade colaboradores desde el botón o el formulario.",
            inline=False,
        )
        e.add_field(
            name="Urgente", value="Admins o Staff pueden marcar urgente.", inline=False
        )
        e.add_field(
            name="Asignación",
            value="Staff puede asignarse o transferir desde comandos.",
            inline=False,
        )
        e.add_field(
            name="Transcript",
            value="Exporta el historial con /oraculo_exportar.",
            inline=False,
        )
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(
        name="oraculo_controles",
        description="Muestra controles de Oráculo (solo Staff)",
    )
    async def oraculo_controles(self, interaction: discord.Interaction):
        g = interaction.guild
        rol_staff = g.get_role(STAFF_ROLE_ID) or discord.utils.get(
            g.roles, name=STAFF_ROLE_NAME
        )
        if not (
            interaction.user.guild_permissions.administrator
            or (rol_staff and rol_staff in interaction.user.roles)
        ):
            await interaction.response.send_message(
                "⛔ Solo Staff o administradores.", ephemeral=True
            )
            return
        canal = interaction.channel
        try:
            toks = _topic_tokens(canal)
        except Exception:
            toks = {}
        tipo = normalizar_tipo(toks.get("tipo", "general"))
        motivo = toks.get("motivo")
        owner = toks.get("owner")
        staff_id = toks.get("staff")
        urg = False
        try:
            urg = canal.name.startswith("urgente-")
        except Exception:
            urg = False
        e = discord.Embed(
            title=f"🏛️ Atenea — Panel interno ({tipo.capitalize()})",
            description=(
                "╔══════════════════════════════╗\n"
                "Controles del Oráculo — solo Staff\n"
                "╚══════════════════════════════╝\n\n"
                "Usa este panel para gestionar asignación, urgencia y checklist."
            ),
            color=color_por_tipo(tipo),
        )
        e.add_field(
            name="Tipo", value=("URGENTE" if urg else tipo.capitalize()), inline=True
        )
        if owner:
            e.add_field(name="Autor", value=f"<@{owner}>", inline=True)
        if staff_id:
            e.add_field(name="Asignado", value=f"<@{staff_id}>", inline=True)
        if motivo:
            e.add_field(name="Motivo", value=motivo, inline=False)
        e.add_field(name="Guía", value=guia_por_tipo(tipo), inline=False)
        try:
            e.set_thumbnail(
                url="https://cdn.discordapp.com/attachments/1425781431682076682/1440115588746706984/Imagen_para_el_bot_d.png"
            )
        except Exception:
            pass
        e.set_footer(text=Theme.get_footer_text(interaction.guild.id))
        await interaction.response.send_message(
            embed=e, view=OraculoChannelView(canal), ephemeral=True
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            if not message.guild:
                return
            if message.author.bot:
                return
            canal = message.channel
            if not isinstance(canal, discord.TextChannel):
                return
            cat = canal.category
            if not cat or cat.name != CATEGORIA_ABIERTOS:
                return
            if not message.attachments:
                return
            files = []
            names = []
            for a in message.attachments:
                try:
                    files.append(await a.to_file())
                    names.append(getattr(a, "filename", "archivo"))
                except Exception:
                    pass
            if files:
                max_per = 5
                total = len(files)
                for i in range(0, total, max_per):
                    chunk_files = files[i : i + max_per]
                    chunk_names = names[i : i + max_per]
                    title = (
                        "Nuevos adjuntos"
                        if total <= max_per
                        else f"Nuevos adjuntos ({i//max_per+1})"
                    )
                    e = discord.Embed(
                        title=title,
                        description=f"Autor: {message.author.mention}",
                        color=Theme.get_color(message.guild.id, 'primary'),
                    )
                    e.add_field(
                        name="Lista", value=", ".join(chunk_names)[:1024], inline=False
                    )
                    e.add_field(
                        name="Resumen",
                        value=f"{len(chunk_files)} de {total} archivos",
                        inline=True,
                    )
                    try:
                        e.add_field(
                            name="Mensaje",
                            value=f"[Ir al mensaje]({message.jump_url})",
                            inline=False,
                        )
                    except Exception:
                        pass
                    await _alert_thread_post(
                        message.guild, canal, embed=e, files=chunk_files
                    )
        except Exception:
            pass

    @app_commands.command(
        name="oraculo_abrir", description="Abre un Oráculo con opciones"
    )
    @app_commands.describe(tipo="Tipo de Oráculo")
    async def oraculo_abrir(
        self,
        interaction: discord.Interaction,
        tipo: str,
        participante: discord.User | None = None,
        adjunto1: discord.Attachment | None = None,
        adjunto2: discord.Attachment | None = None,
    ):
        t = normalizar_tipo(tipo)
        modal = AperturaOraculoModal(t, participante, [adjunto1, adjunto2])
        await interaction.response.send_modal(modal)

    @oraculo_abrir.autocomplete("tipo")
    async def auto_tipo(self, interaction: discord.Interaction, current: str):
        cur = (current or "").lower().strip()
        out = []
        for n in TIPOS_ORACULO:
            if not cur or cur in n.lower():
                out.append(app_commands.Choice(name=n.capitalize(), value=n))
            if len(out) >= 25:
                break
        return out

    @app_commands.command(
        name="oraculo_panel_refrescar", description="Republica el panel del Oráculo"
    )
    async def oraculo_panel_refrescar(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "⛔ Solo administradores.", ephemeral=True
            )
            return
        g = interaction.guild
        canal = discord.utils.get(g.text_channels, name=PANEL_CHANNEL_NAME)
        if not canal:
            try:
                canal = await g.create_text_channel(
                    PANEL_CHANNEL_NAME, reason="Panel del Oráculo"
                )
            except Exception:
                await interaction.response.send_message(
                    "⚠️ No se pudo crear el canal del panel.", ephemeral=True
                )
                return
        try:
            pins = await canal.pins()
            for msg in pins:
                if msg.author == self.bot.user and msg.embeds:
                    e = msg.embeds[0]
                    if e.title == "📩 Panel del Oráculo de Atenea":
                        try:
                            await msg.unpin()
                        except Exception:
                            pass
        except Exception:
            pass
        try:
            async for m in canal.history(limit=100):
                if m.author == self.bot.user and not m.pinned:
                    try:
                        await m.delete()
                    except Exception:
                        pass
        except Exception:
            pass
        embed = discord.Embed(
            title="📩 Panel del Oráculo de Atenea",
            description=(
                "╔══════════════════════════════╗\n"
                "Pulsa el selector para abrir un Oráculo según tu necesidad.\n"
                "╚══════════════════════════════╝\n\n"
                "Tipos disponibles:\n"
                "🌟 General\n⚡ Urgente\n🎨 Creativo\n"
                "🛠️ Soporte\n📑 Administrativo\n🚨 Denuncia\n"
                "🤝 Colaboración\n🔮 Místico"
            ),
            color=Theme.get_color(g.id, 'secondary'),
        )
        embed.set_image(
            url="https://cdn.discordapp.com/attachments/1425781431682076682/1440115588746706984/Imagen_para_el_bot_d.png"
        )
        embed.set_footer(text=Theme.get_footer_text(g.id))
        try:
            msg = await canal.send(embed=embed, view=OraculoOpenView())
            try:
                await msg.pin()
            except Exception:
                pass
            await interaction.response.send_message(
                "✅ Panel del Oráculo actualizado.", ephemeral=True
            )
        except Exception:
            await interaction.response.send_message(
                "⚠️ No se pudo publicar el panel.", ephemeral=True
            )


class AutoArchivador(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.archivar_oraculos.start()

    @tasks.loop(hours=24)
    async def archivar_oraculos(self):
        for guild in self.bot.guilds:
            categoria_abiertos = discord.utils.get(
                guild.categories, name=CATEGORIA_ABIERTOS
            )
            categoria_cerrados = discord.utils.get(
                guild.categories, name=CATEGORIA_CERRADOS
            )
            if not (categoria_abiertos and categoria_cerrados):
                continue

            for canal in categoria_abiertos.text_channels:
                last_msg = None
                async for msg in canal.history(limit=1):
                    last_msg = msg
                if last_msg is None:
                    continue
                delta = datetime.utcnow() - last_msg.created_at.replace(tzinfo=None)
                if delta.days >= 7:
                    await canal.edit(
                        category=categoria_cerrados, name=f"auto-{canal.name}"
                    )
                    await canal.send(
                        "📜 Este Oráculo ha sido archivado automáticamente por inactividad."
                    )

    @archivar_oraculos.before_loop
    async def before_archivar(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(OraculoPanel(bot))
    await bot.add_cog(AutoArchivador(bot))
    try:
        bot.add_view(OraculoOpenView())
        bot.add_view(OraculoChannelView())
    except Exception:
        pass


def _find_alert_channel(guild: discord.Guild) -> discord.TextChannel | None:
    ch_id = guild.get_channel(ALERT_CHANNEL_ID)
    if isinstance(ch_id, discord.TextChannel):
        return ch_id
    ch = discord.utils.get(guild.text_channels, name=ALERT_CHANNEL_NAME)
    if ch:
        return ch
    for n in ["⚔️-alertas", "alertas", "alerts"]:
        ch = discord.utils.get(guild.text_channels, name=n)
        if ch:
            return ch
    return None


async def _alert_thread_post(
    guild: discord.Guild,
    canal: discord.TextChannel,
    content: str | None = None,
    embed: discord.Embed | None = None,
    files: list[discord.File] | None = None,
):
    try:
        toks = _topic_tokens(canal)
        tid = toks.get("alert_thread")
        thread = None
        if tid:
            try:
                thread = guild.get_channel(int(tid))
            except Exception:
                thread = None
        if thread is None:
            alert = _find_alert_channel(guild)
            if not alert:
                return
            base = f"Seguimiento del Oráculo: {canal.mention}"
            msg = await alert.send(base)
            try:
                thr = await msg.create_thread(
                    name=f"Seguimiento • {canal.name}", auto_archive_duration=1440
                )
                await _topic_set(canal, alert_thread=str(thr.id))
                thread = thr
            except Exception:
                thread = None
        if thread:
            if files:
                await thread.send(content=content, embed=embed, files=files)
            else:
                await thread.send(content=content, embed=embed)
    except Exception:
        pass
async def _edit_channel(canal: discord.TextChannel, *, name: str | None = None, topic: str | None = None, category: discord.CategoryChannel | None = None):
    try:
        try:
            cooldown = max(0, int(os.getenv("ORACULO_CHANNEL_EDIT_COOLDOWN", "600")))
        except Exception:
            cooldown = 600
        if not hasattr(_edit_channel, "_last"):
            _edit_channel._last = {}
        if not hasattr(_edit_channel, "_pending"):
            _edit_channel._pending = {}
        if not hasattr(_edit_channel, "_scheduled"):
            _edit_channel._scheduled = {}
        last = _edit_channel._last.get(canal.id, 0)
        now = time.time()
        upd = {}
        if name is not None:
            upd["name"] = name[:90]
        if topic is not None:
            upd["topic"] = topic
        if category is not None:
            upd["category"] = category
        if now - last < cooldown:
            pend = dict(_edit_channel._pending.get(canal.id) or {})
            pend.update({k: v for k, v in upd.items() if v is not None})
            _edit_channel._pending[canal.id] = pend
            if not _edit_channel._scheduled.get(canal.id):
                delay = max(1, int(cooldown - (now - last)))
                _edit_channel._scheduled[canal.id] = True
                async def _defer():
                    await asyncio.sleep(delay)
                    _edit_channel._scheduled[canal.id] = False
                    data = dict(_edit_channel._pending.pop(canal.id, {}) or {})
                    if data:
                        try:
                            await canal.edit(**data)
                            _edit_channel._last[canal.id] = time.time()
                        except Exception:
                            pass
                asyncio.create_task(_defer())
            return
        # immediate apply; merge any pending
        pend_now = dict(_edit_channel._pending.pop(canal.id, {}) or {})
        if pend_now:
            upd.update(pend_now)
        if upd:
            try:
                await canal.edit(**upd)
                _edit_channel._last[canal.id] = now
            except Exception:
                pass
    except Exception:
        pass

async def _set_permissions(canal: discord.TextChannel, target, overwrite: discord.PermissionOverwrite | None = None, **kwargs):
    try:
        try:
            cooldown = max(0, int(os.getenv("ORACULO_PERM_EDIT_COOLDOWN", "300")))
        except Exception:
            cooldown = 300
        key = (canal.id, getattr(target, "id", 0))
        if not hasattr(_set_permissions, "_last"):
            _set_permissions._last = {}
        if not hasattr(_set_permissions, "_pending"):
            _set_permissions._pending = {}
        if not hasattr(_set_permissions, "_scheduled"):
            _set_permissions._scheduled = {}
        last = _set_permissions._last.get(key, 0)
        now = time.time()
        desired = overwrite
        if desired is None and kwargs:
            try:
                desired = discord.PermissionOverwrite(**kwargs)
            except Exception:
                desired = None
        if now - last < cooldown:
            _set_permissions._pending[key] = desired
            if not _set_permissions._scheduled.get(key):
                delay = max(1, int(cooldown - (now - last)))
                _set_permissions._scheduled[key] = True
                async def _defer():
                    await asyncio.sleep(delay)
                    _set_permissions._scheduled[key] = False
                    ov = _set_permissions._pending.pop(key, None)
                    try:
                        await canal.set_permissions(target, overwrite=ov)
                        _set_permissions._last[key] = time.time()
                    except Exception:
                        pass
                asyncio.create_task(_defer())
            return
        pend = _set_permissions._pending.pop(key, None)
        if pend is not None:
            desired = pend
        try:
            await canal.set_permissions(target, overwrite=desired)
            _set_permissions._last[key] = now
        except Exception:
            pass
    except Exception:
        pass
