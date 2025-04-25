import discord
import datetime

def create_now_playing_embed(track):
    """
    Create an embed for the currently playing track.
    
    Args:
        track: The wavelink track object
        
    Returns:
        discord.Embed: The formatted embed
    """
    duration = f"{int(track.length / 60000)}:{int((track.length / 1000) % 60):02d}"
    
    embed = discord.Embed(
        title="🎵 Tocando Agora",
        description=f"**{track.title}**",
        color=discord.Color.blue(),
        url=track.uri if hasattr(track, 'uri') else None
    )
    
    # Add track information
    embed.add_field(name="Duração", value=duration, inline=True)
    
    # Add thumbnail if available
    if hasattr(track, 'thumbnail') and track.thumbnail:
        embed.set_thumbnail(url=track.thumbnail)
    
    # Add author if available
    author = getattr(track, 'author', None) or "Chico Buarque"
    embed.add_field(name="Artista", value=author, inline=True)
    
    # Add footer with Chico Buarque reference
    embed.set_footer(text="ChicoDJ - O melhor de Chico Buarque no Discord!")
    
    # Add timestamp
    embed.timestamp = datetime.datetime.now()
    
    return embed

def create_queue_embed(player):
    """
    Create an embed for the current queue.
    
    Args:
        player: The wavelink player object
        
    Returns:
        discord.Embed: The formatted embed
    """
    embed = discord.Embed(
        title="🎶 Fila de Reprodução",
        color=discord.Color.blue()
    )
    
    # Add current track
    if player.current:
        duration = f"{int(player.current.length / 60000)}:{int((player.current.length / 1000) % 60):02d}"
        embed.add_field(
            name="Tocando Agora",
            value=f"**{player.current.title}** `[{duration}]`",
            inline=False
        )
    
    # Add upcoming tracks
    if player.queue.is_empty:
        embed.add_field(
            name="Próximas na Fila",
            value="Não há músicas na fila. Use !play para adicionar mais músicas!",
            inline=False
        )
    else:
        queue_list = []
        position = 1
        
        for track in player.queue:
            duration = f"{int(track.length / 60000)}:{int((track.length / 1000) % 60):02d}"
            queue_list.append(f"`{position}.` **{track.title}** `[{duration}]`")
            position += 1
            
            # Limit to 10 tracks in the embed
            if position > 10:
                queue_list.append(f"*...e mais {len(player.queue) - 10} músicas*")
                break
        
        embed.add_field(
            name=f"Próximas na Fila ({len(player.queue)} músicas)",
            value="\n".join(queue_list),
            inline=False
        )
    
    # Add auto queue information if available
    if hasattr(player, 'auto_queue') and not player.auto_queue.is_empty:
        embed.add_field(
            name="Chico Buarque Sugerido",
            value=f"Mais {len(player.auto_queue)} músicas de Chico Buarque serão tocadas automaticamente após a fila atual.",
            inline=False
        )
    
    # Add footer with instructions
    embed.set_footer(text="Use !play para adicionar mais músicas, !shuffle para embaralhar a fila, ou !skip para pular para a próxima música.")
    
    # Add timestamp
    embed.timestamp = datetime.datetime.now()
    
    return embed

def create_search_results_embed(query, results):
    """
    Create an embed for search results.
    
    Args:
        query (str): The search query
        results (list): List of track results
        
    Returns:
        discord.Embed: The formatted embed
    """
    embed = discord.Embed(
        title=f"🔎 Resultados para: {query}",
        description="Selecione uma música para tocar:",
        color=discord.Color.blue()
    )
    
    # Add results to the embed
    for i, track in enumerate(results, start=1):
        duration = f"{int(track.length / 60000)}:{int((track.length / 1000) % 60):02d}"
        embed.add_field(
            name=f"{i}. {track.title}",
            value=f"Duração: {duration}",
            inline=False
        )
    
    # Add footer
    embed.set_footer(text="Clique nos botões abaixo para selecionar uma música.")
    
    # Add timestamp
    embed.timestamp = datetime.datetime.now()
    
    return embed
