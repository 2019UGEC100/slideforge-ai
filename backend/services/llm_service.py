"""
LLM Orchestration Service
Handles all interactions with Groq API including summarization,
slide content planning, and brand-aware content generation.
Uses Groq's lightning-fast inference with Llama 3.3 70B model.
"""

import os
import json
from typing import List, Optional
from groq import Groq
from dotenv import load_dotenv

# Load .env from project root (parent of backend/)
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def _call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.3, max_tokens: int = 2000) -> str:
    """Helper to call Groq with a system + user prompt."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


def summarize_document(text: str) -> str:
    """Create a structured executive summary of the document."""
    system_prompt = (
        "You are a senior McKinsey consultant. Summarize the following document "
        "into a structured executive brief. Identify:\n"
        "1. Key objectives and goals\n"
        "2. Core value propositions\n"
        "3. Technical capabilities or requirements\n"
        "4. Competitive differentiators\n"
        "5. Key metrics, timelines, or deliverables\n"
        "6. Strategic recommendations\n\n"
        "Write in a clear, concise, and analytical tone suitable for C-suite executives."
    )
    return _call_llm(system_prompt, text[:12000], temperature=0.3, max_tokens=2000)


def extract_brand_style(text: str) -> dict:
    """Extract brand styling cues from a brand guidelines document or style guide."""
    system_prompt = (
        "You are a brand identity expert. Analyze the following brand guidelines / "
        "style document and extract styling information. Return a JSON object with:\n"
        '{\n'
        '  "primary_color": "#hex color for primary brand color",\n'
        '  "accent_color": "#hex color for accent/secondary color",\n'
        '  "background_color": "#hex for background (default #FFFFFF)",\n'
        '  "font_heading": "suggested heading font name",\n'
        '  "font_body": "suggested body font name",\n'
        '  "tone": "brief description of brand voice/tone",\n'
        '  "key_phrases": ["list of key brand phrases or taglines"]\n'
        "}\n\n"
        "If specific colors or fonts are not mentioned, infer professional defaults. "
        "Return ONLY valid JSON, no markdown."
    )

    try:
        raw = _call_llm(system_prompt, text[:8000], temperature=0.2, max_tokens=500)
        raw = raw.strip()
        # Clean potential markdown wrapping
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            raw = raw.rsplit("```", 1)[0]
        return json.loads(raw)
    except (json.JSONDecodeError, IndexError, Exception):
        return {
            "primary_color": "#1B3A5C",
            "accent_color": "#E8792F",
            "background_color": "#FFFFFF",
            "font_heading": "Calibri",
            "font_body": "Calibri",
            "tone": "professional and analytical",
            "key_phrases": [],
        }


def plan_slide_deck(summary: str, brand_info: Optional[dict] = None, num_slides: int = 8) -> dict:
    """
    Generate a structured slide deck plan from the document summary.
    Returns a JSON structure describing each slide.
    """
    brand_context = ""
    if brand_info:
        brand_context = (
            f"\n\nBrand context: Tone should be '{brand_info.get('tone', 'professional')}'. "
            f"Key brand phrases to consider: {', '.join(brand_info.get('key_phrases', []))}."
        )

    system_prompt = (
        "You are a McKinsey senior partner creating an executive presentation. "
        "Create a compelling, data-rich slide deck from the provided summary.\n\n"
        "CRITICAL RULES:\n"
        f"- Create exactly {num_slides} slides\n"
        "- FIRST SLIDE MUST BE layout:'title' - This is the cover slide with:\n"
        "  * A compelling 3-6 word title (e.g., 'Transforming Enterprise Through Cloud')\n"
        "  * A subtitle describing the initiative\n"
        "  * NO bullet points on title slide\n"
        "- Second slide should introduce key objectives or value proposition\n"
        "- Last slide: summary with 3-4 clear next steps/recommendations\n\n"
        "CONTENT QUALITY (VERY IMPORTANT):\n"
        "- Each bullet point MUST be substantive (8-20 words) with specific details\n"
        "- Include specific numbers, percentages, dollar amounts, timeframes wherever possible\n"
        "- BAD: 'Improve scalability' — TOO VAGUE\n"
        "- GOOD: 'Achieve 10x scalability to handle 100K concurrent users by Q3'\n"
        "- BAD: 'Cost reduction' — TOO SHORT\n"
        "- GOOD: '35% infrastructure cost reduction ($4.2M annual savings) through cloud optimization'\n"
        "- Each slide needs 4-6 substantive bullet points (not 2-3 vague ones)\n\n"
        "HEADLINES:\n"
        "- Must be insight-driven, not labels\n"
        "- BAD: 'Technical Requirements' or 'Overview'\n"
        "- GOOD: 'Zero-Trust Security and 99.99% Uptime Drive Technical Architecture'\n\n"
        "LAYOUT SELECTION:\n"
        "- 'kpi_dashboard': Use for metrics/KPI slides. Each bullet MUST follow this EXACT format:\n"
        "  FORMAT: '[NUMBER] [label describing the metric]'\n"
        "  EXAMPLES:\n"
        "  * '15 applications: Migration velocity per month'\n"
        "  * '35%: Cost reduction through infrastructure optimization'\n"
        "  * '50+ engineers: AWS/Azure certified team members'\n"
        "  * '4.5/5.0: Customer satisfaction score from pilot program'\n"
        "  * '$4.2M: Annual savings from cloud migration'\n"
        "  * '99.99%: Uptime SLA guarantee'\n"
        "  BAD: 'Improve performance' (no number)\n"
        "  BAD: 'Cost savings' (no specific number)\n"
        "  Generate 4 KPI bullets with REAL numbers from the document.\n\n"
        "- 'process_flow': Use for phases/timelines. Each bullet = one step:\n"
        "  FORMAT: 'Phase Name: Brief description of activities'\n"
        "  EXAMPLE: 'Discovery: Assess current infrastructure and identify migration candidates'\n"
        "  Generate 4-5 process steps.\n\n"
        "- 'two_column': Use for comparisons, capabilities, features. Need 6+ bullets to fill both columns\n"
        "- 'title_and_content': General content with 5-6 detailed bullets\n"
        "- 'section_header': Section divider. Keep title SHORT (max 4 words). Add 2-3 preview bullets\n\n"
        "AVAILABLE LAYOUTS: title, title_and_content, section_header, two_column, process_flow, kpi_dashboard\n\n"
        "Return ONLY valid JSON:\n"
        "{\n"
        '  "title": "Compelling Deck Title",\n'
        '  "slides": [\n'
        "    {\n"
        '      "title": "Insight-driven headline (not a label)",\n'
        '      "subtitle": "optional clarifying subtitle",\n'
        '      "bullet_points": ["Detailed point with specifics (8-20 words)", "Another substantive point with numbers"],\n'
        '      "layout": "layout_name",\n'
        '      "speaker_notes": "Key talking points for presenter"\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "No markdown, ONLY valid JSON."
        + brand_context
    )

    try:
        raw = _call_llm(system_prompt, summary, temperature=0.4, max_tokens=3000)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            raw = raw.rsplit("```", 1)[0]
        return json.loads(raw)
    except (json.JSONDecodeError, IndexError, Exception):
        # Fallback minimal deck
        return {
            "title": "Executive Presentation",
            "slides": [
                {
                    "title": "Executive Presentation",
                    "subtitle": "Strategic Overview",
                    "bullet_points": [],
                    "layout": "title",
                    "speaker_notes": "",
                },
                {
                    "title": "Key Findings",
                    "subtitle": "",
                    "bullet_points": ["Analysis pending — please retry generation"],
                    "layout": "title_and_content",
                    "speaker_notes": "",
                },
            ],
        }


def chat_with_context(
    user_message: str,
    history: list,
    document_summary: Optional[str] = None,
    brand_info: Optional[dict] = None,
    rag_context: Optional[str] = None,  # RAG: Retrieved document chunks
) -> str:
    """
    Handle conversational interaction with the user.
    Maintains context about uploaded documents and brand guidelines.
    Uses RAG context for more accurate document-based responses.
    """
    system_prompt = (
        "You are an AI presentation assistant. You help users create polished, "
        "McKinsey-style executive slide decks from their business documents.\n\n"
        "Your capabilities:\n"
        "1. Analyze uploaded RFPs, proposals, and business documents\n"
        "2. Extract key insights and structure them for presentations\n"
        "3. Apply brand guidelines to slide styling\n"
        "4. Generate professional slide decks (PPTX)\n\n"
        "Be concise, professional, and helpful. Answer questions about documents directly. "
        "Do NOT offer to generate slides unless the user explicitly requests it.\n\n"
        "CRITICAL - SLIDE GENERATION:\n"
        "- You have a special command: [GENERATE_SLIDES_NOW]\n"
        "- ONLY use this command when the user says words like: 'generate', 'create slides', 'make presentation', 'build deck'\n"
        "- NEVER use this command for questions, summaries, or information requests\n"
        "- NEVER ask 'would you like me to generate slides?' - just answer the question\n"
        "- If user asks 'what is X?' or 'list Y' - just answer, do NOT mention slide generation"
    )

    if document_summary:
        system_prompt += f"\n\nDocument Summary:\n{document_summary}"

    if brand_info:
        system_prompt += f"\n\nBrand Info: {json.dumps(brand_info)}"
    
    # RAG: Add retrieved context for more accurate responses
    if rag_context:
        system_prompt += (
            f"\n\n--- RELEVANT DOCUMENT EXCERPTS (use these for specific details) ---\n"
            f"{rag_context}\n"
            f"--- END EXCERPTS ---"
        )

    # Build conversation messages for Groq (OpenAI-compatible format)
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        role = "user" if msg["role"] == "user" else "assistant"
        messages.append({"role": role, "content": msg["content"]})

    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.5,
        max_tokens=1500,
    )
    return response.choices[0].message.content
