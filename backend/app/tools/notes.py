from app.tools.storage import connect


class NotesTool:
    def create_note(self, text: str) -> dict:
        text = text.strip()
        if not text:
            raise ValueError("Note text is required.")
        with connect() as db:
            cursor = db.execute("INSERT INTO notes(text) VALUES (?)", (text,))
            return {"id": cursor.lastrowid, "text": text}

    def list_notes(self) -> list[dict]:
        with connect() as db:
            return [dict(row) for row in db.execute("SELECT id, text, created_at FROM notes ORDER BY id DESC")]

    def search_notes(self, query: str) -> list[dict]:
        query = query.strip()
        if not query:
            raise ValueError("Search text is required.")
        with connect() as db:
            return [dict(row) for row in db.execute("SELECT id, text, created_at FROM notes WHERE text LIKE ? ORDER BY id DESC", (f"%{query}%",))]


notes_tool = NotesTool()
