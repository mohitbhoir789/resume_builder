from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import List, Tuple

from app.models.schemas import (
    ATSScore,
    KeywordExtractionResult,
    KeywordMapping,
    OptimizerIteration,
    OptimizerResult,
    ProfileInput,
    RankedKeyword,
)
from app.utils.text import normalize_text


@dataclass
class BulletScore:
    index: int
    section: str
    text: str
    score: float


class Optimizer:
    """
    Deterministic, rule-based optimizer that tightens bullets, inserts high-weight keywords when evidence exists,
    reorders by relevance, and trims low-signal content. No free-form generation.
    """

    def __init__(self, pipeline: "Pipeline", max_iterations: int = 5, target_score: float = 8.5) -> None:
        self.pipeline = pipeline
        self.max_iterations = max_iterations
        self.target_score = target_score
        self.filler_phrases = [
            "responsible for",
            "worked on",
            "helped",
            "participated in",
            "involved in",
            "leveraged",
            "utilized",
            "using",
            "with a focus on",
            "various",
        ]

    async def optimize(
        self,
        job,
        profile: ProfileInput,
        extraction: KeywordExtractionResult,
        mapping: KeywordMapping,
        score_detail: ATSScore,
    ) -> OptimizerResult:
        current_profile = deepcopy(profile)
        current_score = score_detail
        iterations: List[OptimizerIteration] = []
        baseline_mapping = mapping

        for i in range(1, self.max_iterations + 1):
            changes: List[str] = []

            tightened, tighten_changes = self._tighten_bullets(current_profile)
            changes.extend(tighten_changes)
            if tightened:
                current_profile = tightened

            insertion_changes = self._insert_keywords(
                current_profile, extraction.ranked_keywords, baseline_mapping, threshold=0.6
            )
            changes.extend(insertion_changes)

            reordered, reorder_changes = self._reorder(current_profile, extraction.ranked_keywords)
            changes.extend(reorder_changes)
            if reordered:
                current_profile = reordered

            trimmed, trim_changes = self._trim_sections(current_profile)
            changes.extend(trim_changes)
            if trimmed:
                current_profile = trimmed

            new_mapping = self.pipeline.semantic_map(extraction.ranked_keywords, current_profile)
            new_score = self.pipeline.compute_ats_score(job, current_profile, extraction, new_mapping)

            iterations.append(
                OptimizerIteration(
                    iteration=i,
                    changes=changes or ["No changes"],
                    score_before=current_score.score,
                    score_after=new_score.score,
                )
            )

            delta = new_score.score - current_score.score
            current_score = new_score
            baseline_mapping = new_mapping

            if new_score.score >= self.target_score:
                break
            if delta < 0.2:
                break

        return OptimizerResult(
            optimized_resume=current_profile,
            iterations=iterations,
            final_score=current_score.score,
            final_score_detail=current_score,
            final_mapping=baseline_mapping,
        )

    def _tighten_bullets(self, profile: ProfileInput) -> Tuple[ProfileInput, List[str]]:
        updated = deepcopy(profile)
        changes: List[str] = []
        for section in ["experience", "projects"]:
            bullets = getattr(profile, section)
            new_bullets = []
            for bullet in bullets:
                tightened = self._tighten_text(bullet)
                if tightened != bullet:
                    changes.append(f"Tightened {section} bullet: '{bullet[:40]}...' -> '{tightened[:40]}...'")
                new_bullets.append(tightened)
            setattr(updated, section, new_bullets)
        return updated, changes

    def _tighten_text(self, text: str) -> str:
        lowered = text.lower()
        for phrase in self.filler_phrases:
            lowered = lowered.replace(phrase, "")
        tightened = " ".join(lowered.split())
        tokens = tightened.split(" ")
        if len(tokens) > 36:
            tightened = " ".join(tokens[:36])
        return tightened.strip().capitalize()

    def _insert_keywords(
        self,
        profile: ProfileInput,
        ranked_keywords: List[RankedKeyword],
        mapping: KeywordMapping,
        threshold: float,
    ) -> List[str]:
        changes: List[str] = []
        missing_high = [rk for rk in ranked_keywords if self._is_missing(rk.keyword, mapping) and rk.weight >= threshold]
        if not missing_high:
            return changes

        normalized_profile_text = normalize_text(
            " ".join(profile.experience + profile.projects + profile.skills + profile.education)
        )
        for rk in missing_high:
            if rk.keyword not in normalized_profile_text:
                continue  # no evidence, skip
            # Prefer inserting into skills list if not present
            if rk.keyword not in [normalize_text(s) for s in profile.skills]:
                profile.skills.append(rk.keyword)
                changes.append(f"Inserted missing keyword '{rk.keyword}' into skills")
                continue
            # Otherwise annotate first bullet containing keyword fragment
            fragment = rk.keyword.split(" ")[0]
            inserted = False
            for section in ["experience", "projects"]:
                bullets = getattr(profile, section)
                for idx, bullet in enumerate(bullets):
                    if fragment in normalize_text(bullet) and rk.keyword not in normalize_text(bullet):
                        bullets[idx] = f"{bullet} ({rk.keyword})"
                        changes.append(f"Inserted keyword '{rk.keyword}' into {section} bullet {idx+1}")
                        inserted = True
                        break
                if inserted:
                    break
        return changes

    def _reorder(
        self, profile: ProfileInput, ranked_keywords: List[RankedKeyword]
    ) -> Tuple[ProfileInput, List[str]]:
        changes: List[str] = []
        keyword_set = {rk.keyword for rk in ranked_keywords}

        updated = deepcopy(profile)
        for section in ["experience", "projects"]:
            bullets = getattr(profile, section)
            if len(bullets) <= 1:
                continue
            scored = []
            for idx, bullet in enumerate(bullets):
                norm = normalize_text(bullet)
                score = sum(1 for kw in keyword_set if kw in norm)
                scored.append(BulletScore(index=idx, section=section, text=bullet, score=score))
            scored.sort(key=lambda x: x.score, reverse=True)
            reordered = [s.text for s in scored]
            if reordered != bullets:
                setattr(updated, section, reordered)
                changes.append(f"Reordered {section} to surface higher-relevance bullets")
        return updated, changes

    def _trim_sections(self, profile: ProfileInput) -> Tuple[ProfileInput, List[str]]:
        """
        Trim lowest-signal bullets if overall length is high (helps conciseness/page limit).
        """
        changes: List[str] = []
        total_length = len(" ".join(profile.experience + profile.projects + profile.education))
        if total_length <= 2200:
            return profile, changes

        updated = deepcopy(profile)
        # drop last project first if needed
        if updated.projects:
            removed = updated.projects.pop()
            changes.append(f"Dropped low-priority project bullet: '{removed[:40]}...'")
        # if still long, drop last experience bullet
        total_length = len(" ".join(updated.experience + updated.projects + updated.education))
        if total_length > 2200 and updated.experience:
            removed = updated.experience.pop()
            changes.append(f"Dropped low-priority experience bullet: '{removed[:40]}...'")
        # education last
        total_length = len(" ".join(updated.experience + updated.projects + updated.education))
        if total_length > 2200 and updated.education:
            removed = updated.education.pop()
            changes.append(f"Trimmed education entry: '{removed[:40]}...'")
        return updated, changes

    def _is_missing(self, keyword: str, mapping: KeywordMapping) -> bool:
        return all(keyword != m.keyword for m in mapping.matched) and all(keyword != m.keyword for m in mapping.partial)
