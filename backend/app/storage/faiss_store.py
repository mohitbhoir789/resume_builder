from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import faiss
import numpy as np


class FaissVectorStore:
    """
    Single-user FAISS store with persistent index + metadata.
    """

    def __init__(self, dim: int = 1024, persist_dir: str = "artifacts") -> None:
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.persist_dir / "faiss.index"
        self.meta_path = self.persist_dir / "faiss_meta.json"
        self.metadata: List[Dict[str, Any]] = []
        self.index: Optional[faiss.IndexFlatIP] = None
        self.dim = dim
        self._load()

    def _load(self) -> None:
        if self.index_path.exists() and self.meta_path.exists():
            try:
                self.index = faiss.read_index(str(self.index_path))
                self.metadata = json.loads(self.meta_path.read_text())
                self.dim = self.index.d
                return
            except Exception:
                pass
        self.index = faiss.IndexFlatIP(self.dim)
        self.metadata = []

    def _persist(self) -> None:
        if self.index is None:
            return
        faiss.write_index(self.index, str(self.index_path))
        self.meta_path.write_text(json.dumps(self.metadata, ensure_ascii=False, indent=2))

    def add(self, vectors: List[List[float]], metadata: List[Dict[str, Any]]) -> None:
        if not vectors:
            return
        if self.index is None or self.index.is_trained is False:
            self.index = faiss.IndexFlatIP(len(vectors[0]))
            self.dim = len(vectors[0])
        arr = np.array(vectors, dtype="float32")
        if arr.shape[1] != self.index.d:
            # recreate index with correct dim
            self.index = faiss.IndexFlatIP(arr.shape[1])
        self.index.add(arr)
        self.metadata.extend(metadata)
        self._persist()

    def search(
        self, vector: List[float], top_k: int = 3, filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[float, Dict[str, Any]]]:
        if self.index is None or self.index.ntotal == 0:
            return []
        q = np.array(vector, dtype="float32").reshape(1, -1)
        sims, idxs = self.index.search(q, top_k)
        results: List[Tuple[float, Dict[str, Any]]] = []
        for score, idx in zip(sims[0], idxs[0]):
            if idx == -1:
                continue
            meta = self.metadata[idx]
            if filters and any(meta.get(k) != v for k, v in filters.items()):
                continue
            results.append((float(score), meta))
        return results
