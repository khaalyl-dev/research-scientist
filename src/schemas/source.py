"""
Pydantic schema for a Source (arXiv paper or web page).
"""

from typing import Optional
from pydantic import BaseModel, Field
from src.schemas.common import SourceType


class SourceSchema(BaseModel):
    """A source document (arXiv paper or web page)."""
    
    id: str = Field(..., description="Unique identifier")
    url: str = Field(..., description="Source URL")  # ← Changed from HttpUrl
    title: str = Field(..., description="Source title")
    source_type: SourceType = Field(..., description="Type of source")
    year: Optional[int] = Field(None, description="Publication year", ge=1900, le=2026)
    content: str = Field(..., description="Full cleaned text content")
    quality_score: Optional[float] = Field(None, description="Quality score", ge=0, le=1)

    class Config:
        use_enum_values = True