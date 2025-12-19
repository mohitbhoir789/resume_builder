from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, Optional

import httpx

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


class OllamaProvider(LLMProvider):
    def __init__(
        self,
        url: str = None,
        model: str = None,
        timeout: int = None,
    ) -> None:
        self.url = url or settings.ollama_url
        self.model = model or settings.ollama_model
        self.timeout = timeout or settings.llm_timeout_seconds

    def extract_keywords(self, jd_text: str) -> Dict:
        prompt = self._build_prompt(jd_text)
        payload = {"model": self.model, "prompt": prompt, "stream": False, "options": {"temperature": 0.0}}
        try:
            start = time.time()
            resp = httpx.post(
                f"{self.url}/api/generate", json=payload, timeout=self.timeout, headers={"Content-Type": "application/json"}
            )
            resp.raise_for_status()
            data = resp.json()
            output_text = data.get("response", "")
            parsed = self._parse_json(output_text)
            parsed["_latency_ms"] = int((time.time() - start) * 1000)
            return parsed
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logging.warning("Ollama extraction failed, fallback to deterministic: %s", exc)
            return {}

    def _parse_json(self, text: str) -> Dict:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            cleaned = text[text.find("{") : text.rfind("}") + 1]
            return json.loads(cleaned)

    def _build_prompt(self, jd_text: str) -> str:
        return (
            "Extract keywords from the following job description. Return JSON with keys: "
            '{"skills":[], "tools":[], "responsibilities":[], "education":[], "action_verbs":[]}. '
            "Use normalized phrases (e.g., 'machine learning', not abbreviations). "
            "Job description:\n"
            f"{normalize_text(jd_text)}"
        )
