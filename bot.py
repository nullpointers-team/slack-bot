import os
import psycopg2
from dotenv import load_dotenv
from slack_bolt import App

# Load environment variables
load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
DATABASE_URL = os.getenv("DATABASE_URL")

print("Database URL:", DATABASE_URL)

# Initialize Slack app
app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)

# -----------------------------
# Database connection
# -----------------------------
def get_connection():
    print("Connecting to database...")
    return psycopg2.connect(DATABASE_URL)

# -----------------------------
# /tasks
# -----------------------------
@app.command("/tasks")
def fetch_tasks(ack, respond, command):
    ack()

    member_id = command["text"].strip()

    if not member_id:
        respond("Usage: /tasks member_id")
        return

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT description, deadline
            FROM tasks
            WHERE member_id = %s
        """, (member_id,))

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

    except Exception as e:
        print("Error:", e)
        respond("Database error occurred.")

# -----------------------------
# /assign
# -----------------------------
@app.command("/assign")
def assign_task(ack, respond, command):
    ack()

    text = command["text"].strip()

    parts = text.split()

    if len(parts) < 3:
        respond("Usage: /assign member_id description deadline(YYYY-MM-DD)")
        return

    member_id = parts[0]
    deadline = parts[-1]
    description = " ".join(parts[1:-1])

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO tasks (member_id, description, deadline)
            VALUES (%s, %s, %s)
        """, (member_id, description, deadline))

        conn.commit()

        respond("✅ Task assigned successfully!")

        cur.close()
        conn.close()

    except Exception as e:
        print("Error:", e)
        respond("Database insert error.")

# -----------------------------
# /meetings
# -----------------------------
@app.command("/meetings")
def fetch_meetings(ack, respond):
    ack()

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT m.meeting_date, t.transcription_summary
            FROM meetings m
            JOIN transcription t
            ON m.transcription_id = t.transcription_id
        """)

        rows = cur.fetchall()

        if not rows:
            respond("No meetings found.")
        else:
            message = "*Meetings:*\n"
            for date, summary in rows:
                message += f"\n*Date:* {date}\n{summary}\n"
            respond(message)

        cur.close()
        conn.close()

    except Exception as e:
        print("Error:", e)
        respond("Database error.")

# -----------------------------
# Start server
# -----------------------------
if __name__ == "__main__":
    app.start(port=3000)