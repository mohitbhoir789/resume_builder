from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Dict

import google.generativeai as genai

from app.core.config import settings
from app.utils.text import normalize_text


class LLMProvider(ABC):
    @abstractmethod
    def extract_keywords(self, jd_text: str) -> Dict:
        ...

    @property
    def name(self) -> str:
        return self.__class__.__name__


class NoOpProvider(LLMProvider):
    def extract_keywords(self, jd_text: str) -> Dict:
        return {}


class GeminiProvider(LLMProvider):
    def __init__(self) -> None:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY not set")
        genai.configure(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model or "gemini-1.5-flash"
        self.client = genai.GenerativeModel(self.model)

    def extract_keywords(self, jd_text: str) -> Dict:
        prompt = self._build_prompt(jd_text)
        try:
            start = time.time()
            resp = self.client.generate_content(
                prompt,
                generation_config={"temperature": 0, "response_mime_type": "application/json"},
            )
            latency = int((time.time() - start) * 1000)
            text = resp.text or "{}"
            parsed = json.loads(text)
            parsed["_latency_ms"] = latency
            return parsed
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logging.warning("Gemini extraction failed, fallback to deterministic: %s", exc)
            return {}

    def _build_prompt(self, jd_text: str) -> str:
        body = normalize_text(jd_text)
        return (
            "Extract keywords from the job description and return strict JSON with keys: "
            '{"skills":[], "tools":[], "responsibilities":[], "education":[], "action_verbs":[]}.'
            " Use normalized phrases (e.g., 'machine learning'). Job description:\n"
            f"{body}"
        )
