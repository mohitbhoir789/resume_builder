import os
from typing import Dict, Iterable, List, Tuple
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.config import settings
from app.models.schemas import (
    ATSBreakdown,
    ATSScore,
    AssemblerResult,
    JobInput,
    KeywordBuckets,
    KeywordExtractionResult,
    KeywordMapping,
    MappingEntry,
    OptimizerResult,
    ProfileInput,
    RankedKeyword,
    ResumeContent,
    ScoreResponse,
)
from app.utils.text import STOPWORDS, normalize_text, tokenize
from app.services.optimizer import Optimizer
from app.services.renderer import Renderer
from app.services.assembler import Assembler
from app.storage.store import LocalArtifactStore
from app.services.embeddings import EmbeddingProvider, E5EmbeddingProvider, HashingEmbeddingProvider
from app.services.llm import LLMProvider, NoOpProvider, GeminiProvider
from app.storage.vector_store import LocalVectorStore, VectorStore
from app.models.schemas import AuditPayload


class Pipeline:
    """
    Keyword extraction, semantic mapping (embeddings with TF-IDF fallback), and ATS scoring.
    """

    def __init__(self) -> None:
        self.action_verbs = {
            "led",
            "lead",
            "managed",
            "built",
            "designed",
            "implemented",
            "optimized",
            "delivered",
            "improved",
            "architected",
            "automated",
            "developed",
            "deployed",
            "migrated",
            "refactored",
            "mentored",
        }
        self.edu_terms = {
            "bachelors",
            "bachelor",
            "masters",
            "master",
            "phd",
            "mba",
            "degree",
            "computer science",
            "information technology",
            "engineering",
            "certification",
            "aws certified",
            "azure certified",
            "google cloud certified",
        }
        self.tool_terms = {
            "python",
            "java",
            "javascript",
            "typescript",
            "node",
            "react",
            "nextjs",
            "aws",
            "gcp",
            "azure",
            "docker",
            "kubernetes",
            "sql",
            "postgres",
            "mysql",
            "redis",
            "spark",
            "hadoop",
            "pytorch",
            "tensorflow",
            "scikit-learn",
            "sklearn",
            "pandas",
            "numpy",
            "airflow",
            "kafka",
        }
        self.resp_terms = {
            "ownership",
            "collaboration",
            "communication",
            "roadmap",
            "planning",
            "delivery",
            "stakeholder",
            "requirements",
            "testing",
            "monitoring",
            "observability",
            "mentorship",
            "leadership",
        }
        self.optimizer = Optimizer(self, max_iterations=settings.max_optimizer_iterations)
        self.assembler = Assembler()
        self.renderer = Renderer(self.assembler, max_attempts=settings.max_render_attempts)
        self.store = LocalArtifactStore()
        self.embedding_provider = self._init_embedding_provider()
        self.vector_store_cls = LocalVectorStore
        self._last_mapping_provider: str | None = None
        self._last_mapping_fallback: bool | None = None
        self.llm_provider = self._init_llm_provider()
        self._last_llm_provider: str | None = None
        self._llm_fallback: bool | None = None

    async def generate(self, job: JobInput, profile: ProfileInput, run_id: str) -> ResumeContent:
        extraction = self.extract_and_classify(job.description)
        mapping = self.semantic_map(extraction.ranked_keywords, profile)
        score_detail = self.compute_ats_score(job, profile, extraction, mapping)
        opt_result = await self.optimizer.optimize(job, profile, extraction, mapping, score_detail)
        # re-run mapping/score after optimization to reflect final state
        final_mapping = self.semantic_map(extraction.ranked_keywords, opt_result.optimized_resume)
        final_score_detail = self.compute_ats_score(job, opt_result.optimized_resume, extraction, final_mapping)
        assembler_result = self.assembler.assemble(opt_result.optimized_resume)
        render_result = self.renderer.render(opt_result.optimized_resume, assembler_result)
        if render_result.error:
            raise RuntimeError(
                f"PDF render failed (pages={render_result.page_count}): {render_result.error} | trims={render_result.final_trims}"
            )
        pdf_bytes = Path(render_result.pdf_path).read_bytes() if render_result.pdf_path else b""
        pdf_path = self.store.save_pdf(run_id, pdf_bytes) if pdf_bytes else render_result.pdf_path
        audit_payload = AuditPayload(
            run_id=run_id,
            job=job,
            profile=profile,
            extraction=extraction,
            mapping=final_mapping,
            score_detail=final_score_detail,
            optimizer=opt_result,
            assembler=assembler_result,
            renderer=render_result,
            final_score=final_score_detail.score,
            mapping_provider=getattr(self, "_last_mapping_provider", None),
            mapping_fallback=getattr(self, "_last_mapping_fallback", None),
            llm_provider=self._last_llm_provider,
            llm_fallback=self._llm_fallback,
            llm_latency_ms=getattr(self, "_llm_latency_ms", None),
            llm_fallback_reason=getattr(self, "_llm_fallback_reason", None),
        )
        audit_path = self.store.save_json(run_id, "audit", audit_payload.model_dump())

        keywords = [rk.keyword for rk in extraction.ranked_keywords]
        gaps = [entry.keyword for entry in final_mapping.missing]
        latex_body = assembler_result.latex_source
        page_count = render_result.page_count or 1
        return ResumeContent(
            latex_body=latex_body,
            page_count=page_count,
            ats_score=final_score_detail.score,
            keywords=keywords,
            gaps=gaps,
            extraction=extraction,
            mapping=final_mapping,
            score_detail=final_score_detail,
            optimizer=opt_result,
            assembler=assembler_result,
            renderer=render_result,
            pdf_path=pdf_path,
            audit_path=audit_path,
        )

    async def score(self, job: JobInput, profile: ProfileInput) -> ScoreResponse:
        extraction = self.extract_and_classify(job.description)
        mapping = self.semantic_map(extraction.ranked_keywords, profile)
        score_detail = self.compute_ats_score(job, profile, extraction, mapping)
        keywords = [rk.keyword for rk in extraction.ranked_keywords]
        gaps = [entry.keyword for entry in mapping.missing]
        return ScoreResponse(
            ats_score=score_detail.score,
            keywords=keywords,
            gaps=gaps,
            extraction=extraction,
            mapping=mapping,
            score_detail=score_detail,
        )

    def extract_and_classify(self, text: str, top_k: int = 32) -> KeywordExtractionResult:
        normalized = normalize_text(text)
        tokens = tokenize(normalized)
        if not tokens:
            empty_buckets = KeywordBuckets()
            return KeywordExtractionResult(keywords=empty_buckets, ranked_keywords=[])

        llm_result = {}
        self._last_llm_provider = None
        self._llm_fallback = False
        self._llm_latency_ms = None
        self._llm_fallback_reason = None
        if self.llm_provider:
            try:
                llm_result = self.llm_provider.extract_keywords(text)
                self._last_llm_provider = self.llm_provider.name
                self._llm_latency_ms = llm_result.pop('_latency_ms', None)
                if not llm_result:
                    self._llm_fallback = True
                    self._llm_fallback_reason = 'empty_response'
            except Exception as exc:  # pylint: disable=broad-exception-caught
                llm_result = {}
                self._llm_fallback = True
                self._llm_fallback_reason = str(exc)

        tfidf = TfidfVectorizer(
            analyzer="word", ngram_range=(1, 2), min_df=1, stop_words=STOPWORDS, lowercase=True
        )
        tfidf_matrix = tfidf.fit_transform([" ".join(tokens)])
        feature_names = np.array(tfidf.get_feature_names_out())
        scores = tfidf_matrix.toarray()[0]

        top_indices = scores.argsort()[::-1][:top_k]
        ranked_keywords: List[RankedKeyword] = []
        buckets = KeywordBuckets()

        max_score = scores[top_indices[0]] if top_indices.size else 1.0

        for idx in top_indices:
            keyword = feature_names[idx].strip()
            if not keyword or len(keyword) < 2:
                continue
            category = self.classify_keyword(keyword)
            weight = round(float(scores[idx] / max_score), 3)
            ranked_keywords.append(RankedKeyword(keyword=keyword, category=category, weight=weight))
            self._add_to_bucket(buckets, keyword, category)

        # merge LLM result if available
        if llm_result:
            for cat, items in llm_result.items():
                if cat.startswith("_"):
                    continue
                if isinstance(items, list):
                    for kw in items:
                        kw_norm = normalize_text(kw)
                        if not kw_norm:
                            continue
                        category = cat if cat in buckets.model_fields else self.classify_keyword(kw_norm)
                        rk = RankedKeyword(keyword=kw_norm, category=category, weight=1.0)
                        ranked_keywords.append(rk)
                        self._add_to_bucket(buckets, kw_norm, category)

        ranked_keywords = self._dedupe_ranked(ranked_keywords)
        buckets = self._dedupe_buckets(buckets)
        ranked_keywords = self._dedupe_ranked(ranked_keywords)
        buckets = self._dedupe_buckets(buckets)
        return KeywordExtractionResult(keywords=buckets, ranked_keywords=ranked_keywords)

    def classify_keyword(self, keyword: str) -> str:
        key = keyword.lower()
        if key in self.action_verbs:
            return "action_verbs"
        if key in self.edu_terms:
            return "education"
        if key in self.tool_terms:
            return "tools"
        if key in self.resp_terms:
            return "responsibilities"
        # heuristics
        if any(ch.isdigit() for ch in key):
            return "tools"
        if len(key.split()) > 1 and key.split()[0] in self.action_verbs:
            return "responsibilities"
        # fallback
        return "skills"

    def _add_to_bucket(self, buckets: KeywordBuckets, keyword: str, category: str) -> None:
        if category == "skills":
            buckets.skills.append(keyword)
        elif category == "tools":
            buckets.tools.append(keyword)
        elif category == "responsibilities":
            buckets.responsibilities.append(keyword)
        elif category == "education":
            buckets.education.append(keyword)
        elif category == "action_verbs":
            buckets.action_verbs.append(keyword)
        else:
            buckets.skills.append(keyword)

    def _dedupe_ranked(self, ranked: List[RankedKeyword]) -> List[RankedKeyword]:
        seen = set()
        unique = []
        for rk in ranked:
            if rk.keyword in seen:
                continue
            seen.add(rk.keyword)
            unique.append(rk)
        return unique

    def _dedupe_buckets(self, buckets: KeywordBuckets) -> KeywordBuckets:
        return KeywordBuckets(
            skills=self._dedupe_list(buckets.skills),
            tools=self._dedupe_list(buckets.tools),
            responsibilities=self._dedupe_list(buckets.responsibilities),
            education=self._dedupe_list(buckets.education),
            action_verbs=self._dedupe_list(buckets.action_verbs),
        )

    def _dedupe_list(self, items: Iterable[str]) -> List[str]:
        seen = set()
        result = []
        for item in items:
            if item in seen:
                continue
            seen.add(item)
            result.append(item)
        return result

    def semantic_map(self, ranked_keywords: List[RankedKeyword], profile: ProfileInput) -> KeywordMapping:
        keywords = [rk.keyword for rk in ranked_keywords] or ["placeholder"]
        profile_chunks = self._build_profile_chunks(profile)
        chunk_texts = [c["text"] for c in profile_chunks] or ["empty profile"]

        matched: List[MappingEntry] = []
        partial: List[MappingEntry] = []
        missing: List[MappingEntry] = []

        use_fallback = False
        thresholds = self._mapping_thresholds()

        if self.embedding_provider:
            try:
                store: VectorStore = self.vector_store_cls()
                chunk_vectors = self.embedding_provider.embed(chunk_texts, kind="passage")
                store.upsert(chunk_vectors, profile_chunks)
                keyword_vectors = self.embedding_provider.embed(keywords, kind="query")
                for kw, vec in zip(keywords, keyword_vectors):
                    results = store.query(vec, top_k=1)
                    if not results:
                        missing.append(MappingEntry(keyword=kw))
                        continue
                    best_sim, meta = results[0]
                    entry = MappingEntry(keyword=kw, evidence=meta.get("text", ""), similarity=round(best_sim, 3))
                    if best_sim >= thresholds["match"]:
                        matched.append(entry)
                    elif best_sim >= thresholds["partial"]:
                        partial.append(entry)
                    else:
                        missing.append(MappingEntry(keyword=kw))
                self._last_mapping_provider = self.embedding_provider.name
                self._last_mapping_fallback = False
                return KeywordMapping(matched=matched, partial=partial, missing=missing)
            except Exception:
                use_fallback = True

        # fallback to TF-IDF
        vectorizer = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), stop_words=STOPWORDS, lowercase=True)
        vectorizer.fit(keywords + chunk_texts)
        keyword_vectors = vectorizer.transform(keywords)
        chunk_vectors = vectorizer.transform(chunk_texts)
        similarity_matrix = cosine_similarity(keyword_vectors, chunk_vectors)

        for idx, kw in enumerate(keywords):
            sims = similarity_matrix[idx]
            best_idx = int(np.argmax(sims))
            best_sim = float(sims[best_idx]) if sims.size else 0.0
            best_evidence = profile_chunks[best_idx]["text"] if profile_chunks else ""
            entry = MappingEntry(keyword=kw, evidence=best_evidence, similarity=round(best_sim, 3))
            if best_sim >= thresholds["match"]:
                matched.append(entry)
            elif best_sim >= thresholds["partial"]:
                partial.append(entry)
            else:
                missing.append(MappingEntry(keyword=kw))

        self._last_mapping_provider = "TFIDF_FALLBACK" if use_fallback or not self.embedding_provider else "TFIDF"
        self._last_mapping_fallback = True if use_fallback else False
        return KeywordMapping(matched=matched, partial=partial, missing=missing)

    def _build_profile_chunks(self, profile: ProfileInput) -> List[Dict[str, str]]:
        chunks: List[Dict[str, str]] = []
        for section, items in {
            "experience": profile.experience,
            "projects": profile.projects,
            "skills": profile.skills,
            "education": profile.education,
        }.items():
            for item in items:
                text = item.strip()
                if not text:
                    continue
                chunks.append({"section": section, "text": normalize_text(text)})
        return chunks

    def _init_embedding_provider(self) -> EmbeddingProvider:
        import logging

        provider = os.getenv("EMBEDDING_PROVIDER", settings.embedding_provider).lower()
        if provider == "hashing":
            return HashingEmbeddingProvider()
        # default e5 with fallback
        try:
            return E5EmbeddingProvider()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logging.warning("E5 embedding init failed, falling back to hashing: %s", exc)
            return HashingEmbeddingProvider()

    def _init_llm_provider(self) -> LLMProvider:
        import logging

        provider = os.getenv("LLM_PROVIDER", settings.llm_provider).lower()
        if provider == "gemini":
            try:
                return GeminiProvider()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logging.warning("Gemini init failed, falling back to NoOp: %s", exc)
                return NoOpProvider()
        return NoOpProvider()

    def _mapping_thresholds(self) -> Dict[str, float]:
        match = float(os.getenv("MAPPING_MATCH_THRESHOLD", "0.8"))
        partial = float(os.getenv("MAPPING_PARTIAL_THRESHOLD", "0.65"))
        return {"match": match, "partial": partial}

    def compute_ats_score(
        self, job: JobInput, profile: ProfileInput, extraction: KeywordExtractionResult, mapping: KeywordMapping
    ) -> ATSScore:
        weights = {rk.keyword: rk.weight for rk in extraction.ranked_keywords}
        total_weight = sum(weights.values()) or 1.0

        def coverage_value(entry: MappingEntry, full: bool) -> float:
            if full:
                return 1.0
            return float(entry.similarity or 0.0)

        weighted_coverage = 0.0
        for entry in mapping.matched:
            weighted_coverage += weights.get(entry.keyword, 0.0) * coverage_value(entry, True)
        for entry in mapping.partial:
            weighted_coverage += weights.get(entry.keyword, 0.0) * coverage_value(entry, False)
        coverage_score = min(weighted_coverage / total_weight, 1.0)

        role_terms = normalize_text(job.title + " " + (job.company or "")).split()
        role_terms = [t for t in role_terms if t not in STOPWORDS]
        role_hits = 0
        for entry in mapping.matched + mapping.partial:
            if any(term in (entry.evidence or "") for term in role_terms):
                role_hits += 1
        role_relevance = min(role_hits / (len(role_terms) or 1), 1.0)

        seniority_score = self._seniority_alignment(job, profile)
        conciseness_score = self._conciseness(profile)

        edu_keywords = extraction.keywords.education
        edu_matches = [m for m in mapping.matched if m.keyword in edu_keywords]
        edu_partials = [m for m in mapping.partial if m.keyword in edu_keywords]
        if not edu_keywords:
            education_score = 1.0
        else:
            edu_cov = (len(edu_matches) + 0.5 * len(edu_partials)) / len(edu_keywords)
            education_score = max(0.0, min(edu_cov, 1.0))

        final_score = 10 * (
            0.5 * coverage_score
            + 0.2 * role_relevance
            + 0.1 * seniority_score
            + 0.1 * conciseness_score
            + 0.1 * education_score
        )
        final_score = round(min(final_score, 10.0), 2)

        explanations = self._build_explanations(mapping, edu_keywords, conciseness_score, coverage_score)

        breakdown = ATSBreakdown(
            keyword_coverage=round(coverage_score * 10, 2),
            role_relevance=round(role_relevance * 10, 2),
            seniority=round(seniority_score * 10, 2),
            conciseness=round(conciseness_score * 10, 2),
            education=round(education_score * 10, 2),
        )
        return ATSScore(score=final_score, breakdown=breakdown, explanations=explanations)

    def _seniority_alignment(self, job: JobInput, profile: ProfileInput) -> float:
        job_title = normalize_text(job.title)
        seniority_terms = {
            "intern": 0.1,
            "junior": 0.4,
            "jr": 0.4,
            "mid": 0.6,
            "senior": 0.8,
            "sr": 0.8,
            "staff": 0.9,
            "principal": 1.0,
            "lead": 0.9,
            "manager": 0.8,
        }
        target = 0.6
        for term, val in seniority_terms.items():
            if term in job_title:
                target = val
                break

        profile_text = normalize_text(" ".join(profile.experience + profile.projects))
        profile_score = 0.6
        for term, val in seniority_terms.items():
            if term in profile_text:
                profile_score = max(profile_score, val)
        diff = abs(profile_score - target)
        return max(0.0, 1.0 - diff)

    def _conciseness(self, profile: ProfileInput) -> float:
        total_text = " ".join(profile.experience + profile.projects + profile.education)
        length = len(total_text)
        if length == 0:
            return 0.7
        if length <= 1200:
            return 1.0
        if length <= 2000:
            return 0.8
        if length <= 2800:
            return 0.6
        return 0.4

    def _build_explanations(
        self, mapping: KeywordMapping, edu_keywords: List[str], conciseness: float, coverage: float
    ) -> List[str]:
        explanations: List[str] = []
        for missing in mapping.missing:
            explanations.append(f"Missing keyword: {missing.keyword}")
        for partial in mapping.partial:
            explanations.append(f"Partial match for {partial.keyword} (sim={partial.similarity})")
        if not mapping.missing and coverage < 0.9:
            explanations.append("Coverage below target despite all keywords mapped")
        if edu_keywords and not any(m.keyword in edu_keywords for m in mapping.matched):
            explanations.append("Education requirement not satisfied")
        if conciseness < 0.8:
            explanations.append("Profile may be verbose; tighten bullets")
        return explanations or ["Good alignment"]

    # build_latex removed in favor of assembler
