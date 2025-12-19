from __future__ import annotations

import hashlib
import io
import json
import logging
import re
import time
from typing import Dict, List, Tuple

import pdfplumber
from fastapi import UploadFile

try:
    import google.genai as genai
except ImportError:
    # Fallback to deprecated package
    import google.generativeai as genai

from app.models.schemas import IngestResponse
from app.services.embeddings import (
    EmbeddingProvider,
    E5EmbeddingProvider,
    HashingEmbeddingProvider,
)
from app.storage.store import LocalArtifactStore
from app.storage.faiss_store import FaissVectorStore
from app.utils.text import normalize_text


class IngestService:
    def __init__(self) -> None:
        self.store = LocalArtifactStore()
        self.vector_store = FaissVectorStore(dim=1024)
        provider = (IngestService._get_env_provider()).lower()
        if provider == "hashing":
            self.embedding_provider: EmbeddingProvider = HashingEmbeddingProvider()
        else:
            try:
                self.embedding_provider = E5EmbeddingProvider()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logging.warning("E5 embedding init failed, falling back to hashing: %s", exc)
                self.embedding_provider = HashingEmbeddingProvider()
        
        # Initialize Gemini
        self._init_gemini()

    @staticmethod
    def _get_env_provider() -> str:
        import os

        return os.getenv("EMBEDDING_PROVIDER", "e5")
    
    @staticmethod
    def _init_gemini() -> None:
        """Initialize Gemini API"""
        import os
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)

    def ingest_text(self, resume_text: str) -> IngestResponse:
        clean_text = self._normalize_text(resume_text)
        structured = self.extract_sections(clean_text)
        chunks = self.chunk(structured)
        vectors = self._embed_chunks(chunks)
        self.vector_store.add(vectors, [c["metadata"] for c in chunks])
        
        # Convert structured sections to ProfileInput format
        profile = self._profile_from_structured(structured)
        
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
            ingest_type="text",
            pages_parsed=None,
            profile=profile,
        )

    def ingest_pdf(self, file: UploadFile) -> IngestResponse:
        if file.content_type != "application/pdf":
            raise ValueError("Only application/pdf is supported")
        pdf_bytes = file.file.read()
        if not pdf_bytes or not pdf_bytes.startswith(b"%PDF"):
            raise ValueError("Invalid or empty PDF")
        text, pages = self._extract_pdf_text(pdf_bytes)
        clean_text = self._normalize_text(text)
        structured = self.extract_sections(clean_text)
        chunks = self.chunk(structured)
        vectors = self._embed_chunks(chunks)
        self.vector_store.add(vectors, [c["metadata"] for c in chunks])
        
        # Convert structured sections to ProfileInput format
        profile = self._profile_from_structured(structured)
        
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
            ingest_type="pdf",
            pages_parsed=pages,
            profile=profile,
        )

    def _extract_pdf_text(self, data: bytes) -> Tuple[str, int]:
        pages_text: List[str] = []
        try:
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                for page in pdf.pages:
                    pages_text.append(page.extract_text() or "")
            return "\n".join(pages_text), len(pages_text)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            raise ValueError(f"PDF parse failed: {exc}") from exc

    def _normalize_text(self, text: str) -> str:
        text = text.replace("•", "-")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def extract_sections(self, text: str) -> Dict[str, List[str]]:
        """Use Gemini to intelligently extract resume sections"""
        try:
            return self._extract_sections_with_gemini(text)
        except Exception as exc:  # Fallback to regex if Gemini fails
            logging.warning("Gemini section extraction failed, using regex fallback: %s", exc)
            return self._extract_sections_regex(text)
    
    def _extract_sections_with_gemini(self, text: str) -> Dict[str, List[str]]:
        """Use Gemini API to extract resume sections"""
        prompt = f"""Analyze the following resume text and extract the following sections:
- experience (work experience/employment)
- projects (projects/portfolio)
- skills (technical skills, languages, tools)
- education (degrees, universities)
- certifications (certifications, licenses)

For each section, extract all bullet points or lines as they appear in the resume.

Resume text:
{text}

Return the response as JSON with this exact format:
{{
    "experience": ["item 1", "item 2", ...],
    "projects": ["item 1", "item 2", ...],
    "skills": ["item 1", "item 2", ...],
    "education": ["item 1", "item 2", ...],
    "certifications": ["item 1", "item 2", ...]
}}

Only include items that actually exist in the resume. Return empty arrays for missing sections."""

        try:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(prompt)
            
            # Parse JSON response
            response_text = response.text.strip()
            # Extract JSON from markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            sections = json.loads(response_text)
            
            # Ensure all keys exist
            default_sections = {"experience": [], "projects": [], "skills": [], "education": [], "certifications": []}
            for key in default_sections:
                if key not in sections:
                    sections[key] = []
                # Ensure values are lists of strings
                if not isinstance(sections[key], list):
                    sections[key] = [str(sections[key])]
                else:
                    sections[key] = [str(item).strip() for item in sections[key] if str(item).strip()]
            
            return sections
        except json.JSONDecodeError as e:
            logging.error("Failed to parse Gemini JSON response: %s", e)
            raise ValueError("Invalid JSON response from Gemini") from e
    
    def _extract_sections_regex(self, text: str) -> Dict[str, List[str]]:
        """Fallback regex-based section extraction"""
        sections = {"experience": [], "projects": [], "skills": [], "education": [], "certifications": []}
        current = None
        lines = text.split("\n")
        for line in lines:
            l = line.strip()
            header = l.lower()
            # Use regex search with word boundaries for more flexible matching
            if re.search(r"^(work\s+)?experience\s*$", header):
                current = "experience"; continue
            if re.search(r"^projects?\s*$", header):
                current = "projects"; continue
            if re.search(r"^(technical\s+)?skills?\s*$", header):
                current = "skills"; continue
            if re.search(r"^education\s*$", header):
                current = "education"; continue
            if re.search(r"^certifications?\s*$", header):
                current = "certifications"; continue
            # Start a new section if we see a company/school pattern (all caps line with pipes or bars)
            if current and len(l) > 0 and l and not re.search(r"^\s*\*|-|•", l):
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
            }
            chunks.append(self._make_chunk(line, meta))

        if structured.get("skills"):
            skills_text = " ".join(structured["skills"])
            meta = {
                "section": "skills",
                "title": "skills",
                "recency_score": 1.0,
                "seniority": "mid",
            }
            chunks.append(self._make_chunk(skills_text, meta))

        for line in structured.get("education", []):
            if not line:
                continue
            meta = {
                "section": "education",
                "title": line[:80],
                "recency_score": recency(line),
                "seniority": "mid",
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
    def _profile_from_structured(self, structured: Dict[str, List[str]]) -> "ProfileInput":
        from app.models.schemas import ProfileInput
        return ProfileInput(
            experience=structured.get("experience", []),
            projects=structured.get("projects", []),
            skills=structured.get("skills", []),
            education=structured.get("education", []),
        )