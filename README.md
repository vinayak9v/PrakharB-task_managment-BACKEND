# AI-PS Platform — Setup & Run Guide

## Tech Stack
- **Backend:** FastAPI (Python)
- **Database:** MySQL + SQLAlchemy ORM (tables auto-create on run)
- **Auth:** JWT Tokens
- **WhatsApp:** Green API
- **AI:** OpenAI GPT-4o
- **Scheduler:** APScheduler (cron jobs for reminders)

---

## Folder Structure

```
ai_ps_backend/
├── app/
│   ├── main.py                    ← FastAPI app entry point
│   ├── api/
│   │   └── v1/
│   │       ├── router.py          ← All routes combined
│   │       └── endpoints/
│   │           ├── auth.py        ← Login, change password
│   │           ├── users.py       ← User management
│   │           ├── projects.py    ← Project management
│   │           ├── tasks.py       ← Task CRUD + escalation
│   │           ├── meetings.py    ← Meetings + AI summary
│   │           ├── eod.py         ← EOD reports
│   │           ├── dashboard.py   ← Dashboard summary
│   │           └── notifications.py ← WhatsApp broadcast
│   ├── core/
│   │   ├── config.py              ← All settings from .env
│   │   ├── security.py            ← Password hash + JWT
│   │   └── dependencies.py        ← Auth middleware, role checks
│   ├── db/
│   │   ├── session.py             ← DB engine + session
│   │   └── init_db.py             ← Auto table creation + super admin
│   ├── models/
│   │   └── models.py              ← All ORM models (auto creates tables)
│   ├── schemas/
│   │   ├── user.py                ← Pydantic schemas for users
│   │   ├── project.py             ← Pydantic schemas for projects
│   │   ├── task.py                ← Pydantic schemas for tasks
│   │   ├── meeting_eod.py         ← Pydantic schemas for meetings + EOD
│   │   └── dashboard.py           ← Pydantic schemas for dashboard
│   └── services/
│       ├── whatsapp_service.py    ← Green API integration + message templates
│       ├── ai_service.py          ← OpenAI meeting summary + task extraction
│       └── scheduler.py           ← Cron jobs (EOD, reminders, daily todo)
├── requirements.txt
├── .env.example
└── README.md
```

---

## Step 1 — Prerequisites

Install these before starting:

1. **Python 3.11+** — https://python.org
2. **MySQL 8.0+** — https://dev.mysql.com/downloads/
3. **Git** (optional)

---

## Step 2 — Clone / Download Project

```bash
# If you have the zip, extract it. Or clone:
cd ai_ps_backend
```

---

## Step 3 — Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac / Linux
python3 -m venv venv
source venv/bin/activate
```

---

## Step 4 — Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Step 5 — Create MySQL Database

Open MySQL and run:

```sql
CREATE DATABASE ai_ps_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

That's it. Tables will be created automatically when you run the app.

---

## Step 6 — Setup .env File

```bash
cp .env.example .env
```

Edit `.env` with your actual values:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=root    ← Change this
DB_NAME=ai_ps_db

SECRET_KEY=any_random_long_string  ← Change this

# WhatsApp (optional for MVP testing)
GREEN_API_INSTANCE_ID=your_id
GREEN_API_TOKEN=your_token

# OpenAI (optional for AI features)
OPENAI_API_KEY=sk-...

# Prakhar Sir's login
SUPER_ADMIN_NAME=Prakhar Bagora
SUPER_ADMIN_PHONE=8827219873    ← Change to real number
SUPER_ADMIN_PASSWORD=Admin@123     ← Change this
```

---

## Step 7 — Run the Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**What happens automatically on first run:**
1. ✅ All MySQL tables are created (users, projects, tasks, meetings, eod_reports, etc.)
2. ✅ Prakhar Sir's Super Admin account is created
3. ✅ Cron jobs start (EOD reminders, daily to-do, etc.)

---

## Step 8 — Access the Platform

| URL | Description |
|-----|-------------|
| http://localhost:8000 | Health check |
| http://localhost:8000/docs | **Swagger UI — Test all APIs** |
| http://localhost:8000/redoc | API Documentation |

---

## Step 9 — First Login

Use Swagger UI at `/docs`:

1. Go to `POST /api/v1/auth/login`
2. Enter:
   ```json
   {
     "phone": "919999999999",
     "password": "Admin@123"
   }
   ```
3. Copy the `access_token` from response
4. Click **Authorize** button in Swagger
5. Paste token as: `Bearer your_token_here`
6. Now all APIs are accessible

---

## All Available API Endpoints

### Auth
| Method | URL | Description |
|--------|-----|-------------|
| POST | /api/v1/auth/login | Login |
| GET | /api/v1/auth/me | Current user info |
| POST | /api/v1/auth/change-password | Change password |

### Users
| Method | URL | Description |
|--------|-----|-------------|
| POST | /api/v1/users/ | Create user (sends WA credentials) |
| GET | /api/v1/users/ | List all users |
| GET | /api/v1/users/{id} | Get user |
| PUT | /api/v1/users/{id} | Update user |
| DELETE | /api/v1/users/{id} | Deactivate user |

### Projects
| Method | URL | Description |
|--------|-----|-------------|
| POST | /api/v1/projects/ | Create project |
| GET | /api/v1/projects/ | List projects |
| PUT | /api/v1/projects/{id} | Update project |
| POST | /api/v1/projects/{id}/members | Add member |
| GET | /api/v1/projects/{id}/members | List members |

### Tasks
| Method | URL | Description |
|--------|-----|-------------|
| POST | /api/v1/tasks/ | Create task (auto WA notification) |
| GET | /api/v1/tasks/ | List tasks |
| GET | /api/v1/tasks/overdue | Get overdue tasks |
| GET | /api/v1/tasks/{id} | Task detail |
| PUT | /api/v1/tasks/{id} | Update task |
| PATCH | /api/v1/tasks/{id}/status | Update status (triggers escalation) |
| POST | /api/v1/tasks/{id}/followup | Add follow-up note |

### Meetings
| Method | URL | Description |
|--------|-----|-------------|
| POST | /api/v1/meetings/ | Create meeting |
| GET | /api/v1/meetings/ | List meetings |
| POST | /api/v1/meetings/{id}/upload-notes | Add meeting notes |
| POST | /api/v1/meetings/{id}/generate-summary | AI summary + auto tasks |

### EOD Reports
| Method | URL | Description |
|--------|-----|-------------|
| POST | /api/v1/eod/submit | Submit EOD |
| GET | /api/v1/eod/daily-summary | Today's EOD summary |
| GET | /api/v1/eod/non-submitters | Who hasn't submitted |
| POST | /api/v1/eod/send-summary-to-admin | Send WA summary to Prakhar Sir |

### Dashboard
| Method | URL | Description |
|--------|-----|-------------|
| GET | /api/v1/dashboard/summary | Full dashboard data |
| GET | /api/v1/dashboard/project/{id} | Project-wise stats |

### Notifications
| Method | URL | Description |
|--------|-----|-------------|
| POST | /api/v1/notifications/broadcast | Send WA to all/selected users |
| POST | /api/v1/notifications/send-eod-reminders | EOD reminder blast |
| POST | /api/v1/notifications/send-task-reminders | Task reminder blast |

---

## Tables Auto-Created in MySQL

When you run the app, these tables are created automatically:

| Table | Purpose |
|-------|---------|
| users | All users — Super Admin, Project Heads, Team Members |
| projects | 9 projects (Garima Group, GVV, etc.) |
| project_members | Who belongs to which project |
| tasks | All tasks with status, deadline, priority |
| task_follow_ups | Follow-up history for each task |
| meetings | Meeting records |
| eod_reports | Daily EOD submissions |
| notifications | Notification history |
| audit_logs | All actions tracked |

---

## WhatsApp Setup (Green API)

1. Go to https://green-api.com
2. Create account → Get Instance ID and Token
3. Scan QR code with your WhatsApp
4. Add to `.env`:
   ```
   GREEN_API_INSTANCE_ID=1234567890
   GREEN_API_TOKEN=abcdef123456
   ```

**Note:** Without Green API configured, the system runs in MOCK mode — messages are printed in console instead of sending.

---

## Cron Jobs Running Automatically

| Time | Job |
|------|-----|
| 7:00 AM | Daily to-do sent to Prakhar Sir via WhatsApp |
| 5:45 PM | EOD reminders sent to all non-submitters |
| 7:00 PM | EOD summary sent to Prakhar Sir |
| Every hour | Overdue tasks auto-marked as Delayed |

---

## Common Issues

**MySQL connection error:**
```
Check DB_HOST, DB_USER, DB_PASSWORD in .env
Make sure MySQL service is running
```

**Port already in use:**
```bash
uvicorn app.main:app --reload --port 8001
```

**Module not found:**
```bash
pip install -r requirements.txt
Make sure virtual environment is activated
```
