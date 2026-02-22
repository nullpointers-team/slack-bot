import os
import json
import psycopg2
from datetime import datetime, timedelta
from dateutil import parser
from dotenv import load_dotenv
from slack_bolt import App
from groq import Groq

# ==============================
# Load Environment Variables
# ==============================
load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
DATABASE_URL = os.getenv("DATABASE_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ==============================
# Initialize Slack & Groq
# ==============================
app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
groq_client = Groq(api_key=GROQ_API_KEY)

# ==============================
# Database Connection
# ==============================
def get_connection():
    return psycopg2.connect(DATABASE_URL)

# ==============================
# Role-Based Access Control
# ==============================
def is_manager(slack_user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT designation FROM members
        WHERE slack_user_id = %s
    """, (slack_user_id,))

    row = cur.fetchone()

    cur.close()
    conn.close()

    return row and row[0].lower() == "manager"

# ==============================
# Deadline Parser
# ==============================
def parse_deadline(text):
    try:
        return parser.parse(text, fuzzy=True).date()
    except:
        return None

# ==============================
# LLM Intent Detection
# ==============================
def extract_intent(text):
    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": """
You are a Slack workflow assistant.

Return ONLY pure JSON.

Possible intents:
- assign_task
- view_tasks
- view_meetings

Format:
{
  "intent": "",
  "member_name": "",
  "description": "",
  "deadline": ""
}

Rules:
- If assigning → assign_task
- If asking tasks → view_tasks
- If asking meetings → view_meetings
- Leave irrelevant fields empty
"""
            },
            {"role": "user", "content": text}
        ],
        temperature=0
    )

    raw = response.choices[0].message.content.strip()

    try:
        return json.loads(raw)
    except:
        return None

# =====================================================
# SLASH COMMAND: /assign
# =====================================================
@app.command("/assign")
def assign_task(ack, respond, command):
    ack()

    slack_user_id = command["user_id"]

    if not is_manager(slack_user_id):
        respond("❌ Only Managers can assign tasks.")
        return

    parts = command["text"].split()

    if len(parts) < 3:
        respond("Usage: /assign member_name description deadline")
        return

    member_name = parts[0]
    deadline = parts[-1]
    description = " ".join(parts[1:-1])

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT member_id FROM members
        WHERE member_name ILIKE %s
    """, (f"%{member_name}%",))

    row = cur.fetchone()

    if not row:
        respond("❌ Member not found.")
        cur.close()
        conn.close()
        return

    member_id = row[0]

    cur.execute("""
        INSERT INTO tasks (member_id, description, deadline)
        VALUES (%s, %s, %s)
    """, (member_id, description, deadline))

    conn.commit()
    cur.close()
    conn.close()

    respond(f"✅ Task assigned to {member_name}.")

# =====================================================
# SLASH COMMAND: /tasks
# =====================================================
@app.command("/tasks")
def fetch_tasks(ack, respond, command):
    ack()

    member_name = command["text"]

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT t.description, t.deadline
        FROM tasks t
        JOIN members m ON t.member_id = m.member_id
        WHERE m.member_name ILIKE %s
    """, (f"%{member_name}%",))

    rows = cur.fetchall()

    if not rows:
        respond("No tasks found.")
    else:
        message = "*Tasks:*\n"
        for desc, deadline in rows:
            message += f"• {desc} (Deadline: {deadline})\n"
        respond(message)

    cur.close()
    conn.close()

# =====================================================
# AI MODE: @Mention
# =====================================================
@app.event("app_mention")
def handle_mention(body, say):
    slack_user_id = body["event"]["user"]
    text = body["event"]["text"]

    ai_data = extract_intent(text)

    if not ai_data:
        say("⚠️ I couldn't understand your request.")
        return

    intent = ai_data.get("intent")
    member_name = ai_data.get("member_name")
    description = ai_data.get("description")
    deadline_text = ai_data.get("deadline")

    conn = get_connection()
    cur = conn.cursor()

    # ======================
    # VIEW TASKS
    # ======================
    if intent == "view_tasks":

        if not member_name:
            say("⚠️ Please specify a member name.")
            return

        cur.execute("""
            SELECT t.description, t.deadline
            FROM tasks t
            JOIN members m ON t.member_id = m.member_id
            WHERE m.member_name ILIKE %s
        """, (f"%{member_name}%",))

        rows = cur.fetchall()

        if not rows:
            say(f"No tasks found for {member_name}.")
        else:
            message = f"*Tasks for {member_name}:*\n"
            for desc, deadline in rows:
                message += f"• {desc} (Deadline: {deadline})\n"
            say(message)

        cur.close()
        conn.close()
        return

    # ======================
    # VIEW MEETINGS
    # ======================
    if intent == "view_meetings":

        cur.execute("""
            SELECT m.meeting_date, t.transcription_summary
            FROM meetings m
            JOIN transcription t ON m.transcription_id = t.transcription_id
            ORDER BY m.meeting_date DESC
        """)

        rows = cur.fetchall()

        if not rows:
            say("No meeting summaries found.")
        else:
            message = "*Meeting Transcriptions:*\n\n"
            for date, summary in rows:
                message += f"*Date:* {date}\n{summary}\n\n"
            say(message)

        cur.close()
        conn.close()
        return

    # ======================
    # ASSIGN TASK
    # ======================
    if intent == "assign_task":

        if not is_manager(slack_user_id):
            say("❌ Only Managers can assign tasks.")
            return

        if not member_name or not description:
            say("⚠️ Incomplete task details.")
            return

        if deadline_text:
            deadline = parse_deadline(deadline_text)
        else:
            deadline = datetime.today().date() + timedelta(days=3)

        if not deadline:
            say("⚠️ Could not understand deadline.")
            return

        cur.execute("""
            SELECT member_id FROM members
            WHERE member_name ILIKE %s
        """, (f"%{member_name}%",))

        row = cur.fetchone()

        if not row:
            say("❌ Member not found.")
            cur.close()
            conn.close()
            return

        member_id = row[0]

        cur.execute("""
            INSERT INTO tasks (member_id, description, deadline)
            VALUES (%s, %s, %s)
        """, (member_id, description, deadline))

        conn.commit()
        cur.close()
        conn.close()

        say(f"✅ Task assigned to {member_name}. Deadline: {deadline}")
        return

    say("⚠️ I couldn't determine your request.")

# ==============================
# Start Server
# ==============================
if __name__ == "__main__":
    app.start(port=3000)