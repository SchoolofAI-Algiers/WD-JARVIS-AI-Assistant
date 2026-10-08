from datetime import datetime

from app.tools.storage import connect


class ReminderTool:
    def create_reminder(self, text: str, due_at: str | None = None) -> dict:
        if not isinstance(text, str):
            raise ValueError("Reminder text is required.")
        text = text.strip()
        if not text:
            raise ValueError("Reminder text is required.")
        if due_at is not None:
            if not isinstance(due_at, str):
                raise ValueError("Reminder due time must be a valid local date and time.")
            due_at = due_at.strip()
            if "T" not in due_at.upper() and " " not in due_at:
                raise ValueError("Reminder due time must include both a date and time.")
            try:
                parsed_due_at = datetime.fromisoformat(due_at)
            except ValueError as error:
                raise ValueError("Reminder due time must be a valid local date and time.") from error
            if parsed_due_at.tzinfo is not None:
                raise ValueError("Reminder due time must use local time without a timezone offset.")
            due_at = parsed_due_at.isoformat(timespec="minutes")
        with connect() as db:
            cursor = db.execute("INSERT INTO reminders(text, due_at) VALUES (?, ?)", (text, due_at))
            return {"id": cursor.lastrowid, "text": text, "due_at": due_at, "completed": False}

    def list_reminders(self) -> list[dict]:
        with connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM reminders WHERE completed=0 ORDER BY due_at, id")]

    def complete_reminder(self, reminder_id: int) -> bool:
        with connect() as db:
            return db.execute(
                "UPDATE reminders SET completed=1 WHERE id=? AND completed=0",
                (reminder_id,),
            ).rowcount > 0


reminder_tool = ReminderTool()
