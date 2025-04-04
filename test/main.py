import discord
from discord.ext import commands
from pytube import YouTube
import asyncio
from dotenv import load_dotenv
import os
import json
import http.cookiejar

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

# YouTube cookie configuration
YOUTUBE_COOKIES_FILE = os.getenv('YOUTUBE_COOKIES_FILE')

class MusicBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = []
        self.current_song = None
        self.cookies = None
        if YOUTUBE_COOKIES_FILE and os.path.exists(YOUTUBE_COOKIES_FILE):
            try:
                self.cookies = http.cookiejar.MozillaCookieJar(YOUTUBE_COOKIES_FILE)
                self.cookies.load()
                print("YouTube cookies loaded successfully")
            except Exception as e:
                print(f"Error loading cookies: {e}")

    @commands.command()
    async def play(self, ctx, *, url: str):
        """Play audio from YouTube URL"""
        if not ctx.author.voice:
            return await ctx.send("You must be in a voice channel to use this command.")
        
        voice_client = ctx.voice_client or await ctx.author.voice.channel.connect()
        
        try:
            # Create YouTube object with cookies
            yt = YouTube(url)
            if self.cookies:
                yt.bypass_age_gate()
                yt.use_oauth = True
                yt.allow_oauth_cache = True
                yt._http = self.cookies
                
            audio_stream = yt.streams.filter(only_audio=True).first()
            if not audio_stream:
                return await ctx.send("Could not find audio stream.")
            
            self.queue.append((audio_stream.url, yt.title))
            await ctx.send(f"Added to queue: **{yt.title}**")
            
            if not voice_client.is_playing():
                await self._play_next(ctx)
                
        except Exception as e:
            error_message = f"Error: {str(e)}"
            print(f"YouTube error: {str(e)}")
            await ctx.send(error_message)
            await ctx.send("Try using a different YouTube URL or check if the video is available.")

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
        """Skip the current song"""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("Skipped current song.")
            await self._play_next(ctx)

    @commands.command()
    async def stop(self, ctx):
        """Stop playback and clear queue"""
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
        """Show current queue"""
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