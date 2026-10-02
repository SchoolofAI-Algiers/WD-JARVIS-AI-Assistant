from __future__ import annotations

from pydantic import BaseModel


class Chunk(BaseModel):

    id: str  
    text: str  
    title: str  
    section: str | None = None 
    source: str 
    category: str | None = None
    lang: str | None = None
    updated: str | None = None
    doc_path: str = ""  

    @property
    def heading(self) -> str:
        """'Title › Section', used as context for embeddings and display."""
        return f"{self.title} › {self.section}" if self.section else self.title