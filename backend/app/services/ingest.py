from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Dict, List

from app.models.schemas import IngestRequest, IngestResponse
import logging

from app.services.embeddings import (
    EmbeddingProvider,
    E5EmbeddingProvider,
    HashingEmbeddingProvider,
    OpenAIEmbeddingProvider,
)
from app.storage.store import LocalArtifactStore
from app.storage.vector_store import LocalVectorStore
from app.utils.text import normalize_text


class IngestService:
    def __init__(self) -> None:
        self.store = LocalArtifactStore()
        self.vector_store = LocalVectorStore()
        provider = (IngestService._get_env_provider()).lower()
        if provider == "openai":
            try:
                self.embedding_provider: EmbeddingProvider = OpenAIEmbeddingProvider()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logging.warning("OpenAI embedding init failed, falling back to hashing: %s", exc)
                self.embedding_provider = HashingEmbeddingProvider()
        elif provider == "hashing":
            self.embedding_provider = HashingEmbeddingProvider()
        else:
            try:
                self.embedding_provider = E5EmbeddingProvider()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logging.warning("E5 embedding init failed, falling back to hashing: %s", exc)
                self.embedding_provider = HashingEmbeddingProvider()

    @staticmethod
    def _get_env_provider() -> str:
        import os

        return os.getenv("EMBEDDING_PROVIDER", "local")

    def ingest(self, payload: IngestRequest) -> IngestResponse:
        structured = self.extract_latex(payload.resume_latex)
        chunks = self.chunk(structured, payload.user_id)
        vectors = []
        for chunk in chunks:
            try:
                vec = self.embedding_provider.embed([chunk["text"]], kind="passage")[0]
            except Exception:
                vec = []
            vectors.append(vec)
        self.vector_store.upsert(
            vectors,
            [
                {
                    **chunk["metadata"],
                    "id": chunk["id"],
                    "namespace": chunk["metadata"]["user_id"],
                    "text": chunk["text"],
                }
                for chunk in chunks
            ],
        )

        audit = {
            "user_id": payload.user_id,
            "chunks_created": len(chunks),
            "sections": list(structured.keys()),
            "embedding_model": self.embedding_provider.name,
            "timestamp": time.time(),
        }
        self.store.save_json(payload.user_id, "profile_ingest_audit", audit)

        return IngestResponse(
            status="success",
            chunks_created=len(chunks),
            sections=list(structured.keys()),
            embedding_provider=self.embedding_provider.name,
        )

    def extract_latex(self, latex: str) -> Dict[str, List[str]]:
        # remove comments
        latex = re.sub(r"%.*", "", latex)
        # focus between \begin{document} and \end{document}
        match = re.search(r"\\begin{document}(.*)\\end{document}", latex, re.S)
        content = match.group(1) if match else latex
        sections = {"skills": [], "experience": [], "projects": [], "education": []}

        # skills section: items after \section{Technical Skills}
        skills_match = re.search(r"\\section{Technical Skills}(.*?)(\\section{Work Experience}|\\section{Projects})", content, re.S)
        if skills_match:
            skills_block = skills_match.group(1)
            for line in re.findall(r"\\item\s+([^\\]+)", skills_block):
                sections["skills"].append(normalize_text(line.strip()))

        # experience: parse resumeSubheading blocks
        exp_blocks = re.split(r"\\resumeSubheading", content)
        for block in exp_blocks[1:]:
            header_match = re.match(r"\s*{([^}]*)}{([^}]*)}{([^}]*)}{([^}]*)}", block, re.S)
            if not header_match:
                continue
            company, dates, role, location = [normalize_text(h) for h in header_match.groups()]
            bullets = re.findall(r"\\resumeItem{([^}]*)}", block)
            bullet_texts = [normalize_text(b) for b in bullets]
            if company:
                sections["experience"].append(
                    {"company": company, "role": role, "dates": dates, "location": location, "bullets": bullet_texts}
                )

        # projects
        proj_blocks = re.split(r"\\resumeProjectHeading", content)
        for block in proj_blocks[1:]:
            header_match = re.match(r"\s*{([^}]*)}{[^}]*}", block, re.S)
            if not header_match:
                continue
            title = normalize_text(header_match.group(1))
            bullets = re.findall(r"\\resumeItem{([^}]*)}", block)
            bullet_texts = [normalize_text(b) for b in bullets]
            if title:
                sections["projects"].append({"project": title, "bullets": bullet_texts})

        # education
        edu_blocks = re.findall(
            r"\\resumeUniSubheading\s*{([^}]*)}{([^}]*)}{([^}]*)}{([^}]*)}{([^}]*)}", content, re.S
        )
        for edu in edu_blocks:
            university, dates, degree, location, gpa = [normalize_text(e) for e in edu]
            sections["education"].append({"school": university, "degree": degree, "dates": dates, "location": location, "gpa": gpa})

        return sections

    def chunk(self, structured: Dict[str, List[str]], user_id: str) -> List[Dict]:
        chunks: List[Dict] = []
        current_year = time.localtime().tm_year

        def recency(date_str: str) -> float:
            years = re.findall(r"(20\d{2}|19\d{2})", date_str)
            if not years:
                return 0.5
            end_year = max(int(y) for y in years)
            diff = max(0, current_year - end_year)
            return 1.0 / (1 + diff)

        # skills
        if isinstance(structured.get("skills"), list):
            for skill in structured["skills"]:
                text = skill
                meta = {
                    "user_id": user_id,
                    "section": "skills",
                    "company": "",
                    "role": "",
                    "project": "",
                    "start_date": "",
                    "end_date": "",
                    "seniority": "mid",
                    "recency_score": 1.0,
                }
                chunks.append(self._make_chunk(text, meta))

        # experience
        for exp in structured.get("experience", []):
            text = f"{exp.get('company','')} | {exp.get('role','')} | {exp.get('dates','')}. " + " ".join(
                exp.get("bullets", [])
            )
            meta = {
                "user_id": user_id,
                "section": "experience",
                "company": exp.get("company", ""),
                "role": exp.get("role", ""),
                "project": "",
                "start_date": "",
                "end_date": exp.get("dates", ""),
                "seniority": "mid",
                "recency_score": recency(exp.get("dates", "")),
            }
            chunks.append(self._make_chunk(text, meta))

        # projects
        for proj in structured.get("projects", []):
            text = f"{proj.get('project','')}. " + " ".join(proj.get("bullets", []))
            meta = {
                "user_id": user_id,
                "section": "projects",
                "company": "",
                "role": "",
                "project": proj.get("project", ""),
                "start_date": "",
                "end_date": "",
                "seniority": "mid",
                "recency_score": 0.8,
            }
            chunks.append(self._make_chunk(text, meta))

        # education
        for edu in structured.get("education", []):
            text = f"{edu.get('school','')} | {edu.get('degree','')} | {edu.get('dates','')} | {edu.get('location','')}"
            meta = {
                "user_id": user_id,
                "section": "education",
                "company": "",
                "role": "",
                "project": "",
                "start_date": "",
                "end_date": edu.get("dates", ""),
                "seniority": "mid",
                "recency_score": recency(edu.get("dates", "")),
            }
            chunks.append(self._make_chunk(text, meta))

        return chunks

    def _make_chunk(self, text: str, metadata: Dict) -> Dict:
        raw = f"{text}|{json.dumps(metadata, sort_keys=True)}"
        chunk_id = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return {"id": chunk_id, "text": text, "metadata": metadata}
