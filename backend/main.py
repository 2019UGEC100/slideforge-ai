"""
SlideForge AI — FastAPI Backend
================================
AI-powered document-to-presentation generator.

Main API endpoints:
- POST /api/upload      → Upload documents (PDF/DOCX/TXT) or brand guidelines
- POST /api/chat        → Chat with AI, triggers slide generation on explicit request
- POST /api/generate-slides → Direct slide generation
- GET  /api/download/{filename} → Download generated PPTX
- GET  /api/session/{id} → Get session info (documents, RAG chunks, etc.)
- GET  /api/rag-status  → Check if RAG/embeddings are available
"""

import os
import uuid
import shutil
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv

# Internal services
from models.schemas import GenerateRequest, GenerateResponse, UploadResponse
from services.document_parser import parse_document, chunk_text
from services.llm_service import (
    summarize_document,      # Summarizes uploaded documents
    extract_brand_style,     # Extracts colors, fonts, tone from brand guides
    plan_slide_deck,         # LLM plans slide structure and content
    chat_with_context,       # Conversational AI with RAG context
)
from services.slide_generator import create_mckinsey_deck  # PPTX generation
from services.vector_store import (
    get_store,               # Get/create vector store for a session
    clear_store,             # Clear vector store (on session reset)
    chunk_text_with_overlap, # Smart text chunking for RAG
    is_rag_available,        # Check if sentence-transformers is installed
)

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

app = FastAPI(
    title="SlideForge AI",
    description="AI-powered document-to-presentation generator",
    version="1.0.0",
)

# CORS: Allow React frontend (dev mode)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Session Storage (In-Memory — use Redis/PostgreSQL for production)
# ─────────────────────────────────────────────────────────────────────────────

sessions = {}  # conversation_id → session dict

# File storage directories
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_or_create_session(conversation_id: Optional[str] = None) -> dict:
    """
    Get existing session or create a new one.
    
    Session structure:
    - id: Unique conversation ID
    - documents: List of uploaded document filenames
    - document_texts: Raw text content from documents
    - document_summary: LLM-generated summary for slide planning
    - brand_info: Extracted brand colors, fonts, tone
    - brand_file: Brand guidelines filename
    - history: Chat message history
    - deck_path: Path to generated PPTX (if any)
    """
    if conversation_id and conversation_id in sessions:
        return sessions[conversation_id]

    cid = conversation_id or str(uuid.uuid4())
    sessions[cid] = {
        "id": cid,
        "documents": [],
        "document_texts": [],
        "document_summary": None,
        "brand_info": None,
        "brand_file": None,
        "history": [],
        "deck_path": None,
    }
    return sessions[cid]


@app.get("/")
async def root():
    return {"status": "ok", "app": "SlideForge AI", "version": "1.0.0"}


# ─────────────────────────────────────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    conversation_id: Optional[str] = None,
    file_purpose: Optional[str] = "document",  # "document" or "brand"
):
    """
    Upload a document or brand guidelines file.
    
    - document: PDF/DOCX/TXT → summarized + chunked for RAG
    - brand: TXT with brand info → colors, fonts, tone extracted
    """
    allowed_extensions = {".pdf", ".docx", ".doc", ".txt", ".md", ".pptx"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(allowed_extensions)}",
        )

    # Save file
    file_id = str(uuid.uuid4())
    save_path = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Parse document
    try:
        text, file_type = parse_document(save_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Update session
    session = get_or_create_session(conversation_id)
    cid = session["id"]

    if file_purpose == "brand":
        # Extract brand styling
        brand_info = extract_brand_style(text)
        session["brand_info"] = brand_info
        session["brand_file"] = file.filename
        summary_text = (
            f"Brand guidelines extracted from '{file.filename}':\n"
            f"• Primary color: {brand_info.get('primary_color', 'N/A')}\n"
            f"• Accent color: {brand_info.get('accent_color', 'N/A')}\n"
            f"• Heading font: {brand_info.get('font_heading', 'N/A')}\n"
            f"• Body font: {brand_info.get('font_body', 'N/A')}\n"
            f"• Tone: {brand_info.get('tone', 'N/A')}"
        )
    else:
        # Summarize document
        session["documents"].append(file.filename)
        session["document_texts"].append(text)
        doc_summary = summarize_document(text)
        session["document_summary"] = doc_summary
        
        # RAG: Chunk document and add to vector store
        try:
            chunks = chunk_text_with_overlap(text, chunk_size=500, overlap=100)
            if chunks:
                vector_store = get_store(cid)
                metadata = [{"filename": file.filename, "chunk_idx": i} for i in range(len(chunks))]
                vector_store.add_chunks(chunks, metadata)
                rag_status = f" ({len(chunks)} chunks indexed for RAG)"
            else:
                rag_status = ""
        except Exception as e:
            print(f"RAG indexing warning: {e}")
            rag_status = ""
        
        summary_text = f"Document '{file.filename}' analyzed successfully. Key insights extracted.{rag_status}"

    return UploadResponse(
        file_id=file_id,
        filename=file.filename,
        file_type=file_type,
        summary=summary_text,
        conversation_id=cid,
    )


@app.post("/api/chat", response_model=GenerateResponse)
async def chat(request: GenerateRequest):
    """
    Chat with the AI assistant.
    
    Features:
    - RAG: Retrieves relevant document chunks for accurate answers
    - Auto-generation: If LLM includes [GENERATE_SLIDES_NOW], slides are created
    - Context-aware: Uses document summary + brand info in prompts
    """
    import traceback
    try:
        session = get_or_create_session(request.conversation_id)
        cid = session["id"]

        # Build history from request
        history = [{"role": m.role.value, "content": m.content} for m in request.history]

        # RAG: Retrieve relevant context for the query
        rag_context = None
        try:
            vector_store = get_store(cid)
            if len(vector_store) > 0:
                rag_context = vector_store.get_context(request.message, max_tokens=1500, top_k=4)
        except Exception as e:
            print(f"RAG retrieval warning: {e}")
            rag_context = None

        # Get AI response with RAG context
        reply = chat_with_context(
            user_message=request.message,
            history=history,
            document_summary=session.get("document_summary"),
            brand_info=session.get("brand_info"),
            rag_context=rag_context,  # Pass RAG context
        )
    except Exception as e:
        traceback.print_exc()
        # Also write to error log file for debugging
        with open(os.path.join(os.path.dirname(__file__), 'error.log'), 'a') as f:
            traceback.print_exc(file=f)
        raise HTTPException(status_code=500, detail=str(e))

    # Store in session history
    session["history"].append({"role": "user", "content": request.message})
    session["history"].append({"role": "assistant", "content": reply})

    # Check if slides should be generated (strict check for explicit trigger)
    slide_ready = False
    slide_url = None
    
    # Only trigger on exact phrase - prevents accidental generation
    SLIDE_TRIGGER = "[GENERATE_SLIDES_NOW]"
    if SLIDE_TRIGGER in reply:
        reply = reply.replace(SLIDE_TRIGGER, "").strip()
        try:
            deck_plan = plan_slide_deck(
                session.get("document_summary", "No document uploaded yet."),
                session.get("brand_info"),
                num_slides=8,
            )
            output_filename = f"SlideForge_{cid[:8]}.pptx"
            output_path = os.path.join(OUTPUT_DIR, output_filename)
            create_mckinsey_deck(deck_plan, session.get("brand_info"), output_path)
            session["deck_path"] = output_path
            slide_ready = True
            slide_url = f"/api/download/{output_filename}"
            reply += (
                "\n\n✅ Your slide deck has been generated! "
                "Click the download button to get your PPTX file."
            )
        except Exception as e:
            reply += f"\n\n⚠️ Slide generation encountered an error: {str(e)}"

    return GenerateResponse(
        reply=reply,
        conversation_id=cid,
        slide_ready=slide_ready,
        slide_download_url=slide_url,
    )


@app.post("/api/generate-slides")
async def generate_slides(conversation_id: str):
    """Directly trigger slide generation for a session."""
    if conversation_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[conversation_id]

    if not session.get("document_summary"):
        raise HTTPException(status_code=400, detail="No document uploaded yet. Please upload a document first.")

    try:
        deck_plan = plan_slide_deck(
            session["document_summary"],
            session.get("brand_info"),
            num_slides=8,
        )

        output_filename = f"SlideForge_{conversation_id[:8]}.pptx"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        create_mckinsey_deck(deck_plan, session.get("brand_info"), output_path)
        session["deck_path"] = output_path

        return {
            "status": "success",
            "download_url": f"/api/download/{output_filename}",
            "num_slides": len(deck_plan.get("slides", [])),
            "deck_title": deck_plan.get("title", "Executive Presentation"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Slide generation failed: {str(e)}")


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """Download a generated PPTX file."""
    file_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        file_path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=filename,
    )


@app.get("/api/session/{conversation_id}")
async def get_session(conversation_id: str):
    """Get session state for debugging/display."""
    if conversation_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[conversation_id]
    
    # Get RAG info
    try:
        vector_store = get_store(conversation_id)
        rag_chunks = len(vector_store)
    except:
        rag_chunks = 0
    
    return {
        "id": session["id"],
        "documents": session["documents"],
        "has_brand_info": session["brand_info"] is not None,
        "has_summary": session["document_summary"] is not None,
        "has_deck": session["deck_path"] is not None,
        "message_count": len(session["history"]),
        "rag_chunks": rag_chunks,
        "rag_enabled": is_rag_available(),
    }


@app.get("/api/rag-status")
async def rag_status():
    """Check if RAG/vector store is available."""
    return {
        "rag_available": is_rag_available(),
        "embedding_method": "sentence-transformers" if is_rag_available() else "tfidf-fallback",
    }


@app.get("/api/sessions")
async def list_sessions():
    """List all active sessions (for debugging)."""
    session_list = []
    for cid, session in sessions.items():
        try:
            vector_store = get_store(cid)
            rag_chunks = len(vector_store)
        except:
            rag_chunks = 0
        
        session_list.append({
            "conversation_id": cid,
            "documents": session.get("documents", []),
            "has_brand": session.get("brand_info") is not None,
            "rag_chunks": rag_chunks,
        })
    return {"sessions": session_list, "total": len(session_list)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("BACKEND_HOST", "0.0.0.0"),
        port=int(os.getenv("BACKEND_PORT", "8001")),
        reload=True,
    )
