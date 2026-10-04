import os
import subprocess
import webbrowser
from pathlib import Path
from urllib.parse import urlparse


class WorkspaceTool:
    APPS = {
        "notepad": ["notepad.exe"],
        "vs code": ["code", "--new-window"],
        "chrome": ["chrome", "--new-window"],
    }

    def __init__(self, workspace: str | Path | None = None):
        self.workspace = Path(workspace or Path(__file__).resolve().parents[3]).resolve()

    def open_application(self, name: str) -> dict:
        key = name.strip().lower()
        if key not in self.APPS or os.name != "nt":
            raise ValueError("Application is not allowed or unavailable on this platform.")
        subprocess.Popen(self.APPS[key], shell=False)
        return {"action": "application", "name": key}

    def open_workspace(self, relative_path: str = ".") -> dict:
        target = (self.workspace / relative_path).resolve()
        if not target.is_relative_to(self.workspace) or not target.exists() or not target.is_dir():
            raise ValueError("Workspace path is invalid or outside the project workspace.")
        if os.name != "nt":
            raise ValueError("Opening workspace folders is available on Windows only.")
        os.startfile(str(target))
        return {"action": "workspace", "path": str(target)}

    def open_url(self, url: str) -> dict:
        parsed = urlparse(url.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("Only valid HTTP or HTTPS URLs can be opened.")
        webbrowser.open(url)
        return {"action": "url", "url": url}


workspace_tool = WorkspaceTool()
