"""Shared path utilities for tools."""

from __future__ import annotations

from pathlib import Path


def safe_path(p: str, workdir: Path) -> Path:
    """Resolve a path relative to the workspace root.

    Args:
        p: Relative or absolute path.
        workdir: Workspace root directory.

    Returns:
        Resolved absolute path.
    """
    return (workdir / p).resolve()
