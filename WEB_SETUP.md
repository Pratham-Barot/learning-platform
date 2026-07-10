# Website Setup (React + FastAPI + PostgreSQL, no Docker)

## Architecture

```text
React (localhost:5173) → FastAPI + JWT (localhost:8000) → PostgreSQL (localhost:5432)
                                                      ↘ chroma_data/ (vectors)
```

The Streamlit `app.py` has been removed. Use the React website in `frontend/` and the API in `backend/`.

## 1. PostgreSQL

```bash
sudo apt install postgresql postgresql-contrib
sudo -u postgres psql
```

```sql
CREATE DATABASE study_assistant;
CREATE USER study_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE study_assistant TO study_user;
```

Use pgAdmin only as a GUI to inspect tables.

## 2. Environment

In project root `.env`:

- `GEMINI_API_KEY`
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- `JWT_SECRET` (use a long random string in production)

In `frontend/.env`:

- `VITE_API_URL=http://localhost:8000`

## 3. Backend

```bash
cd backend
source ../.venv/bin/activate
pip install -r requirements.txt
fuser -k 8000/tcp   # if port is busy
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

## 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open: http://localhost:5173 — register or sign in first.

## Database tables

| Table | Purpose |
|-------|---------|
| `users` | Accounts (email + password hash) |
| `study_sessions` | Notes, quiz, source — per user |
| `chat_messages` | Chat history per session |
| `quiz_attempts` | Saved quiz scores per user |

## API Endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/auth/register` | No | Create account |
| POST | `/api/auth/login` | No | Get JWT token |
| GET | `/api/auth/me` | Yes | Current user |
| POST | `/api/generate` | Yes | Start generation |
| GET | `/api/generate/{job_id}/status` | Yes | Poll job |
| GET | `/api/sessions` | Yes | List your sessions |
| GET | `/api/sessions/{id}` | Yes | Load session |
| PATCH | `/api/sessions/{id}` | Yes | Rename |
| DELETE | `/api/sessions/{id}` | Yes | Delete |
| GET | `/api/sessions/{id}/pdf` | Yes | Download PDF |
| POST | `/api/sessions/{id}/quiz/submit` | Yes | Submit quiz (saved to DB) |
| GET | `/api/sessions/{id}/quiz/attempts` | Yes | Quiz history |
| GET | `/api/sessions/{id}/chat` | Yes | Chat history |
| POST | `/api/sessions/{id}/chat/stream` | Yes | Streaming chat |

Send JWT as: `Authorization: Bearer <token>`

## Reused Python modules (project root)

- `pipeline.py`, `chatbot.py`, `source_router.py`, `web_extractor.py`
- `pdf_generator.py`, `notes_generation.py`, `quiz_generation.py`
