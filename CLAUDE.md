# Gennis — Project Config for Claude

## Overview

Education center management system (ERP). Flask backend + React frontend (served as static build).
Production URL: `https://admin.gennis.uz`
Git branch for active dev: `server` (push here, not `master`)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.14, Flask 2.2.3 |
| ORM | SQLAlchemy 2.0.7, Flask-SQLAlchemy 3.0.3 |
| Migrations | Flask-Migrate (Alembic) |
| Auth | Flask-JWT-Extended 4.4.4 (access 1h, refresh 30d) |
| Task queue | Celery 5.5.3 + Redis (broker db=2, result db=2) |
| WebSocket | Flask-SocketIO (eventlet, Redis message queue db=0) |
| API | Flask-RESTful 0.3.10 |
| Admin UI | Flask-Admin 1.6.1 (basic-auth protected at `/admin`) |
| PDF/Excel | ReportLab, PyPDF2, openpyxl, pandas |
| AI | OpenAI via proxy (`OPENAI_BASE_URL`) |
| Telegram | Bot token in `TOKEN` env var |
| CORS | Flask-CORS, allows all origins on `/api/*` and `/media/*` |

---

## Production Infrastructure

| Item | Value |
|------|-------|
| DB host | `5.129.242.151` |
| DB name | `gennis` |
| DB user | `postgres` |
| DB port | `5432` |
| Redis | `localhost:6379` |
| Celery broker | `redis://localhost:6379/2` |
| SocketIO queue | `redis://localhost:6379/0` |
| Management DB | `postgresql://postgres:...@localhost:5432/gennis_management` |
| Classroom server | `classroom.gennis.uz` |
| School server | `https://school.gennis.uz` |
| Process manager | gunicorn via systemd (`gennis_app`) |
| Logs | `journalctl -u gennis_app -n 200 --no-pager` |

**DB credentials are in `.env` — never hardcode.**

---

## Project Structure

```
gennis/
├── app.py                         # App factory, blueprint registration, SocketIO handlers
├── backend/
│   ├── models/
│   │   ├── models.py              # ALL core ORM models (single file, ~1500+ lines)
│   │   ├── config.py              # Flask/SQLAlchemy config, reads from .env
│   │   └── settings.py            # iterate_models helper
│   ├── functions/
│   │   ├── utils.py               # update_salary, find_calendar_date, api, refreshdatas
│   │   ├── filters.py             # teacher_filter, new_students_filters, group_filter
│   │   ├── functions.py           # Misc utility functions
│   │   └── debt_salary_update.py  # Debt/salary recalculation helpers
│   ├── routes/
│   │   ├── base_routes.py         # login, get_user, register, my_profile, block_information2
│   │   ├── checks.py              # Generic check routes
│   │   ├── classroom/
│   │   │   └── send_user_data.py  # send_user_data, send_student_data, send_parent_data
│   │   └── views.py
│   ├── account/
│   │   ├── payment.py             # Payment CRUD, teacher salary payments
│   │   ├── salary.py              # Teacher salary routes (block_salary, teacher_salary, get_teacher_balance)
│   │   ├── account.py             # General accounting
│   │   ├── models.py              # Accounting models (TeacherSalary, TeacherBlackSalary, etc.)
│   │   ├── utils.py               # Account utilities
│   │   ├── views.py               # Account blueprint registration
│   │   ├── overhead_type.py       # Overhead type management
│   │   ├── overhead_capital.py    # Capital overhead
│   │   ├── branch_transaction.py  # Branch transactions
│   │   ├── branch_loan.py         # Branch loans
│   │   └── overall_datas/
│   │       ├── home_screen.py     # Home screen aggregated data
│   │       ├── daily_datas.py     # Daily accounting data
│   │       └── views.py
│   │   └── profile/               # Director/investor profile views
│   ├── teacher/
│   │   ├── teacher.py             # Teacher CRUD, get_teacher_balance, attendance_delete
│   │   ├── models.py              # Teacher-specific models
│   │   ├── utils.py               # Teacher utilities
│   │   ├── lesson_plan.py         # Lesson plan management
│   │   ├── observation.py         # Teacher observation
│   │   ├── teacher_delete.py      # Teacher deletion logic
│   │   ├── teacher_home_page.py   # Teacher home page data
│   │   ├── assistent/crud.py      # Assistant CRUD
│   │   └── classroom/             # Classroom-facing teacher routes
│   ├── student/
│   │   ├── change_student.py      # Student update routes
│   │   ├── models.py              # Student-specific models
│   │   ├── student_functions.py   # Student utilities
│   │   ├── calling_to_students.py # VATS calling integration
│   │   ├── functions.py           # Student helper functions
│   │   └── platform/              # Platform-specific student routes
│   ├── group/
│   │   ├── create_group.py        # Group creation, student add/remove, time_table management
│   │   ├── change.py              # Group update routes
│   │   ├── basic.py               # Group basic info routes
│   │   ├── models.py              # Group-specific models
│   │   └── classroom/
│   │       ├── attendance.py      # Attendance recording
│   │       ├── profile.py         # Group profile
│   │       └── test.py            # Group tests
│   ├── lead/
│   │   ├── crud.py                # Lead CRUD operations
│   │   ├── functions.py           # Lead utilities
│   │   ├── models.py              # Lead models
│   │   └── views.py
│   ├── celery/
│   │   ├── celery_app.py          # Celery app init + beat schedule
│   │   ├── tasks.py               # Periodic task definitions
│   │   ├── recompute_salaries.py  # Celery: recompute all teacher salaries
│   │   ├── overhead_logs.py       # Celery: overhead log tasks
│   │   ├── debt_calls.py          # Celery: debt reminder calls
│   │   ├── lead_calls.py          # Celery: lead follow-up calls
│   │   ├── new_students.py        # Celery: new student processing
│   │   ├── check_lesson_plan.py   # Celery: lesson plan checks
│   │   └── worker.py              # Worker entrypoint
│   ├── time_table/
│   │   ├── route.py               # Time table routes
│   │   ├── room.py                # Room management
│   │   ├── models.py              # Time table models
│   │   └── views.py
│   ├── home_page/
│   │   └── route.py               # Public home page data (get_home_info)
│   ├── certificate/
│   │   └── views.py               # Certificate generation/listing
│   ├── book/                      # Book/library management
│   ├── parent/                    # Parent portal routes
│   ├── mobile/                    # Mobile app parent routes
│   ├── school/                    # School management (separate DB context)
│   ├── reports/                   # Report generation
│   ├── tasks/                     # Task/mission management system
│   │   ├── missions/              # Mission CRUD, comments, attachments, proofs
│   │   ├── admin/                 # Admin task views
│   │   └── teacher/               # Teacher-facing task routes
│   ├── telegram_bot/              # Telegram bot handlers
│   ├── for_programmers/           # Admin tools (shows ALL data including disabled)
│   ├── chat_analyzer/             # AI chat analysis
│   ├── vats/                      # VATS VoIP integration
│   └── admin_request/             # Admin request handling
```

---

## Key Models (backend/models/models.py)

| Model | Table | Notes |
|-------|-------|-------|
| `Users` | `users` | Core user. `balance` = teacher remaining salary, student balance, etc. |
| `Teachers` | `teachers` | Links to `Users` via `user_id`. Has `groups` M2M. |
| `Students` | `students` | Links to `Users` via `user_id`. Has `groups` M2M, `subject` M2M. |
| `Groups` | `groups` | Has `subject_id`, `level_id`. |
| `Subjects` | `subjects` | Has `disabled` bool. Filter `disabled==False OR NULL` in all listing routes. |
| `SubjectLevels` | `subjectlevels` | Has `disabled` bool. |
| `TeacherSalary` | `teachersalary` | Per-month salary rows. `remaining_salary` = `total_salary - (taken_money + black_salary + total_fine - debt)`. `status=False/None` = open month. |
| `TeacherBlackSalary` | `teacherblacksalary` | Group-level salary per attendance period. |
| `Group_Room_Week` | `group_room_week` | Time table entry per group. |
| `time_table_student` | `time_table_student` | Association table: `(student_id, group_room_week)`. Use raw SQL DELETE — ORM causes StaleDataError on duplicate rows. |
| `Attendance` | `attendance` | Attendance per group session. |
| `AttendanceDays` | `attendancedays` | Per-student attendance record. Can be None — always null-check before accessing. |
| `Locations` | `locations` | Branch/location. |
| `Roles` | `roles` | `type_role`: director, student, teacher, programmer, staff, parent. |
| `PhoneList` | `phonelist` | User phones. `personal=True` = own phone, `parent=True` = parent phone. |
| `Lead` | `leads` | Prospective student leads. |
| `ApiLog` | `apilog` | Auto-logged per request via `after_request` middleware. |

---

## Critical Business Logic

### Teacher Balance (`user.balance`)

`update_salary(teacher_id)` in `backend/functions/utils.py`:
- Queries all open `TeacherSalary` rows (status=False or None) for that teacher
- Sets `user.balance = SUM(remaining_salary)` across those rows
- Must call `db.session.refresh(user)` after to see the updated value in the same request

**Every route that returns teacher `user.balance` must call `update_salary` first:**

| Route | File | Status |
|-------|------|--------|
| `GET /api/base/login` | `base_routes.py` | ✅ Fixed |
| `GET /api/base/get_user` | `base_routes.py` | ✅ Fixed |
| `GET /api/base/my_profile/<id>` | `base_routes.py` | ✅ Fixed |
| `GET /api/teacher/get_teacher_balance/<id>` | `teacher/teacher.py` | ✅ Fixed |
| `GET /api/classroom/send_student_data/<id>` | `routes/classroom/send_user_data.py` | ✅ Fixed |

`TeacherSalary.remaining_salary` formula (stored in DB):
```
remaining_salary = total_salary - (taken_money + black_salary + total_fine - debt)
```

### Subjects Disabled Filter

All subject listing routes must filter: `or_(Subjects.disabled == False, Subjects.disabled == None)`

**Fixed routes:**
- `base_routes.py` — `block_information2`, `get_user`, `register`
- `home_page/route.py` — `get_home_info`
- `certificate/views.py` — `certificate`
- `group/create_group.py` — `create_group_tools`
- `functions/filters.py` — `teacher_filter`, `new_students_filters`, `group_filter`

**Exception:** `for_programmers/for_programmers.py` intentionally shows all subjects (admin tool).

### Payment Loop Pattern

When iterating payments affecting multiple teachers, collect unique teacher IDs and call `update_salary` once per teacher AFTER the loop — never inside the loop:
```python
affected_ids = set()
for item in items:
    ...
    affected_ids.add(teacher.id)
db.session.commit()
for tid in affected_ids:
    teacher = Teachers.query.filter(Teachers.id == tid).first()
    update_salary(teacher.user_id)
```

### time_table_student Deletion

Use raw SQL — ORM `student.time_table.remove(time)` causes `StaleDataError` on duplicate rows:
```python
grw_ids = [t.id for t in time_table]
if grw_ids:
    db.session.execute(
        text("DELETE FROM time_table_student WHERE student_id = :sid AND group_room_week = ANY(:grw_ids)"),
        {"sid": student.id, "grw_ids": grw_ids}
    )
    db.session.commit()
```

---

## Connected Projects

| Project | Path | Role |
|---------|------|------|
| Classroom | `/home/rimefara/projects/classroom/` | Separate Flask app, calls gennis API. No own git repo. |

**Classroom → Gennis API calls:**
- Login: `POST /api/base/login` → `GET /api/classroom/send_user_data/<username>`
- Refresh: `GET /api/teacher/get_teacher_balance/<platform_id>`
- Student data: `GET /api/classroom/send_student_data/<user_id>`

Classroom login saves fresh balance: `login_balance = user_get.get('balance')` from gennis login response, applied after `add_gennis_user_data()` overwrites `user_get`.

---

## Environment Variables (.env)

| Variable | Purpose |
|----------|---------|
| `DB_HOST` | PostgreSQL host (production: `5.129.242.151`) |
| `FLASK_DB_USER` | DB user |
| `FLASK_DB_PASSWORD` | DB password |
| `FLASK_DB_NAME` | DB name (`gennis`) |
| `FLASK_DB_PORT` | DB port (`5432`) |
| `MANAGEMENT_DB_URL` | Management DB (separate) |
| `BASE_URL` | `https://admin.gennis.uz` |
| `CLASSROOM_SERVER_URL` | `classroom.gennis.uz` |
| `SCHOOL_SERVER_URL` | `https://school.gennis.uz` |
| `CELERY_BROKER_URL` | `redis://localhost:6379/2` |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/2` |
| `TOKEN` | Telegram bot token |
| `OPENAI_API_KEY` | OpenAI key (proxied) |
| `OPENAI_BASE_URL` | Cloudflare worker proxy |
| `VATS_DOMAIN` | VoIP domain |
| `VATS_API_KEY` | VoIP API key |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | Flask-Admin basic auth |

---

## Git Workflow

- Active branch: `server`
- Remote: `https://github.com/Begzod10/gennis-1.0.git`
- Always push to `origin server`
- Commit format: `type(scope): description` — e.g. `fix(balance): ...`, `fix(subjects): ...`
- Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`

---

## Common Queries (Production DB)

```bash
# Connect
PGPASSWORD='<from .env>' psql -h 5.129.242.151 -U postgres -d gennis

# Unused subjects (no groups)
SELECT id, name, disabled FROM subjects WHERE id NOT IN (SELECT DISTINCT subject_id FROM groups WHERE subject_id IS NOT NULL);

# Teacher salary open months
SELECT * FROM teachersalary WHERE teacher_id = <id> AND (status = false OR status IS NULL);

# Check user balance
SELECT id, name, balance FROM users WHERE id = <id>;
```

---

## Deployment

Production runs via systemd `gennis_app`. After pushing to `origin/server`, SSH to server and:
```bash
cd /home/gennis && git pull origin server && sudo systemctl restart gennis_app
```
Check logs: `journalctl -u gennis_app -n 200 --no-pager`
