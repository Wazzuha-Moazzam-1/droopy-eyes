"""Backend API used by the Focus Guard frontend.

This module keeps file access and monitor calls out of the Tkinter UI. It is
intentionally a local Python API; no web server is required for the desktop
application.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import TypedDict

import psutil


PROJECT_DIR = Path(__file__).resolve().parents[1]
APP_BLACKLIST_FILE = PROJECT_DIR / "monitors" / "blacklisted.csv"
WEBSITE_BLACKLIST_FILE = PROJECT_DIR / "monitors" / "website_blacklisted.csv"


class ClosedApp(TypedDict):
    name: str
    method: str


class CloseFailure(TypedDict):
    name: str
    reason: str


def _read_values(path: Path) -> list[str]:
    if not path.exists():
        return []

    values: list[str] = []
    with path.open("r", encoding="utf-8", newline="") as file:
        for row in csv.reader(file):
            for value in row:
                cleaned = value.strip()
                if cleaned and cleaned.casefold() not in {
                    item.casefold() for item in values
                }:
                    values.append(cleaned)
    return values


def _write_values(path: Path, values: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(values)


class DetectionAPI:
    """Local service for blacklist management and application detection."""

    def __init__(
        self,
        app_blacklist_file: Path = APP_BLACKLIST_FILE,
        website_blacklist_file: Path = WEBSITE_BLACKLIST_FILE,
    ) -> None:
        self.app_blacklist_file = app_blacklist_file
        self.website_blacklist_file = website_blacklist_file

    def get_blacklist(self, kind: str) -> list[str]:
        return _read_values(self._path_for(kind))

    def add_blacklist_item(self, kind: str, value: str) -> list[str]:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Blacklist value cannot be empty.")

        values = self.get_blacklist(kind)
        if not any(item.casefold() == cleaned.casefold() for item in values):
            values.append(cleaned)
            _write_values(self._path_for(kind), values)
        return values

    def delete_blacklist_items(self, kind: str, values_to_remove: set[str]) -> list[str]:
        if not values_to_remove:
            raise ValueError("Select at least one blacklist item to delete.")

        values = self.get_blacklist(kind)
        remove_keys = {value.casefold() for value in values_to_remove}
        remaining = [value for value in values if value.casefold() not in remove_keys]
        path = self._path_for(kind)
        _write_values(path, remaining)
        saved_values = _read_values(path)
        if any(value.casefold() in remove_keys for value in saved_values):
            raise OSError(f"Could not remove the selected {kind} blacklist item(s).")
        return saved_values

    def find_running_blacklisted_apps(self) -> set[str]:
        blacklist = {value.casefold() for value in self.get_blacklist("app")}
        return {
            process_name
            for process in psutil.process_iter(["name"])
            if (process_name := self._process_name(process)) in blacklist
        }

    def close_running_blacklisted_apps(
        self, app_names: set[str] | None = None
    ) -> tuple[list[ClosedApp], list[CloseFailure]]:
        """Terminate matching processes and report successes and failures."""
        names = app_names or self.find_running_blacklisted_apps()
        wanted = {name.casefold() for name in names}
        closed: list[ClosedApp] = []
        failures: list[CloseFailure] = []

        for process in psutil.process_iter(["name"]):
            process_name = self._process_name(process)
            if not process_name or process_name not in wanted:
                continue
            if process.pid == os.getpid():
                failures.append({"name": process_name, "reason": "Skipped the frontend process"})
                continue
            try:
                process.terminate()
                try:
                    process.wait(timeout=1)
                    method = "closed"
                except psutil.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=1)
                    method = "force-closed"
                closed.append({"name": process_name, "method": method})
            except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.TimeoutExpired, OSError) as error:
                failures.append({"name": process_name, "reason": str(error) or error.__class__.__name__})

        return closed, failures

    @staticmethod
    def _process_name(process: psutil.Process) -> str | None:
        try:
            name = process.info["name"]
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            return None
        return name.casefold() if name else None

    def _path_for(self, kind: str) -> Path:
        if kind == "app":
            return self.app_blacklist_file
        if kind == "website":
            return self.website_blacklist_file
        raise ValueError(f"Unsupported blacklist type: {kind}")
