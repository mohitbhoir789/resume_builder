from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import faiss
import numpy as np


class VectorStore:
    def add(self, vectors: List[List[float]], metadata: List[Dict[str, Any]]) -> None:
        raise NotImplementedError

    def search(self, vector: List[float], top_k: int = 3, filters: Optional[Dict[str, Any]] = None) -> List[Tuple[float, Dict[str, Any]]]:
        raise NotImplementedError


class FaissVectorStore(VectorStore):
    def __init__(self, dim: int = 384, persist_dir: str = "artifacts") -> None:
        self.dim = dim
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(exist_ok=True, parents=True)
        self.index_path = self.persist_dir / "faiss.index"
        self.meta_path = self.persist_dir / "faiss_meta.json"
        self.metadata: List[Dict[str, Any]] = []
        self.index = self._load_index()

    def _load_index(self) -> faiss.IndexFlatIP:
        if self.index_path.exists() and self.meta_path.exists():
            try:
                index = faiss.read_index(str(self.index_path))
                self.metadata = json.loads(self.meta_path.read_text())
                return index
            except Exception:
                pass
        return faiss.IndexFlatIP(self.dim)

    def _persist(self) -> None:
        faiss.write_index(self.index, str(self.index_path))
        self.meta_path.write_text(json.dumps(self.metadata, ensure_ascii=False, indent=2))

    def add(self, vectors: List[List[float]], metadata: List[Dict[str, Any]]) -> None:
        if not vectors:
            return
        arr = np.array(vectors, dtype="float32")
        self.index.add(arr)
        self.metadata.extend(metadata)
        self._persist()

    def search(self, vector: List[float], top_k: int = 3, filters: Optional[Dict[str, Any]] = None) -> List[Tuple[float, Dict[str, Any]]]:
        if self.index.ntotal == 0:
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
