from datetime import datetime, timezone


class DateTimeTool:
    def get_current_datetime(self) -> dict:
        now = datetime.now(timezone.utc)

        return {
            "iso": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
        }


datetime_tool = DateTimeTool()