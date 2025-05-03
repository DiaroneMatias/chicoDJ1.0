import discord
from discord.ext import commands
from discord.ui import Button, View
import yt_dlp as youtube_dl
import asyncio
import os
import sys
import subprocess
import time
from dotenv import load_dotenv

# Configuração inicial de verificação de dependências
load_dotenv()

try:
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
    print("FFmpeg detectado:\n", result.stdout)
except Exception as e:
    print(f"Erro ao verificar FFmpeg: {str(e)}")

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
ffmpeg_path = 'ffmpeg'  # Assume que está no PATH do sistema

# Verificar/criar pasta de downloads
if not os.path.exists('downloads'):
    os.makedirs('downloads')

# Configuração do yt-dlp
ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
    'socket_timeout': 30,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'referer': 'https://www.youtube.com/',
}

# Estado do Player
music_queue = []
current_index = 0
voice_client = None
is_paused = False


# Funções dos botões
async def button_previous(interaction, ctx):
    global current_index, voice_client
    current_index = max(0, current_index - 2)
    voice_client.stop()
    await interaction.response.send_message("⏮️ Voltando para música anterior...")

async def button_pause(interaction):
    global voice_client, is_paused
    if voice_client.is_playing():
        voice_client.pause()
        is_paused = True
        await interaction.response.send_message("⏸️ Música pausada!")

async def button_resume(interaction):
    global voice_client, is_paused
    if is_paused:
        voice_client.resume()
        is_paused = False
        await interaction.response.send_message("▶️ Música retomada!")

async def button_skip(interaction):
    global voice_client
    voice_client.stop()
    await interaction.response.send_message("⏭️ Pulando música...")

async def button_stop(interaction, ctx):
    await stop_player(ctx)
    await interaction.response.send_message("⏹️ Reprodução interrompida!")


# View de Controles
def build_view(ctx):
    view = View(timeout=None)

    buttons = [
        Button(label='⏮️ Anterior', style=discord.ButtonStyle.secondary, callback=lambda i: button_previous(i, ctx)),
        Button(label='⏸️ Pausar', style=discord.ButtonStyle.danger, callback=button_pause),
        Button(label='▶️ Retomar', style=discord.ButtonStyle.success, callback=button_resume),
        Button(label='⏭️ Próxima', style=discord.ButtonStyle.primary, callback=button_skip),
        Button(label='⏹️ Parar', style=discord.ButtonStyle.danger, callback=lambda i: button_stop(i, ctx))
    ]

    for button in buttons:
        view.add_item(button)

    return view


# Funções do Player
async def play_next(ctx):
    global music_queue, current_index, voice_client, is_paused

    if current_index >= len(music_queue):
        await ctx.send("🎉 Fim da playlist!")
        return

    url, title, file_path = music_queue[current_index]
    current_index += 1

    try:
        voice_client.play(
            discord.FFmpegPCMAudio(
                file_path,
                executable=ffmpeg_path,
                **FFMPEG_OPTIONS
            ),
            after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
        )
        
        await ctx.send(f"🎶 Tocando: **{title}**", view=build_view(ctx))
    except Exception as e:
        print(f"Erro na reprodução: {str(e)}")
        await ctx.send(f"⚠️ Erro ao reproduzir {title}")
        await play_next(ctx)

   
async def stop_player(ctx):
    global voice_client, music_queue, current_index, is_paused
    music_queue = []
    current_index = 0
    is_paused = False
    
    if voice_client:
        await voice_client.disconnect()
        voice_client = None
    
    for file in os.listdir('downloads'):
        file_path = os.path.join('downloads', file)
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Erro ao limpar arquivos: {str(e)}")


# Comandos do Bot
@bot.command()
async def play(ctx, *, query=None):
    global voice_client, music_queue

    if not query:
        await ctx.send("❗ Use: !play <nome da música> ou !play playlist")
        return

    try:
        if not ctx.author.voice:
            await ctx.send("⚠️ Você precisa estar em um canal de voz!")
            return

        if voice_client and voice_client.is_connected():
            await voice_client.move_to(ctx.author.voice.channel)
        else:
            voice_client = await ctx.author.voice.channel.connect()

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
            search_queries = [query]
            await ctx.send(f"🔍 Procurando: {query}...")

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            for search in search_queries:
                try:
                    info = ydl.extract_info(f"ytsearch:{search}", download=True)['entries'][0]
                    file_path = ydl.prepare_filename(info).replace('.webm', '.mp3').replace('.m4a', '.mp3')
                    
                    if not os.path.exists(file_path):
                        raise Exception("Arquivo não encontrado após download")
                        
                    music_queue.append((info['webpage_url'], info['title'], file_path))
                except Exception as e:
                    print(f"Erro no download: {str(e)}")
                    await ctx.send(f"⚠️ Não foi possível baixar: {search}")

        if music_queue:
            await ctx.send(f"✅ {len(music_queue)} músicas carregadas!")
            await play_next(ctx)
        else:
            await ctx.send("⚠️ Nenhuma música encontrada!")

    except Exception as e:
        print(f"Erro geral: {str(e)}", file=sys.stderr)
        await ctx.send(f"⚠️ Ocorreu um erro inesperado: {str(e)}")


@bot.command()
async def stop(ctx):
    await stop_player(ctx)
    await ctx.send("⏹️ Player totalmente reiniciado!")


@bot.command()
async def skip(ctx):
    global voice_client
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await ctx.send("⏭️ Pulando para próxima música...")


@bot.command()
async def letra(ctx, musica):
    pass  # Código omitido


@bot.command()
async def chico(ctx):
    pass  # Código omitido


@bot.command()
async def discografia(ctx):
    pass  # Código omitido


@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user.name}")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="!ajuda"))


bot.run(TOKEN)
