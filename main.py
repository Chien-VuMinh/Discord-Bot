# mypy: ignore-errors
import discord
from discord.ext import  commands
from discord import app_commands
import logging
from dotenv import load_dotenv
import os 
import yt_dlp 
from collections import deque
import asyncio


load_dotenv()

token = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True 
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user.name} is here")


@bot.event
async def on_member_join(member):
    await bot.tree.sync()
    await member.send(f'Hello {member.name}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    if "shit" in message.content.lower():
        await message.channel.send(f"Hey {message.author.mention} watch your mouth")


    await bot.process_commands(message)



@bot.command()
async def yo(ctx):
    await ctx.send(f'Hi~~~ {ctx.author.mention}')

@bot.command()
async def reply(ctx):
    await ctx.reply(f'You are correct!!!')

@bot.command()
async def H(ctx):
    await ctx.reply(f'Giàu nhưng cứ bảo không có tiền')

@bot.command()
async def K(ctx):
    await ctx.reply(f'Vua bùng kèo, trùm ngủ nướng, sv tdt')


@bot.command()
async def stupid(ctx):
    await ctx.reply(f'Mày mới là thằng ngu')


@bot.command()
async def Càp(ctx):
    embed = discord.Embed(
        title="Danh sách lệnh của bot 🎵",
        description="Dưới đây là tất cả các lệnh bạn có thể sử dụng:",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="!play <tìm kiếm>",
        value="Phát một bài hát từ YouTube hoặc thêm vào hàng đợi.",
        inline=False
    )
    embed.add_field(
        name="!skip",
        value="Bỏ qua bài hát đang phát và chuyển sang bài tiếp theo.",
        inline=False
    )
    embed.add_field(
        name="!stop",
        value="Dừng phát nhạc và xóa toàn bộ hàng đợi.",
        inline=False
    )
    embed.add_field(
        name="!pause",
        value="Tạm dừng bài hát đang phát.",
        inline=False
    )
    embed.add_field(
        name="!resume",
        value="Tiếp tục bài hát đã bị tạm dừng.",
        inline=False
    )
    embed.add_field(
        name="!Càp",
        value="Hiển thị danh sách tất cả các lệnh (lệnh này).",
        inline=False
    )
    embed.set_footer(text="Bot tự rời kênh nếu không còn ai trong kênh thoại.")
    await ctx.send(embed=embed)




FFMPEG_OPTIONS = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            "options": "-vn -c:a libopus -b:a 96k",
            # Remove executable if FFmpeg is in PATH
        }
YDL_OPTIONS = {'format' : 'bestaudio', 'noplaylist' : True}

class MusicBot(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.queue = []

    @commands.command()
    async def play(self, ctx, *, search):
        voice_channel = ctx.author.voice.channel if ctx.author.voice else None
        if not voice_channel:
            return await ctx.reply('You\'re not in a voice channel')
        if not ctx.voice_client: 
            await voice_channel.connect()

        async with ctx.typing():
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(f'ytsearch:{search}', download=False)
                if 'entries' in info:
                    info = info['entries'][0]
                url = info['url']
                title = info['title']
                self.queue.append((url, title))
                await ctx.send(f'Added to queue: **{title}**')

        if not ctx.voice_client.is_playing():
            await self.play_next(ctx)

    async def play_next(self, ctx):
        if self.queue: 
            url, title = self.queue.pop(0)
            source = await discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS, executable="bin\\ffmpeg.exe")
            ctx.voice_client.play(source, after = lambda _:self.client.loop.create_task(self.play_next(ctx)))
            await ctx.send(f'Now playing **{title}**')
        elif not ctx.voice_client.is_playing: 
            await ctx.send('Queue is empty!')

    @commands.command()
    async def skip(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("Skipped")

    @commands.command()
    async def stop(self, ctx):
        if not ctx.voice_client:
            return await ctx.reply("I\'m not in a channel")
        ctx.voice_client.stop()
        self.queue.clear()
        await ctx.send("Stop and delete queue!")    


    @commands.command()
    async def pause(self, ctx):
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            return await ctx.reply("I\'m not playing song!")
        if ctx.voice_client.is_paused():
            return await ctx.reply("The song is already paused!")
        ctx.voice_client.pause()
        await ctx.send("Paused!")


    @commands.command()
    async def resume(self, ctx):
        if not ctx.voice_client or not ctx.voice_client.is_paused():
            return await ctx.reply("No songs are being paused!")
        ctx.voice_client.resume()
        await ctx.send("Continue song!")    

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return  # Bỏ qua bot
        voice_client = member.guild.voice_client
        if not voice_client or not voice_client.is_connected():
            return
        await self.check_empty_channel(voice_client)

    async def check_empty_channel(self, voice_client):
        """Kiểm tra và ngắt kết nối nếu không còn người trong kênh thoại."""
        if not voice_client or not voice_client.is_connected():
            return
        channel = voice_client.channel
        # Đếm số thành viên không phải bot
        members = [m for m in channel.members if not m.bot]
        if not members:  # Nếu không còn người
            self.queue.clear()  # Xóa hàng đợi
            await voice_client.disconnect()
            if channel.guild.text_channels:
                await channel.guild.text_channels[0].send(f"Left {channel.name}!")


              

async def main():
    await bot.add_cog(MusicBot(bot))
    await bot.start(token)


asyncio.run(main())