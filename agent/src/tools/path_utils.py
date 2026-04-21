"""Path safety helpers used by file-access tools.

Two helpers, two threat models:

* `safe_path(p, workdir)` — tool-controlled sandbox. Resolves `p` under
  `workdir` and rejects any escape. Used by `read_file` / `write_file` /
  `edit_file` where the LLM must stay inside the current run dir.

* `safe_user_path(p)` — user-supplied broker files. Accepts any path inside
  the user's home directory or the project CWD, rejects UNC and system
  paths. Used by `analyze_trade_journal` and the Shadow Account tools
  where the journal CSV is legitimately anywhere in the user's filesystem.

Both raise ``ValueError`` on rejection — callers already expect this.
"""

from __future__ import annotations

from pathlib import Path


def _rejects_unc(p: str) -> None:
    """Raise ValueError if `p` starts with a UNC share prefix."""
    if p.startswith("\\\\") or p.startswith("//"):
        raise ValueError(f"UNC paths are not allowed: {p!r}")


def safe_path(p: str, workdir: Path) -> Path:
    """Resolve `p` under `workdir` and ensure it stays inside.

    Args:
        p: User-supplied path (relative or absolute).
        workdir: Workspace root. `p` must resolve to a location inside.

    Returns:
        Absolute resolved path inside `workdir`.

    Raises:
        ValueError: If `p` uses a UNC share, or its resolved form escapes
            `workdir`. Callers surface this back to the LLM as a tool error.
    """
    _rejects_unc(p)
    base = Path(workdir).resolve()
    resolved = (base / p).resolve()
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise ValueError(f"Path {p!r} escapes workspace {base}") from exc
    return resolved


def safe_user_path(p: str) -> Path:
    """Validate a user-supplied absolute file path.

    Used when the LLM passes a broker-export path the user referenced in
    natural language. The path may legitimately live anywhere the user
    keeps files (Desktop, Downloads, a project subdirectory), so the
    envelope is HOME ∪ CWD rather than a tight sandbox.

    Args:
        p: User-supplied path. `~` expansion supported.

    Returns:
        Absolute resolved path.

    Raises:
        ValueError: If `p` is a UNC share, or resolves outside both the
            user's home directory and the current working directory.
    """
    _rejects_unc(p)
    resolved = Path(p).expanduser().resolve()

    home = Path.home().resolve()
    cwd = Path.cwd().resolve()

    if resolved.is_relative_to(home) or resolved.is_relative_to(cwd):
        return resolved

    raise ValueError(
        f"Path {p!r} is outside the user home directory and project directory"
    )
