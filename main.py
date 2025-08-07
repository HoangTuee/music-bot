import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio
import pytz
import os # Đã thêm dòng này

TOKEN = os.getenv('DISCORD_TOKEN')
WELCOME_CHANNEL_ID = int(os.getenv('WELCOME_CHANNEL_ID'))
LEAVE_CHANNEL_ID = int(os.getenv('LEAVE_CHANNEL_ID'))  

# Biến toàn cục để lưu hàng đợi cho mỗi server
music_queues = {}

# Cài đặt quyền (Intents) cho bot
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# Khởi tạo bot với tiền tố lệnh là '!'
bot = commands.Bot(command_prefix='!', intents=intents)

# --- HÀM HỖ TRỢ PHÁT NHẠC ---
# Hàm để phát bài hát tiếp theo trong hàng đợi
# SỬA LẠI TOÀN BỘ HÀM NÀY
def play_next(ctx):
    guild_id = ctx.guild.id
    if guild_id in music_queues and music_queues[guild_id]:
        song = music_queues[guild_id].pop(0)
        
        voice_client = ctx.guild.voice_client
        
        # Thêm các tùy chọn để FFmpeg hoạt động ổn định hơn
        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn',
        }
        
        # Tạo nguồn phát với các tùy chọn mới
        source = discord.FFmpegPCMAudio(song['url'], **ffmpeg_options)
        
        voice_client.play(source, after=lambda e: play_next(ctx))
        
        # Gửi thông báo mà không cần chờ đợi
        coro = ctx.send(f'**▶️ Đang phát:** {song["title"]}')
        asyncio.run_coroutine_threadsafe(coro, bot.loop)

# --- CÁC SỰ KIỆN CỦA BOT ---
# Sự kiện khi bot sẵn sàng
@bot.event
async def on_ready():
    print(f'✅ {bot.user.name} đã kết nối thành công tới Discord!')

# Sự kiện chào mừng thành viên mới
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel is not None:
        await channel.send(f'🎉 Chào mừng {member.mention} đã đến với server! Hy vọng bạn có những giây phút vui vẻ.')

# Sự kiện khi thành viên rời đi
@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(LEAVE_CHANNEL_ID)
    if channel is not None:
        await channel.send(f'👋 Tạm biệt {member.name}. Hẹn gặp lại!')

# Sự kiện khi có tin nhắn mới trong kênh
@bot.event
async def on_message(message):
    # Ngăn bot tự trả lời chính nó
    if message.author == bot.user:
        return

    content = message.content.lower()

    # Các kịch bản tương tác
    if 'chào bot' in content:
        await message.channel.send(f'Chào bạn {message.author.mention}! 👋')
    elif 'bot có khỏe không' in content:
        await message.channel.send('Tôi khỏe, cảm ơn bạn đã hỏi thăm! 😊')
    elif content == 'bot ơi':
        await message.channel.send('Dạ, có tôi đây!')
    elif 'mấy giờ rồi bot' in content:
        tz_vietnam = pytz.timezone('Asia/Ho_Chi_Minh') 
        datetime_vietnam = discord.utils.utcnow().astimezone(tz_vietnam)
        current_time = datetime_vietnam.strftime("%H:%M:%S ngày %d/%m/%Y")
        await message.channel.send(f'Bây giờ là **{current_time}** tại Việt Nam. ⏰')

    # Xử lý các lệnh (!play, !join...) sau khi đã check tin nhắn
    await bot.process_commands(message)

# --- CÁC LỆNH CỦA BOT ---
# THAY THẾ TOÀN BỘ HÀM PLAY CŨ BẰNG HÀM NÀY

# THAY THẾ TOÀN BỘ HÀM PLAY CŨ BẰNG HÀM NÀY

@bot.command(name='play', help='Phát nhạc hoặc thêm vào hàng đợi')
async def play(ctx, *, url):
    if not ctx.message.author.voice:
        await ctx.send(f"{ctx.message.author.name} ơi, bạn cần vào một kênh thoại trước đã!")
        return

    voice_channel = ctx.message.author.voice.channel
    guild_id = ctx.guild.id

    if ctx.voice_client is None:
        await voice_channel.connect()
    else:
        await ctx.voice_client.move_to(voice_channel)
        
    async with ctx.typing():
        # Tùy chọn cuối cùng: Dùng cookie để không bị chặn
        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'default_search': 'auto',
            'source_address': '0.0.0.0', # Ưu tiên dùng IPv4
            # Đường dẫn đến file cookie an toàn trên Render
            'cookiefile': '/etc/secrets/cookies.txt' 
        }
        
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(f"ytsearch:{url}", download=False)['entries'][0]
            except Exception as e:
                print(e)
                # Kiểm tra xem có phải lỗi do cookie không
                if 'HTTP Error 429' in str(e) or 'This content isn’t available' in str(e):
                     await ctx.send("Lỗi: YouTube đang chặn yêu cầu. Có thể cookie đã hết hạn hoặc không hợp lệ.")
                else:
                     await ctx.send("Bot không tìm thấy bài hát. Hãy thử lại với tên khác.")
                return
        
        song = {'title': info['title'], 'url': info['url']}

        if guild_id not in music_queues:
            music_queues[guild_id] = []
        
        music_queues[guild_id].append(song)
        await ctx.send(f'**✅ Đã thêm vào hàng đợi:** {song["title"]}')

    if not ctx.voice_client.is_playing():
        play_next(ctx)

@bot.command(name='skip', help='Bỏ qua bài hát hiện tại')
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Đã bỏ qua bài hát! ⏭️")
    else:
        await ctx.send("Không có bài hát nào đang phát để bỏ qua.")

@bot.command(name='queue', help='Hiển thị hàng đợi bài hát')
async def queue(ctx):
    guild_id = ctx.guild.id
    if guild_id in music_queues and music_queues[guild_id]:
        queue_list = ""
        for i, song in enumerate(music_queues[guild_id][:10]):
            queue_list += f"{i+1}. {song['title']}\n"
        
        embed = discord.Embed(title="🎶 Hàng đợi bài hát 🎶", description=queue_list, color=discord.Color.blue())
        if len(music_queues[guild_id]) > 10:
            embed.set_footer(text=f"và {len(music_queues[guild_id]) - 10} bài hát khác...")
            
        await ctx.send(embed=embed)
    else:
        await ctx.send("Hàng đợi trống trơn! Dùng `!play` để thêm nhạc nhé.")

@bot.command(name='stop', help='Dừng nhạc và xóa toàn bộ hàng đợi')
async def stop(ctx):
    guild_id = ctx.guild.id
    if guild_id in music_queues:
        music_queues[guild_id].clear()

    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Đã dừng nhạc và xóa hàng đợi! ⏹️")
    else:
        await ctx.send("Đã xóa hàng đợi! ⏹️")

@bot.command(name='leave', help='Bot sẽ rời khỏi kênh thoại và xóa hàng đợi')
async def leave(ctx):
    guild_id = ctx.guild.id
    if guild_id in music_queues:
        music_queues[guild_id].clear()

    if ctx.voice_client and ctx.voice_client.is_connected():
        await ctx.voice_client.disconnect()
        await ctx.send("Tạm biệt! Hẹn gặp lại nhé. 👋")
    else:
        await ctx.send("Bot đang không ở trong kênh thoại nào.")

@bot.command(name='pause', help='Tạm dừng bài hát hiện tại')
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("Đã tạm dừng. ⏸️")
    else:
        await ctx.send("Không có bài hát nào đang phát để tạm dừng.")

@bot.command(name='resume', help='Tiếp tục phát bài hát')
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("Tiếp tục phát nào! ▶️")
    else:
        await ctx.send("Bot không có bài hát nào đang tạm dừng.")

# --- PHẦN GIỮ BOT THỨC TRÊN RENDER ---
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
  # Chạy web server trên cổng mà Render cung cấp
  port = int(os.environ.get('PORT', 8080))
  app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- CHẠY BOT VÀ CHẠY WEB SERVER ---
keep_alive() # Thêm dòng này

# --- CHẠY BOT ---

bot.run(TOKEN)


