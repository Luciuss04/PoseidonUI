import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio
import os
import ctypes
import ctypes.util
from bot.themes import Theme

try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
    SPOTIPY_AVAILABLE = True
except ImportError:
    SPOTIPY_AVAILABLE = False
    print("⚠️ [Musica] La librería 'spotipy' no está instalada. El soporte para Spotify será limitado (vía yt-dlp).")

# FFMPEG Options - Stable Configuration
# Removed aggressive buffering/reconnects that cause zombie processes
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin',
    'options': '-vn'
}

AUDIO_FILTERS = {
    "normal": "",
    "bassboost": "bass=g=15:f=110:w=0.3",
    "nightcore": "asetrate=48000*1.25,aresample=48000",
    "vaporwave": "asetrate=48000*0.8,aresample=48000",
    "8d": "apulsator=hz=0.125",
    "soft": "lowpass=f=3000"
}

# YTDL Options
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': False,
    'default_search': 'auto',
    'quiet': True,
    'extract_flat': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'no_warnings': True,
    'socket_timeout': 30, # Increased timeout
    'source_address': '0.0.0.0', # Forced IPv4 to avoid IPv6 routing lags
    'http_chunk_size': 10485760, # 10MB chunk size for stable streaming
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.google.com/',
        'Accept-Language': 'en-US,en;q=0.9',
    },
    'cookiefile': 'cookies.txt',
}

class MusicPlayerView(discord.ui.View):
    def __init__(self, voice_client):
        super().__init__(timeout=None)
        self.voice_client = voice_client

    @discord.ui.button(style=discord.ButtonStyle.primary, emoji="⏯️")
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.voice_client.is_paused():
            self.voice_client.resume()
            await interaction.response.send_message("▶️ Reanudado", ephemeral=True)
        elif self.voice_client.is_playing():
            self.voice_client.pause()
            await interaction.response.send_message("⏸️ Pausado", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No hay nada sonando", ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji="⏭️")
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.voice_client.is_playing() or self.voice_client.is_paused():
            self.voice_client.stop()
            await interaction.response.send_message("⏭️ Saltado", ephemeral=True)
        else:
             await interaction.response.send_message("❌ No hay nada para saltar", ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.danger, emoji="⏹️")
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.voice_client:
            await self.voice_client.disconnect()
            await interaction.response.send_message("🛑 Desconectado", ephemeral=True)
            self.stop() # Stop the view

class Musica(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.queues = {} # {guild_id: [url, url, ...]}
        self.titles = {} # {guild_id: [title, title, ...]}
        self.voice_clients = {} # {guild_id: voice_client}
        self.loop_mode = {} # {guild_id: bool}
        self.active_filters = {} # {guild_id: "filter_name"}
        self.player_messages = {} # {guild_id: discord.Message}

        # Grupo de comandos de música
        music_group = app_commands.Group(name="musica", description="Comandos de música y reproducción")
        
        # Intentar cargar Opus manualmente para entornos Linux/Docker
        if not discord.opus.is_loaded():
            try:
                # Lista de nombres comunes de librerías Opus en Linux
                opus_libs = ['libopus.so.0', 'libopus.so', 'libopus-0.so', 'libopus.so.0.8.0']
                for lib in opus_libs:
                    try:
                        discord.opus.load_opus(lib)
                        print(f"✅ [Musica] Opus cargado manualmente: {lib}")
                        break
                    except Exception:
                        continue
                
                if not discord.opus.is_loaded():
                     # Intentar buscar con ctypes como último recurso
                    lib_path = ctypes.util.find_library('opus')
                    if lib_path:
                        discord.opus.load_opus(lib_path)
                        print(f"✅ [Musica] Opus cargado via find_library: {lib_path}")
            except Exception as e:
                print(f"⚠️ [Musica] No se pudo cargar Opus automáticamente: {e}")

    @music_group.command(name="debug", description="Diagnóstico del sistema de música")
    async def musica_debug(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # 1. Check Opus
        opus_status = "✅ Cargado" if discord.opus.is_loaded() else "❌ No cargado (Voice no funcionará)"
        
        # 2. Check FFMPEG
        import shutil
        ffmpeg_path = shutil.which("ffmpeg")
        ffmpeg_status = f"✅ Encontrado: {ffmpeg_path}" if ffmpeg_path else "❌ NO ENCONTRADO en PATH"
        
        # 3. Check YTDL
        ytdl_status = "⏳ Probando..."
        try:
            with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                ydl.extract_info("https://www.youtube.com/watch?v=jNQXAC9IVRw", download=False)
            ytdl_status = "✅ Funciona (Extracción básica)"
        except Exception as e:
            ytdl_status = f"❌ Error: {str(e)}"

        # 4. Check Connectivity
        import socket
        try:
            socket.create_connection(("www.google.com", 80), timeout=2)
            conn_status = "✅ Conexión OK"
        except:
            conn_status = "❌ Sin conexión a Internet"

        # 5. Check PyNaCl
        try:
            import nacl
            nacl_status = f"✅ Instalado (v{nacl.__version__})"
        except ImportError:
            nacl_status = "❌ NO INSTALADO (Voz imposible)"

        # 6. Test UDP Socket (Vital for Voice)
        udp_status = "❓ No probado"
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(('', 0)) # Try to bind to any random port
            sock.close()
            udp_status = "✅ Socket UDP creado OK"
        except Exception as e:
            udp_status = f"❌ Error UDP: {e}"

        embed = discord.Embed(title="🕵️ Diagnóstico de Música", color=Theme.get_color(interaction.guild.id, 'warning'))
        embed.add_field(name="LibOpus", value=opus_status, inline=False)
        embed.add_field(name="PyNaCl", value=nacl_status, inline=False)
        embed.add_field(name="FFmpeg", value=ffmpeg_status, inline=False)
        embed.add_field(name="yt-dlp", value=ytdl_status, inline=False)
        embed.add_field(name="UDP Check", value=udp_status, inline=False)
        embed.add_field(name="Internet", value=conn_status, inline=False)
        
        await interaction.followup.send(embed=embed)

    def _get_queue(self, guild_id):
        if guild_id not in self.queues:
            self.queues[guild_id] = []
            self.titles[guild_id] = []
        return self.queues[guild_id], self.titles[guild_id]

    async def _play_next(self, interaction: discord.Interaction):
        if interaction.guild.id not in self.queues or not self.queues[interaction.guild.id]:
            return
        
        # Check loop mode
        if self.loop_mode.get(interaction.guild.id, False):
            # Simple loop implementation could go here
            pass

        # Robust voice client retrieval
        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_connected():
            # Try to reconnect if possible, or abort
            if interaction.user.voice:
                try:
                    voice_client = await interaction.user.voice.channel.connect()
                except:
                    return # Cannot connect, abort
            else:
                return # No voice client and user not in voice

        url = self.queues[interaction.guild.id].pop(0)
        title = self.titles[interaction.guild.id].pop(0)

        try:
            # Notify user - SILENT MODE
            # await interaction.channel.send(f"🔍 Procesando: **{title}**...", delete_after=10)

            # Re-extract real audio URL just before playing to avoid expiration
            # Use specific options for audio extraction
            play_opts = YTDL_OPTIONS.copy()
            play_opts['extract_flat'] = False # Need full extraction now
            
            def run_full_extraction():
                with yt_dlp.YoutubeDL(play_opts) as ydl:
                    return ydl.extract_info(url, download=False)
            
            info = await self.bot.loop.run_in_executor(None, run_full_extraction)

            if 'entries' in info:
                info = info['entries'][0]
                
            url2 = info['url']

            # Find ffmpeg explicitly
            import shutil
            ffmpeg_path = shutil.which("ffmpeg")
            if not ffmpeg_path:
                raise Exception("FFMPEG no encontrado en el sistema")

            # Create source with explicit executable
            # METHOD 1: Direct FFMPEG Audio (More robust than from_probe for long URLs)
            
            # Apply Filters
            current_filter_name = self.active_filters.get(interaction.guild.id, "normal")
            filter_str = AUDIO_FILTERS.get(current_filter_name, "")
            
            final_options = FFMPEG_OPTIONS['options']
            if filter_str:
                final_options += f' -af "{filter_str}"'

            source = discord.FFmpegPCMAudio(
                url2,
                executable=ffmpeg_path,
                before_options=FFMPEG_OPTIONS['before_options'],
                options=final_options
            )
            
            # METHOD 2 (Fallback): If above fails, we might need to stream via stdin (complex)
            # But usually FFmpegPCMAudio is safer than from_probe for raw URLs
            
            # Volume control
            source = discord.PCMVolumeTransformer(source, volume=0.5)
            
            def after_playing(error):
                if error:
                    print(f"Error playing: {error}")
                
                # Check connection before recursion
                vc = interaction.guild.voice_client
                if not vc or not vc.is_connected():
                    return

                # Recursive call to play next
                coro = self._play_next(interaction)
                fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
                try:
                    fut.result()
                except:
                    pass

            if voice_client.is_playing():
                voice_client.stop()
                await asyncio.sleep(0.5) # Allow FFMPEG process to terminate cleanly
                
            voice_client.play(source, after=after_playing)
            
            # Create graphic panel
            embed = discord.Embed(
                color=Theme.get_color(interaction.guild.id, 'secondary') # Cyan Poseidon
            )
            embed.set_author(name="Poseidon Music Player", icon_url=self.bot.user.display_avatar.url)
            
            description = f"### 🔱 [{title}]({info.get('webpage_url', url2)})\n"
            description += f"**▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬**\n\n"
            description += f"⏱️ **Tiempo:** `{info.get('duration_string', '??:??')}`\n"
            description += f"🎵 **Invocador:** {interaction.user.mention}\n"
            description += f"🎛️ **Filtro:** `{current_filter_name.capitalize()}`\n"
            description += f"📡 **Estado:** `Reproduciendo en el Olimpo`\n"
            
            embed.description = description
            
            if 'thumbnail' in info:
                embed.set_thumbnail(url=info['thumbnail'])
            
            embed.set_footer(text=Theme.get_footer_text(interaction.guild.id), icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
            
            view = MusicPlayerView(voice_client)
            
            # Logic to reuse the panel
            guild_id = interaction.guild.id
            message_sent = False
            
            if guild_id in self.player_messages:
                try:
                    msg = self.player_messages[guild_id]
                    await msg.edit(embed=embed, view=view)
                    message_sent = True
                except (discord.NotFound, discord.HTTPException):
                    # Message deleted or not accessible, we will send a new one
                    pass

            if not message_sent:
                msg = await interaction.channel.send(embed=embed, view=view)
                self.player_messages[guild_id] = msg
            
        except Exception as e:
            print(f"Error in _play_next: {e}")
            import traceback
            traceback.print_exc()
            await interaction.channel.send(f"❌ Error al reproducir la siguiente canción: {e}")
            
            # Avoid infinite recursion loop on error
            await asyncio.sleep(1) 
            if voice_client and voice_client.is_connected():
                 await self._play_next(interaction)

    @music_group.command(name="play", description="Reproduce música de YouTube o Spotify")
    @app_commands.describe(busqueda="Nombre de la canción o URL")
    async def play(self, interaction: discord.Interaction, busqueda: str):
        # 1. Defer immediately
        await interaction.response.defer()
        
        # 2. Check user voice state
        if not interaction.user.voice:
            await interaction.followup.send("❌ Debes estar en un canal de voz.")
            return

        channel = interaction.user.voice.channel
        
        # 3. Connect to voice channel (with feedback)
        voice_client = interaction.guild.voice_client
        
        if not voice_client:
            # Silent connection attempt (or edit original defer)
            try:
                # Use wait_for to prevent infinite hang
                # self_deaf=True is CRITICAL for some hosts to complete handshake
                voice_client = await asyncio.wait_for(
                    channel.connect(timeout=20, reconnect=True, self_deaf=True), 
                    timeout=25
                )
            except asyncio.TimeoutError:
                await interaction.followup.send("❌ Timeout: No pude conectar al canal de voz.")
                return
            except Exception as e:
                await interaction.followup.send(f"❌ Error al conectar: {e}")
                return
        elif voice_client.channel != channel:
            await voice_client.move_to(channel)

        # 4. Search and Queue
        try:
            # Notify user quietly
            status_msg = await interaction.followup.send(f"🔎 Buscando: **{busqueda}**...", ephemeral=True)
            # Check for Spotify
            if "open.spotify.com" in busqueda:
                # Try to get credentials
                client_id = os.getenv("SPOTIFY_CLIENT_ID")
                client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
                
                # Check if library is available
                if not SPOTIPY_AVAILABLE:
                     client_id = None # Force fallback

                if not client_id or not client_secret:
                    # FALLBACK: Use yt-dlp for metadata extraction if no keys
                    await interaction.followup.send("⚠️ Sin claves de API (Usando modo lento/fallback)...")
                    try:
                        def extract_spotify_no_api():
                            # Extract metadata using yt-dlp
                            with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True, 'ignoreerrors': True}) as ydl:
                                return ydl.extract_info(busqueda, download=False)
                        
                        info = await self.bot.loop.run_in_executor(None, extract_spotify_no_api)
                        
                        tracks_to_add = []
                        if 'entries' in info:
                            # Playlist/Album
                            for entry in info['entries']:
                                if entry:
                                    # Try to get artist/title, fallback to title only
                                    artist = entry.get('artist') or entry.get('creator') or ''
                                    title = entry.get('title') or entry.get('track') or ''
                                    if title:
                                        query = f"{artist} - {title}" if artist else title
                                        tracks_to_add.append(query)
                            await interaction.channel.send(f"✅ Spotify Fallback: **{len(tracks_to_add)}** canciones encontradas.")
                        else:
                            # Single track
                            artist = info.get('artist') or info.get('creator') or ''
                            title = info.get('title') or info.get('track') or ''
                            if title:
                                query = f"{artist} - {title}" if artist else title
                                tracks_to_add.append(query)
                                await interaction.channel.send(f"✅ Spotify Fallback: **{title}**")

                        # Add to queue
                        q, t = self._get_queue(interaction.guild.id)
                        for query in tracks_to_add:
                            q.append(f"ytsearch:{query}")
                            t.append(query)
                            
                        if not voice_client.is_playing():
                            await self._play_next(interaction)
                        return

                    except Exception as e:
                        await interaction.followup.send(f"❌ Error en modo sin claves: {e}. El dueño debe configurar SPOTIFY_CLIENT_ID.")
                        return
                
                await interaction.followup.send(f"🔎 Analizando lista de Spotify (API)...")
                
                try:
                    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret))
                    
                    tracks_to_add = []
                    
                    if "track" in busqueda:
                        track = sp.track(busqueda)
                        search_query = f"{track['artists'][0]['name']} - {track['name']}"
                        tracks_to_add.append(search_query)
                        await interaction.channel.send(f"✅ Canción detectada: **{track['name']}**")
                        
                    elif "playlist" in busqueda:
                        results = sp.playlist_tracks(busqueda)
                        tracks = results['items']
                        # Handle pagination if needed, but start with first 100
                        count = 0
                        for item in tracks:
                            track = item['track']
                            if track:
                                search_query = f"{track['artists'][0]['name']} - {track['name']}"
                                tracks_to_add.append(search_query)
                                count += 1
                        await interaction.channel.send(f"✅ Playlist detectada: **{count}** canciones añadidas a la cola.")
                        
                    elif "album" in busqueda:
                        results = sp.album_tracks(busqueda)
                        tracks = results['items']
                        count = 0
                        for track in tracks:
                            search_query = f"{track['artists'][0]['name']} - {track['name']}"
                            tracks_to_add.append(search_query)
                            count += 1
                        await interaction.channel.send(f"✅ Álbum detectado: **{count}** canciones añadidas a la cola.")
                    
                    # Add all to queue
                    q, t = self._get_queue(interaction.guild.id)
                    for query in tracks_to_add:
                        q.append(f"ytsearch:{query}")
                        t.append(query) # Placeholder title
                        
                    # Play if not playing
                    if not voice_client.is_playing():
                        await self._play_next(interaction)
                    
                    return # Exit successfully
                    
                except Exception as e:
                    print(f"Spotify Error: {e}")
                    await interaction.followup.send(f"❌ Error al procesar Spotify: {e}")
                    return

            # Normal YouTube Search
            
            # Helper function for search
            def run_search():
                with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
                    if busqueda.startswith("http"):
                        return ydl.extract_info(busqueda, download=False)
                    else:
                        return ydl.extract_info(f"ytsearch1:{busqueda}", download=False)

            info = await self.bot.loop.run_in_executor(None, run_search)
            
            # Unified handling for Playlist (entries) or Single Video
            entries = []
            if 'entries' in info:
                entries = info['entries']
            else:
                entries = [info]

            if not entries:
                await interaction.followup.send(f"❌ No encontré nada para: {busqueda}", ephemeral=True)
                return

            # Add to queue
            q, t = self._get_queue(interaction.guild.id)
            added_count = 0
            
            for entry in entries:
                if not entry: continue
                url = entry.get('url')
                title = entry.get('title', 'Canción sin título')
                
                # If using flat extraction, url might be just ID for some versions
                # Ensure we have a valid playable reference
                if not url.startswith("http"):
                    url = f"https://www.youtube.com/watch?v={url}"
                
                q.append(url)
                t.append(title)
                added_count += 1
            
            if added_count > 1:
                await interaction.channel.send(f"✅ Playlist de YouTube: **{added_count}** canciones añadidas.")
            elif added_count == 1:
                await interaction.channel.send(f"✅ **{t[-1]}** añadido a la cola.")
            
            # 5. Playback
            if not voice_client.is_playing():
                await self._play_next(interaction)
            else:
                pass # Already playing

        except Exception as e:
            print(f"Error in play command: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(f"❌ Error al buscar la canción: {e}", ephemeral=True)

    @music_group.command(name="stop", description="Detiene la música y desconecta")
    async def stop(self, interaction: discord.Interaction):
        if not interaction.guild.voice_client:
            await interaction.response.send_message("❌ No estoy conectado.", ephemeral=True)
            return
        
        # Clear queue
        if interaction.guild.id in self.queues:
            self.queues[interaction.guild.id] = []
            self.titles[interaction.guild.id] = []
            
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("🛑 Música detenida y desconectado.")

    @music_group.command(name="skip", description="Salta la canción actual")
    async def skip(self, interaction: discord.Interaction):
        if not interaction.guild.voice_client or not interaction.guild.voice_client.is_playing():
            await interaction.response.send_message("❌ No hay nada reproduciéndose.", ephemeral=True)
            return
            
        interaction.guild.voice_client.stop() # This triggers after_playing which calls _play_next
        await interaction.response.send_message("⏭️ Canción saltada.")

    @music_group.command(name="queue", description="Muestra la cola de reproducción")
    async def queue(self, interaction: discord.Interaction):
        queue, titles = self._get_queue(interaction.guild.id)
        if not titles:
            await interaction.response.send_message("📭 La cola está vacía.", ephemeral=True)
            return
            
        desc = ""
        for i, title in enumerate(titles[:10], 1):
            desc += f"{i}. {title}\n"
            
        if len(titles) > 10:
            desc += f"\n... y {len(titles)-10} más."
            
        embed = discord.Embed(title="🎵 Cola de Reproducción", description=desc, color=Theme.get_color(interaction.guild.id, 'secondary'))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pause", description="Pausa la música")
    async def pause(self, interaction: discord.Interaction):
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.pause()
            await interaction.response.send_message("⏸️ Música pausada.")
        else:
            await interaction.response.send_message("❌ No hay música reproduciéndose.", ephemeral=True)

    @music_group.command(name="resume", description="Reanuda la música")
    async def resume(self, interaction: discord.Interaction):
        if interaction.guild.voice_client and interaction.guild.voice_client.is_paused():
            interaction.guild.voice_client.resume()
            await interaction.response.send_message("▶️ Música reanudada.")
        else:
            await interaction.response.send_message("❌ La música no está pausada.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Musica(bot))
