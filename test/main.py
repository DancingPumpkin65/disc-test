import discord
from discord.ext import commands
import asyncio
from dotenv import load_dotenv
import os
from youtube_dl import YoutubeDL
import requests

# Load environment variables
load_dotenv()

# Configure intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

# Configure FFmpeg options
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

# Configure youtube_dl options
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

class MusicBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = []
        self.current_song = None
        self.ytdl = YoutubeDL(YTDL_OPTIONS)
        
    def search(self, query):
        try:
            with YoutubeDL(YTDL_OPTIONS) as ydl:
                try:
                    # Try treating the query as a direct URL
                    requests.get(query)
                    info = ydl.extract_info(query, download=False)
                except Exception:
                    # If not a URL, search on YouTube
                    info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
                
                # Get the best audio stream URL
                for format in info['formats']:
                    if format.get('acodec') != 'none' and format.get('vcodec') == 'none':
                        audio_url = format['url']
                        break
                else:
                    # Fallback to the first format if no audio-only stream is found
                    audio_url = info['formats'][0]['url']
                
                return {
                    'source': audio_url,
                    'title': info['title']
                }
        except Exception as e:
            print(f"Error in search: {e}")
            raise e

    @commands.command()
    async def play(self, ctx, *, query: str):
        """Play audio from YouTube URL or search query"""
        if not ctx.author.voice:
            return await ctx.send("You must be in a voice channel to use this command.")
        
        voice_client = ctx.voice_client or await ctx.author.voice.channel.connect()
        
        try:
            # Search for the video
            await ctx.send(f"🔎 Searching for: **{query}**...")
            song_info = self.search(query)
            
            # Add to queue and notify
            self.queue.append((song_info['source'], song_info['title']))
            await ctx.send(f"Added to queue: **{song_info['title']}**")
            
            # Play if not already playing something
            if not voice_client.is_playing():
                await self._play_next(ctx)
                
        except Exception as e:
            error_message = f"Error: {str(e)}"
            print(f"YouTube error: {str(e)}")
            await ctx.send(error_message)
            await ctx.send("Try using a different search term or YouTube URL.")

    async def _play_next(self, ctx):
        if self.queue:
            self.current_song = self.queue.pop(0)
            source = discord.FFmpegPCMAudio(self.current_song[0], **FFMPEG_OPTIONS)
            
            ctx.voice_client.play(source, after=lambda e: self.bot.loop.create_task(self._play_next(ctx)))
            await ctx.send(f"Now playing: **{self.current_song[1]}**")
        else:
            await ctx.send("Queue is empty.")
            await self._safe_disconnect(ctx)

    @commands.command()
    async def skip(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("Skipped current song.")
            await self._play_next(ctx)

    @commands.command()
    async def stop(self, ctx):
        self.queue.clear()
        if ctx.voice_client:
            ctx.voice_client.stop()
            await self._safe_disconnect(ctx)
        await ctx.send("Playback stopped and queue cleared.")

    async def _safe_disconnect(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()

    @commands.command()
    async def queue(self, ctx):
        if not self.queue:
            return await ctx.send("Queue is empty.")
        
        queue_list = "\n".join([f"{i+1}. {song[1]}" for i, song in enumerate(self.queue)])
        await ctx.send(f"Current Queue:\n{queue_list}")

# Initialize bot
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    await bot.add_cog(MusicBot(bot))
    print(f'Logged in as {bot.user}')

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    await ctx.send(f"Error: {str(error)}")

if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_TOKEN'))