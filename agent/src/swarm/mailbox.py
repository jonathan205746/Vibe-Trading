"""Swarm multi-agent system — file-based Mailbox.

File-system-based message passing between agents. Each agent has an independent
inbox directory. Messages are sorted by timestamp and carry only summaries and
artifact paths, not full content.

Directory structure:
    inboxes/{agent_id}/msg-{timestamp}-{uuid_short}.json
"""

from __future__ import annotations

import uuid
from pathlib import Path

from src.swarm.models import SwarmMessage


class Mailbox:
    """File-based agent message inbox.

    Each agent has an independent directory under run_dir/inboxes/{agent_id}/.
    Messages are stored as JSON files with timestamps in the filename for ordering.

    Attributes:
        run_dir: Root directory of the current run.
    """

    def __init__(self, run_dir: Path) -> None:
        """Initialize Mailbox.

        Args:
            run_dir: Path to .swarm/runs/{run_id}/ directory.
        """
        self.run_dir = run_dir
        self._inboxes_dir = run_dir / "inboxes"
        self._inboxes_dir.mkdir(parents=True, exist_ok=True)

    def send(self, msg: SwarmMessage) -> None:
        """Send a message to the target agent's inbox.

        Args:
            msg: SwarmMessage to send.
        """
        inbox_dir = self._inboxes_dir / msg.to
        inbox_dir.mkdir(parents=True, exist_ok=True)

        ts_safe = msg.timestamp.replace(":", "-").replace(".", "-")
        uid = uuid.uuid4().hex[:8]
        filename = f"msg-{ts_safe}-{uid}.json"

        msg_path = inbox_dir / filename
        tmp_path = msg_path.with_suffix(".tmp")
        tmp_path.write_text(msg.model_dump_json(indent=2), encoding="utf-8")
        tmp_path.replace(msg_path)

    def read_inbox(self, agent_id: str) -> list[SwarmMessage]:
        """Read all messages for the given agent, sorted by timestamp.

        Args:
            agent_id: Agent ID.

        Returns:
            List of SwarmMessage sorted by timestamp ascending.
        """
        inbox_dir = self._inboxes_dir / agent_id
        if not inbox_dir.exists():
            return []

        messages: list[SwarmMessage] = []
        for path in sorted(inbox_dir.glob("msg-*.json")):
            messages.append(
                SwarmMessage.model_validate_json(path.read_text(encoding="utf-8"))
            )

        messages.sort(key=lambda m: m.timestamp)
        return messages

    def read_from(self, agent_id: str, from_agent: str) -> list[SwarmMessage]:
        """Read messages in an agent's inbox from a specific sender.

        Args:
            agent_id: Receiving agent ID.
            from_agent: Sending agent ID.

        Returns:
            List of SwarmMessage from from_agent, sorted by timestamp ascending.
        """
        all_messages = self.read_inbox(agent_id)
        return [m for m in all_messages if m.from_agent == from_agent]
