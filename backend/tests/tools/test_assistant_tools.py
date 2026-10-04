import os
from pathlib import Path
from unittest.mock import Mock

import pytest

from app.tools.notes import NotesTool
from app.tools.reminders import ReminderTool
from app.tools.router import ToolRouter
from app.tools.schedule import ScheduleTool
from app.tools.workspace import WorkspaceTool


@pytest.fixture(autouse=True)
def isolated_database(monkeypatch):
    path = Path(__file__).resolve().parents[2] / ".test-tools.sqlite3"
    path.unlink(missing_ok=True)
    monkeypatch.setenv("JARVIS_TOOLS_DB", str(path))
    yield
    path.unlink(missing_ok=True)


def test_reminders_create_list_complete_and_validate():
    tool = ReminderTool()
    reminder = tool.create_reminder("Submit demo", "2030-04-05T18:00")
    assert tool.list_reminders()[0]["text"] == "Submit demo"
    assert tool.complete_reminder(reminder["id"])
    assert tool.list_reminders() == []
    with pytest.raises(ValueError):
        tool.create_reminder(" ")


def test_notes_create_search_and_list():
    tool = NotesTool()
    tool.create_note("Discuss JARVIS voice input")
    tool.create_note("Prepare demo")
    assert len(tool.list_notes()) == 2
    assert tool.search_notes("JARVIS")[0]["text"].startswith("Discuss")


def test_schedule_create_and_list_by_date():
    tool = ScheduleTool()
    tool.create_event("Review", "2030-04-05T15:00")
    assert [e["title"] for e in tool.list_events("2030-04-05")] == ["Review"]
    assert tool.list_events("2030-04-06") == []


def test_workspace_allowlist_and_path_validation(monkeypatch):
    workspace_root = Path(__file__).resolve().parents[3]
    tool = WorkspaceTool(workspace_root)
    monkeypatch.setattr(os, "name", "nt")
    calls = []
    monkeypatch.setattr("app.tools.workspace.subprocess.Popen", lambda *a, **k: calls.append(a))
    assert tool.open_application("Notepad")["name"] == "notepad"
    assert calls
    with pytest.raises(ValueError):
        tool.open_application("PowerShell")
    with pytest.raises(ValueError):
        tool.open_workspace("../outside")


def test_router_detects_tools_and_preserves_existing_intents(monkeypatch):
    router = ToolRouter()
    assert router.detect_tool("Remind me tomorrow at 6 PM to submit the hackathon") == "reminders"
    assert router.detect_tool("Show my notes") == "notes"
    assert router.detect_tool("Add a meeting tomorrow at 3 PM") == "schedule"
    assert router.detect_tool("Open Notepad") == "workspace"
    assert router.detect_tool("calculate 2 + 3") == "calculator"
    assert router.detect_tool("what time is it") == "datetime"
    assert router.detect_tool("weather in Algiers") == "weather"
    assert router.detect_tool("tell me a story") is None


def test_router_executes_new_intents_without_system_actions(monkeypatch):
    router = ToolRouter()
    reminder = router.execute("reminders", "Remind me to call home")
    assert reminder["result"]["text"] == "to call home"
    note = router.execute("notes", "Take a note: add voice input")
    assert note["result"]["text"] == "add voice input"
    open_application = Mock(return_value={"action": "application", "name": "notepad"})
    monkeypatch.setattr("app.tools.router.workspace_tool.open_application", open_application)
    assert router.execute("workspace", "Open Notepad")["result"]["name"] == "notepad"
    open_application.assert_called_once_with("Notepad")
