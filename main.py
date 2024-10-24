import io
import os
import discord
import pydub
from discord.sinks import MP3Sink
from dotenv import load_dotenv

load_dotenv()

bot = discord.Bot()

@bot.event
async def on_ready():
    print(f'Logged on as {bot.user}')

    await bot.sync_commands()

    print('commands synced')

async def finish_callback(sink: MP3Sink, channel: discord.TextChannel):
    mention_strs = []
    audio_segs: list[pydub.AudioSegment] = []
    files: list[discord.File] = []

    longest = pydub.AudioSegment.empty()

    for user_id, audio in sink.audio_data.items():
        mention_strs.append(f'<@{user_id}>')

        seg = pydub.AudioSegment.from_file(audio.file, format=sink.encoding)

        if len(seg) > len(longest):
            audio_segs.append(longest)
            longest = seg
        else:
            audio_segs.append(seg)

        audio.file.seek(0)
        files.append(discord.File(audio.file, f'{user_id}.{sink.encoding}'))

    for seg in audio_segs:
        longest = longest.overlay(seg)

    with io.BytesIO() as fp:
        longest.export(fp, format=sink.encoding)
        await channel.send(f'Finished recording audio for: {", ".join(mention_strs)}', file=discord.File(fp, f'recording.{sink.encoding}'))

@bot.command()
async def join(ctx: discord.ApplicationContext):
    voice = ctx.author.voice

    if not voice:
        return await ctx.respond('You are not in a voice channel')
    
    await voice.channel.connect()

    await ctx.respond(f'Joined {voice.channel.name}')

@bot.command()
async def start(ctx: discord.ApplicationContext):
    voice = ctx.guild.voice_client

    if not voice:
        return await ctx.respond('You are not in a voice channel')

    voice_client: discord.VoiceClient = ctx.voice_client

    if not voice_client:
        return await ctx.respond('I am not in a voice channel')

    voice_client.start_recording(MP3Sink(), finish_callback, ctx.channel)

    await ctx.respond('Started recording')

@bot.command()
async def stop(ctx: discord.ApplicationContext):
    voice_client: discord.VoiceClient = ctx.voice_client

    if not voice_client:
        return await ctx.respond('No recording to stop')

    voice_client.stop_recording()

    await ctx.respond('Stopped recording')

@bot.command()
async def leave(ctx: discord.ApplicationContext):
    voice_client: discord.VoiceClient = ctx.voice_client

    if not voice_client:
        return await ctx.respond('I am not in a voice channel')

    await voice_client.disconnect()

    await ctx.respond('Left voice channel')

bot.run(os.getenv('DISCORD_BOT_TOKEN'))