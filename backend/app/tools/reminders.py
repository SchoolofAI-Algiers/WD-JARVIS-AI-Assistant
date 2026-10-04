from datetime import datetime

from app.tools.storage import connect


class ReminderTool:
    def create_reminder(self, text: str, due_at: str | None = None) -> dict:
        text = text.strip()
        if not text:
            raise ValueError("Reminder text is required.")
        if due_at:
            due_at = datetime.fromisoformat(due_at).isoformat(timespec="minutes")
        with connect() as db:
            cursor = db.execute("INSERT INTO reminders(text, due_at) VALUES (?, ?)", (text, due_at))
            return {"id": cursor.lastrowid, "text": text, "due_at": due_at, "completed": False}

    def list_reminders(self) -> list[dict]:
        with connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM reminders WHERE completed=0 ORDER BY due_at, id")]

    def complete_reminder(self, reminder_id: int) -> bool:
        with connect() as db:
            return db.execute("UPDATE reminders SET completed=1 WHERE id=?", (reminder_id,)).rowcount > 0


reminder_tool = ReminderTool()
