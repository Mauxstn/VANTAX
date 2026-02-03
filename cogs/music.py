import discord
import asyncio
import youtube_dl
import random
from discord.ext import commands
import json
from datetime import datetime

# YouTube DL options
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'options': '-vn',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class MusicPlayer:
    def __init__(self):
        self.queue = []
        self.current = None
        self.voice_client = None
        self.loop_mode = "off"  # off, track, queue
        self.volume = 0.5

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration')
        self.thumbnail = data.get('thumbnail')
        self.uploader = data.get('uploader')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        
        if 'entries' in data:
            data = data['entries'][0]
            
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players = {}

    def get_player(self, guild):
        if guild.id not in self.players:
            self.players[guild.id] = MusicPlayer()
        return self.players[guild.id]

    @commands.command(name="play")
    async def play(self, ctx, *, url):
        """YouTube/Spotify Integration"""
        player = self.get_player(ctx.guild)
        
        if not ctx.author.voice:
            await ctx.send("Du musst in einem Voice-Channel sein!")
            return
            
        if not ctx.voice_client:
            await ctx.author.voice.channel.connect()
            
        async with ctx.typing():
            try:
                player = self.get_player(ctx.guild)
                
                if player.current is None:
                    player.current = await YTDLSource.from_url(url, loop=self.bot.loop)
                    ctx.voice_client.play(player.current, after=lambda e: self.play_next(ctx))
                    
                    embed = discord.Embed(
                        title="🎵 Jetzt spielt",
                        description=f"**{player.current.title}**",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="Dauer", value=f"{player.current.duration // 60}:{player.current.duration % 60:02d}")
                    embed.add_field(name="Uploader", value=player.current.uploader)
                    embed.set_thumbnail(url=player.current.thumbnail)
                    embed.set_footer(text=f"Requested by {ctx.author.name}")
                    await ctx.send(embed=embed)
                else:
                    player.queue.append(url)
                    embed = discord.Embed(
                        title="🎵 Zur Warteschlange hinzugefügt",
                        description=f"**{url}**",
                        color=discord.Color.blue()
                    )
                    embed.set_footer(text=f"In Warteschlange: {len(player.queue)}")
                    await ctx.send(embed=embed)
                    
            except Exception as e:
                await ctx.send(f"Fehler beim Abspielen: {e}")

    @commands.command(name="queue")
    async def queue(self, ctx):
        """Visuelle Warteschlange"""
        player = self.get_player(ctx.guild)
        
        if not player.queue and not player.current:
            await ctx.send("Die Warteschlange ist leer!")
            return
            
        embed = discord.Embed(
            title="🎵 Warteschlange",
            color=discord.Color.purple()
        )
        
        if player.current:
            embed.add_field(
                name="🎵 Jetzt spielt",
                value=f"**{player.current.title}**\nDauer: {player.current.duration // 60}:{player.current.duration % 60:02d}",
                inline=False
            )
        
        if player.queue:
            queue_text = ""
            for i, url in enumerate(player.queue[:10], 1):
                queue_text += f"{i}. {url}\n"
            
            embed.add_field(
                name=f"📋 Nächste ({len(player.queue)} Songs)",
                value=queue_text if queue_text else "Keine Songs in der Warteschlange",
                inline=False
            )
        
        embed.set_footer(text=f"Loop Mode: {player.loop_mode} | Volume: {int(player.volume * 100)}%")
        await ctx.send(embed=embed)

    @commands.command(name="nowplaying")
    async def nowplaying(self, ctx):
        """Beautiful Now Playing Embed"""
        player = self.get_player(ctx.guild)
        
        if not player.current:
            await ctx.send("Es wird nichts abgespielt!")
            return
            
        # Create progress bar
        if ctx.voice_client and ctx.voice_client.is_playing():
            progress = "▬" * 10 + "🔘"
        else:
            progress = "🔘" + "▬" * 10
            
        embed = discord.Embed(
            title="🎵 Jetzt spielt",
            description=f"**{player.current.title}**",
            color=discord.Color.green()
        )
        embed.add_field(name="👤 Artist", value=player.current.uploader)
        embed.add_field(name="⏱️ Dauer", value=f"{player.current.duration // 60}:{player.current.duration % 60:02d}")
        embed.add_field(name="🔊 Lautstärke", value=f"{int(player.volume * 100)}%")
        embed.add_field(name="🔄 Loop", value=player.loop_mode.capitalize())
        embed.add_field(name="📊 Fortschritt", value=progress)
        embed.set_thumbnail(url=player.current.thumbnail)
        embed.set_footer(text=f"Requested by {ctx.author.name}")
        await ctx.send(embed=embed)

    @commands.command(name="volume")
    async def volume(self, ctx, vol: int = None):
        """Lautstärke Control"""
        player = self.get_player(ctx.guild)
        
        if vol is None:
            embed = discord.Embed(
                title="🔊 Aktuelle Lautstärke",
                description=f"**{int(player.volume * 100)}%**",
                color=discord.Color.blue()
            )
            return await ctx.send(embed=embed)
            
        if vol < 0 or vol > 100:
            await ctx.send("Lautstärke muss zwischen 0 und 100 sein!")
            return
            
        player.volume = vol / 100
        if ctx.voice_client and ctx.voice_client.source:
            ctx.voice_client.source.volume = player.volume
            
        embed = discord.Embed(
            title="🔊 Lautstärke geändert",
            description=f"**{vol}%**",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @commands.command(name="loop")
    async def loop(self, ctx, mode: str = None):
        """Loop/Queue/Track Modus"""
        player = self.get_player(ctx.guild)
        
        if mode is None:
            embed = discord.Embed(
                title="🔄 Loop Modus",
                description=f"Aktuell: **{player.loop_mode}**",
                color=discord.Color.blue()
            )
            embed.add_field(name="Verfügbare Modi", value="off, track, queue")
            return await ctx.send(embed=embed)
            
        modes = ["off", "track", "queue"]
        if mode.lower() not in modes:
            await ctx.send(f"Bitte wähle: {', '.join(modes)}")
            return
            
        player.loop_mode = mode.lower()
        
        embed = discord.Embed(
            title="🔄 Loop Modus geändert",
            description=f"**{player.loop_mode}**",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @commands.command(name="skip")
    async def skip(self, ctx):
        """Song überspringen"""
        player = self.get_player(ctx.guild)
        
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            await ctx.send("Es wird nichts abgespielt!")
            return
            
        ctx.voice_client.stop()
        
        embed = discord.Embed(
            title="⏭️ Song übersprungen",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)

    @commands.command(name="pause")
    async def pause(self, ctx):
        """Musik pausieren"""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            embed = discord.Embed(
                title="⏸️ Pausiert",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("Es wird nichts abgespielt!")

    @commands.command(name="resume")
    async def resume(self, ctx):
        """Musik fortsetzen"""
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            embed = discord.Embed(
                title="▶️ Wiedergabe fortgesetzt",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("Die Wiedergabe ist nicht pausiert!")

    @commands.command(name="stop")
    async def stop(self, ctx):
        """Musik stoppen"""
        player = self.get_player(ctx.guild)
        
        if ctx.voice_client:
            ctx.voice_client.stop()
            await ctx.voice_client.disconnect()
            
        player.queue.clear()
        player.current = None
        
        embed = discord.Embed(
            title="⏹️ Musik gestoppt",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

    def play_next(self, ctx):
        player = self.get_player(ctx.guild)
        
        if player.loop_mode == "track" and player.current:
            ctx.voice_client.play(player.current, after=lambda e: self.play_next(ctx))
        elif player.queue or (player.loop_mode == "queue" and player.current):
            if player.queue:
                next_url = player.queue.pop(0)
            elif player.loop_mode == "queue":
                next_url = player.current.url
                
            asyncio.run_coroutine_threadsafe(
                self.play_next_song(ctx, next_url), 
                self.bot.loop
            )
        else:
            player.current = None

    async def play_next_song(self, ctx, url):
        try:
            player = self.get_player(ctx.guild)
            player.current = await YTDLSource.from_url(url, loop=self.bot.loop)
            ctx.voice_client.play(player.current, after=lambda e: self.play_next(ctx))
            
            embed = discord.Embed(
                title="🎵 Nächster Song",
                description=f"**{player.current.title}**",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=player.current.thumbnail)
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"Fehler beim Abspielen des nächsten Songs: {e}")
            self.play_next(ctx)

async def setup(bot):
    await bot.add_cog(Music(bot))
