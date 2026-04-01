"""Swarm API — FastAPI request/response models.

Separate from core models (models.py), designed for HTTP API serialization.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateSwarmRunRequest(BaseModel):
    """Request body for creating a Swarm Run.

    Attributes:
        preset_name: YAML preset name.
        user_vars: User variables for template rendering.
    """

    preset_name: str
    user_vars: dict[str, str] = Field(default_factory=dict)


class SwarmRunSummary(BaseModel):
    """Summary entry for a Swarm Run list item.

    Attributes:
        id: Run unique ID.
        preset_name: Preset name used.
        status: Current status.
        created_at: ISO-format creation time.
        task_count: Total task count.
        completed_count: Completed task count.
    """

    id: str
    preset_name: str
    status: str
    created_at: str
    task_count: int
    completed_count: int


class SwarmRunResponse(BaseModel):
    """Swarm Run detail response.

    Attributes:
        id: Run unique ID.
        preset_name: Preset name used.
        status: Current status.
        user_vars: User-provided variables.
        agents: List of agent definitions.
        tasks: List of task statuses.
        created_at: ISO-format creation time.
        completed_at: ISO-format completion time.
        final_report: Final aggregated report.
    """

    id: str
    preset_name: str
    status: str
    user_vars: dict[str, str]
    agents: list[dict]
    tasks: list[dict]
    created_at: str
    completed_at: str | None = None
    final_report: str | None = None


class SwarmPresetInfo(BaseModel):
    """Swarm preset summary info.

    Attributes:
        name: Preset name.
        title: Preset title.
        description: Preset description.
        agent_count: Number of agents.
        variables: Variable definition list.
    """

    name: str
    title: str
    description: str
    agent_count: int
    variables: list[dict]
