import datetime
import io
import os
import discord
import pydub
from discord.sinks import MP3Sink
from dotenv import load_dotenv

load_dotenv()

bot = discord.Bot()
TARGET_USER_ID = 274340078015217666

if not os.path.exists('recordings'):
    os.mkdir('recordings')

@bot.event
async def on_ready():
    print(f'Logged on as {bot.user}')

    #await bot.sync_commands()

    print('commands synced')

async def finish_callback_combine(sink: MP3Sink):
    audio_segs: list[pydub.AudioSegment] = []
    files: list[discord.File] = []

    longest = pydub.AudioSegment.empty()

    for user_id, audio in sink.audio_data.items():

        seg = pydub.AudioSegment.from_file(audio.file, format=sink.encoding)

        if len(seg) > len(longest):
            audio_segs.append(longest)
            longest = seg
        else:
            audio_segs.append(seg)

        files.append(discord.File(audio.file, f'{user_id}.{sink.encoding}'))

    for seg in audio_segs:
        longest = longest.overlay(seg)

    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    filename = f'recordings/{timestamp}.mp3'
    if len(longest) < 10000: # 10 second minimum recording length 
        print('Recording too short, not saving')
        return
    longest.export(filename, format='mp3')
    print('Recording saved to', filename)

async def finish_callback_single(sink: MP3Sink):
    for user_id, audio in sink.audio_data.items():
        seg = pydub.AudioSegment.from_file(audio.file, format=sink.encoding)

        if len(seg) > 10000: # 10 second minimum recording length
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            user_dir = f'recordings/{user_id}'
            filename = f'{user_dir}/{timestamp}.mp3'
            os.makedirs(user_dir, exist_ok=True)
            seg.export(filename, format='mp3')
            print('Recording saved to', filename)

@bot.command()
async def join(ctx: discord.ApplicationContext):
    voice = ctx.author.voice

    if not voice:
        return await ctx.respond('You are not in a voice channel')
    
    voice_client: discord.VoiceClient = await voice.channel.connect()
    voice_client.start_recording(MP3Sink(), finish_callback_single)

    return await ctx.respond(f'Joined {voice.channel.name}')

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    print('voice state update', member.id, before.channel, after.channel)
    if member.id == TARGET_USER_ID:
        if after.channel is not None:
            # Disconnect from previous channel
            before_voice_client: discord.VoiceClient = member.guild.voice_client
            if before_voice_client:
                before_voice_client.stop_recording()
                await before_voice_client.disconnect()
                print(f'Left {before.channel.name} and stopped recording {member.display_name}')

            # Connect to new channel
            voice_client: discord.VoiceClient = await after.channel.connect()
            voice_client.start_recording(MP3Sink(), finish_callback_combine)
            print(f'Joined {after.channel.name} and started recording {member.display_name}')

        # Disconnect if user leaves voice channel
        elif after.channel is None:
            voice_client: discord.VoiceClient = before.channel.guild.voice_client
            #voice_client.stop_recording()
            print(f'Left {before.channel.name} and stopped recording {member.display_name}')

            await voice_client.disconnect()

@bot.command()
async def start(ctx: discord.ApplicationContext):
    voice = ctx.guild.voice_client

    if not voice:
        return await ctx.respond('You are not in a voice channel')

    voice_client: discord.VoiceClient = ctx.voice_client

    if not voice_client:
        return await ctx.respond('I am not in a voice channel')

    voice_client.start_recording(MP3Sink(), finish_callback_combine)

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