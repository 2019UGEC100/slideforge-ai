# SlideForge AI

> AI-powered document-to-presentation generator — transforms RFPs, proposals, and business documents into polished, McKinsey-style executive slide decks.

## Architecture

```
┌─────────────────────┐     ┌──────────────────────────────┐
│   React Frontend    │────▶│     FastAPI Backend           │
│   (Port 3000)       │     │     (Port 8001)               │
│                     │     │                                │
│  • Chat UI          │     │  • Document Parser (PDF/DOCX) │
│  • File Upload      │     │  • LLM Service (Groq)         │
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
# Add your Groq API key to .env (get one free at https://console.groq.com/)
```

### 3. Start Backend

```bash
cd backend
python main.py
# API runs on http://localhost:8001
```

### 4. Frontend Setup

```bash
cd frontend
npm install
npm start
# UI runs on http://localhost:3000
```

## Usage

1. **Upload a document** — Click the 📎 paperclip icon in the input bar. Supports PDF, DOCX, TXT.
2. **Upload brand guidelines** (optional) — Click the 🎨 palette icon for styling cues (colors, fonts, tone).
3. **Chat** — Ask questions about your document or request specific content.
4. **Generate** — Type "generate slides" or click the presentation icon to create your deck.
5. **Download** — Click the download button to get your polished PPTX file.

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

## Future Roadmap

### Near-Term Enhancements
- [ ] **Multi-LLM Selection** — User chooses between Groq, OpenAI GPT-4, Anthropic Claude, or local Ollama models
- [ ] **Streaming Responses** — Real-time token streaming for better UX
- [ ] **Template PPTX Import** — Upload a reference deck to match exact brand styling
- [ ] **Multi-Document Merging** — Combine multiple RFPs/proposals into a single presentation
- [ ] **Slide Refinement Loop** — User feedback triggers targeted slide regeneration

### Advanced GenAI Features
- [ ] **Agentic Workflow** — Multi-agent pipeline (Researcher → Outliner → Writer → Designer)
- [ ] **Chart Auto-Generation** — Detect tables → generate actual PowerPoint charts
- [ ] **Image Generation** — DALL-E/Stable Diffusion for contextual slide imagery
- [ ] **Voice-to-Slides** — Speech input → transcription → slide generation

### Enterprise Features
- [ ] Persistent storage (PostgreSQL/Redis)
- [ ] SSO/Authentication
- [ ] API endpoints for integration
- [ ] Google Slides / Canva export
- [ ] Version control for slides

## License

MIT