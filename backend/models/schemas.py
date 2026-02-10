from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    role: MessageRole
    content: str


class GenerateRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    history: List[ChatMessage] = Field(default_factory=list)


class GenerateResponse(BaseModel):
    reply: str
    conversation_id: str
    slide_ready: bool = False
    slide_download_url: Optional[str] = None


class UploadResponse(BaseModel):
    file_id: str
    filename: str
    file_type: str
    summary: str
    conversation_id: str  # Return session ID so frontend can generate slides


class SlideContent(BaseModel):
    title: str
    subtitle: Optional[str] = None
    bullet_points: List[str] = Field(default_factory=list)
    layout: str = "title_and_content"  # title, title_and_content, two_column, section_header, blank
    speaker_notes: Optional[str] = None
    chart_data: Optional[dict] = None


class DeckPlan(BaseModel):
    title: str
    slides: List[SlideContent]
    theme_color: Optional[str] = "#1B3A5C"
    accent_color: Optional[str] = "#E8792F"
    font_heading: Optional[str] = "Calibri"
    font_body: Optional[str] = "Calibri"


class BrandStyle(BaseModel):
    primary_color: str = "#1B3A5C"
    accent_color: str = "#E8792F"
    background_color: str = "#FFFFFF"
    font_heading: str = "Calibri"
    font_body: str = "Calibri"
    logo_path: Optional[str] = None
