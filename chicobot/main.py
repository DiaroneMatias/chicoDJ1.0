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

# View de Controles
def build_view(ctx):
    view = View(timeout=None)

    async def control_interaction(interaction):
        if interaction.user != ctx.author:
            await interaction.response.send_message("⚠️ Apenas quem iniciou a reprodução pode controlar!", ephemeral=True)
            return
        await interaction.response.defer()

    # Botões
    buttons = [
        ('⏮️ Anterior', discord.ButtonStyle.secondary, 'previous'),
        ('⏸️ Pausar', discord.ButtonStyle.danger, 'pause'),
        ('▶️ Retomar', discord.ButtonStyle.success, 'resume'),
        ('⏭️ Próxima', discord.ButtonStyle.primary, 'skip'),
        ('⏹️ Parar', discord.ButtonStyle.danger, 'stop')
    ]

    for label, style, action in buttons:
        button = Button(label=label, style=style)
        button.callback = lambda i, a=action: handle_controls(i, a, ctx)
        view.add_item(button)

    return view

async def handle_controls(interaction, action, ctx):
    global voice_client, is_paused, current_index
    
    if action == 'pause' and voice_client.is_playing():
        voice_client.pause()
        is_paused = True
        await interaction.followup.send("⏸️ Música pausada!")
    elif action == 'resume' and is_paused:
        voice_client.resume()
        is_paused = False
        await interaction.followup.send("▶️ Música retomada!")
    elif action == 'skip':
        voice_client.stop()
        await interaction.followup.send("⏭️ Pulando música...")
    elif action == 'previous':
        current_index = max(0, current_index - 2)
        voice_client.stop()
        await interaction.followup.send("⏮️ Voltando para música anterior...")
    elif action == 'stop':
        await stop_player(ctx)
        await interaction.followup.send("⏹️ Reprodução interrompida!")

# Funções do Player
async def play_next(ctx):
    global music_queue, current_index, voice_client, is_paused

    if current_index >= len(music_queue):
        await ctx.send("🎉 Fim da playlist!")
        return

    url, title, file_path = music_queue[current_index]
    current_index += 1

    try:
        voice_client.play(discord.FFmpegPCMAudio(file_path, executable=ffmpeg_path, **FFMPEG_OPTIONS),
        after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
        
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
        try:
            os.remove(os.path.join('downloads', file))
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
        # Conectar ao canal de voz
        if not ctx.author.voice:
            await ctx.send("⚠️ Você precisa estar em um canal de voz!")
            return
            
        voice_client = await ctx.author.voice.channel.connect()

        # Configurar busca
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

        # Processar buscas
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
        print(f"Erro geral: {str(e)}")
        await ctx.send(f"⚠️ Erro crítico: {str(e)}")

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
    # ... (mantenha o mesmo código de letras) ...

@bot.command()
async def chico(ctx):
    # ... (mantenha o mesmo código de informações) ...

@bot.command()
async def discografia(ctx):
    # ... (mantenha o mesmo código de discografia) ...

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user.name}")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="!ajuda"))

bot.run(TOKEN)
