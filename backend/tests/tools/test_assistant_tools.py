import os
import tempfile
from datetime import date, datetime, time, timedelta
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.core.assistant import Assistant
from app.tools.notes import NotesTool
from app.tools.reminders import ReminderTool
from app.tools.router import ToolRouter
from app.tools.schedule import ScheduleTool
from app.tools.workspace import WorkspaceTool


@pytest.fixture(autouse=True)
def isolated_database(monkeypatch):
    database = Path(__file__).resolve().parents[2] / f".test-tools-{uuid4().hex}.sqlite3"
    monkeypatch.setenv("JARVIS_TOOLS_DB", str(database))
    yield database
    database.unlink(missing_ok=True)


def test_reminders_create_list_complete_and_validate():
    tool = ReminderTool()
    reminder = tool.create_reminder(" to call home ", "2030-04-05T18:00")

    assert reminder == {
        "id": reminder["id"],
        "text": "to call home",
        "due_at": "2030-04-05T18:00",
        "completed": False,
    }
    assert ReminderTool().list_reminders() == [reminder]
    assert tool.complete_reminder(reminder["id"]) is True
    assert tool.complete_reminder(reminder["id"]) is False
    assert tool.list_reminders() == []

    with pytest.raises(ValueError, match="text is required"):
        tool.create_reminder("  ")
    with pytest.raises(ValueError, match="valid local date and time"):
        tool.create_reminder("Task", "not-a-date")
    with pytest.raises(ValueError, match="date and time"):
        tool.create_reminder("Task", "2030-04-05")
    with pytest.raises(ValueError, match="timezone offset"):
        tool.create_reminder("Task", "2030-04-05T18:00+01:00")


def test_reminder_router_preserves_task_text_and_parses_due_time():
    router = ToolRouter()
    result = router.execute(
        "reminders",
        "Remind me tomorrow at 6 PM to submit the hackathon.",
    )["result"]

    assert result["text"] == "to submit the hackathon"
    assert result["due_at"] == datetime.combine(
        date.today() + timedelta(days=1), time(18, 0)
    ).isoformat(timespec="minutes")

    second = router.execute(
        "reminders",
        "Remind me at 18:00 to finish the JARVIS tools.",
    )["result"]
    assert second["text"] == "to finish the JARVIS tools"
    assert second["due_at"].endswith("T18:00")


def test_reminder_router_rejects_missing_text_and_invalid_time():
    router = ToolRouter()
    with pytest.raises(ValueError, match="text is required"):
        router.execute("reminders", "Remind me")
    with pytest.raises(ValueError, match="valid 24-hour time"):
        router.execute("reminders", "Remind me tomorrow at 25:00 to call home")
    with pytest.raises(ValueError, match="minutes from 00 to 59"):
        router.execute("reminders", "Remind me at 18:75 to call home")


def test_reminder_router_supports_task_create_list_and_complete():
    router = ToolRouter()
    created = router.execute("reminders", "Add a task: finish the documentation")['result']
    assert created["text"] == "finish the documentation"
    alias = router.execute("reminders", "Set a reminder: call home")["result"]
    assert alias["text"] == "call home"

    pending = router.execute("reminders", "List pending reminders")["result"]
    assert {item["id"] for item in pending} == {created["id"], alias["id"]}

    completed = router.execute("reminders", f"Complete reminder #{created['id']}")["result"]
    assert completed == {"id": created["id"], "completed": True}
    assert [item["id"] for item in router.execute("reminders", "Show my reminders")["result"]] == [alias["id"]]


def test_notes_create_list_search_and_validate():
    tool = NotesTool()
    first = tool.create_note("Discuss JARVIS voice input")
    tool.create_note("Prepare Welcome Day demo")

    assert first["text"] == "Discuss JARVIS voice input"
    assert len(NotesTool().list_notes()) == 2
    assert tool.search_notes("jarvis")[0]["text"] == first["text"]
    assert tool.search_notes("missing") == []
    with pytest.raises(ValueError, match="Note text is required"):
        tool.create_note("  ")
    with pytest.raises(ValueError, match="Search text is required"):
        tool.search_notes("  ")


def test_notes_router_supports_create_list_and_search():
    router = ToolRouter()
    created = router.execute("notes", "Take a note: Prepare the JARVIS demo")['result']
    assert created["text"] == "Prepare the JARVIS demo"
    assert router.execute("notes", "Show my notes")["result"][0]["id"] == created["id"]
    searched = router.execute("notes", "Search my notes for jarvis")["result"]
    assert [note["id"] for note in searched] == [created["id"]]


def test_schedule_create_list_sort_and_validate():
    tool = ScheduleTool()
    tool.create_event("Later", "2030-04-05T16:30")
    tool.create_event("Earlier", "2030-04-05T09:15")

    events = tool.list_events("2030-04-05")
    assert [event["title"] for event in events] == ["Earlier", "Later"]
    assert tool.list_events("2030-04-06") == []

    with pytest.raises(ValueError, match="title is required"):
        tool.create_event("  ", "2030-04-05T10:00")
    with pytest.raises(ValueError, match="valid date and time"):
        tool.create_event("Review", "not-a-date")
    with pytest.raises(ValueError, match="date and time"):
        tool.create_event("Review", "2030-04-05")
    with pytest.raises(ValueError, match="timezone offset"):
        tool.create_event("Review", "2030-04-05T10:00+01:00")
    with pytest.raises(ValueError):
        tool.list_events("2030-02-31")


def test_schedule_router_creates_and_lists_today_and_tomorrow():
    router = ToolRouter()
    tomorrow = date.today() + timedelta(days=1)
    created = router.execute("schedule", "Add a meeting tomorrow at 3 PM")

    assert created["result"]["title"] == "Meeting"
    assert created["result"]["starts_at"] == datetime.combine(
        tomorrow, time(15, 0)
    ).isoformat(timespec="minutes")

    tomorrow_result = router.execute("schedule", "What do I have tomorrow?")
    assert tomorrow_result["date"] == tomorrow.isoformat()
    assert tomorrow_result["result"][0]["title"] == "Meeting"

    today_event = ScheduleTool().create_event(
        "Today review", datetime.combine(date.today(), time(9, 0)).isoformat()
    )
    today_result = router.execute("schedule", "Show my schedule for today")
    assert today_result["date"] == date.today().isoformat()
    assert today_event in today_result["result"]


def test_schedule_router_parses_explicit_date_and_rejects_invalid_input():
    router = ToolRouter()
    result = router.execute(
        "schedule",
        "Add an event: Review on 2030-04-05 at 14:30",
    )
    assert result["result"]["title"] == "Review"
    assert result["result"]["starts_at"] == "2030-04-05T14:30"

    with pytest.raises(ValueError, match="valid event date"):
        router.execute("schedule", "Add a meeting on 2030-02-31 at 3 PM")
    with pytest.raises(ValueError, match="valid 24-hour time"):
        router.execute("schedule", "Schedule dentist tomorrow at 25:00")
    with pytest.raises(ValueError, match="event time"):
        router.execute("schedule", "Schedule dentist tomorrow")
    with pytest.raises(ValueError, match="event title"):
        router.execute("schedule", "Schedule at 3 PM")


def test_workspace_allowlist_paths_and_system_calls_are_mocked(monkeypatch):
    workspace_root = Path(__file__).resolve().parents[3]
    tool = WorkspaceTool(workspace_root)
    monkeypatch.setattr(os, "name", "nt")
    popen = Mock()
    startfile = Mock()
    monkeypatch.setattr("app.tools.workspace.subprocess.Popen", popen)
    monkeypatch.setattr(os, "startfile", startfile, raising=False)

    assert tool.open_application("VS Code") == {"action": "application", "name": "vs code"}
    popen.assert_called_once_with(["code", "--new-window"], shell=False)
    assert tool.open_workspace("backend")["action"] == "workspace"
    startfile.assert_called_once_with(str((workspace_root / "backend").resolve()))

    with pytest.raises(ValueError, match="not allowed"):
        tool.open_application("PowerShell")
    with pytest.raises(ValueError, match="invalid or outside"):
        tool.open_workspace("../outside")
    for shell_path in ("%TEMP%", "$env:TEMP", "~"):
        with pytest.raises(ValueError, match="invalid or outside"):
            tool.open_workspace(shell_path)
    with pytest.raises(ValueError, match="invalid or outside"):
        tool.open_workspace(str(Path(tempfile.gettempdir()).resolve()))
    assert popen.call_count == 1


def test_workspace_validates_urls_and_mocks_browser(monkeypatch):
    tool = WorkspaceTool()
    open_browser = Mock()
    monkeypatch.setattr("app.tools.workspace.webbrowser.open", open_browser)

    assert tool.open_url(" https://example.org/path ") == {
        "action": "url",
        "url": "https://example.org/path",
    }
    open_browser.assert_called_once_with("https://example.org/path")

    for invalid_url in (
        "javascript:alert(1)",
        "ftp://example.org",
        "https://user:pass@example.org",
        "https://example.org:99999",
        "https:///missing-host",
        "https://example.org/path with spaces",
    ):
        with pytest.raises(ValueError, match="HTTP or HTTPS"):
            tool.open_url(invalid_url)
    assert open_browser.call_count == 1


def test_workspace_router_calls_only_mocked_workspace_operations(monkeypatch):
    router = ToolRouter()
    open_application = Mock(return_value={"action": "application", "name": "notepad"})
    open_url = Mock(return_value={"action": "url", "url": "https://example.org"})
    monkeypatch.setattr("app.tools.router.workspace_tool.open_application", open_application)
    monkeypatch.setattr("app.tools.router.workspace_tool.open_url", open_url)

    assert router.execute("workspace", "Open Notepad")["result"]["name"] == "notepad"
    open_application.assert_called_once_with("Notepad")
    assert router.execute("workspace", "Open https://example.org")["result"]["url"] == "https://example.org"
    open_url.assert_called_once_with("https://example.org")


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Remind me tomorrow at 6 PM to submit the hackathon", "reminders"),
        ("Set a reminder to call home", "reminders"),
        ("Add a task: finish the documentation", "reminders"),
        ("Show my reminders", "reminders"),
        ("List pending reminders", "reminders"),
        ("Complete reminder #12", "reminders"),
        ("Take a note: add voice input", "notes"),
        ("Save this note: prepare the demo", "notes"),
        ("Show my notes", "notes"),
        ("Search my notes for JARVIS", "notes"),
        ("Add a meeting tomorrow at 3 PM", "schedule"),
        ("What do I have tomorrow?", "schedule"),
        ("Show my schedule for today", "schedule"),
        ("Schedule dentist tomorrow at 2 PM", "schedule"),
        ("Open VS Code", "workspace"),
        ("Open Chrome", "workspace"),
        ("Prepare my workspace", "workspace"),
        ("Open https://example.org", "workspace"),
        ("Calculate 2 + 3", "calculator"),
        ("What time is it?", "datetime"),
        ("Weather in Algiers", "weather"),
        ("Tell me about Chrome releases", None),
        ("I have notes about tomorrow's meeting", None),
        ("Tell me a story", None),
    ],
)
def test_router_detects_intents_without_broad_collisions(message, expected):
    assert ToolRouter().detect_tool(message) == expected


def test_router_executes_existing_tools_without_changing_their_implementations(monkeypatch):
    router = ToolRouter()
    assert router.execute("calculator", "calculate 2 + 3")["result"] == 5

    current_time = router.execute("datetime", "What time is it?")["result"]
    assert set(current_time) == {"iso", "date", "time"}

    weather = {
        "city": "Paris",
        "country": "France",
        "temperature": 18,
        "humidity": 50,
        "weather_code": 1,
        "wind_speed": 5,
        "timezone": "Europe/Paris",
    }
    get_weather = Mock(return_value=weather)
    monkeypatch.setattr("app.tools.router.weather_tool.get_weather", get_weather)
    assert router.execute("weather", "Weather in Paris")["result"] == weather
    get_weather.assert_called_once_with("Paris")


def test_assistant_formats_productivity_tool_results():
    assistant = Assistant()

    reminder = assistant._format_tool_response({
        "tool": "reminders",
        "result": {"id": 3, "text": "to call home", "due_at": "2030-04-05T18:00", "completed": False},
    })
    assert reminder == "Reminder created for 2030-04-05 18:00: to call home"
    assert assistant._format_tool_response({
        "tool": "reminders",
        "result": {"id": 3, "completed": False},
    }) == "I couldn't find that reminder."

    notes = assistant._format_tool_response({
        "tool": "notes",
        "result": [{"id": 1, "text": "Add voice input"}],
    })
    assert "Add voice input" in notes

    schedule = assistant._format_tool_response({
        "tool": "schedule",
        "date": "2030-04-05",
        "result": [{"title": "Review", "starts_at": "2030-04-05T15:00"}],
    })
    assert "Review" in schedule
    assert "2030-04-05T15:00" in schedule

    workspace = assistant._format_tool_response({
        "tool": "workspace",
        "result": {"action": "application", "name": "vs code"},
    })
    assert workspace == "VS Code opened successfully."


def test_assistant_turns_tool_errors_into_user_readable_responses(monkeypatch):
    assistant = Assistant()
    monkeypatch.setattr("app.core.assistant.conversation_memory.get_messages", lambda _: [])
    monkeypatch.setattr("app.core.assistant.conversation_memory.add_message", lambda **_: None)
    monkeypatch.setattr("app.core.assistant.tool_router.detect_tool", lambda _: "reminders")
    monkeypatch.setattr(
        "app.core.assistant.tool_router.execute",
        Mock(side_effect=ValueError("Reminder text is required.")),
    )

    result = assistant.process("isolated-test-conversation", "Remind me")
    assert result["message"] == "I couldn't process that request: Reminder text is required."
    assert result["metadata"] == {"type": "error", "tool": "reminders"}
