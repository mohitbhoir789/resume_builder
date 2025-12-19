from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import List

import httpx
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import HashingVectorizer

from app.utils.text import normalize_text


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: List[str], kind: str = "passage") -> List[List[float]]: ...

    @property
    def name(self) -> str:
        return self.__class__.__name__


class HashingEmbeddingProvider(EmbeddingProvider):
    """
    Deterministic local embedding via HashingVectorizer (simulates sentence embeddings without external calls).
    """

    def __init__(self, n_features: int = 384) -> None:
        self.vectorizer = HashingVectorizer(
            n_features=n_features, alternate_sign=False, norm="l2", ngram_range=(1, 2), lowercase=True
        )

    def embed(self, texts: List[str], kind: str = "passage") -> List[List[float]]:
        normalized = [normalize_text(t) for t in texts]
        mat = self.vectorizer.transform(normalized)
        return mat.toarray().tolist()


class E5EmbeddingProvider(EmbeddingProvider):
    """
    Local semantic embeddings using intfloat/e5-large-v2.
    """

    def __init__(self) -> None:
        self.model = SentenceTransformer("intfloat/e5-large-v2")

    def embed(self, texts: List[str], kind: str = "passage") -> List[List[float]]:
        prefixes = {"query": "query: ", "passage": "passage: "}
        prefix = prefixes.get(kind, "passage: ")
        inputs = [prefix + t for t in texts]
        emb = self.model.encode(inputs, normalize_embeddings=True, show_progress_bar=False, batch_size=16)
        return emb.tolist()


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    Calls OpenAI embedding API (text-embedding-3-large).
    """

    def __init__(self, model: str = "text-embedding-3-large", api_base: str = "https://api.openai.com/v1") -> None:
        self.model = model
        self.api_base = api_base
        self.api_key = os.getenv("OPENAI_API_KEY", "")

    def embed(self, texts: List[str], kind: str = "passage") -> List[List[float]]:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        url = f"{self.api_base}/embeddings"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"input": texts, "model": self.model}
        resp = httpx.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        vectors = [item["embedding"] for item in data["data"]]
        return vectors
