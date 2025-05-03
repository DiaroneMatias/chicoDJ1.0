import discord
from discord.ext import commands
from discord.ui import Button, View
import yt_dlp as youtube_dl
import asyncio
import os
import sys
import subprocess
import time
import traceback  # Adicionado para logs detalhados
from dotenv import load_dotenv

# Configuração inicial de verificação de dependências
load_dotenv()

# Verificação do FFmpeg com tratamento melhorado
try:
    ffmpeg_path = subprocess.check_output(["which", "ffmpeg"]).decode().strip()
    print(f"FFmpeg detectado em: {ffmpeg_path}")
except Exception as e:
    ffmpeg_path = '/usr/bin/ffmpeg'  # Fallback para Railway
    print(f"Usando FFmpeg padrão em: {ffmpeg_path}")

try:
    import nacl.secret
    print("PyNaCl está instalado corretamente")
except ImportError:
    print("AVISO: PyNaCl não está instalado")

# Configuração do Bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Configurações Globais
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("Erro: Token do bot não configurado. Verifique o arquivo .env.")
    sys.exit(1)

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -sn'
}

# Configuração do yt-dlp atualizada
ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'quiet': False,
    'no_warnings': False,
    'default_search': 'ytsearch',
    'socket_timeout': 30,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'cookiefile': 'cookies.txt',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'referer': 'https://www.youtube.com/',
    'extractor_args': {
        'youtube': {
            'player_client': ['android_embedded'],
            'skip': ['dash', 'hls']
        }
    },
}

# Estado do Player
music_queue = []
current_index = 0
voice_client = None
is_paused = False

# Funções dos botões (atualizadas com verificação de canal de voz)
async def button_previous(interaction, ctx):
    global current_index, voice_client
    if interaction.user.voice and interaction.user.voice.channel == voice_client.channel:
        current_index = max(0, current_index - 2)
        voice_client.stop()
        await interaction.response.send_message("⏮️ Voltando para música anterior...")
    else:
        await interaction.response.send_message("⚠️ Você precisa estar no mesmo canal de voz!", ephemeral=True)

async def button_pause(interaction):
    global voice_client, is_paused
    if interaction.user.voice and interaction.user.voice.channel == voice_client.channel:
        if voice_client.is_playing():
            voice_client.pause()
            is_paused = True
            await interaction.response.send_message("⏸️ Música pausada!")
    else:
        await interaction.response.send_message("⚠️ Você precisa estar no mesmo canal de voz!", ephemeral=True)

async def button_resume(interaction):
    global voice_client, is_paused
    if interaction.user.voice and interaction.user.voice.channel == voice_client.channel:
        if is_paused:
            voice_client.resume()
            is_paused = False
            await interaction.response.send_message("▶️ Música retomada!")
    else:
        await interaction.response.send_message("⚠️ Você precisa estar no mesmo canal de voz!", ephemeral=True)

async def button_skip(interaction):
    global voice_client
    if interaction.user.voice and interaction.user.voice.channel == voice_client.channel:
        voice_client.stop()
        await interaction.response.send_message("⏭️ Pulando música...")
    else:
        await interaction.response.send_message("⚠️ Você precisa estar no mesmo canal de voz!", ephemeral=True)

async def button_stop(interaction, ctx):
    if interaction.user.voice and interaction.user.voice.channel == voice_client.channel:
        await stop_player(ctx)
        await interaction.response.send_message("⏹️ Reprodução interrompida!")
    else:
        await interaction.response.send_message("⚠️ Você precisa estar no mesmo canal de voz!", ephemeral=True)

# View de Controles
def build_view(ctx):
    view = View(timeout=None)
    # [...] (mesma implementação anterior)
    return view

# Funções do Player (com tratamento de erro melhorado)
async def play_next(ctx):
    global music_queue, current_index, voice_client, is_paused

    if current_index >= len(music_queue):
        await ctx.send("🎉 Fim da playlist!")
        return

    try:
        url, title, file_path = music_queue[current_index]
        current_index += 1

        # Verificação adicional do arquivo
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        voice_client.play(
            discord.FFmpegPCMAudio(
                source=file_path,
                executable=ffmpeg_path,
                **FFMPEG_OPTIONS
            ),
            after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
        )
        
        await ctx.send(f"🎶 Tocando: **{title}**", view=build_view(ctx))

    except Exception as e:
        error_msg = f"Erro na reprodução: {str(e)}"
        print(traceback.format_exc())
        await ctx.send(f"⚠️ {error_msg}")
        await play_next(ctx)  # Tenta próxima música mesmo com erro

# Função play atualizada com busca otimizada
@bot.command()
async def play(ctx, *, query=None):
    global voice_client, music_queue

    if not query:
        await ctx.send("❗ Use: !play <nome da música> ou !play playlist")
        return

    try:
        # Verificação de canal de voz
        if not ctx.author.voice:
            await ctx.send("⚠️ Você precisa estar em um canal de voz!")
            return

    except Exception as e:
        if "cookies" in str(e).lower():
            error_msg = """🔒 **Erro de Autenticação:**
             O YouTube está bloqueando requisições automáticas!
            Por favor, peça ao administrador para:
            1. Atualizar o arquivo cookies.txt
            2. Verificar as permissões
            """
            await ctx.send(error_msg)
        else:
            await ctx.send(f"❌ Erro desconhecido: `{type(e).__name__}`")
    
        print(f"ERRO CRÍTICO: {traceback.format_exc()}")


    
        # Conexão/redirecionamento do bot
        channel = ctx.author.voice.channel
        if voice_client:
            if voice_client.channel != channel:
                await voice_client.move_to(channel)
        else:
            voice_client = await channel.connect()

        # Construção da query de busca
        if query.lower() == "playlist":
            search_queries = [
                "Os Saltimbancos - Bicharia",
                "Os Saltimbancos - Um dia de cão",
                "Os Saltimbancos - História de uma gata",
                "Os Saltimbancos - O jumento",
                "Os Saltimbancos - Todos juntos"
            ]
            await ctx.send("🎭 Carregando playlist dos Saltimbancos...")
        else:
            # Adiciona o artista padrão para melhorar os resultados
            search_queries = [f"{query} Chico Buarque"] if "saltimbancos" not in query.lower() else [query]

        # Processamento das músicas
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            for search in search_queries:
                try:
                    await ctx.send(f"🔍 Buscando: _{search}_...")
                    
                    # Busca com timeout
                    info = await asyncio.wait_for(
                        bot.loop.run_in_executor(None, lambda: ydl.extract_info(
                            f"ytsearch:{search}", download=True
                        )['entries'][0]),
                        timeout=30
                    )

                    # Verificação dos resultados
                    if not info:
                        raise Exception("Nenhum resultado encontrado")

                    # Processamento do arquivo
                    file_path = ydl.prepare_filename(info)
                    file_path = file_path.replace('.webm', '.mp3').replace('.m4a', '.mp3')

                    if not os.path.exists(file_path):
                        raise Exception(f"Arquivo não gerado: {file_path}")

                    music_queue.append((info['webpage_url'], info['title'], file_path))
                    await ctx.send(f"✅ Adicionado: {info['title']}")

                except Exception as e:
                    error_type = type(e).__name__
                    full_error = f"{error_type}: {str(e)}"
                    await ctx.send(f"❌ **Erro ao processar _{search}_:**\n`{full_error}`")
                    print(f"ERRO: {traceback.format_exc()}")

        # Inicia reprodução se houver músicas
        if music_queue:
            await play_next(ctx)
        else:
            await ctx.send("⚠️ Nenhuma música válida encontrada!")

    except Exception as e:
        error_msg = f"Erro geral: {str(e)}"
        print(traceback.format_exc())
        await ctx.send(f"⚠️ Erro crítico: {error_msg}")

# [...] (outros comandos mantidos)

bot.run(TOKEN)
