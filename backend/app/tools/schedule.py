from datetime import date, datetime, time, timedelta

from app.tools.storage import connect


class ScheduleTool:
    def create_event(self, title: str, starts_at: str) -> dict:
        if not isinstance(title, str):
            raise ValueError("Event title is required.")
        title = title.strip()
        if not title:
            raise ValueError("Event title is required.")
        if not isinstance(starts_at, str) or ("T" not in starts_at.upper() and " " not in starts_at):
            raise ValueError("Event start must include a valid date and time.")
        try:
            parsed = datetime.fromisoformat(starts_at)
        except ValueError as error:
            raise ValueError("Event start must include a valid date and time.") from error
        if parsed.tzinfo is not None:
            raise ValueError("Event start must use local time without a timezone offset.")
        starts_at = parsed.isoformat(timespec="minutes")
        with connect() as db:
            cursor = db.execute("INSERT INTO events(title, starts_at) VALUES (?, ?)", (title, starts_at))
            return {"id": cursor.lastrowid, "title": title, "starts_at": starts_at}

    def list_events(self, day: str) -> list[dict]:
        parsed = date.fromisoformat(day)
        start = datetime.combine(parsed, time.min).isoformat(timespec="minutes")
        end = datetime.combine(parsed + timedelta(days=1), time.min).isoformat(timespec="minutes")
        with connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM events WHERE starts_at >= ? AND starts_at < ? ORDER BY starts_at", (start, end))]


schedule_tool = ScheduleTool()
