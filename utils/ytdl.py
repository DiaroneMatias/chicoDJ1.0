                import yt_dlp as youtube_dl
                import asyncio
                import re
                import os
                import time

                # Configure youtube_dl options
                ytdl_format_options = {
                    'format': 'bestaudio/best',
                    'nocheckcertificate': True,
                    'ignoreerrors': False,
                    'quiet': True,
                    'no_warnings': True,
                    'default_search': 'ytsearch',
                    'source_address': '0.0.0.0',
                    'noplaylist': True,
                    'extract_flat': False,
                    'force_generic_extractor': False,
                    'cookiefile': 'cookies.txt',
                    'external_downloader_args': ['-loglevel', 'panic'],
                    'socket_timeout': 30
                }

                ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

                async def get_stream_url(url):
                    """Get direct stream URL from YouTube link or search term"""
                    ydl_opts = {
                        'format': 'bestaudio/best',
                        'quiet': True,
                        'no_warnings': True,
                        'default_search': 'ytsearch',  # define a pesquisa padrão para YouTube
                        'extract_audio': True,
                        'audio-quality': 0,
                        'prefer_ffmpeg': True,
                        'nocheckcertificate': True,
                        'ignoreerrors': False,
                        'logtostderr': False,
                        'retries': 5,
                        'fragment_retries': 5,
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192',
                        }],
                    }

                    try:
                        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                            # Aguardando 5 segundos antes de cada requisição para evitar limitação de taxa
                            time.sleep(5)

                            # Verifica se a URL é um link do YouTube ou deve ser uma pesquisa
                            if "youtube.com" in url or "youtu.be" in url:
                                info = ydl.extract_info(url, download=False)
                            else:
                                info = ydl.extract_info(f"ytsearch:{url}", download=False)
                                if 'entries' in info:
                                    info = info['entries'][0]

                            # Obter o melhor formato de áudio
                            formats = info.get('formats', [])
                            audio_formats = [f for f in formats if f.get('acodec') != 'none']
                            if audio_formats:
                                best_audio = max(audio_formats, key=lambda f: f.get('abr', 0) if f.get('abr') else 0)
                                return best_audio['url']
                            return None
                    except Exception as e:
                        print(f"Erro ao obter URL de streaming: {e}")
                        return None