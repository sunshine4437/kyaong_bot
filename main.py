import os
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
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
        # 📌 channel.threads 대신 실시간 활성화된 스레드를 비동기로 안전하게 긁어옵니다.
        active_threads_response = await channel.active_threads()
        threads_list = active_threads_response.threads
    except Exception as e:
        print(f"❌ 스레드 목록 가져오기 실패: {e}")
        await ctx.send("❌ 포럼 채널의 게시글 목록을 불러오지 못했습니다.")
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

def run_flask():
    # 📌 Render가 부여하는 동적 포트를 할당받고, 없으면 8080을 씁니다.
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Flask 웹 서버를 백그라운드 스레드에서 구동
flask_thread = Thread(target=run_flask, daemon=True)
flask_thread.start()

# 5. 봇 기동 (토큰은 환경 변수에서 안전하게 가져옴)
# 📌 로컬 환경 변수나 Render 대시보드 환경 변수에 'DISCORD_TOKEN' 이름으로 토큰을 넣으세요.
TOKEN = os.getenv('DISCORD_TOKEN')

if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ 에러: DISCORD_TOKEN 환경 변수를 찾을 수 없습니다. .env 파일이나 Render 설정을 확인하세요.")
