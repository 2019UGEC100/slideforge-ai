# SlideForge AI

> AI-powered document-to-presentation generator — transforms RFPs, proposals, and business documents into polished, McKinsey-style executive slide decks.

## Architecture

```
┌─────────────────────┐     ┌──────────────────────────────┐
│   React Frontend    │────▶│     FastAPI Backend           │
│   (Port 3000)       │     │     (Port 8000)               │
│                     │     │                                │
│  • Chat UI          │     │  • Document Parser (PDF/DOCX) │
│  • File Upload      │     │  • LLM Service (Groq)       │
│  • Slide Download   │     │  • Slide Generator (PPTX)     │
│                     │     │  • RAG Vector Store ✨        │
└─────────────────────┘     └──────────────────────────────┘
```

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Groq API key

### 1. Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # Mac/Linux

pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# In project root, copy and edit .env
cp .env.example .env
# Add your OpenAI API key to .env
```

### 3. Start Backend

```bash
cd backend
python main.py
# API runs on http://localhost:8000
```

### 4. Frontend Setup

```bash
cd frontend
npm install
npm start
# UI runs on http://localhost:3000
```

## Usage

1. **Upload a document** — Click the paperclip icon or the "Upload Document" button. Supports PDF, DOCX, TXT.
2. **Upload brand guidelines** (optional) — Click "Upload Brand Guide" for styling cues (colors, fonts, tone).
3. **Chat** — Ask the AI to refine content, adjust the number of slides, etc.
4. **Generate** — Click the presentation icon or ask the AI to generate slides.
5. **Download** — Get your polished PPTX file.

## Tech Stack

| Layer      | Technology              |
|------------|----------------------- |
| Frontend   | React (JavaScript), Axios, Lucide Icons |
| Backend    | FastAPI, Pydantic       |
| LLM        | Groq llama          |
| Doc Parse  | PyPDF2, python-docx    |
| Slides     | python-pptx            |
| RAG        | sentence-transformers, numpy (TF-IDF fallback) |

## Pipeline Overview

```
Document (PDF/DOCX)
        │
        ▼
  ┌─────────────┐
  │   Parser     │  ← PyPDF2 / python-docx
  └─────┬───────┘
        │
        ├──────────────────────────┐
        ▼                          ▼
  ┌─────────────┐          ┌─────────────────┐
  │ Summarizer   │          │  Vector Store   │  ← RAG chunking + embeddings
  │ (Groq)       │          │  (Retrieval)    │
  └─────┬───────┘          └────────┬────────┘
        │                           │
        ▼                           │ (Query-time retrieval)
  ┌─────────────┐       ┌──────────────┐    │
  │ Deck Planner │──────│ Brand Style  │    │
  └─────┬───────┘       └──────────────┘    │
        │                                    │
        ├────────────────────────────────────┘
        ▼
  ┌─────────────┐
  │  Chat/LLM   │  ← Uses RAG context for accurate responses
  └─────┬───────┘
        ▼
  ┌─────────────┐
  │ PPTX Engine  │  ← python-pptx McKinsey layouts
  └─────┬───────┘
        ▼
   Output .pptx
```

## Known Limitations

- **In-memory sessions** — sessions are stored in memory (not persistent). Restarting the server clears all data.
- **Single-file ingestion** — currently processes one document + one brand guide per session.
- **No image extraction** — images from source documents are not transferred to slides.
- **Limited chart support** — chart data placeholders are noted but actual chart rendering is not implemented.
- **Font availability** — generated PPTX uses Calibri by default; fonts must be installed on the viewing machine.

## Next-Step Roadmap

- [ ] Persistent storage (PostgreSQL / Redis for sessions)
- [ ] **Conversation history** — display past sessions in sidebar, allow resuming
- [ ] **Model selector** — dropdown to choose between LLM models (Llama, Mixtral, etc.)
- [x] ~~Multi-document merging with RAG (vector store + retrieval)~~ ✅ **Implemented!**
- [ ] Actual chart/graph rendering from data tables
- [ ] Image extraction and placement from source docs
- [ ] Template PPTX import — use a real reference deck as the base template
- [ ] Export to Google Slides / PDF
- [ ] Streaming LLM responses for real-time chat UX
- [ ] Authentication and multi-user support
- [ ] Deployment with Docker Compose

## License

MIT
