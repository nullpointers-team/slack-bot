import os
import psycopg2
import json
from dotenv import load_dotenv
from slack_bolt import App
from groq import Groq
from dateutil import parser
from datetime import datetime, timedelta

# -------------------------
# LOAD ENV
# -------------------------
load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
DATABASE_URL = os.getenv("DATABASE_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

print("🚀 Slack Hybrid Bot Starting...")
print("Database URL:", DATABASE_URL)

app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
groq_client = Groq(api_key=GROQ_API_KEY)

# -------------------------
# DATABASE CONNECTION
# -------------------------
def get_connection():
    return psycopg2.connect(DATABASE_URL)

# -------------------------
# ROLE CHECK USING SLACK ID
# -------------------------
def is_manager_by_slack_id(slack_user_id):
    print("🔎 Checking role using Slack ID:", slack_user_id)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT designation FROM members
        WHERE slack_user_id = %s
    """, (slack_user_id,))

    row = cur.fetchone()
    print("🗂 DB Role Row:", row)

    cur.close()
    conn.close()

    return row and row[0].lower() == "manager"

# -------------------------
# PARSE DEADLINE
# -------------------------
def parse_deadline(text):
    try:
        return parser.parse(text, fuzzy=True).date()
    except:
        return None

# -------------------------
# AI EXTRACTION
# -------------------------
def extract_task_details(text):
    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": """
Return ONLY pure JSON.
No explanation text.

Format:
{
  "member_name": "",
  "description": "",
  "deadline": ""
}

If deadline missing, leave empty.
"""
            },
            {"role": "user", "content": text}
        ],
        temperature=0
    )

    raw = response.choices[0].message.content.strip()
    print("🤖 AI RAW RESPONSE:", raw)

    try:
        return json.loads(raw)
    except:
        return None

# =====================================================
# SLASH COMMAND: /assign (NAME-BASED)
# =====================================================
@app.command("/assign")
def assign_task(ack, respond, command):
    ack()
    print("⚡ Slash /assign Triggered")

    slack_user_id = command["user_id"]

    if not is_manager_by_slack_id(slack_user_id):
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

    # Lookup member_id from name
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

    respond(f"✅ Task assigned to {member_name} (Structured Mode).")

# =====================================================
# SLASH COMMAND: /tasks
# =====================================================
@app.command("/tasks")
def fetch_tasks(ack, respond, command):
    ack()
    print("⚡ Slash /tasks Triggered")

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
        msg = "*Tasks:*\n"
        for desc, deadline in rows:
            msg += f"• {desc} (Deadline: {deadline})\n"
        respond(msg)

    cur.close()
    conn.close()

# =====================================================
# AI NATURAL LANGUAGE: @mention
# =====================================================
@app.event("app_mention")
def handle_mention(body, say, client):
    print("🔥 Mention Triggered")

    slack_user_id = body["event"]["user"]
    text = body["event"]["text"]

    if not is_manager_by_slack_id(slack_user_id):
        say("❌ Only Managers can assign tasks.")
        return

    task_data = extract_task_details(text)

    if not task_data:
        say("⚠️ AI extraction failed.")
        return

    member_name = task_data.get("member_name", "")
    description = task_data.get("description", "")
    deadline_text = task_data.get("deadline", "")

    if not member_name or not description:
        say("⚠️ Could not extract task details.")
        return

    if not deadline_text:
        deadline = datetime.today().date() + timedelta(days=3)
    else:
        deadline = parse_deadline(deadline_text)

    if not deadline:
        say("⚠️ Could not understand deadline.")
        return

    conn = get_connection()
    cur = conn.cursor()

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

    say(f"✅ Task assigned to {member_name} (AI Mode). Deadline: {deadline}")

# =====================================================
# START SERVER
# =====================================================
if __name__ == "__main__":
    app.start(port=3000)