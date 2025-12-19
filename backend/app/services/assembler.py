from __future__ import annotations

from copy import deepcopy
from typing import Dict, List

from app.models.schemas import AssemblerBudgets, AssemblerResult, ProfileInput
from app.utils.text import escape_latex, normalize_text


class Assembler:
    """
    Deterministic LaTeX assembler.
    - Applies line budgeting
    - Trims/prioritizes content before rendering
    - Uses fixed macros (template assumed immutable)
    """

    def __init__(self, line_limit: int = 55) -> None:
        self.line_limit = line_limit

    def assemble(self, profile: ProfileInput) -> AssemblerResult:
        working = deepcopy(profile)
        trims: List[str] = []

        budgets = self._estimate_budgets(working)
        if budgets.total_lines > self.line_limit:
            working, budget_updates, trim_changes = self._trim_to_fit(working, budgets)
            trims.extend(trim_changes)
            budgets = budget_updates

        latex = self._build_latex_source(working)
        return AssemblerResult(latex_source=latex, section_budgets=budgets, trims_applied=trims)

    def _estimate_budgets(self, profile: ProfileInput) -> AssemblerBudgets:
        def lines_for_bullets(bullets: List[str], cap: int) -> int:
            total = 0
            for b in bullets[:cap]:
                length = len(b)
                if length <= 90:
                    total += 1
                elif length <= 170:
                    total += 2
                else:
                    total += 3
            return total

        exp_lines = lines_for_bullets(profile.experience, cap=8)
        proj_lines = lines_for_bullets(profile.projects, cap=6)
        skills_lines = max(1, (len(" ".join(profile.skills)) // 70) + 1) if profile.skills else 1
        edu_lines = max(1, len(profile.education))

        total = exp_lines + proj_lines + skills_lines + edu_lines
        return AssemblerBudgets(
            total_lines=total,
            experience_lines=exp_lines,
            project_lines=proj_lines,
            skills_lines=skills_lines,
            education_lines=edu_lines,
            limit=self.line_limit,
        )

    def _trim_to_fit(
        self, profile: ProfileInput, budgets: AssemblerBudgets
    ) -> (ProfileInput, AssemblerBudgets, List[str]):
        updated = deepcopy(profile)
        trims: List[str] = []

        def shorten_bullets(bullets: List[str], cap: int) -> List[str]:
            tightened = []
            for b in bullets[:cap]:
                tightened.append(self._tighten_text(b))
            return tightened

        updated.experience = shorten_bullets(updated.experience, 8)
        updated.projects = shorten_bullets(updated.projects, 6)

        budgets = self._estimate_budgets(updated)
        if budgets.total_lines <= self.line_limit:
            return updated, budgets, trims

        # Drop lowest-signal project bullet first
        if updated.projects:
            removed = updated.projects.pop()
            trims.append(f"Dropped project bullet: '{removed[:50]}...'")
        budgets = self._estimate_budgets(updated)
        if budgets.total_lines <= self.line_limit:
            return updated, budgets, trims

        # Drop lowest-signal experience bullet
        if updated.experience:
            removed = updated.experience.pop()
            trims.append(f"Dropped experience bullet: '{removed[:50]}...'")
        budgets = self._estimate_budgets(updated)
        if budgets.total_lines <= self.line_limit:
            return updated, budgets, trims

        # Collapse education entries if needed
        if len(updated.education) > 1:
            removed = updated.education.pop()
            trims.append(f"Trimmed education entry: '{removed[:50]}...'")
        budgets = self._estimate_budgets(updated)
        return updated, budgets, trims

    def _tighten_text(self, text: str) -> str:
        lowered = normalize_text(text)
        tokens = lowered.split()
        if len(tokens) > 28:
            tokens = tokens[:28]
        tightened = " ".join(tokens)
        if tightened and tightened[0].islower():
            tightened = tightened.capitalize()
        return tightened

    def _build_latex_source(self, profile: ProfileInput) -> str:
        parts: List[str] = []
        parts.append("% Auto-generated resume body")
        parts.append("\\section{Experience}")
        parts.append("\\begin{itemize}")
        for bullet in profile.experience[:8]:
            parts.append(f"  \\resumeItem{{{escape_latex(bullet)}}}")
        parts.append("\\end{itemize}")

        parts.append("\\section{Projects}")
        parts.append("\\begin{itemize}")
        for bullet in profile.projects[:6]:
            parts.append(f"  \\resumeItem{{{escape_latex(bullet)}}}")
        parts.append("\\end{itemize}")

        parts.append("\\section{Skills}")
        skill_lines = self._chunk_skills(profile.skills, max_chars=70, max_lines=2)
        for line in skill_lines:
            parts.append(f"\\resumeSubheading{{{escape_latex(line)}}}{{}}")

        parts.append("\\section{Education}")
        for edu in profile.education[:3]:
            parts.append(f"\\resumeSubheading{{{escape_latex(edu)}}}{{}}")

        return "\n".join(parts)

    def _chunk_skills(self, skills: List[str], max_chars: int, max_lines: int) -> List[str]:
        lines: List[str] = []
        current = ""
        for skill in skills:
            candidate = skill if not current else f"{current}, {skill}"
            if len(candidate) <= max_chars:
                current = candidate
            else:
                lines.append(current)
                current = skill
            if len(lines) >= max_lines:
                break
        if current and len(lines) < max_lines:
            lines.append(current)
        return lines or [""]
