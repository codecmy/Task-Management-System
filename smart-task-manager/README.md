# Smart Task Manager

![Python](https://img.shields.io/badge/python-3.13-blue)![Flask](https://img.shields.io/badge/flask-3.1-lightgrey)![PostgreSQL](https://img.shields.io/badge/postgres-16-31648c)![Docker](https://img.shields.io/badge/docker-compose-2496ed)![tests](https://img.shields.io/badge/tests-80_passing-brightgreen)

A full-stack task manager built with Flask, featuring real-time WebSocket updates, Pandas/NumPy analytics, a REST API, and Docker-based PostgreSQL deployment.

---

## Features

- Full task CRUD with title, description, priority (low/medium/high), and due dates
- Filters by status, priority, and text search
- Real-time dashboard updates via SocketIO (no page reload needed)
- Analytics page with completion rates, overdue/due-soon tracking, and priority breakdown (powered by Pandas & NumPy)
- REST API (JSON) for all task operations
- Session-based authentication (register, login, logout)
- Responsive design
- Docker Compose deployment with PostgreSQL 16

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Flask 3.1, Flask-SQLAlchemy, Flask-Login, Flask-SocketIO |
| Frontend | Jinja2 templates, vanilla JavaScript, Socket.IO client |
| Database | PostgreSQL 16 (production), SQLite (development/test) |
| Analytics | Pandas 3.x, NumPy |
| DevOps | Docker Compose, gunicorn + eventlet worker |
| Testing | pytest 9.x, pytest-cov |

---

## Screenshots

> Add screenshots to this section.
>
> **Suggested captures:**
>
> 1. **Dashboard** — task list with a mix of priorities, statuses, and due dates; filters visible; stats grid showing counts
> 2. **Analytics page** — completion rate, overdue/due-soon badges, priority breakdown cards
> 3. **Mobile view** — dashboard on a narrow viewport demonstrating responsive layout
>
> Place images in `screenshots/` directory and reference them:
>
> ```markdown
> ![Dashboard](screenshots/dashboard.png)
> ![Analytics](screenshots/analytics.png)
> ```

---

## Setup

### Local Development

```bash
# 1. Clone and enter the project
cd smart-task-manager

# 2. Create a virtual environment
python -m venv venv
.\venv\Scripts\Activate    # Windows
source venv/bin/activate   # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run (uses SQLite by default)
python app.py

# 5. Open in browser
# http://localhost:5000
```

### Docker (PostgreSQL)

```bash
docker compose up --build
```

The app will be available at `http://localhost:5000`.  
PostgreSQL is configured with user `smarttask`, database `smart_tasks`.

---

## Running Tests

```bash
pytest -v        # 80 tests
pytest --cov     # with coverage report
```

Tests use an in-memory SQLite database and do not require Docker or PostgreSQL.

---

## REST API

All API endpoints require authentication (session cookie).

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/tasks` | Create a task |
| `GET` | `/tasks` | List tasks (optional: `?status=`, `?priority=`, `?q=`) |
| `PUT` | `/tasks/<id>` | Update a task |
| `DELETE` | `/tasks/<id>` | Delete a task |
| `GET` | `/api/analytics` | Get analytics data (JSON) |

---

## Project Structure

```
smart-task-manager/
├── app.py              # Flask application + routes
├── analytics.py        # Pandas/NumPy analytics functions
├── models.py           # SQLAlchemy models (User, Task)
├── extensions.py       # Flask extensions (db, login_manager, socketio)
├── config.py           # Configuration (DB URL, secret key)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── wait-for-db.py      # Docker entrypoint helper
├── schema.sql          # PostgreSQL schema dump
├── static/
│   ├── css/style.css
│   └── js/
│       ├── main.js
│       └── socket.js   # Socket.IO client
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── analytics.html
│   ├── login.html
│   ├── register.html
│   └── edit_task.html
└── tests/
    ├── conftest.py
    ├── test_auth.py
    ├── test_api.py
    ├── test_dashboard.py
    ├── test_tasks.py
    ├── test_analytics.py
    ├── test_database.py
    └── test_websocket.py
```
