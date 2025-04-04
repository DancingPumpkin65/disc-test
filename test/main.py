import discord
from discord.ext import commands
from pytube import YouTube
import asyncio
from dotenv import load_dotenv
import os

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

class MusicBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = []
        self.current_song = None

    @commands.command()
    async def play(self, ctx, *, url: str):
        """Play audio from YouTube URL"""
        if not ctx.author.voice:
            return await ctx.send("You must be in a voice channel to use this command.")
        
        voice_client = ctx.voice_client or await ctx.author.voice.channel.connect()
        
        try:
            yt = YouTube(url)
            audio_stream = yt.streams.filter(only_audio=True).first()
            if not audio_stream:
                return await ctx.send("Could not find audio stream.")
            
            self.queue.append((audio_stream.url, yt.title))
            await ctx.send(f"Added to queue: **{yt.title}**")
            
            if not voice_client.is_playing():
                await self._play_next(ctx)
                
        except Exception as e:
            await ctx.send(f"Error: {str(e)}")

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