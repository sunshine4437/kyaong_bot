import os
import asyncio
import time
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
from dotenv import load_dotenv

# .env 파일 로드 (로컬 테스트용)
load_dotenv()

# 1. 봇 권한 세팅
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

def create_bot():
    return commands.Bot(command_prefix="!", intents=intents)

# 2. 🔥 [!오늘의캬옹] / [!오캬] 명령어 등록 함수
def setup_commands(bot_obj):
    @bot_obj.event
    async def on_ready():
        print(f"🤖 캬옹 일정 관리 봇 로그인 완료: {bot_obj.user.name}")

    @bot_obj.command(name="오늘의캬옹", aliases=["오캬"])
    async def today_schedule(ctx):
        FORUM_CHANNEL_ID = 1467848861681979476  # 실제 일정 포럼 채널 ID

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

# 3. 웹 서버 설정 (Render 24시간 호스팅용 웹 서버)
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

# 4. 안전하게 봇을 시작하고 429 차단 시 재시도하는 비동기 메인 함수
async def start_bot_async(token):
    bot_obj = create_bot()
    setup_commands(bot_obj)

    try:
        print("🚀 디스코드 봇 로그인 시도 중...")
        await bot_obj.start(token)
    except discord.errors.HTTPException as e:
        if e.status == 429:
            retry_after = getattr(e, 'retry_after', 60)
            wait_time = int(retry_after) + 5
            print(f"⚠️ 디스코드 API 차단(429 Rate Limit) 발생. {wait_time}초 후 재시도합니다...")
            await bot_obj.close()
            await asyncio.sleep(wait_time)
        else:
            print(f"❌ HTTP 오류 발생: {e}")
            await bot_obj.close()
    except Exception as e:
        print(f"❌ 봇 중단 오류: {e}")
        await bot_obj.close()

# 백그라운드 스레드용 동기 워커
def run_bot():
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        print("❌ 에러: DISCORD_TOKEN 환경 변수가 없습니다.")
        return

    while True:
        try:
            asyncio.run(start_bot_async(TOKEN))
        except Exception as e:
            print(f"❌ 루프 실행 오류: {e}")
            time.sleep(10)

# 5. Gunicorn 부팅과 함께 스레드 시작
t = Thread(target=run_bot, daemon=True)
t.start()