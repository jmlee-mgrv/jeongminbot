import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from groq import Groq

load_dotenv()

app = App(token=os.environ["SLACK_BOT_TOKEN"])
groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])

SYSTEM = """당신은 '정민봇'입니다. 기획 전문 AI 에이전트로서 다음을 도와줍니다:

1. 기획서 작성 - 구조화된 기획안 양식 제공
2. 일정 관리 - 할 일 목록과 우선순위 정리
3. 아이디어 구체화 - 아이디어를 실행 가능한 계획으로 발전
4. 시장/경쟁 분석 프레임워크 제공

항상 한국어로 답변하고, 실용적이고 구체적인 내용을 제공하세요.
기획서 요청시 반드시 제목, 배경, 목표, 실행계획, 일정, 예산, KPI 항목을 포함하세요."""

# 사용자별 대화 기록 저장 (최대 20개)
conversation_history = {}


def ask_groq(user_id, text):
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    conversation_history[user_id].append({"role": "user", "content": text})

    # 최대 20개 메시지만 유지
    if len(conversation_history[user_id]) > 20:
        conversation_history[user_id] = conversation_history[user_id][-20:]

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": SYSTEM}] + conversation_history[user_id]
    )

    reply = response.choices[0].message.content
    conversation_history[user_id].append({"role": "assistant", "content": reply})
    return reply


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

    # 대화 초기화 명령어
    if text.strip() == "대화초기화":
        conversation_history.pop(user, None)
        say("대화 기록을 초기화했어요! 새로 시작해요. 👋")
        return

    say("생각 중... 🤔")
    say(ask_groq(user, text))


if __name__ == "__main__":
    print("정민봇 시작!")
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
