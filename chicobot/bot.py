import subprocess

try:
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
    print("FFmpeg detectado:\n", result.stdout)
except FileNotFoundError:
    print("FFmpeg **NÃO** encontrado.")

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
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")


# Verificar o PyNaCl para áudio
try:
    import nacl.secret
    print("PyNaCl está instalado corretamente")
except ImportError:
    print("AVISO: PyNaCl não está instalado, que é necessário para áudio em Discord")

load_dotenv(dotenv_path='discord.env')
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Detectar caminho do ffmpeg
ffmpeg_path = None
possible_paths = [
    # Linux (Replit)
    "/nix/store/3zc5jbvqzrn8zmva4fx5p0nh4yy03wk4-ffmpeg-6.1.1-bin/bin/ffmpeg",
    "/usr/bin/ffmpeg", 
    "/usr/local/bin/ffmpeg",
    # Windows
    r"C:\\ffmpeg\\bin\\ffmpeg.exe"
]

# Tentar localizar o ffmpeg
for path in possible_paths:
    if os.path.exists(path):
        ffmpeg_path = path
        print(f"FFmpeg encontrado: {ffmpeg_path}")
        break

if not ffmpeg_path:
    print("AVISO: FFmpeg não encontrado em caminhos comuns. Tentando usar 'ffmpeg' diretamente.")
    ffmpeg_path = "ffmpeg"

# Verificar se o diretório downloads existe, criar se necessário
if not os.path.exists('downloads'):
    os.makedirs('downloads')
    print("Diretório de downloads criado.")
else:
    print(f"Diretório de downloads disponível: {os.path.abspath('downloads')}")
    files = os.listdir('downloads')
    if files:
        print(f"Arquivos disponíveis ({len(files)}): {', '.join(files[:5])}{'...' if len(files) > 5 else ''}")

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
            await interaction.response.send_message("⏸️ Música pausada!")

    async def resume_callback(interaction):
        global voice_client, is_paused
        if voice_client and is_paused:
            voice_client.resume()
            is_paused = False
            await interaction.response.send_message("▶️ Música retomada!")

    async def skip_callback(interaction):
        global voice_client
        if voice_client and voice_client.is_playing():
            voice_client.stop()
            await interaction.response.send_message("⏭️ Pulando música...")

    async def previous_callback(interaction):
        global current_index, voice_client
        current_index = max(0, current_index - 2)
        if voice_client and voice_client.is_playing():
            voice_client.stop()
            await interaction.response.send_message("⏮️ Voltando para música anterior...")

    async def stop_callback(interaction):
        # Usar o mesmo código do comando stop
        global music_queue, current_index, is_paused, voice_client

        # Resetar todas as variáveis do player
        music_queue = []
        current_index = 0
        is_paused = False

        # Desconectar do voice client
        if voice_client and voice_client.is_connected():
            if voice_client.is_playing():
                voice_client.stop()
            await voice_client.disconnect()
            voice_client = None

        # Limpar a pasta de downloads
        try:
            if os.path.exists('downloads'):
                msg = "🗑️ Limpando pasta de downloads..."
                await interaction.response.send_message(msg)
                deleted = 0
                for file in os.listdir('downloads'):
                    file_path = os.path.join('downloads', file)
                    if os.path.isfile(file_path):
                        try:
                            os.remove(file_path)
                            deleted += 1
                        except Exception as e:
                            print(f"Erro ao remover arquivo {file}: {e}")
                await ctx.send(f"✅ {deleted} arquivos removidos com sucesso.")
        except Exception as e:
            await ctx.send(f"⚠️ Erro ao limpar pasta de downloads: {e}")

        await ctx.send("⏹️ Reprodução interrompida e fila esvaziada.")

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
    add_button("⏹️ Parar", discord.ButtonStyle.danger, stop_callback)

    return view

async def play_next(ctx):
    """Versão simulada que não depende do FFmpeg no Replit."""
    global music_queue, current_index, voice_client, is_paused

    # Reset status de pausa para a nova música
    is_paused = False

    # Verificar se terminamos a playlist
    if current_index >= len(music_queue):
        await ctx.send("Fim da playlist! 🐾")
        await ctx.send("Obrigado por ouvir Chico Buarque através do ChicoDJ!")
        if voice_client and voice_client.is_connected():
            await voice_client.disconnect()
            voice_client = None
        return

    # Obter informações da próxima música
    url, title, file_path = music_queue[current_index]
    current_index += 1

    # Verificar se o arquivo existe (apenas para registrar)
    if not os.path.exists(file_path):
        print(f"Arquivo não encontrado: {file_path}, mas continuando em modo simulado")
    else:
        print(f"Arquivo encontrado: {file_path} ({os.path.getsize(file_path) / (1024*1024):.2f} MB)")

    # Simular a reprodução sem usar FFmpeg (ambiente Replit tem problemas com áudio)
    emojis = ["🎵", "🎶", "🎸", "🎹", "🎷", "🎺", "🥁"]
    random_emoji = emojis[int(time.time()) % len(emojis)]

    # Enviar mensagem indicando início da música
    message = await ctx.send(f"{random_emoji} **Tocando:** {title}")

    # Exibir os botões de controle
    controls_view = build_view(ctx)
    await ctx.send("**Controles:**", view=controls_view)

    # Exibir mensagem sobre o modo simulado
    await ctx.send("**ℹ️ Nota:** Devido a restrições do ambiente Replit, o áudio está sendo simulado.")

    # Mostrar letra da música, se disponível
    letra_disponivel = False
    song_title_lower = title.lower()
    music_name = ""

    # Palavras-chave para verificar
    if "bicharia" in song_title_lower:
        letra_disponivel = True
        music_name = "bicharia"
    elif "jumento" in song_title_lower:
        letra_disponivel = True
        music_name = "jumento"
    elif "todos juntos" in song_title_lower:
        letra_disponivel = True
        music_name = "todos juntos"

    if letra_disponivel:
        await ctx.send(f"Veja a letra desta música com **!letra {music_name}**")

    # Aguardar um tempo simulando a duração da música (30 segundos)
    await asyncio.sleep(30)

    # Verificar se ainda estamos "simulando" tocar (não pausado ou foi pulado)
    if not is_paused:
        # Ir para a próxima música
        await ctx.send(f"✅ **{title}** terminou de tocar!")
        await play_next(ctx)

@bot.command()
async def play(ctx, *, arg=None):
    global music_queue, current_index, voice_client

    try:
        music_queue = []
        current_index = 0

        if voice_client and voice_client.is_connected():
            await voice_client.disconnect()
            voice_client = None

        # Determinar quais músicas tocar
        if arg == "playlist":
            titles = playlist
            await ctx.send("🎭 Preparando a playlist dos Saltimbancos...")
        elif arg:
            titles = [arg]
            await ctx.send(f"🔍 Buscando: **{arg}**...")
        else:
            await ctx.send("Por favor, especifique uma música ou use `!play playlist` para ouvir Os Saltimbancos.")
            return

        # Configuração do youtube-dl para formato PCM (mais compatível com discord.py)
        ydl_opts = {
            'format': 'bestaudio/best',
            'extract_audio': True,
            'audio_format': 'wav',  # Tentar formato não comprimido mais simples
            'outtmpl': 'downloads/%(id)s.%(ext)s',
            'noplaylist': True,
            'quiet': False,
            'default_search': 'ytsearch',
            'socket_timeout': 30,
            'nocheckcertificate': True,
            # Sem pós-processamento complexo
        }

        # Tentar encontrar arquivos válidos disponíveis na pasta downloads para usar como fallbacks
        print("Buscando arquivos disponíveis para fallback...")
        fallback_songs = {}
        available_files = []

        if os.path.exists('downloads'):
            # Verificar quais arquivos estão disponíveis
            for file in os.listdir('downloads'):
                if file.endswith('.mp3') or file.endswith('.webm') or file.endswith('.m4a') or file.endswith('.mp4'):
                    file_path = os.path.join('downloads', file)
                    if os.path.getsize(file_path) > 100 * 1024:  # Arquivos maiores que 100 KB
                        available_files.append(file_path)
                        print(f"Arquivo válido para fallback: {file_path}")

        # Se houver arquivos disponíveis, usar o primeiro como fallback para todas as músicas
        if available_files:
            for title in playlist:
                fallback_songs[title] = available_files[0]
                print(f"Configurado fallback para '{title}': {available_files[0]}")
        else:
            print("Nenhum arquivo de fallback encontrado!")

        # Baixar e adicionar músicas à fila
        successful_songs = 0
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            for title in titles:
                try:
                    # Mostrar progresso
                    await ctx.send(f"🔄 Buscando: **{title}**...")

                    # Tentar buscar no YouTube
                    search_query = f"ytsearch:{title} Chico Buarque"
                    info = ydl.extract_info(search_query, download=True)['entries'][0]
                    file_path = ydl.prepare_filename(info)

                    # Verificar todos os formatos possíveis (wav, mp3, webm, m4a)
                    base_path = file_path.rsplit('.', 1)[0]
                    for ext in ['.wav', '.mp3', '.webm', '.m4a']:
                        possible_path = base_path + ext
                        if os.path.exists(possible_path):
                            file_path = possible_path
                            print(f"Arquivo encontrado: {file_path}")
                            break

                    # Se nenhum arquivo for encontrado, imprimir aviso
                    if not os.path.exists(file_path):
                        print(f"AVISO: Nenhum arquivo encontrado com o base path: {base_path}")

                    # Verificar se o arquivo existe
                    if os.path.exists(file_path):
                        music_queue.append((info['webpage_url'], info['title'], file_path))
                        print(f"Adicionado à fila: {info['title']} ({file_path})")
                        successful_songs += 1
                    else:
                        raise FileNotFoundError(f"Arquivo baixado não encontrado: {file_path}")

                except Exception as e:
                    print(f"Erro ao buscar/baixar música '{title}': {e}")

                    # Verificar se temos um fallback
                    if title in fallback_songs:
                        fallback_path = fallback_songs[title]
                        # Verificar explicitamente se o arquivo de fallback existe
                        if os.path.exists(fallback_path):
                            await ctx.send(f"⚠️ Erro ao buscar '{title}' no YouTube. Usando versão offline.")
                            music_queue.append((None, title, fallback_path))
                            print(f"Usando fallback para '{title}': {fallback_path}")
                        else:
                            print(f"Arquivo de fallback não encontrado: {fallback_path}")
                            await ctx.send(f"⚠️ Não foi possível encontrar o arquivo para '{title}'")
                    else:
                        await ctx.send(f"⚠️ Erro ao buscar/baixar música '{title}': {str(e)}")

                # Adicionar um pequeno atraso entre as requisições para evitar rate limiting
                await asyncio.sleep(1)

        # Iniciar reprodução se houver músicas na fila
        if music_queue:
            await ctx.send(f"📋 Adicionadas {len(music_queue)} músicas à fila!")
            await play_next(ctx)
        else:
            await ctx.send("Não foi possível encontrar nenhuma música para adicionar à fila.")
            if voice_client and voice_client.is_connected():
                await voice_client.disconnect()
                voice_client = None
    except Exception as e:
        print(f"Erro geral no comando play: {e}")
        await ctx.send(f"Ocorreu um erro: {str(e)}")

@bot.command()
async def pause(ctx):
    global is_paused
    if current_index > 0 and current_index <= len(music_queue):
        is_paused = True
        await ctx.send("⏸️ Música pausada!", view=build_view(ctx))
    else:
        await ctx.send("Não há música tocando no momento.")

@bot.command()
async def resume(ctx):
    global is_paused
    if is_paused:
        is_paused = False
        await ctx.send("▶️ Música retomada!", view=build_view(ctx))
    else:
        await ctx.send("A música não está pausada.")

@bot.command()
async def skip(ctx):
    global is_paused

    # Verificar se há uma música atual
    if current_index > 0 and current_index <= len(music_queue):
        is_paused = False  # Resetar o status de pausa
        await ctx.send("⏭️ Pulando para a próxima música...")

        # Verificar se há mais músicas na fila
        if current_index >= len(music_queue):
            await ctx.send("Fim da playlist! 🐾")
        else:
            # Ir para a próxima música
            await play_next(ctx)
    else:
        await ctx.send("Não há música tocando no momento.")

@bot.command()
async def queue(ctx):
    global music_queue, current_index
    if not music_queue:
        await ctx.send("A fila de reprodução está vazia.")
        return

    queue_list = "🎵 **Fila de reprodução:**\n"
    for i, (_, title, _) in enumerate(music_queue):
        prefix = "▶️ " if i == current_index - 1 else f"{i + 1}. "
        queue_list += f"{prefix}{title}\n"

    await ctx.send(queue_list)

@bot.command()
async def stop(ctx):
    global music_queue, current_index, is_paused, voice_client

    # Resetar todas as variáveis do player
    music_queue = []
    current_index = 0
    is_paused = False

    # Desconectar do voice client (se estiver conectado)
    if voice_client and voice_client.is_connected():
        if voice_client.is_playing():
            voice_client.stop()
        await voice_client.disconnect()
        voice_client = None

    # Limpar a pasta de downloads
    try:
        if os.path.exists('downloads'):
            await ctx.send("🗑️ Limpando pasta de downloads...")
            deleted = 0
            for file in os.listdir('downloads'):
                file_path = os.path.join('downloads', file)
                if os.path.isfile(file_path):
                    try:
                        os.remove(file_path)
                        deleted += 1
                    except Exception as e:
                        print(f"Erro ao remover arquivo {file}: {e}")
            await ctx.send(f"✅ {deleted} arquivos removidos com sucesso.")
    except Exception as e:
        await ctx.send(f"⚠️ Erro ao limpar pasta de downloads: {e}")

    await ctx.send("⏹️ Reprodução interrompida e fila esvaziada.")

@bot.command(name="chico")
async def chico_info(ctx):
    """Exibe informações sobre Chico Buarque"""
    embed = discord.Embed(
        title="🎭 Chico Buarque",
        description="**Francisco Buarque de Hollanda** (Rio de Janeiro, 19 de junho de 1944), conhecido como Chico Buarque, é um músico, dramaturgo, escritor e ator brasileiro.",
        color=0xf1c40f
    )

    embed.add_field(
        name="Carreira",
        value="Chico iniciou sua carreira musical na década de 1960, durante o movimento da MPB. Consagrou-se como um dos maiores nomes da música brasileira, com canções que retratam a realidade social e política do Brasil.",
        inline=False
    )

    embed.add_field(
        name="Prêmios",
        value="Vencedor de diversos prêmios, incluindo Grammy Latino, Prêmio Jabuti de Literatura e o Prêmio Camões, o mais importante prêmio literário de língua portuguesa.",
        inline=False
    )

    embed.add_field(
        name="Os Saltimbancos",
        value="Adaptação do conto 'Os Músicos de Bremen' dos irmãos Grimm, em parceria com Sérgio Bardotti e Luís Enríquez Bacalov. Uma fábula musical infantil que retrata a união dos oprimidos contra seus opressores.",
        inline=False
    )

    embed.set_footer(text="Use !discografia para ver algumas das obras principais | !play playlist para ouvir Os Saltimbancos")

    await ctx.send(embed=embed)

@bot.command(name="discografia")
async def discografia(ctx):
    """Exibe algumas obras principais da discografia de Chico Buarque"""
    embed = discord.Embed(
        title="📀 Discografia Selecionada de Chico Buarque",
        description="Alguns dos álbuns mais importantes da carreira de Chico Buarque:",
        color=0x3498db
    )

    discografia = [
        {"nome": "Chico Buarque de Hollanda (1966)", "desc": "Álbum de estreia com 'A Banda' e 'Olê Olá'"},
        {"nome": "Construção (1971)", "desc": "Obra-prima com as faixas 'Construção' e 'Deus lhe Pague'"},
        {"nome": "Os Saltimbancos (1977)", "desc": "Álbum infantil que adaptou 'Os Músicos de Bremen'"},
        {"nome": "Chico Buarque (1978)", "desc": "Com sucessos como 'Cálice' e 'Pedaço de Mim'"},
        {"nome": "Paratodos (1993)", "desc": "Homenagem a diversos artistas brasileiros"},
        {"nome": "As Cidades (1998)", "desc": "Com 'Carioca' e 'Iracema'"},
        {"nome": "Caravanas (2017)", "desc": "Seu último álbum de inéditas lançado até agora"},
    ]

    for album in discografia:
        embed.add_field(
            name=album["nome"],
            value=album["desc"],
            inline=False
        )

    embed.set_footer(text="Use !play seguido do nome de uma música para ouvir | !chico para mais informações")

    await ctx.send(embed=embed)

@bot.command(name="letra")
async def letra(ctx, *, musica=None):
    """Exibe a letra de algumas músicas selecionadas de Chico Buarque"""
    if not musica:
        await ctx.send("Por favor, especifique uma música. Exemplo: `!letra bicharia`")
        return

    musica = musica.lower().strip()

    letras = {
        "bicharia": {
            "titulo": "Bicharia (Os Saltimbancos)",
            "letra": """Au, au, au. Hi-ho, hi-ho
Miau, miau, miau. Cocorocó
Bicharia, bicharada,
Bicharia, bicharada.
É gato, é cachorro,
É galinha, é jumento,
Bicho não é gente,
Diga logo o nome do teu bicho,
Senão eu te arrebento..."""
        },
        "jumento": {
            "titulo": "O Jumento (Os Saltimbancos)",
            "letra": """Atenção cidadãos, aqui é o dono do circo Alaklan a falar
Para vocês inocentes
Essa história de bicho é conversa, é conversa fiada
Bicho é coisa pra jaula, luxo de gente metida
Vou já mandar meus capangas acertar
Os paus nas suas costas galopantes
Eu vou mostrar com quantos paus se faz uma cangalha"""
        },
        "todos juntos": {
            "titulo": "Todos Juntos (Os Saltimbancos)",
            "letra": """Todos juntos somos fortes
Somos flecha e somos arco
Todos nós no mesmo barco
Não há nada pra temer
- Ao meu lado há um amigo
Que é preciso proteger
Todos juntos somos fortes
Não há nada pra temer..."""
        }
    }

    # Verificar se a música está disponível
    for key, value in letras.items():
        if musica in key:
            embed = discord.Embed(
                title=f"📝 {value['titulo']}",
                description=value['letra'],
                color=0x2ecc71
            )
            embed.set_footer(text="Use !play playlist para ouvir a música | !chico para mais informações")
            await ctx.send(embed=embed)
            return

    await ctx.send(f"Desculpe, não tenho a letra de '{musica}'. Tente uma das seguintes: bicharia, jumento, todos juntos.")

@bot.command(name="limpar")
async def limpar_downloads(ctx):
    """Limpa os arquivos da pasta downloads sem interromper a reprodução atual"""

    # Criar uma lista dos arquivos em reprodução atual para não apagá-los
    arquivos_em_uso = []
    if music_queue and current_index > 0 and current_index <= len(music_queue):
        _, _, file_path = music_queue[current_index - 1]
        arquivos_em_uso.append(file_path)

    # Limpar a pasta de downloads
    deleted = 0
    skipped = 0
    try:
        if os.path.exists('downloads'):
            await ctx.send("🗑️ Limpando pasta de downloads...")
            for file in os.listdir('downloads'):
                file_path = os.path.join('downloads', file)
                if os.path.isfile(file_path):
                    if file_path in arquivos_em_uso:
                        skipped += 1
                        print(f"Arquivo em uso, não será apagado: {file_path}")
                        continue
                    try:
                        os.remove(file_path)
                        deleted += 1
                    except Exception as e:
                        print(f"Erro ao remover arquivo {file}: {e}")

            # Mensagem informativa
            if deleted > 0:
                await ctx.send(f"✅ {deleted} arquivos removidos com sucesso.")
            if skipped > 0:
                await ctx.send(f"ℹ️ {skipped} arquivos em uso não foram removidos.")
            if deleted == 0 and skipped == 0:
                await ctx.send("📂 Nenhum arquivo encontrado para remover.")
        else:
            await ctx.send("📂 Pasta de downloads não encontrada.")
    except Exception as e:
        await ctx.send(f"⚠️ Erro ao limpar pasta de downloads: {e}")

@bot.command(name="debug")
async def debug_audio(ctx):
    """Verifica se os arquivos de áudio estão disponíveis e exibe informações de diagnóstico"""
    response = "📊 **Diagnóstico do Sistema de Áudio**\n\n"

    # Verificar diretório downloads
    response += "📁 **Diretório Downloads:**\n"
    if os.path.exists("downloads"):
        files = os.listdir("downloads")
        if files:
            response += f"- {len(files)} arquivos encontrados\n"
            # Listar alguns dos arquivos encontrados (limitado a 5)
            for file in files[:5]:
                file_path = os.path.join("downloads", file)
                size = os.path.getsize(file_path) / (1024 * 1024)  # em MB
                response += f"- {file} ({size:.2f} MB)\n"
        else:
            response += "- Diretório vazio\n"
    else:
        response += "- ❌ Diretório não encontrado\n"

    # Verificar FFmpeg
    response += "\n🔧 **FFmpeg:**\n"
    if os.path.exists(ffmpeg_path):
        response += f"- ✅ FFmpeg encontrado em: {ffmpeg_path}\n"
    else:
        response += f"- ❌ FFmpeg NÃO encontrado em: {ffmpeg_path}\n"

    # Verificar conexão com canal de voz
    response += "\n🎤 **Conexão de Voz:**\n"
    if voice_client and voice_client.is_connected():
        response += f"- ✅ Conectado ao canal: {voice_client.channel.name}\n"
        if voice_client.is_playing():
            response += "- 🎵 Reproduzindo áudio agora\n"
        elif is_paused:
            response += "- ⏸️ Áudio pausado\n"
        else:
            response += "- ⏹️ Não está reproduzindo áudio\n"
    else:
        response += "- ❌ Não conectado a nenhum canal de voz\n"

    # Verificar fila de reprodução
    response += "\n📋 **Fila de Reprodução:**\n"
    if music_queue:
        response += f"- ✅ {len(music_queue)} músicas na fila\n"
        response += f"- 🎵 Música atual: {current_index}/{len(music_queue)}\n"
    else:
        response += "- ❌ Fila vazia\n"

    await ctx.send(response)

@bot.event
async def on_ready():
    print(f"Bot está online como {bot.user.name}")
    print(f"Bot está pronto para uso! Use !play playlist para começar a ouvir música.")

bot.run(TOKEN)
