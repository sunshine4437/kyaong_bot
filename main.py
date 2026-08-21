import os
import asyncio
import discord
from discord.ext import commands
from flask import Flask
from dotenv import load_dotenv

# .env 파일 로드 (로컬 테스트용)
load_dotenv()

# 1. 봇 권한 및 접두사 세팅
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"🤖 캬옹 일정 관리 봇 로그인 완료: {bot.user.name}")

# 2. 🔥 [!오늘의캬옹] / [!오캬] 명령어 구현
@bot.command(name="오늘의캬옹", aliases=["오캬"])
async def today_schedule(ctx):
    FORUM_CHANNEL_ID = 1467848861681979476  # 실제 일정 포럼 채널 ID

    try:
        # 디스코드 API 서버에서 포럼 채널 정보 실시간 원격 요청
        channel = await bot.fetch_channel(FORUM_CHANNEL_ID)
    except discord.NotFound:
        print(f"❌ 에러: 채널 ID {FORUM_CHANNEL_ID}를 찾을 수 없습니다.")
        await ctx.send("❌ 지정된 채널 ID를 찾을 수 없습니다.")
        return
    except discord.Forbidden:
        print(f"❌ 권한 에러: 봇이 채널 ID {FORUM_CHANNEL_ID}를 볼 수 없습니다.")
        await ctx.send("❌ 봇이 해당 채널을 볼 수 있는 권한이 없습니다.")
        return

    if not isinstance(channel, discord.ForumChannel):
        await ctx.send("❌ 지정된 채널 ID가 포럼 채널이 아닙니다.")
        return

    # 리스트 객체 생성
    schedule_list = []
    apply_list = []
    try_list = []

    try:
        # 📌 [서버 최적화] 라이브러리 캐시와 실시간 서버 활성 스레드를 병합하여 누락을 원천 차단합니다.
        threads_list = list(channel.threads)
        
        # 해당 서버(Guild) 전체의 실시간 활성 스레드 목록을 강제 요청하여 포럼 채널 대상만 필터링합니다.
        guild_active_threads = await ctx.guild.active_threads()
        for thread in guild_active_threads.threads:
            if thread.parent_id == FORUM_CHANNEL_ID and thread not in threads_list:
                threads_list.append(thread)
                
    except Exception as e:
        print(f"❌ 스레드 목록 가져오기 실패: {e}")
        # 어떤 문제 때문에 실패했는지 원인을 상세히 알 수 있도록 출력문을 강화했습니다.
        await ctx.send(f"❌ 포럼 채널의 게시글 목록을 불러오지 못했습니다. (원인: {e})")
        return

    # 📌 포스트들을 '제목(이름) 순'으로 정렬 (가나다/ABC 오름차순)
    sorted_threads = sorted(threads_list, key=lambda t: t.name)

    # 정렬된 포스트 목록 순회 및 조건 분류
    for thread in sorted_threads:
        # 검색 정확도를 높이기 위한 공백 제거 및 소문자화
        clean_name = thread.name.replace(" ", "").lower()

        # 📌 설정하신 키워드 매칭 규칙 적용
        if "[캬옹][상시모집]" in clean_name:
            apply_list.append(f"<#{thread.id}>")
        elif "[캬옹]" in clean_name and "트라이" in clean_name:
            try_list.append(f"<#{thread.id}>")
        elif "완" not in clean_name and "마감" not in clean_name:
            schedule_list.append(f"<#{thread.id}>")

    # 3. 💡 f-string 멀티라인 문법을 활용한 메시지 조립
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

    # 결과 전송
    await ctx.send(response)

# 4. 웹 서버 유지 대기 설정 (Render 24시간 호스팅용 웹 서버)
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

# 5. WSGI 호환 및 비동기 멀티 구동 핵심 설정
def create_app():
    TOKEN = os.getenv('DISCORD_TOKEN')
    
    if not TOKEN:
        print("❌ 에러: DISCORD_TOKEN 환경 변수를 찾을 수 없습니다. .env 파일이나 Render 설정을 확인하세요.")
        return app

    # Gunicorn 환경에서 디스코드 비동기 태스크를 안전하게 여는 통합 구동 함수
    async def run_bot_async():
        try:
            print("🚀 디스코드 봇 연결 시도 중...")
            await bot.start(TOKEN)
        except Exception as e:
            print(f"❌ 봇 구동 중 에러 발생: {e}")

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.create_task(run_bot_async())
    return app

# Gunicorn 배포용 진입점 변수 지정
wsgi_app = create_app()
