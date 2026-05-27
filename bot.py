import os
import threading
from datetime import datetime
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from groq import Groq
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

load_dotenv()

app = App(token=os.environ["SLACK_BOT_TOKEN"])
groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])
SLACK_USER_ID = os.environ.get("SLACK_USER_ID", "U09UBT93JUX")

SYSTEM = """당신은 '정민봇'입니다. 기획 전문 AI 에이전트로서 다음을 도와줍니다:

1. 기획서 작성 - 구조화된 기획안 양식 제공
2. 일정 관리 - 할 일 목록과 우선순위 정리
3. 아이디어 구체화 - 아이디어를 실행 가능한 계획으로 발전
4. 시장/경쟁 분석 프레임워크 제공

항상 한국어로 답변하고, 실용적이고 구체적인 내용을 제공하세요.
기획서 요청시 반드시 제목, 배경, 목표, 실행계획, 일정, 예산, KPI 항목을 포함하세요."""

conversation_history = {}


def ask_groq(user_id, text):
    if user_id not in conversation_history:
        conversation_history[user_id] = []
    conversation_history[user_id].append({"role": "user", "content": text})
    if len(conversation_history[user_id]) > 20:
        conversation_history[user_id] = conversation_history[user_id][-20:]
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": SYSTEM}] + conversation_history[user_id]
    )
    reply = response.choices[0].message.content
    conversation_history[user_id].append({"role": "assistant", "content": reply})
    return reply


def send_morning_message():
    kst = pytz.timezone("Asia/Seoul")
    today = datetime.now(kst).strftime("%Y년 %m월 %d일 %A")

    prompt = f"""오늘은 {today}입니다.
아침 기획 브리핑을 해주세요. 다음 3가지를 포함해주세요:

1. 오늘의 기획 팁 또는 영감 한 가지 (실용적이고 구체적으로)
2. 오늘 하루를 시작하기 좋은 기획자의 마인드셋 한 문장
3. "오늘 가장 집중해야 할 일 한 가지는 무엇인가요?" 라는 질문

짧고 임팩트 있게 작성해주세요."""

    message = ask_groq("morning_alarm", prompt)

    try:
        dm = app.client.conversations_open(users=SLACK_USER_ID)
        channel_id = dm["channel"]["id"]
        app.client.chat_postMessage(
            channel=channel_id,
            text=f"좋은 아침이에요! 오늘도 멋진 하루 되세요 ☀️\n\n{message}"
        )
        print(f"아침 알림 전송 완료: {datetime.now(kst)}")
    except Exception as e:
        print(f"아침 알림 오류: {e}")


@app.event("app_mention")
def handle_mention(event, say):
    user = event["user"]
    text = event["text"]
    say("잠깐만요, 기획안 작성 중... 🤔")
    say(f"<@{user}>\n\n{ask_groq(user, text)}")


@app.event("message")
def handle_dm(event, say):
    if event.get("channel_type") != "im":
        return
    if event.get("bot_id"):
        return
    user = event["user"]
    text = event.get("text", "")

    if text.strip() == "대화초기화":
        conversation_history.pop(user, None)
        say("대화 기록을 초기화했어요! 새로 시작해요. 👋")
        return

    if text.strip() == "내 아이디":
        say(f"슬랙 사용자 ID: `{user}`")
        return

    if text.strip() == "알림테스트":
        send_morning_message()
        say("아침 알림을 테스트로 전송했어요!")
        return

    say("생각 중... 🤔")
    say(ask_groq(user, text))


if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        send_morning_message,
        CronTrigger(hour=8, minute=0, timezone=pytz.timezone("Asia/Seoul"))
    )
    scheduler.start()
    print("정민봇 시작! (매일 오전 8시 알림 설정됨)")
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
