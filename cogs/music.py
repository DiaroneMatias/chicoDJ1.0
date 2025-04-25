import asyncio
import discord
from discord.ext import commands
import wavelink
# Removendo a importação problemática - wavelink.ext
import re
import os
from utils.embeds import create_now_playing_embed, create_queue_embed
from utils.ytdl import search_youtube, get_song_info
import random

# Chico Buarque search terms to ensure we prioritize his music
CHICO_SEARCH_TERMS = [
    "Chico Buarque", 
    "Chico Buarque de Hollanda",
    "MPB Chico",
    "Construção Chico Buarque",
    "Roda Viva Chico",
    "A Banda Chico",
    "Vai Passar Chico",
    "Cálice Chico e Gil",
    "Apesar de Você Chico",
    "Geni e o Zepelim"
]

RELATED_ARTISTS = [
    "Caetano Veloso",
    "Gilberto Gil",
    "Milton Nascimento",
    "Maria Bethânia",
    "Gal Costa",
    "Elis Regina",
    "Tom Jobim",
    "Vinicius de Moraes",
    "João Gilberto"
]

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_states = {}
        bot.loop.create_task(self.connect_nodes())
        
    async def connect_nodes(self):
        """Connect to wavelink nodes."""
        await self.bot.wait_until_ready()
        
        try:
            # Lista de servidores Lavalink (incluindo o principal e alternativos)
            all_servers = [
                {"host": "lavalink.clxud.pro", "port": 2333, "password": "youshallnotpass", "secure": False},
                {"host": "lavalink.horizxon.studio", "port": 80, "password": "horizxon.studio", "secure": False},
                {"host": "lava.link", "port": 80, "password": "dismusic", "secure": False},
                {"host": "lavalink.lexnet.cc", "port": 443, "password": "lexn3tl4v4", "secure": True},
                {"host": "lavalink.eliximo.dev", "port": 443, "password": "lava", "secure": True}
            ]
            
            # Flag para rastrear se algum servidor conectou
            connected = False
            
            print("🔄 Tentando conectar aos servidores Lavalink...")
            print("📝 Nota: Servidores Lavalink públicos podem estar temporariamente indisponíveis.")
            print("💡 O bot continuará funcionando com comandos informativos mesmo sem conexão ao Lavalink.")
            
            # Tenta conectar a cada servidor na lista
            for i, server in enumerate(all_servers):
                try:
                    protocol = "https" if server.get("secure", False) else "http"
                    print(f"🔄 Tentando servidor {i+1}: {server['host']}:{server['port']} ({protocol})")
                    
                    node = wavelink.Node(
                        uri=f'{protocol}://{server["host"]}:{server["port"]}',
                        password=server["password"]
                    )
                    
                    # Configurar um timeout mais curto para cada tentativa
                    try:
                        await asyncio.wait_for(
                            wavelink.Pool.connect(nodes=[node], client=self.bot),
                            timeout=5.0  # 5 segundos de timeout para cada servidor
                        )
                        print(f"✅ Conectado com sucesso ao servidor Lavalink {i+1}!")
                        connected = True
                        break
                    except asyncio.TimeoutError:
                        print(f"⏱️ Timeout ao conectar ao servidor {i+1}")
                        continue
                        
                except Exception as e:
                    print(f"❌ Erro no servidor {i+1}: {e}")
                    await asyncio.sleep(0.5)  # Pequena pausa antes de tentar o próximo servidor
                    continue
                        
            if connected:
                print("🎉 Bot conectado a um servidor Lavalink. Comandos de música estão disponíveis!")
            else:
                print("⚠️ Não foi possível conectar a nenhum servidor Lavalink.")
                print("📢 NOTA IMPORTANTE: O bot continuará funcionando, mas os comandos de música não estarão disponíveis.")
                print("💡 Você ainda pode usar os comandos !chico, !discografia e !letra.")
            
            # Spotify integration desativada devido à incompatibilidade de versão
            # Não é necessário para o funcionamento básico do bot
            
        except Exception as e:
            print(f"Erro ao configurar conexão com Lavalink: {e}")
            print("O bot continuará funcionando, mas os comandos de música podem não funcionar corretamente.")
    
    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, node: wavelink.Node):
        """Event fired when a wavelink node is ready."""
        print(f"Node {node.identifier} is ready!")
    
    @commands.Cog.listener()
    async def on_track_start(self, player, track):
        """Event fired when a track starts playing."""
        # Get the original channel where the command was invoked
        if hasattr(player, "text_channel") and player.text_channel:
            embed = create_now_playing_embed(track)
            
            # Create the control buttons
            view = MusicControlView(self.bot, player)
            
            # Store the message for updating later
            if hasattr(player, "controller_message") and player.controller_message:
                try:
                    await player.controller_message.delete()
                except discord.errors.NotFound:
                    pass
                
            player.controller_message = await player.text_channel.send(embed=embed, view=view)
    
    @commands.Cog.listener()
    async def on_track_end(self, player, track, reason):
        """Event fired when a track ends."""
        # If reason is FINISHED, the track ended normally and autoplay should handle the next track
        if reason == "FINISHED" and player.queue.is_empty and hasattr(player, "auto_queue") and not player.auto_queue.is_empty:
            # Get a song from the auto_queue if available
            try:
                next_track = await player.auto_queue.get_wait()
                await player.play(next_track)
            except Exception as e:
                print(f"Erro ao tocar próxima música da auto_queue: {e}")
                pass
    
    @commands.command(name="play", aliases=["p"])
    async def play(self, ctx, *, query=None):
        """Plays a song from YouTube by searching for Chico Buarque or providing a URL."""
        if not ctx.author.voice:
            return await ctx.send("Você precisa estar em um canal de voz para usar este comando!")
        
        try:
            # Check if wavelink is connected to any nodes
            if not wavelink.Pool.nodes:
                await ctx.send("⚠️ Não foi possível conectar ao servidor de música. O desenvolvedor está trabalhando para resolver o problema.\n\nVocê ainda pode usar outros comandos do bot!")
                return
                
            # Get or create a player for the guild
            player: wavelink.Player = ctx.voice_client or await ctx.author.voice.channel.connect(cls=wavelink.Player)
            
            # Store the text channel for later use
            player.text_channel = ctx.channel
            
            # If no query is provided, play a random Chico Buarque song
            if not query:
                random_term = random.choice(CHICO_SEARCH_TERMS)
                await ctx.send(f"Tocando um clássico aleatório de Chico Buarque... 🎵")
                query = random_term
            
            # Check if this is a URL or a search query
            is_url = re.match(r'https?://', query) is not None
            
            try:
                if is_url:
                    # Handle URLs directly
                    tracks = await wavelink.Playable.search(query)
                    if not tracks:
                        return await ctx.send("Não foi possível encontrar essa música. Tente novamente!")
                    track = tracks[0]
                else:
                    # Add "Chico Buarque" to the search query if it's not already there
                    # and doesn't contain any related artist name
                    has_artist_name = False
                    for artist in [*CHICO_SEARCH_TERMS, *RELATED_ARTISTS]:
                        if artist.lower() in query.lower():
                            has_artist_name = True
                            break
                    
                    if not has_artist_name:
                        query = f"{query} Chico Buarque"
                    
                    # Search for tracks
                    tracks = await wavelink.Playable.search(query)
                    
                    if not tracks:
                        return await ctx.send("Não foi possível encontrar essa música. Tente novamente!")
                    
                    track = tracks[0]
                
                # Check if already playing, if so add to queue
                if player.playing:
                    # Add the track to the queue
                    await player.queue.put_wait(track)
                    await ctx.send(f"**{track.title}** foi adicionada à fila.")
                else:
                    # Play the track
                    await player.play(track)
                    await ctx.send(f"Tocando agora: **{track.title}**")
                    
                # Inicializa auto_queue se não existir
                if not hasattr(player, "auto_queue"):
                    player.auto_queue = wavelink.Queue()
                    
                # Suggest auto queue tracks if auto_queue is empty
                if player.auto_queue.is_empty:
                    # Generate auto queue with Chico Buarque songs
                    random_term = random.choice(CHICO_SEARCH_TERMS)
                    recommended = await wavelink.Playable.search(random_term)
                    
                    print(f"Adicionando {len(recommended[:5])} músicas recomendadas à fila automática")
                    for recommended_track in recommended[:5]:  # Add up to 5 recommended tracks
                        try:
                            await player.auto_queue.put_wait(recommended_track)
                        except Exception as e:
                            print(f"Erro ao adicionar música à auto_queue: {e}")
                            pass
                        
            except Exception as e:
                print(f"Erro detalhado ao reproduzir música: {e}")
                await ctx.send(f"Erro ao reproduzir a música: {str(e)}")
                
        except Exception as e:
            print(f"Erro geral no comando play: {e}")
            await ctx.send("⚠️ Não foi possível conectar ao servidor de música. Por favor, tente novamente mais tarde.")
    
    @commands.command(name="search")
    async def search_command(self, ctx, *, query):
        """Search for Chico Buarque songs and choose one to play using YouTube."""
        if not ctx.author.voice:
            return await ctx.send("Você precisa estar em um canal de voz para usar este comando!")
            
        try:
            # First try to use wavelink if available
            if wavelink.Pool.nodes:
                # Try original wavelink search logic
                has_artist_name = False
                for artist in [*CHICO_SEARCH_TERMS, *RELATED_ARTISTS]:
                    if artist.lower() in query.lower():
                        has_artist_name = True
                        break
                        
                if not has_artist_name:
                    query = f"{query} Chico Buarque"
                
                try:
                    tracks = await wavelink.Playable.search(query)
                    
                    if tracks:
                        # Create an embed with the search results
                        embed = discord.Embed(
                            title=f"Resultados da busca para: {query}",
                            description="Selecione uma música para tocar:",
                            color=discord.Color.blue()
                        )
                        
                        # Add up to 5 tracks to the embed
                        for i, track in enumerate(tracks[:5], start=1):
                            duration = f"{int(track.length / 60000)}:{int((track.length / 1000) % 60):02d}"
                            embed.add_field(
                                name=f"{i}. {track.title}",
                                value=f"Duração: {duration}",
                                inline=False
                            )
                        
                        # Use wavelink results if available
                        await ctx.send(embed=embed, view=SearchResultView(ctx, tracks[:5], self))
                        return
                except Exception as e:
                    print(f"Wavelink search failed, falling back to YouTube: {e}")
            
            # Fallback to direct YouTube search
            await ctx.send("🔍 Buscando no YouTube...")
            
            # Use the YouTube search function from utils/ytdl.py
            search_results = await search_youtube(query, max_results=5)
            
            if not search_results:
                return await ctx.send("Não foi possível encontrar músicas com essa busca no YouTube. Tente novamente!")
            
            # Create an embed with the search results
            embed = discord.Embed(
                title=f"Resultados da busca no YouTube para: {query}",
                description="Selecione uma música para tocar:",
                color=discord.Color.blue()
            )
            
            # Add up to 5 videos to the embed
            for i, video in enumerate(search_results, start=1):
                duration = f"{int(video.get('duration', 0) / 60)}:{int(video.get('duration', 0) % 60):02d}" if video.get('duration') else "Desconhecida"
                embed.add_field(
                    name=f"{i}. {video.get('title', 'Título desconhecido')}",
                    value=f"Duração: {duration}",
                    inline=False
                )
                
            # Create and send search results view
            yt_tracks = search_results
            view = SearchResultView(ctx, yt_tracks, self)
            await ctx.send(embed=embed, view=view)
        except Exception as e:
            print(f"Erro ao buscar músicas: {e}")
            await ctx.send(f"Erro ao buscar músicas: {str(e)}")
        
    except Exception as e:
        print(f"Erro geral no comando search: {e}")
        await ctx.send("⚠️ Não foi possível conectar ao servidor de música. Por favor, tente novamente mais tarde.")
    
    @commands.command(name="pause")
    async def pause(self, ctx):
        """Pauses the currently playing song."""
        player = ctx.voice_client
        
        if not player or not player.playing:
            return await ctx.send("Não estou tocando nada no momento!")
        
        if player.paused:
            return await ctx.send("A música já está pausada!")
        
        await player.pause()
        await ctx.send("⏸️ Música pausada.")
    
    @commands.command(name="resume")
    async def resume(self, ctx):
        """Resumes the paused song."""
        player = ctx.voice_client
        
        if not player:
            return await ctx.send("Não estou conectado a um canal de voz!")
        
        if not player.paused:
            return await ctx.send("A música não está pausada!")
        
        await player.resume()
        await ctx.send("▶️ Música retomada.")
    
    @commands.command(name="skip")
    async def skip(self, ctx):
        """Skips the current song."""
        player = ctx.voice_client
        
        if not player or not player.playing:
            return await ctx.send("Não estou tocando nada no momento!")
        
        # Skip the current track
        await player.stop()
        await ctx.send("⏭️ Música pulada.")
    
    @commands.command(name="back")
    async def back(self, ctx):
        """Goes back to the previous song if available."""
        player = ctx.voice_client
        
        if not player or not player.playing:
            return await ctx.send("Não estou tocando nada no momento!")
        
        if not hasattr(player, "history") or not player.history:
            return await ctx.send("Não há músicas anteriores!")
        
        # Get the last track from history
        try:
            prev_track = player.history[-1]
            
            # Stop current track and play the previous one
            await player.stop()
            await player.play(prev_track)
            
            await ctx.send(f"⏮️ Voltando para: **{prev_track.title}**")
        except (IndexError, Exception) as e:
            await ctx.send(f"Não foi possível voltar para a música anterior: {str(e)}")
    
    @commands.command(name="queue", aliases=["q"])
    async def queue(self, ctx):
        """Shows the current song queue."""
        player = ctx.voice_client
        
        if not player or not player.playing:
            return await ctx.send("Não estou tocando nada no momento!")
        
        # Create and send the queue embed
        embed = create_queue_embed(player)
        await ctx.send(embed=embed)
    
    @commands.command(name="shuffle")
    async def shuffle(self, ctx):
        """Shuffles the current queue."""
        player = ctx.voice_client
        
        if not player:
            return await ctx.send("Não estou conectado a um canal de voz!")
        
        if player.queue.is_empty:
            return await ctx.send("A fila está vazia!")
        
        # Shuffle the queue
        player.queue.shuffle()
        await ctx.send("🔀 Fila embaralhada!")
    
    @commands.command(name="stop")
    async def stop(self, ctx):
        """Stops the music and clears the queue."""
        player = ctx.voice_client
        
        if not player:
            return await ctx.send("Não estou conectado a um canal de voz!")
        
        # Clear the queue and stop the player
        player.queue.clear()
        await player.stop()
        await ctx.send("⏹️ Reprodução parada e fila limpa.")
    
    @commands.command(name="now", aliases=["np"])
    async def now_playing(self, ctx):
        """Shows information about the currently playing song."""
        player = ctx.voice_client
        
        if not player or not player.playing:
            return await ctx.send("Não estou tocando nada no momento!")
        
        # Create and send the now playing embed
        embed = create_now_playing_embed(player.current)
        
        # Create the control buttons
        view = MusicControlView(self.bot, player)
        
        await ctx.send(embed=embed, view=view)
    
    @commands.command(name="join")
    async def join(self, ctx):
        """Joins the user's voice channel."""
        if not ctx.author.voice:
            return await ctx.send("Você precisa estar em um canal de voz para usar este comando!")
        
        try:
            # Check if wavelink is connected to any nodes
            if not wavelink.Pool.nodes:
                await ctx.send("⚠️ Não foi possível conectar ao servidor de música. O desenvolvedor está trabalhando para resolver o problema.\n\nVocê ainda pode usar outros comandos do bot!")
                return
                
            # Check if the bot is already in a voice channel
            if ctx.voice_client:
                return await ctx.send("Já estou conectado a um canal de voz!")
            
            try:
                # Join the voice channel
                await ctx.author.voice.channel.connect(cls=wavelink.Player)
                await ctx.send(f"Conectado ao canal: {ctx.author.voice.channel.name}")
            except Exception as e:
                print(f"Erro ao conectar ao canal de voz: {e}")
                await ctx.send(f"Erro ao conectar ao canal de voz: {str(e)}")
        except Exception as e:
            print(f"Erro geral no comando join: {e}")
            await ctx.send("⚠️ Não foi possível conectar ao canal de voz. Por favor, tente novamente mais tarde.")
    
    @commands.command(name="leave", aliases=["disconnect", "dc"])
    async def leave(self, ctx):
        """Leaves the voice channel."""
        player = ctx.voice_client
        
        if not player:
            return await ctx.send("Não estou conectado a um canal de voz!")
        
        # Disconnect from the voice channel
        await player.disconnect()
        await ctx.send("Desconectado do canal de voz.")

    @commands.command(name="volume", aliases=["vol"])
    async def volume(self, ctx, volume: int = None):
        """Sets the volume of the player (0-100)."""
        player = ctx.voice_client
        
        if not player:
            return await ctx.send("Não estou conectado a um canal de voz!")
        
        if volume is None:
            return await ctx.send(f"O volume atual é: **{player.volume}%**")
        
        if not 0 <= volume <= 100:
            return await ctx.send("O volume deve estar entre 0 e 100!")
        
        # Set the volume
        await player.set_volume(volume)
        await ctx.send(f"Volume definido para: **{volume}%**")

class MusicControlView(discord.ui.View):
    def __init__(self, bot, player):
        super().__init__(timeout=None)
        self.bot = bot
        self.player = player
    
    @discord.ui.button(label="⏮️ Anterior", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not hasattr(self.player, "history") or not self.player.history:
            await interaction.response.send_message("Não há músicas anteriores!", ephemeral=True)
            return
        
        try:
            prev_track = self.player.history[-1]
            
            # Stop current track and play the previous one
            await self.player.stop()
            await self.player.play(prev_track)
            
            await interaction.response.send_message(f"⏮️ Voltando para: **{prev_track.title}**", ephemeral=True)
        except (IndexError, Exception) as e:
            await interaction.response.send_message(f"Não foi possível voltar para a música anterior: {str(e)}", ephemeral=True)
    
    @discord.ui.button(label="⏯️ Pause/Play", style=discord.ButtonStyle.primary)
    async def pause_resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.player or not self.player.playing and not self.player.paused:
            await interaction.response.send_message("Não estou tocando nada no momento!", ephemeral=True)
            return
        
        if self.player.paused:
            await self.player.resume()
            await interaction.response.send_message("▶️ Música retomada.", ephemeral=True)
        else:
            await self.player.pause()
            await interaction.response.send_message("⏸️ Música pausada.", ephemeral=True)
    
    @discord.ui.button(label="⏭️ Próxima", style=discord.ButtonStyle.secondary)
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.player or not self.player.playing:
            await interaction.response.send_message("Não estou tocando nada no momento!", ephemeral=True)
            return
        
        # Skip the current track
        await self.player.stop()
        await interaction.response.send_message("⏭️ Música pulada.", ephemeral=True)
    
    @discord.ui.button(label="🔀 Embaralhar", style=discord.ButtonStyle.secondary)
    async def shuffle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.player:
            await interaction.response.send_message("Não estou conectado a um canal de voz!", ephemeral=True)
            return
        
        if self.player.queue.is_empty:
            await interaction.response.send_message("A fila está vazia!", ephemeral=True)
            return
        
        # Shuffle the queue
        self.player.queue.shuffle()
        await interaction.response.send_message("🔀 Fila embaralhada!", ephemeral=True)
    
    @discord.ui.button(label="⏹️ Parar", style=discord.ButtonStyle.danger)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.player:
            await interaction.response.send_message("Não estou conectado a um canal de voz!", ephemeral=True)
            return
        
        # Clear the queue and stop the player
        self.player.queue.clear()
        await self.player.stop()
        await interaction.response.send_message("⏹️ Reprodução parada e fila limpa.", ephemeral=True)

class SearchResultView(discord.ui.View):
    def __init__(self, ctx, tracks, cog):
        super().__init__()
        self.ctx = ctx
        self.tracks = tracks
        self.cog = cog
        self.is_youtube_result = isinstance(tracks, list) and tracks and not isinstance(tracks[0], wavelink.Playable)
    
    @discord.ui.button(label="1", style=discord.ButtonStyle.primary)
    async def button_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._play_track(interaction, 0)
    
    @discord.ui.button(label="2", style=discord.ButtonStyle.primary)
    async def button_2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._play_track(interaction, 1)
    
    @discord.ui.button(label="3", style=discord.ButtonStyle.primary)
    async def button_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._play_track(interaction, 2)
    
    @discord.ui.button(label="4", style=discord.ButtonStyle.primary)
    async def button_4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._play_track(interaction, 3)
    
    @discord.ui.button(label="5", style=discord.ButtonStyle.primary)
    async def button_5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._play_track(interaction, 4)
    
    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.danger)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Busca cancelada.", embed=None, view=None)
    
    async def _play_track(self, interaction, index):
        # Check if the track index is valid
        if index >= len(self.tracks):
            await interaction.response.send_message("Opção inválida!", ephemeral=True)
            return
        
        # Check if the interaction user is the command author
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Apenas quem fez a busca pode selecionar uma música!", ephemeral=True)
            return
        
        track = self.tracks[index]
        
        try:
            if self.is_youtube_result:
                # Handle YouTube result
                await self._play_youtube_track(interaction, track)
            else:
                # Handle Wavelink result
                await self._play_wavelink_track(interaction, track)
        except Exception as e:
            print(f"Erro ao reproduzir música: {e}")
            await interaction.response.edit_message(content=f"Erro ao reproduzir a música: {str(e)}", embed=None, view=None)
    
    async def _play_youtube_track(self, interaction, video_data):
        """Handle playing a track directly from YouTube data."""
        await interaction.response.edit_message(content=f"🎵 Preparando: **{video_data.get('title', 'Música do YouTube')}**...", embed=None, view=None)
        
        try:
            # Connect to voice if not already connected
            if not self.ctx.voice_client:
                vc = await self.ctx.author.voice.channel.connect()
            else:
                vc = self.ctx.voice_client
            
            # Get the video URL (for direct YouTube results this is in a different format)
            video_url = video_data.get('webpage_url') or f"https://www.youtube.com/watch?v={video_data.get('id')}"
            
            # Try to use wavelink if it's available
            if wavelink.Pool.nodes:
                try:
                    # Try to search and play with wavelink
                    tracks = await wavelink.Playable.search(video_url)
                    if tracks:
                        player = vc if isinstance(vc, wavelink.Player) else await self.ctx.author.voice.channel.connect(cls=wavelink.Player)
                        player.text_channel = self.ctx.channel
                        
                        # Play or queue
                        if player.playing:
                            await player.queue.put_wait(tracks[0])
                            await interaction.followup.send(f"**{tracks[0].title}** foi adicionada à fila.")
                        else:
                            await player.play(tracks[0])
                            await interaction.followup.send(f"Tocando agora: **{tracks[0].title}**")
                        return
                except Exception as e:
                    print(f"Erro ao reproduzir via wavelink, tentando fallback: {e}")
            
            # Fallback to direct YouTube playback using yt-dlp if wavelink fails
            import yt_dlp as youtube_dl
            with youtube_dl.YoutubeDL({'format': 'bestaudio/best'}) as ydl:
                info = ydl.extract_info(video_url, download=False)
                url = info['url']
                title = info.get('title', 'Música do YouTube')
                
                if vc.is_playing():
                    vc.stop()
                
                vc.play(discord.FFmpegPCMAudio(url))
                await interaction.followup.send(f"Tocando agora: **{title}**")
                
        except Exception as e:
            print(f"Erro ao reproduzir do YouTube: {e}")
            await interaction.followup.send(f"Erro ao reproduzir a música do YouTube: {str(e)}")

    async def _play_wavelink_track(self, interaction, track):
        """Handle playing a track using wavelink."""
        # Get or create a player for the guild
        player: wavelink.Player = self.ctx.voice_client or await self.ctx.author.voice.channel.connect(cls=wavelink.Player)
        
        # Store the text channel for later use
        player.text_channel = self.ctx.channel
        
        # Check if already playing, if so add to queue
        if player.playing:
            # Add the track to the queue
            await player.queue.put_wait(track)
            await interaction.response.edit_message(content=f"**{track.title}** foi adicionada à fila.", embed=None, view=None)
        else:
            # Play the track
            await player.play(track)
            await interaction.response.edit_message(content=f"Tocando agora: **{track.title}**", embed=None, view=None)

async def setup(bot):
    """Setup function to add the cog to the bot."""
    await bot.add_cog(Music(bot))
