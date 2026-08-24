import os
import asyncio
import discord
from discord.ext import commands
from aiohttp import web
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

def setup_bot():
    bot_obj = commands.Bot(command_prefix="!", intents=intents)

    @bot_obj.event
    async def on_ready():
        print(f"🤖 캬옹 일정 관리 봇 로그인 완료: {bot_obj.user.name}", flush=True)

    @bot_obj.command(name="오늘의캬옹", aliases=["오캬"])
    async def today_schedule(ctx):
        FORUM_CHANNEL_ID = 1467848861681979476

        try:
            channel = await ctx.bot.fetch_channel(FORUM_CHANNEL_ID)
        except discord.NotFound:
            await ctx.send("❌ 지정된 채널 ID를 찾을 수 없습니다.")
            return
        except discord.Forbidden:
            await ctx.send("❌ 봇이 해당 채널을 볼 수 있는 권한이 없습니다.")
            return

        if not isinstance(channel, discord.ForumChannel):
            await ctx.send("❌ 지정된 채널 ID가 포럼 채널이 아닙니다.")
            return

        schedule_list = []
        apply_list = []
        try_list = []

        try:
            threads_list = list(channel.threads)
            active_threads_response = await ctx.guild.active_threads()

            if hasattr(active_threads_response, 'threads'):
                raw_threads = active_threads_response.threads
            else:
                raw_threads = active_threads_response

            for thread in raw_threads:
                if thread.parent_id == FORUM_CHANNEL_ID and thread not in threads_list:
                    threads_list.append(thread)

        except Exception as e:
            await ctx.send(f"❌ 포럼 채널의 게시글 목록을 불러오지 못했습니다. (원인: {e})")
            return

        sorted_threads = sorted(threads_list, key=lambda t: t.name)

        for thread in sorted_threads:
            clean_name = thread.name.replace(" ", "").lower()

            if "[캬옹][상시모집]" in clean_name:
                apply_list.append(f"<#{thread.id}>")
            elif "[캬옹]" in clean_name and "트라이" in clean_name:
                try_list.append(f"<#{thread.id}>")
            elif "완" not in clean_name and "마감" not in clean_name:
                schedule_list.append(f"<#{thread.id}>")

        schedules = "\n".join(schedule_list) if schedule_list else "ㆍ 진행 중인 일정이 없습니다."
        applies = "\n".join(apply_list) if apply_list else "ㆍ 신청 중인 일정이 없습니다."
        tries = "\n".join(try_list) if try_list else "ㆍ 진행 중인 트라이가 없습니다."

        response = f"""**<오늘의 캬옹>**

<:aeromancer_3:1534374208002461766> **일정**
{schedules}

<:meow:1534388083158552636> **[캬옹]트라이 신청**
{applies}

<:rm_mococo_26:1534407987945537576> **[캬옹]트라이**
{tries}

다들 많관부! <#1467848861681979476> 사용은 자유롭게! 양식무관! 누구나!
문의사항은 연락주세요 <:artist_3:1534374268132135053>"""

        await ctx.send(response)

    return bot_obj

async def handle_ping(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 웹 서버가 포트 {port}에서 정상 시작되었습니다.", flush=True)

async def main():
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        print("❌ 에러: DISCORD_TOKEN 환경 변수가 없습니다.", flush=True)
        return

    await start_web_server()

    while True:
        bot = setup_bot()
        try:
            print("🚀 디스코드 봇 로그인 시도 중...", flush=True)
            async with bot:
                await bot.start(TOKEN)
        except discord.errors.HTTPException as e:
            if e.status == 429:
                # 30분(1800초) 대기 후 재시도
                wait_time = 1800
                print(f"⚠️ 디스코드 API 차단(429 Rate Limit) 발생. {wait_time // 60}분 후 재시도합니다...", flush=True)
                await asyncio.sleep(wait_time)
            else:
                print(f"❌ HTTP 오류 발생: {e}", flush=True)
                await asyncio.sleep(10)
        except Exception as e:
            print(f"❌ 봇 비정상 중단: {e}", flush=True)
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())