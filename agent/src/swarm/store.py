"""Swarm multi-agent system — run state persistence.

File-system-based persistence for SwarmRun. Directory structure:
    .swarm/runs/{run_id}/
    ├── run.json         # SwarmRun state (atomic write)
    ├── events.jsonl     # append-only event log
    ├── tasks/           # task state files
    ├── inboxes/         # agent message inboxes
    └── artifacts/       # agent outputs
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

from src.swarm.models import SwarmEvent, SwarmRun


class SwarmStore:
    """File-based persistence store for SwarmRun.

    Each run is stored under base_dir/{run_id}/. run.json uses atomic writes
    (write to .tmp then rename) to prevent corruption. events.jsonl is append-only
    and supports offset-based reads for SSE streaming.

    Attributes:
        base_dir: Storage root directory, typically agent/.swarm/runs.
    """

    def __init__(self, base_dir: Path) -> None:
        """Initialize SwarmStore.

        Args:
            base_dir: Storage root directory path.
        """
        self.base_dir = base_dir
        self._write_lock = threading.Lock()

    def run_dir(self, run_id: str) -> Path:
        """Return the directory path for a given run.

        Args:
            run_id: Run identifier.

        Returns:
            Path to the run directory.
        """
        return self.base_dir / run_id

    def create_run(self, run: SwarmRun) -> Path:
        """Create the directory structure for a new run and write initial state.

        Args:
            run: SwarmRun instance.

        Returns:
            Path to the created run directory.

        Raises:
            FileExistsError: If the run directory already exists.
        """
        rd = self.run_dir(run.id)
        rd.mkdir(parents=True, exist_ok=False)
        (rd / "tasks").mkdir()
        (rd / "inboxes").mkdir()
        (rd / "artifacts").mkdir()
        self._atomic_write(rd / "run.json", run.model_dump_json(indent=2))
        return rd

    def load_run(self, run_id: str) -> SwarmRun | None:
        """Load the state for a given run.

        Args:
            run_id: Run identifier.

        Returns:
            SwarmRun instance, or None if not found.
        """
        run_file = self.run_dir(run_id) / "run.json"
        if not run_file.exists():
            return None
        return SwarmRun.model_validate_json(run_file.read_text(encoding="utf-8"))

    def update_run(self, run: SwarmRun) -> None:
        """Atomically update run state.

        Args:
            run: Updated SwarmRun instance.

        Raises:
            FileNotFoundError: If the run directory does not exist.
        """
        rd = self.run_dir(run.id)
        if not rd.exists():
            raise FileNotFoundError(f"Run directory not found: {rd}")
        self._atomic_write(rd / "run.json", run.model_dump_json(indent=2))

    def list_runs(self, limit: int = 50) -> list[SwarmRun]:
        """List all runs sorted by created_at descending.

        Args:
            limit: Maximum number of runs to return.

        Returns:
            List of SwarmRun instances.
        """
        if not self.base_dir.exists():
            return []

        runs: list[SwarmRun] = []
        for entry in self.base_dir.iterdir():
            if not entry.is_dir():
                continue
            run_file = entry / "run.json"
            if run_file.exists():
                try:
                    run = SwarmRun.model_validate_json(
                        run_file.read_text(encoding="utf-8")
                    )
                    runs.append(run)
                except (json.JSONDecodeError, ValueError):
                    continue

        runs.sort(key=lambda r: r.created_at, reverse=True)
        return runs[:limit]

    def append_event(self, run_id: str, event: SwarmEvent) -> None:
        """Append an event to events.jsonl.

        Args:
            run_id: Run identifier.
            event: Event to append.

        Raises:
            FileNotFoundError: If the run directory does not exist.
        """
        rd = self.run_dir(run_id)
        if not rd.exists():
            raise FileNotFoundError(f"Run directory not found: {rd}")
        events_file = rd / "events.jsonl"
        with self._write_lock:
            with events_file.open("a", encoding="utf-8") as f:
                f.write(event.model_dump_json() + "\n")

    def read_events(
        self, run_id: str, after_index: int = 0
    ) -> list[SwarmEvent]:
        """Read the event log with optional offset for SSE incremental streaming.

        Args:
            run_id: Run identifier.
            after_index: Skip the first N events and return from event N+1 onward.

        Returns:
            List of SwarmEvent instances.
        """
        events_file = self.run_dir(run_id) / "events.jsonl"
        if not events_file.exists():
            return []

        events: list[SwarmEvent] = []
        lines = events_file.read_text(encoding="utf-8").strip().splitlines()
        for line in lines[after_index:]:
            stripped = line.strip()
            if stripped:
                events.append(SwarmEvent.model_validate_json(stripped))
        return events

    def _atomic_write(self, path: Path, content: str) -> None:
        """Atomically write a file: write to .tmp then rename.

        Args:
            path: Target file path.
            content: File content.
        """
        tmp_path = path.with_suffix(".tmp")
        with self._write_lock:
            tmp_path.write_text(content, encoding="utf-8")
            tmp_path.replace(path)
