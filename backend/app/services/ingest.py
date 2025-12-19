from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from pathlib import Path
from typing import Dict, List, Tuple

import pdfplumber
from fastapi import UploadFile

from app.models.schemas import IngestResponse
from app.services.embeddings import (
    EmbeddingProvider,
    E5EmbeddingProvider,
    HashingEmbeddingProvider,
)
from app.storage.store import LocalArtifactStore
from app.storage.vector_store import FaissVectorStore
from app.utils.text import normalize_text


class IngestService:
    def __init__(self) -> None:
        self.store = LocalArtifactStore()
        self.vector_store = FaissVectorStore(dim=384)
        provider = (IngestService._get_env_provider()).lower()
        if provider == "hashing":
            self.embedding_provider: EmbeddingProvider = HashingEmbeddingProvider()
        else:
            try:
                self.embedding_provider = E5EmbeddingProvider()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logging.warning("E5 embedding init failed, falling back to hashing: %s", exc)
                self.embedding_provider = HashingEmbeddingProvider()

    @staticmethod
    def _get_env_provider() -> str:
        import os

        return os.getenv("EMBEDDING_PROVIDER", "e5")

    def ingest_text(self, resume_text: str) -> IngestResponse:
        clean_text = self._normalize_text(resume_text)
        structured = self.extract_sections(clean_text)
        chunks = self.chunk(structured)
        vectors = self._embed_chunks(chunks)
        self.vector_store.add(vectors, [c["metadata"] for c in chunks])
        audit = {
            "ingest_type": "text",
            "pages_parsed": None,
            "sections": list(structured.keys()),
            "chunks_created": len(chunks),
            "embedding_model": self.embedding_provider.name,
            "vector_store": "faiss",
            "timestamp": time.time(),
        }
        self.store.save_json("profile", "profile_ingest_audit", audit)
        return IngestResponse(
            status="success",
            chunks_created=len(chunks),
            sections=list(structured.keys()),
            embedding_provider=self.embedding_provider.name,
        )

    def ingest_pdf(self, file: UploadFile) -> IngestResponse:
        if file.content_type != "application/pdf":
            raise ValueError("Only application/pdf is supported")
        pdf_bytes = file.file.read()
        text, pages = self._extract_pdf_text(pdf_bytes)
        clean_text = self._normalize_text(text)
        structured = self.extract_sections(clean_text)
        chunks = self.chunk(structured)
        vectors = self._embed_chunks(chunks)
        self.vector_store.add(vectors, [c["metadata"] for c in chunks])
        audit = {
            "ingest_type": "pdf",
            "pages_parsed": pages,
            "sections": list(structured.keys()),
            "chunks_created": len(chunks),
            "embedding_model": self.embedding_provider.name,
            "vector_store": "faiss",
            "timestamp": time.time(),
            "source_bytes": len(pdf_bytes),
        }
        self.store.save_json("profile", "profile_ingest_audit", audit)
        return IngestResponse(
            status="success",
            chunks_created=len(chunks),
            sections=list(structured.keys()),
            embedding_provider=self.embedding_provider.name,
        )

    def _extract_pdf_text(self, data: bytes) -> Tuple[str, int]:
        with pdfplumber.open(Path("/tmp/_resume_ingest.pdf")) as _:
            pass
        tmp = Path("/tmp/resume_ingest.pdf")
        tmp.write_bytes(data)
        pages_text = []
        with pdfplumber.open(str(tmp)) as pdf:
            for page in pdf.pages:
                pages_text.append(page.extract_text() or "")
        tmp.unlink(missing_ok=True)
        return "
".join(pages_text), len(pages_text)

    def _normalize_text(self, text: str) -> str:
        text = text.replace("•", "-")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def extract_sections(self, text: str) -> Dict[str, List[str]]:
        sections = {"experience": [], "projects": [], "skills": [], "education": [], "certifications": []}
        current = None
        lines = text.split("
")
        for line in lines:
            l = line.strip()
            header = l.lower()
            if re.match(r"experience|work experience", header):
                current = "experience"; continue
            if re.match(r"projects?", header):
                current = "projects"; continue
            if re.match(r"skills?", header):
                current = "skills"; continue
            if re.match(r"education", header):
                current = "education"; continue
            if re.match(r"certifications?", header):
                current = "certifications"; continue
            if current:
                sections[current].append(l)
        return sections

    def chunk(self, structured: Dict[str, List[str]]) -> List[Dict]:
        chunks: List[Dict] = []
        current_year = time.localtime().tm_year

        def recency(line: str) -> float:
            years = re.findall(r"(20\d{2}|19\d{2})", line)
            if not years:
                return 0.5
            end_year = max(int(y) for y in years)
            diff = max(0, current_year - end_year)
            return 1.0 / (1 + diff)

        for line in structured.get("experience", []):
            if not line:
                continue
            meta = {
                "section": "experience",
                "title": line[:80],
                "recency_score": recency(line),
                "seniority": "mid",
                "text": normalize_text(line),
            }
            chunks.append(self._make_chunk(line, meta))

        for line in structured.get("projects", []):
            if not line:
                continue
            meta = {
                "section": "projects",
                "title": line[:80],
                "recency_score": 0.8,
                "seniority": "mid",
                "text": normalize_text(line),
            }
            chunks.append(self._make_chunk(line, meta))

        if structured.get("skills"):
            skills_text = " ".join(structured["skills"])
            meta = {"section": "skills", "title": "skills", "recency_score": 1.0, "seniority": "mid", "text": normalize_text(skills_text)}
            chunks.append(self._make_chunk(skills_text, meta))

        for line in structured.get("education", []):
            if not line:
                continue
            meta = {
                "section": "education",
                "title": line[:80],
                "recency_score": recency(line),
                "seniority": "mid",
                "text": normalize_text(line),
            }
            chunks.append(self._make_chunk(line, meta))

        return chunks

    def _make_chunk(self, text: str, metadata: Dict) -> Dict:
        raw = f"{text}|{json.dumps(metadata, sort_keys=True)}"
        chunk_id = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        metadata = {**metadata, "id": chunk_id}
        return {"id": chunk_id, "text": text, "metadata": metadata}

    def _embed_chunks(self, chunks: List[Dict]) -> List[List[float]]:
        if not chunks:
            return []
        texts = ["passage: " + normalize_text(c["text"]) for c in chunks]
        return self.embedding_provider.embed(texts, kind="passage")
