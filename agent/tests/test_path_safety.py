"""Tests for path safety helpers in src.tools.path_utils."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.tools.path_utils import safe_path, safe_user_path


# ---------------------------------------------------------------------------
# safe_path — tool-controlled sandbox under a fixed workdir
# ---------------------------------------------------------------------------

class TestSafePath:
    def test_relative_path_resolves_under_workdir(self, tmp_path: Path):
        result = safe_path("notes.md", tmp_path)
        assert result == (tmp_path / "notes.md").resolve()

    def test_nested_relative_path_ok(self, tmp_path: Path):
        result = safe_path("sub/dir/file.txt", tmp_path)
        assert result == (tmp_path / "sub" / "dir" / "file.txt").resolve()

    def test_parent_traversal_rejected(self, tmp_path: Path):
        with pytest.raises(ValueError, match="escapes workspace"):
            safe_path("../../etc/passwd", tmp_path)

    def test_absolute_path_outside_workdir_rejected(self, tmp_path: Path):
        outside = tmp_path.parent / "elsewhere.txt"
        with pytest.raises(ValueError, match="escapes workspace"):
            safe_path(str(outside), tmp_path)

    def test_unc_path_rejected(self, tmp_path: Path):
        with pytest.raises(ValueError, match="UNC paths"):
            safe_path("\\\\server\\share\\evil.csv", tmp_path)

    def test_unix_double_slash_rejected(self, tmp_path: Path):
        with pytest.raises(ValueError, match="UNC paths"):
            safe_path("//server/share/evil.csv", tmp_path)

    def test_normalizes_redundant_segments(self, tmp_path: Path):
        (tmp_path / "a").mkdir()
        result = safe_path("a/./file.txt", tmp_path)
        assert result == (tmp_path / "a" / "file.txt").resolve()


# ---------------------------------------------------------------------------
# safe_user_path — user-supplied broker files, HOME ∪ CWD envelope
# ---------------------------------------------------------------------------

class TestSafeUserPath:
    def test_home_file_accepted(self, tmp_path: Path, monkeypatch):
        # Pretend HOME is tmp_path so we can control the envelope
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        target = tmp_path / "Desktop" / "broker.csv"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch()

        result = safe_user_path(str(target))
        assert result == target.resolve()

    def test_tilde_expansion_works(self, tmp_path: Path, monkeypatch):
        # Both Path.home() and Path.expanduser() read environment variables,
        # so set HOME / USERPROFILE directly rather than patching Path.home.
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        target = tmp_path / "journal.csv"
        target.touch()

        result = safe_user_path("~/journal.csv")
        assert result == target.resolve()

    def test_cwd_file_accepted(self, tmp_path: Path, monkeypatch):
        # HOME is far away; CWD is tmp_path
        other = tmp_path.parent / "somewhere_else"
        other.mkdir(exist_ok=True)
        monkeypatch.setattr(Path, "home", lambda: other)
        monkeypatch.chdir(tmp_path)

        target = tmp_path / "local.csv"
        target.touch()
        result = safe_user_path("local.csv")
        assert result == target.resolve()

    def test_system_path_outside_envelope_rejected(self, tmp_path: Path, monkeypatch):
        # HOME and CWD both inside tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.chdir(tmp_path)

        # /etc is outside both
        with pytest.raises(ValueError, match="outside the user home"):
            safe_user_path("/etc/passwd")

    def test_parent_traversal_from_cwd_rejected(self, tmp_path: Path, monkeypatch):
        deep = tmp_path / "deep" / "cwd"
        deep.mkdir(parents=True)
        monkeypatch.setattr(Path, "home", lambda: deep)
        monkeypatch.chdir(deep)

        # Resolve back above both HOME and CWD
        with pytest.raises(ValueError, match="outside the user home"):
            safe_user_path("../../../../../etc/passwd")

    def test_unc_path_rejected(self):
        with pytest.raises(ValueError, match="UNC paths"):
            safe_user_path("\\\\evil-server\\share\\passwd.csv")

    def test_unix_double_slash_rejected(self):
        with pytest.raises(ValueError, match="UNC paths"):
            safe_user_path("//evil-server/share/passwd.csv")
