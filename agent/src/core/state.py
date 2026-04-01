"""Run state persistence: lightweight, no dependency on legacy agent types."""

from __future__ import annotations

import copy
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class RunStateStore:
    """Run state store: records key files such as req/design/code/logs/review."""

    def create_run_dir(self, workspace: Path) -> Path:
        """Create a unique run directory.

        Args:
            workspace: Parent directory (typically runs/).

        Returns:
            Newly created run directory path.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:18]
        suffix = uuid.uuid4().hex[:6]
        run_dir = workspace / f"{timestamp}_{suffix}"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "code").mkdir(exist_ok=True)
        (run_dir / "logs").mkdir(exist_ok=True)
        (run_dir / "artifacts").mkdir(exist_ok=True)
        return run_dir

    def save_request(self, run_dir: Path, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Save the user request.

        Args:
            run_dir: Run directory.
            prompt: User prompt.
            context: Context metadata.

        Returns:
            Saved payload.
        """
        payload = {"prompt": prompt, "context": context}
        self._write_json(run_dir / "req.json", payload)
        return payload

    def save_planner_output(self, run_dir: Path, planner_output: Dict[str, Any]) -> Dict[str, Any]:
        """Save planner output.

        Args:
            run_dir: Run directory.
            planner_output: Planner output dict.

        Returns:
            Saved payload.
        """
        self._write_json(run_dir / "planner_output.json", planner_output)
        return planner_output

    def save_design(self, run_dir: Path, spec: Dict[str, Any], decision: Dict[str, Any]) -> None:
        """Save design spec and judge decision.

        Args:
            run_dir: Run directory.
            spec: Strategy design spec.
            decision: Judge decision result.
        """
        self._write_json(run_dir / "design_spec.json", spec)
        self._write_json(run_dir / "judge_decision.json", decision)

    def save_rag_spec(
        self,
        run_dir: Path,
        selection: Dict[str, Any],
        spec: Dict[str, Any],
        *,
        candidates: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Save RAG results.

        Args:
            run_dir: Run directory.
            selection: Selected API metadata.
            spec: Enriched data API spec.
            candidates: Candidate API list.
        """
        enriched_spec = copy.deepcopy(spec) if spec else {}
        enriched_spec["_rag_metadata"] = selection
        spec_yaml = yaml.safe_dump(enriched_spec, allow_unicode=True, sort_keys=False)
        (run_dir / "data_api_spec.yaml").write_text(spec_yaml, encoding="utf-8")
        self._write_json(run_dir / "rag_metadata.json", selection)
        if candidates:
            candidate_yaml = yaml.safe_dump(
                {"generated_at": datetime.now().isoformat(), "candidates": candidates},
                allow_unicode=True,
                sort_keys=False,
            )
            (run_dir / "rag_candidates.yaml").write_text(candidate_yaml, encoding="utf-8")

    def mark_success(self, run_dir: Path) -> None:
        """Mark the run as successful.

        Args:
            run_dir: Run directory.
        """
        self._write_json(run_dir / "state.json", {"status": "success"})

    def mark_failure(self, run_dir: Path, reason: str) -> None:
        """Mark the run as failed.

        Args:
            run_dir: Run directory.
            reason: Failure reason.
        """
        self._write_json(run_dir / "state.json", {"status": "failed", "reason": reason})

    # -----------------------------------------------------------------------
    # Generic persistence: extract and save key artifacts by tool name
    # -----------------------------------------------------------------------

    _PERSIST_MAP: Dict[str, str] = {
        "plan": "_persist_plan",
        "search": "_persist_search",
        "resolve": "_persist_resolve",
        "design": "_persist_design",
    }

    def persist_tool_result(self, tool_name: str, result_data: Dict[str, Any], run_dir: Path) -> None:
        """Persist key artifacts by tool name.

        Args:
            tool_name: Tool name.
            result_data: Parsed tool result dict.
            run_dir: Run directory.
        """
        method_name = self._PERSIST_MAP.get(tool_name)
        if method_name:
            method = getattr(self, method_name, None)
            if method:
                try:
                    method(result_data, run_dir)
                except Exception:
                    pass

    def _persist_plan(self, data: Dict[str, Any], run_dir: Path) -> None:
        if data and "error" not in data:
            self.save_planner_output(run_dir, data)

    def _persist_search(self, data: Dict[str, Any], run_dir: Path) -> None:
        if data.get("selections"):
            sel = data["selections"][0] if data["selections"] else {}
            spec = data.get("data_api_spec") or {}
            self.save_rag_spec(run_dir, sel, spec, candidates=data.get("candidates"))

    def _persist_resolve(self, data: Dict[str, Any], run_dir: Path) -> None:
        if data and data.get("status") == "ok":
            self._write_json(run_dir / "data_config.json", data)

    def _persist_design(self, data: Dict[str, Any], run_dir: Path) -> None:
        spec = data.get("spec") or {}
        decision = data.get("judge_decision") or {}
        if spec:
            self.save_design(run_dir, spec, decision)

    @staticmethod
    def _write_json(path: Path, data: Any) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
