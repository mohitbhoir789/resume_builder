from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import List, Tuple

from app.models.schemas import AssemblerResult, ProfileInput, RenderAttempt, RendererResult
from app.services.assembler import Assembler
from app.utils.text import normalize_text


class Renderer:
    """
    PDF renderer with hard 1-page guardrail using pdflatex + pdfinfo.
    Applies stricter trimming retries if overflow detected.
    """

    def __init__(self, assembler: Assembler, max_attempts: int = 3) -> None:
        self.assembler = assembler
        self.max_attempts = max_attempts

    def render(self, profile: ProfileInput, assembler_result: AssemblerResult) -> RendererResult:
        render_attempts: List[RenderAttempt] = []
        current_profile = deepcopy(profile)
        trims = list(assembler_result.trims_applied)

        for attempt in range(1, self.max_attempts + 1):
            if attempt == 1:
                latex_source = assembler_result.latex_source
            else:
                new_asm = self.assembler.assemble(current_profile)
                latex_source = new_asm.latex_source
                trims.extend(new_asm.trims_applied)

            pdf_path, log_output = self._run_pdflatex(latex_source)
            page_count = self._get_page_count(pdf_path, log_output)
            render_attempts.append(
                RenderAttempt(
                    attempt=attempt,
                    page_count=page_count,
                    trims=list(trims),
                    log_excerpt=log_output[:500],
                )
            )
            if page_count == 1:
                return RendererResult(
                    pdf_path=str(pdf_path),
                    page_count=1,
                    render_attempts=render_attempts,
                    final_trims=trims,
                )

            # apply stricter trims
            current_profile, new_trims = self._tighten_for_overflow(current_profile)
            trims.extend(new_trims)

        return RendererResult(
            pdf_path="",
            page_count=render_attempts[-1].page_count if render_attempts else 0,
            render_attempts=render_attempts,
            final_trims=trims,
            error="Unable to enforce 1-page limit after retries. Consider removing low-priority bullets or shortening content.",
        )

    def _run_pdflatex(self, latex_source: str) -> Tuple[Path, str]:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            tex_file = tmp_path / "main.tex"
            tex_file.write_text(latex_source, encoding="utf-8")

            cmd = [
                "pdflatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                "-output-directory",
                str(tmp_path),
                str(tex_file),
            ]
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
                text=True,
            )
            log_output = proc.stdout
            pdf_file = tmp_path / "main.pdf"
            # copy pdf to workspace if produced
            dest = Path.cwd() / "artifacts"
            dest.mkdir(exist_ok=True)
            final_pdf = dest / f"resume_{os.getpid()}.pdf"
            if pdf_file.exists():
                shutil.copy(pdf_file, final_pdf)
            return final_pdf, log_output

    def _get_page_count(self, pdf_path: Path, log_output: str) -> int:
        if not pdf_path.exists():
            return 0
        try:
            proc = subprocess.run(
                ["pdfinfo", str(pdf_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            match = re.search(r"Pages:\s+(\d+)", proc.stdout)
            if match:
                return int(match.group(1))
        except FileNotFoundError:
            pass
        # fallback to pdflatex log
        match = re.search(r"Output written on .*\((\d+) page", log_output)
        if match:
            return int(match.group(1))
        return 0

    def _tighten_for_overflow(self, profile: ProfileInput) -> Tuple[ProfileInput, List[str]]:
        updated = deepcopy(profile)
        changes: List[str] = []

        # 1) Reduce bullets per experience/project
        if len(updated.experience) > 3:
            removed = updated.experience.pop()
            changes.append(f"Overflow trim: removed experience bullet '{removed[:50]}...'")
        if len(updated.projects) > 2:
            removed = updated.projects.pop()
            changes.append(f"Overflow trim: removed project bullet '{removed[:50]}...'")

        # 2) Drop lowest-priority project
        if not changes and updated.projects:
            removed = updated.projects.pop()
            changes.append(f"Overflow trim: dropped project '{removed[:50]}...'")

        # 3) Collapse older experience
        if not changes and len(updated.experience) > 2:
            removed = updated.experience.pop()
            changes.append(f"Overflow trim: collapsed older experience '{removed[:50]}...'")

        # 4) Remove education details (keep degree name only)
        if not changes and updated.education:
            collapsed = []
            for edu in updated.education:
                collapsed.append(edu.split(",")[0].strip())
            if collapsed != updated.education:
                changes.append("Overflow trim: reduced education detail to degree name")
            updated.education = collapsed

        if not changes:
            changes.append("Overflow trim: no-op (no more content to drop)")
        return updated, changes
