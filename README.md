# StudyMate AI 🎓

> **AI-powered learning assistant for students** — Upload study materials, generate summaries, ask questions, take quizzes, and plan your exam preparation — all powered by a local Ollama model (Qwen 2.5 7B).

---

## Features

| Feature | Description |
|---|---|
| 📤 **Document Upload** | PDF, DOCX, TXT support with automatic text extraction |
| 📝 **AI Summaries** | Quick summary, detailed summary, and key bullet points |
| 💬 **Ask Notes** | Chat with your documents — get answers grounded in your material |
| 🧪 **MCQ Quiz** | 5–20 questions, Easy/Medium/Hard, with scoring and explanations |
| 📋 **Exam Prep** | 2-mark, 5-mark, and 10-mark questions with model answers |
| 📅 **Study Planner** | Personalized day-by-day study schedule based on your exam date |
| 📊 **Dashboard** | Track documents, quiz scores, and progress with charts |

---

## Architecture

```
study_ai/
├── backend/                    # FastAPI application
│   ├── main.py                 # App entry point, router registration
│   ├── config.py               # Settings (env vars via pydantic-settings)
│   ├── database.py             # Async SQLAlchemy setup
│   ├── models/models.py        # ORM models (Document, Quiz, StudyPlan, …)
│   ├── routes/                 # API route handlers
│   │   ├── documents.py        # Upload, list, get, summary
│   │   ├── chat.py             # Q&A conversations
│   │   ├── quiz.py             # Quiz generation and submission
│   │   ├── exam.py             # Exam question generation
│   │   ├── planner.py          # Study plan CRUD
│   │   └── dashboard.py        # Dashboard statistics
│   ├── services/
│   │   ├── ollama_service.py   # All Ollama local AI API calls (centralized)
│   │   ├── document_service.py # File handling and DB persistence
│   │   ├── quiz_service.py     # Quiz answer validation
│   │   └── planner_service.py  # Plan input validation
│   └── utils/
│       └── document_parser.py  # PDF/DOCX/TXT text extraction
│
├── frontend/                   # Vanilla HTML/CSS/JS
│   ├── index.html              # Landing page
│   ├── dashboard.html          # Dashboard with Chart.js
│   ├── upload.html             # Document management
│   ├── chat.html               # AI Q&A chat interface
│   ├── quiz.html               # MCQ quiz
│   ├── exam.html               # Exam prep questions
│   ├── planner.html            # Study planner
│   ├── css/style.css           # Complete design system
│   └── js/                     # Page-specific JavaScript
│
├── tests/test_backend.py       # Pytest test suite
├── uploads/                    # Uploaded files (git-ignored)
├── data/                       # SQLite database (git-ignored)
├── .env.example                # Environment variable template
├── requirements.txt
└── README.md
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.11+, FastAPI, Uvicorn |
| **Data Validation** | Pydantic v2, pydantic-settings |
| **Database** | SQLite + SQLAlchemy (async) |
| **AI Provider** | Local Ollama (`qwen2.5:7b`) |
| **PDF Parsing** | PyMuPDF (fitz) |
| **DOCX Parsing** | python-docx |
| **Frontend** | HTML5, Vanilla CSS, Vanilla JavaScript |
| **Charts** | Chart.js |
| **Testing** | pytest, pytest-asyncio, httpx |

---

## Installation

### Prerequisites
- Python 3.11+ (tested on 3.13)
- [Ollama](https://ollama.com/) installed and running locally
- Qwen 2.5 7B model:
  ```bash
  ollama run qwen2.5:7b
  ```

### 1. Clone the repository
```bash
git clone https://github.com/reddypraneeth430-stack/study_ai.git
cd study_ai
```

### 2. Create and activate a virtual environment
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
```bash
# Copy the example env file
copy .env.example .env     # Windows
cp .env.example .env       # macOS/Linux

# Default settings are configured for local Ollama:
# OLLAMA_BASE_URL=http://localhost:11434
# OLLAMA_MODEL=qwen2.5:7b
```

> ⚠️ **Never commit `.env`** — it is in `.gitignore`

---

## Running the Application

```bash
# From the project root (with .venv activated)
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Open your browser at:
- **Landing Page**: http://127.0.0.1:8000
- **Dashboard**: http://127.0.0.1:8000/dashboard.html
- **API Docs** (Swagger): http://127.0.0.1:8000/api/docs
- **Health Check**: http://127.0.0.1:8000/api/health

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/documents/upload` | Upload a document |
| `GET` | `/api/documents` | List all documents |
| `GET` | `/api/documents/{id}` | Get document details |
| `POST` | `/api/documents/{id}/summary` | Generate AI summary |
| `POST` | `/api/documents/{id}/chat` | Ask a question |
| `GET` | `/api/documents/{id}/conversations` | List conversations |
| `POST` | `/api/documents/{id}/quiz` | Generate MCQ quiz |
| `GET` | `/api/quiz/{id}` | Get quiz (no answers) |
| `POST` | `/api/quiz/{id}/submit` | Submit and score answers |
| `POST` | `/api/exam/generate` | Generate exam questions |
| `GET` | `/api/exam/{id}` | Get exam set |
| `POST` | `/api/planner/generate` | Generate study plan |
| `GET` | `/api/planner` | List study plans |
| `GET` | `/api/planner/{id}` | Get study plan |
| `PUT` | `/api/planner/{id}` | Update study plan |
| `GET` | `/api/dashboard/stats` | Dashboard statistics |

---

## Running Tests

```bash
# With .venv activated
pytest tests/ -v
```

---

## Environment Variables
 
| Variable | Description | Default |
|---|---|---|
| `OLLAMA_BASE_URL` | Ollama server URL | `http://localhost:11434` |
| `OLLAMA_MODEL` | Ollama model name | `qwen2.5:7b` |
| `OLLAMA_TIMEOUT_SECONDS` | Request timeout | `120` |
| `APP_HOST` | Server host | `127.0.0.1` |
| `APP_PORT` | Server port | `8000` |
| `DEBUG` | Enable debug logging | `true` |
| `DATABASE_URL` | SQLite DB path | `sqlite:///./data/studymate.db` |
| `MAX_FILE_SIZE_MB` | Max upload file size | `20` |
| `UPLOAD_DIR` | Upload directory path | `uploads` |

---

## Security Notes

- Local Ollama AI keeps all documents and conversations on your machine — 100% private
- `.env` is in `.gitignore` and will never be committed
- File uploads are validated for extension, size, and sanitized for safe filenames
- Global exception handler prevents raw stack traces from reaching users
- AI errors (timeout, connection failure, missing model) are caught and returned as user-friendly messages

---

## Future Improvements

- [ ] User authentication (JWT or session-based)
- [ ] Multi-user support
- [ ] OCR support for scanned PDFs (Tesseract)
- [ ] Flashcard generation
- [ ] Export study plans as PDF
- [ ] Notes highlighting and annotation
- [ ] Offline mode / PWA
- [ ] Mobile-responsive improvements

---

## Project Structure (Phase 1 Complete)

```
✅ FastAPI backend with all routes
✅ Local Ollama AI service (centralized, error-handled)
✅ Document processing (PDF/DOCX/TXT)
✅ SQLite database with all tables
✅ Modern dark-theme frontend (6 pages)
✅ Tests for core functionality
✅ .gitignore, .env.example, README
```

---

*Built with ❤️ using FastAPI, Ollama (Qwen 7B), and Vanilla JS*
