import json
import os
import random
from datetime import datetime, timedelta
import discord
from discord.ext import commands, tasks

LOG_FILE = "oraculos.json"
PANEL_CHANNEL_NAME = "📩-oráculo-de-ayuda"
CATEGORIA_ABIERTOS = "Oráculos de Atenea"
CATEGORIA_CERRADOS = "Oráculos Sellados"
STAFF_ROLE_NAME = "Staff"

FRASES_APERTURA = {
    "general": [
        "🌟 *Atenea escucha tu llamado y abre las puertas del Olimpo.*",
        "✨ *La sabiduría desciende sobre ti, expón tu duda con valor.*",
        "🏛️ *El Oráculo se enciende con la luz de la verdad.*",
        "⚡ *Los dioses han atendido tu invocación, habla mortal.*",
        "🌌 *El cosmos se abre para escuchar tu voz.*"
    ],
    "urgente": [
        "⚡ *Los dioses han atendido tu invocación con premura.*",
        "🔥 *El Oráculo arde con la urgencia de tu consulta.*",
        "🚨 *El Olimpo se estremece ante tu clamor.*",
        "💥 *La verdad se precipita con fuerza hacia ti.*"
    ],
    "creativo": [
        "🎨 *Las musas inspiran tu Oráculo, deja fluir tu visión.*",
        "🌌 *La imaginación se abre como un cosmos infinito.*",
        "🪄 *La magia del arte envuelve tu consulta.*",
        "🎭 *El teatro de los dioses se abre para ti.*"
    ],
    "soporte": [
        "🛠️ *Los artesanos del Olimpo afinan sus herramientas para tu causa.*",
        "⚙️ *El Oráculo se abre para reparar y guiar.*",
        "🔧 *Las manos divinas ajustan los engranajes de tu destino.*",
        "💻 *La sabiduría técnica desciende desde los cielos.*"
    ],
    "administrativo": [
        "📑 *Los escribas del Olimpo preparan los registros sagrados.*",
        "🏛️ *El Oráculo abre sus archivos divinos para tu gestión.*",
        "🖋️ *Las plumas doradas redactan tu petición en los pergaminos celestiales.*",
        "⚖️ *La justicia de Atenea guía tu trámite.*"
    ],
    "denuncia": [
        "🚨 *El Oráculo escucha tu clamor y convoca a los guardianes.*",
        "⚔️ *Los dioses se preparan para impartir justicia.*",
        "🛡️ *La verdad será protegida por el Olimpo.*",
        "🔥 *La voz de Atenea arde contra la injusticia.*"
    ],
    "colaboración": [
        "🤝 *Los lazos divinos se entretejen en tu consulta.*",
        "🌐 *El Oráculo abre caminos de unión y alianza.*",
        "🏛️ *Atenea convoca a los mortales a trabajar juntos.*",
        "✨ *La cooperación se convierte en fuerza celestial.*"
    ],
    "místico": [
        "🔮 *El velo del misterio se levanta ante tu consulta.*",
        "🌌 *El cosmos susurra secretos ancestrales.*",
        "🕯️ *La luz de las velas guía tu pregunta.*",
        "🌙 *La luna revela símbolos ocultos en tu destino.*"
    ]
}

FRASES_CIERRE = [
    "⚖️ *El Oráculo ha hablado, y su voz queda sellada en la eternidad.*",
    "🔒 *Atenea guarda silencio, tu consulta ha sido archivada.*",
    "📜 *Las palabras se desvanecen, pero la sabiduría permanece.*",
    "🏛️ *El Olimpo cierra sus puertas hasta tu próxima invocación.*"
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
    m = {
        "colaboracion": "colaboración",
        "mistico": "místico"
    }
    return m.get(t, "general")

def color_por_tipo(tipo: str) -> discord.Color:
    tipo = tipo.lower()
    if tipo == "urgente":
        return discord.Color.red()
    if tipo == "creativo":
        return discord.Color.blue()
    if tipo == "soporte":
        return discord.Color.teal()
    if tipo == "administrativo":
        return discord.Color.gold()
    if tipo == "denuncia":
        return discord.Color.dark_red()
    if tipo == "colaboración":
        return discord.Color.green()
    if tipo == "místico":
        return discord.Color.purple()
    return discord.Color.purple()

class OraculoOpenView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="Selecciona el tipo de Oráculo",
        options=[
            discord.SelectOption(label="General", description="Consulta normal", emoji="🌟"),
            discord.SelectOption(label="Urgente", description="Necesita atención rápida", emoji="⚡"),
            discord.SelectOption(label="Creativo", description="Ideas, proyectos, inspiración", emoji="🎨"),
            discord.SelectOption(label="Soporte", description="Problemas técnicos o bugs", emoji="🛠️"),
            discord.SelectOption(label="Administrativo", description="Gestiones internas o permisos", emoji="📑"),
            discord.SelectOption(label="Denuncia", description="Reportar incidencias o abusos", emoji="🚨"),
            discord.SelectOption(label="Colaboración", description="Propuestas y alianzas", emoji="🤝"),
            discord.SelectOption(label="Místico", description="Consultas simbólicas o roleplay", emoji="🔮")
        ],
        custom_id="tipo_oraculo"
    )
    async def seleccionar_tipo(self, interaction: discord.Interaction, select: discord.ui.Select):
        tipo = normalizar_tipo(select.values[0])
        await crear_oraculo(interaction, tipo)

class OraculoChannelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="❌ Sellar Oráculo", style=discord.ButtonStyle.danger, custom_id="close_oraculo")
    async def cerrar_oraculo(self, interaction: discord.Interaction, button: discord.ui.Button):
        miembro = interaction.user
        guild = interaction.guild
        canal = interaction.channel

        rol_staff = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)
        if not (miembro.guild_permissions.administrator or (rol_staff and rol_staff in miembro.roles)):
            await interaction.response.send_message(
                "⛔ Solo los administradores o el rol **Staff** pueden sellar Oráculos.",
                ephemeral=True
            )
            return
        modal = CloseOraculoModal()
        await interaction.response.send_modal(modal)

class CloseOraculoModal(discord.ui.Modal, title="Sellar Oráculo"):
    resumen = discord.ui.TextInput(label="Resumen del cierre", style=discord.TextStyle.paragraph, required=False, max_length=500)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        canal = interaction.channel
        miembro = interaction.user
        categoria_cerrados = discord.utils.get(guild.categories, name=CATEGORIA_CERRADOS)
        if not categoria_cerrados:
            categoria_cerrados = await guild.create_category(CATEGORIA_CERRADOS)
        await canal.edit(category=categoria_cerrados, name=f"sellado-{canal.name}")
        for overwrite_target in list(canal.overwrites):
            if isinstance(overwrite_target, discord.Member):
                await canal.set_permissions(overwrite_target, send_messages=False)
        frase = random.choice(FRASES_CIERRE)
        desc = frase
        if str(self.resumen.value).strip():
            desc = f"{frase}\n\n📝 Resumen: {self.resumen.value.strip()}"
        embed = discord.Embed(
            title="⚖️ Oráculo Sellado",
            description=desc,
            color=discord.Color.dark_gold()
        )
        embed.set_footer(text="Atenea vigila desde las alturas 🏛️")
        await canal.send(embed=embed)
        guardar_log({
            "canal": canal.name,
            "cerrado_por": f"{miembro} ({miembro.id})",
            "fecha_cierre": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "resumen": self.resumen.value.strip()
        })
        await interaction.response.send_message("✅ El Oráculo ha sido sellado correctamente.", ephemeral=True)

async def crear_oraculo(interaction: discord.Interaction, tipo: str = "general"):
    guild = interaction.guild
    miembro = interaction.user

    categoria_abiertos = discord.utils.get(guild.categories, name=CATEGORIA_ABIERTOS)
    if not categoria_abiertos:
        categoria_abiertos = await guild.create_category(CATEGORIA_ABIERTOS)

    nombre_base = miembro.name.lower().replace(" ", "-")
    nombre_canal = f"oraculo-{nombre_base}"
    existentes = [c for c in categoria_abiertos.text_channels if c.name.startswith(nombre_canal)]
    if existentes:
        await interaction.response.send_message(f"ℹ️ Ya tienes un Oráculo abierto: {existentes[0].mention}", ephemeral=True)
        return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        miembro: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
    }
    rol_staff = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)
    if rol_staff:
        overwrites[rol_staff] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    canal = await guild.create_text_channel(
        nombre_canal,
        overwrites=overwrites,
        category=categoria_abiertos,
        reason=f"Oráculo abierto por {miembro}"
    )
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
        color=color
    )
    embed.set_footer(text="Que la sabiduría guíe tu camino ✨")
    embed.add_field(name="Tipo", value=tipo_norm.capitalize(), inline=True)
    embed.add_field(name="Apertura", value=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"), inline=True)
    if rol_staff:
        embed.add_field(name="Staff", value=rol_staff.mention, inline=False)

    view = OraculoChannelView()
    content = f"{miembro.mention}"
    if rol_staff:
        content += f" {rol_staff.mention}"
    msg = await canal.send(content=content + ", tu Oráculo ha sido abierto.", embed=embed, view=view)
    try:
        await msg.pin()
    except Exception:
        pass

    await interaction.response.send_message(f"✅ Tu Oráculo ha sido abierto: {canal.mention}", ephemeral=True)

    guardar_log({
        "canal": canal.name,
        "tipo": tipo_norm,
        "abierto_por": f"{miembro} ({miembro.id})",
        "fecha_apertura": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    })

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
                            "Pulsa el selector para abrir un Oráculo según tu necesidad.\n\n"
                            "Tipos disponibles: General, Urgente, Creativo, Soporte, Administrativo, Denuncia, Colaboración, Místico"
                        ),
                        color=discord.Color.gold()
                    )
                    embed.set_image(url="https://cdn.discordapp.com/attachments/1425781431682076682/1440115588746706984/Imagen_para_el_bot_d.png")
                    msg = await canal.send(embed=embed, view=OraculoOpenView())
                    try:
                        await msg.pin()
                    except Exception:
                        pass

class AutoArchivador(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.archivar_oraculos.start()

    @tasks.loop(hours=24)
    async def archivar_oraculos(self):
        for guild in self.bot.guilds:
            categoria_abiertos = discord.utils.get(guild.categories, name=CATEGORIA_ABIERTOS)
            categoria_cerrados = discord.utils.get(guild.categories, name=CATEGORIA_CERRADOS)
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
                    await canal.edit(category=categoria_cerrados, name=f"auto-{canal.name}")
                    await canal.send("📜 Este Oráculo ha sido archivado automáticamente por inactividad.")

    @archivar_oraculos.before_loop
    async def before_archivar(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(OraculoPanel(bot))
    await bot.add_cog(AutoArchivador(bot))
