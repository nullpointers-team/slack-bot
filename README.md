# 🤖 Workflow Automator – AI Powered Slack Bot

Workflow Automator is an AI-powered Slack bot that automates **task assignment, task retrieval, and meeting summary access** using natural language.

The bot integrates **Slack, Groq LLM, and PostgreSQL** to allow teams to manage workflows directly from Slack. Managers can assign tasks using plain English, and team members can retrieve their tasks or meeting summaries instantly.

---

# 🚀 Features

## 🧠 Natural Language Task Assignment
Managers can assign tasks using natural language.

Example:

```
@Workflow Automator assign Mukundan to complete DevOps setup by tomorrow
```

The bot will:
- Extract task details using an LLM
- Identify the team member
- Parse the deadline
- Store the task in PostgreSQL

---

## 🔐 Role Based Access Control (RBAC)

Only **Managers** are allowed to assign tasks.

Example command:

```
/assign Govind Submit report 2026-03-10
```

If a non-manager tries:

```
❌ Only Managers can assign tasks.
```

---

## 📋 Retrieve Tasks

Users can retrieve tasks using either **slash commands** or **natural language**.

Example:

```
/tasks Govind
```

or

```
@Workflow Automator give the tasks of Govind
```

---

## 📝 Meeting Summaries

Meeting transcripts stored in the database can be retrieved directly from Slack.

Example:

```
@Workflow Automator show meeting summaries
```

---

## 📅 Intelligent Deadline Parsing

The bot understands different formats such as:

```
tomorrow
today
next week
2026-03-10
March 10
```

If the LLM fails to extract the deadline, the bot automatically parses it from the message.

---

# 🏗 System Architecture

```
Slack User
   │
   ▼
Slack Workspace
   │
   ▼
Slack App (Bot)
   │
   ▼
Ngrok Tunnel
   │
   ▼
Python Slack Bolt Server
   │
   ├── Groq LLM (Intent Extraction)
   │
   └── PostgreSQL Database (Neon)
```

Flow:

1. User sends message in Slack
2. Slack sends event to bot webhook
3. Ngrok tunnels request to local server
4. Bot extracts intent using Groq LLM
5. Bot queries or updates PostgreSQL
6. Response is sent back to Slack

---

# 🛠 Tech Stack

- **Python**
- **Slack Bolt SDK**
- **Groq LLM**
- **PostgreSQL (Neon Database)**
- **Ngrok**
- **Python Dotenv**

---

# 📂 Project Structure

```
Slack-Bot
│
├── bot.py
├── requirements.txt
├── .env
├── .gitignore
├── venv/
└── ngrok.exe
```

---

# 🗄 Database Schema

## Members Table

```
member_id
member_name
designation
password
slack_user_id
```

---

## Tasks Table

```
task_id
member_id
description
deadline
```

---

## Meetings Table

```
meeting_id
meeting_date
transcription_id
```

---

## Transcription Table

```
transcription_id
transcription_summary
```

---

# ⚙️ Setup Instructions

## 1. Clone Repository

```
git clone <repository-url>
cd Slack-Bot
```

---

## 2. Create Virtual Environment

```
python -m venv venv
```

Activate (Windows):

```
venv\Scripts\activate
```

---

## 3. Install Dependencies

```
pip install -r requirements.txt
```

---

# 🔑 Environment Variables

Create a `.env` file in the project root.

```
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_SIGNING_SECRET=your_slack_signing_secret
DATABASE_URL=your_postgres_connection_string
GROQ_API_KEY=your_groq_api_key
```

⚠️ Never push `.env` to GitHub.

---

# ▶️ Running the Bot

Start the bot:

```
python bot.py
```

You should see:

```
Bolt app is running! (development server)
```

---

# 🌐 Running Ngrok

In another terminal:

```
ngrok http 3000
```

Ngrok will generate a public URL:

```
https://abcd1234.ngrok-free.app
```

---

# 🔗 Update Slack URLs

Every time ngrok restarts the URL changes.

Update these in Slack App configuration.

### Event Subscriptions

```
https://your-ngrok-url/slack/events
```

### Slash Commands

For `/assign` and `/tasks`:

```
https://your-ngrok-url/slack/events
```

---

# 💬 Example Commands

### Assign Task

```
/assign Govind Submit report 2026-03-10
```

or

```
@Workflow Automator assign Govind to submit report by Friday
```

---

### View Tasks

```
/tasks Govind
```

or

```
@Workflow Automator show tasks of Govind
```

---

### View Meetings

```
@Workflow Automator show meeting summaries
```

---

# 🧪 Testing Checklist

Before deployment verify:

- Manager can assign tasks
- Developer cannot assign tasks
- Tasks are stored in database
- Tasks can be retrieved
- Meeting summaries are accessible
- Natural language assignment works
- Deadline parsing works correctly

---

# 🔒 Security Notes

- Do not commit `.env`
- Store API keys securely
- Use RBAC for sensitive commands
- Validate database inputs

---

# 🚧 Future Improvements

- Task status (Pending / Completed)
- Slack interactive buttons
- Automatic reminders
- Task analytics dashboard
- Cloud deployment (Render / Railway)
- AI meeting summarization
- Task priority classification

---

# 📄 License

MIT License
