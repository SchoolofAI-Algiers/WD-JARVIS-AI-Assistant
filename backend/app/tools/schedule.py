from datetime import date, datetime, time, timedelta

from app.tools.storage import connect


class ScheduleTool:
    def create_event(self, title: str, starts_at: str) -> dict:
        title = title.strip()
        if not title:
            raise ValueError("Event title is required.")
        parsed = datetime.fromisoformat(starts_at)
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
