from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class VectorStore:
    def upsert(self, vectors: List[List[float]], metadata: List[Dict[str, Any]]) -> None:
        raise NotImplementedError

    def query(
        self, vector: List[float], top_k: int = 3, filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[float, Dict[str, Any]]]:
        raise NotImplementedError


class LocalVectorStore(VectorStore):
    _store_vectors: List[np.ndarray] = []
    _store_metadata: List[Dict[str, Any]] = []

    def __init__(self) -> None:
        # shared in-memory store
        pass

    def upsert(self, vectors: List[List[float]], metadata: List[Dict[str, Any]]) -> None:
        for vec, meta in zip(vectors, metadata):
            self._store_vectors.append(np.array(vec, dtype=float))
            self._store_metadata.append(meta)

    def query(
        self, vector: List[float], top_k: int = 3, filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[float, Dict[str, Any]]]:
        if not self._store_vectors:
            return []
        q = np.array(vector, dtype=float)
        norms = np.linalg.norm(self._store_vectors, axis=1) * np.linalg.norm(q)
        sims = np.dot(self._store_vectors, q) / (norms + 1e-8)
        results: List[Tuple[float, Dict[str, Any]]] = []
        for sim, meta in zip(sims, self._store_metadata):
            if filters:
                if any(meta.get(k) != v for k, v in filters.items()):
                    continue
            results.append((float(sim), meta))
        results.sort(key=lambda x: x[0], reverse=True)
        return results[:top_k]
