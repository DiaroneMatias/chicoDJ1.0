import discord
from discord.ext import commands
from discord.ui import Button, View
import yt_dlp as youtube_dl
import asyncio
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path='discord.env')
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

ffmpeg_path = r"C:\\ffmpeg\\bin\\ffmpeg.exe"

music_queue = []
current_index = 0
voice_client = None
is_paused = False

playlist = [
    "Os Saltimbancos - Bicharia",
    "Os Saltimbancos - Um dia de cão",
    "Os Saltimbancos - História de uma gata",
    "Os Saltimbancos - O jumento",
    "Os Saltimbancos - Todos juntos"
]

def build_view(ctx):
    view = View()

    async def pause_callback(interaction):
        global voice_client, is_paused
        if voice_client and voice_client.is_playing():
            voice_client.pause()
            is_paused = True

    async def resume_callback(interaction):
        global voice_client, is_paused
        if voice_client and is_paused:
            voice_client.resume()
            is_paused = False

    async def skip_callback(interaction):
        global voice_client
        if voice_client and voice_client.is_playing():
            voice_client.stop()

    async def previous_callback(interaction):
        global current_index, voice_client
        current_index = max(0, current_index - 2)
        if voice_client and voice_client.is_playing():
            voice_client.stop()

    def add_button(label, style, callback):
        button = Button(label=label, style=style)

        async def wrapper(interaction):
            if interaction.user == ctx.author:
                await callback(interaction)
        button.callback = wrapper
        view.add_item(button)

    add_button("⏮️ Anterior", discord.ButtonStyle.secondary, previous_callback)
    add_button("⏸️ Pausar", discord.ButtonStyle.danger, pause_callback)
    add_button("▶️ Retomar", discord.ButtonStyle.success, resume_callback)
    add_button("⏭️ Próxima", discord.ButtonStyle.primary, skip_callback)

    return view

async def play_next(ctx):
    global music_queue, current_index, voice_client

    if current_index >= len(music_queue):
        await ctx.send("Fim da playlist! 🐾")
        return

    url, title, file_path = music_queue[current_index]
    current_index += 1

    # Verificar se o bot já está no canal de voz, e conectar se necessário
    try:
        if voice_client is None or not voice_client.is_connected():
            voice_channel = ctx.author.voice.channel if ctx.author.voice else None
            if not voice_channel:
                await ctx.send("Você não está em um canal de voz. 😕")
                return
            voice_client = await voice_channel.connect(timeout=30)  # Aumentando o timeout
    except asyncio.TimeoutError:
        await ctx.send("⏳ Não consegui me conectar ao canal de voz. Tente novamente mais tarde.")
        print("Timeout ao tentar conectar ao canal de voz.")
        return

    def after_playing(error):
        fut = asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
        try:
            fut.result()
        except Exception as e:
            print(f"Erro no after_playing: {e}")

    voice_client.play(discord.FFmpegPCMAudio(file_path, executable=ffmpeg_path), after=after_playing)
    await ctx.send(f"🎵 Tocando agora: **{title}**", view=build_view(ctx))

@bot.command()
async def play(ctx, *, arg=None):
    global music_queue, current_index, voice_client
    music_queue = []
    current_index = 0

    if voice_client and voice_client.is_connected():
        await voice_client.disconnect()
        voice_client = None

    titles = playlist if arg == "playlist" else [arg]

    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'default_search': 'ytsearch',
        'outtmpl': 'downloads/%(id)s.%(ext)s'
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        for title in titles:
            info = ydl.extract_info(f"ytsearch:{title} Chico Buarque", download=True)['entries'][0]
            file_path = ydl.prepare_filename(info)
            music_queue.append((info['webpage_url'], info['title'], file_path))

    await play_next(ctx)

@bot.command()
async def pause(ctx):
    global voice_client, is_paused
    if voice_client and voice_client.is_playing():
        voice_client.pause()
        is_paused = True
        await ctx.send("⏸️ Música pausada!", view=build_view(ctx))

bot.run(TOKEN)
