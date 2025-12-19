from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List


class ArtifactStore(ABC):
    @abstractmethod
    def save_pdf(self, run_id: str, pdf_bytes: bytes) -> str: ...

    @abstractmethod
    def save_json(self, run_id: str, name: str, payload: Dict[str, Any]) -> str: ...

    @abstractmethod
    def get_artifact(self, path: str) -> bytes: ...

    @abstractmethod
    def list_artifacts(self, run_id: str) -> List[str]: ...


class LocalArtifactStore(ArtifactStore):
    def __init__(self, base_dir: str = "artifacts") -> None:
        self.base = Path(base_dir).resolve()
        self.base.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, run_id: str, name: str) -> Path:
        safe_run = run_id.replace("/", "_")
        safe_name = name.replace("/", "_")
        path = self.base / safe_run / safe_name
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def save_pdf(self, run_id: str, pdf_bytes: bytes) -> str:
        path = self._safe_path(run_id, "resume.pdf")
        path.write_bytes(pdf_bytes)
        return str(path)

    def save_json(self, run_id: str, name: str, payload: Dict[str, Any]) -> str:
        path = self._safe_path(run_id, f"{name}.json")
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(path)

    def get_artifact(self, path: str) -> bytes:
        safe_path = Path(path).resolve()
        if not str(safe_path).startswith(str(self.base)):
            raise ValueError("unsafe path")
        if not safe_path.exists():
            raise FileNotFoundError(path)
        return safe_path.read_bytes()

    def list_artifacts(self, run_id: str) -> List[str]:
        run_path = self.base / run_id
        if not run_path.exists():
            return []
        return [str(p) for p in run_path.glob("*") if p.is_file()]
