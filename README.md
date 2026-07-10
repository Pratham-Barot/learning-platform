# StudyForge

AI study assistant that turns YouTube videos, PDFs, and web articles into structured notes, quizzes, and an interactive chat — with PDF export.

## Features

- **Multi-source input** — YouTube links, PDF uploads, and blog/article URLs
- **Smart notes** — LangGraph pipeline with rolling context summarization for long videos
- **Auto quiz** — Difficulty-aware multiple-choice questions with weak-topic tracking
- **RAG chat** — Ask questions about your session content (ChromaDB + Gemini)
- **PDF export** — Download notes as PDF (English and Hindi supported)
- **Output languages** — Generate notes and quizzes in English or Hindi
- **User accounts** — JWT auth, session history, quiz attempt tracking

## Tech Stack

| Layer | Stack |
|-------|-------|
| Frontend | React, TypeScript, Vite |
| Backend | FastAPI, PostgreSQL, JWT |
| AI | Google Gemini, LangGraph |
| Vectors | ChromaDB |

## Project Structure

```text
Link_to_Text/
├── backend/          # FastAPI API (auth, sessions, chat, export)
├── frontend/         # React web app
├── pipeline.py       # LangGraph study pipeline
├── chatbot.py        # Session-scoped RAG chat
├── content_*.py      # Chunking & summarization for long content
├── notes_generation.py
├── quiz_generation.py
├── pdf_generator.py
└── WEB_SETUP.md      # Detailed setup guide
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL
- [Gemini API key](https://aistudio.google.com/apikey)

### 1. Environment

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_key
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=study_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=study_assistant
JWT_SECRET=your_long_random_secret
```

Create `frontend/.env`:

```env
VITE_API_URL=http://localhost:8000
```

### 2. Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd backend
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and register an account.

For PostgreSQL setup, database tables, and full API reference, see [WEB_SETUP.md](WEB_SETUP.md).

## Pipeline

```text
Source (YouTube / PDF / URL)
  → prepare_source_for_notes (rolling outline for long videos)
  → notes_generator
  → difficulty_detector
  → quiz_generator
```

Chat uses session-scoped Chroma vectors built from generated notes.

## Tests

```bash
source .venv/bin/activate
pytest tests/
```

## License

MIT
