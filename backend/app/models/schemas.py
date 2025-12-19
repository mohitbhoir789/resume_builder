from typing import List, Optional

from pydantic import BaseModel, Field


class JobInput(BaseModel):
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    description: str = Field(..., description="Full JD text including responsibilities/skills/education")


class ProfileInput(BaseModel):
    experience: List[str] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    education: List[str] = Field(default_factory=list)


class KeywordBuckets(BaseModel):
    skills: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    education: List[str] = Field(default_factory=list)
    action_verbs: List[str] = Field(default_factory=list)


class RankedKeyword(BaseModel):
    keyword: str
    category: str
    weight: float


class KeywordExtractionResult(BaseModel):
    keywords: KeywordBuckets
    ranked_keywords: List[RankedKeyword]


class MappingEntry(BaseModel):
    keyword: str
    evidence: Optional[str] = None
    similarity: Optional[float] = None


class KeywordMapping(BaseModel):
    matched: List[MappingEntry] = Field(default_factory=list)
    partial: List[MappingEntry] = Field(default_factory=list)
    missing: List[MappingEntry] = Field(default_factory=list)


class ATSBreakdown(BaseModel):
    keyword_coverage: float
    role_relevance: float
    seniority: float
    conciseness: float
    education: float


class ATSScore(BaseModel):
    score: float
    breakdown: ATSBreakdown
    explanations: List[str]


class OptimizerIteration(BaseModel):
    iteration: int
    changes: List[str]
    score_before: float
    score_after: float


class OptimizerResult(BaseModel):
    optimized_resume: ProfileInput
    iterations: List[OptimizerIteration]
    final_score: float
    final_score_detail: ATSScore
    final_mapping: KeywordMapping


class AssemblerBudgets(BaseModel):
    total_lines: int
    experience_lines: int
    project_lines: int
    skills_lines: int
    education_lines: int
    limit: int = 55


class AssemblerResult(BaseModel):
    latex_source: str
    section_budgets: AssemblerBudgets
    trims_applied: List[str]


class RenderAttempt(BaseModel):
    attempt: int
    page_count: int
    trims: List[str]
    log_excerpt: str


class RendererResult(BaseModel):
    pdf_path: str
    page_count: int
    render_attempts: List[RenderAttempt]
    final_trims: List[str]
    error: Optional[str] = None


class AuditPayload(BaseModel):
    run_id: str
    job: JobInput
    profile: ProfileInput
    extraction: Optional[KeywordExtractionResult] = None
    mapping: Optional[KeywordMapping] = None
    score_detail: Optional[ATSScore] = None
    optimizer: Optional[OptimizerResult] = None
    assembler: Optional[AssemblerResult] = None
    renderer: Optional[RendererResult] = None
    final_score: Optional[float] = None
    mapping_provider: Optional[str] = None
    mapping_fallback: Optional[bool] = None
    llm_provider: Optional[str] = None
    llm_fallback: Optional[bool] = None
    llm_latency_ms: Optional[int] = None
    llm_fallback_reason: Optional[str] = None


class IngestResponse(BaseModel):
    status: str
    chunks_created: int
    sections: List[str]
    embedding_provider: str
    ingest_type: str | None = None
    pages_parsed: int | None = None
    profile: Optional[ProfileInput] = None


class ResumeRequest(BaseModel):
    job: JobInput
    profile: Optional[ProfileInput] = None
    profile_name: Optional[str] = None
    run_id: Optional[str] = Field(None, description="Optional idempotency token")


class ResumeContent(BaseModel):
    latex_body: str
    page_count: int
    ats_score: float
    keywords: List[str]
    gaps: List[str] = Field(default_factory=list)
    pdf_path: Optional[str] = None
    audit_path: Optional[str] = None
    extraction: Optional[KeywordExtractionResult] = None
    mapping: Optional[KeywordMapping] = None
    score_detail: Optional[ATSScore] = None
    optimizer: Optional[OptimizerResult] = None
    assembler: Optional[AssemblerResult] = None
    renderer: Optional[RendererResult] = None


class ResumeResponse(BaseModel):
    run_id: str
    status: str
    ats_score: float
    pdf_url: str
    page_count: Optional[int] = None
    render_attempts: Optional[int] = None
    audit_url: Optional[str] = None
    keywords: List[str]
    gaps: List[str]
    notes: Optional[str] = None
    extraction: Optional[KeywordExtractionResult] = None
    mapping: Optional[KeywordMapping] = None
    score_detail: Optional[ATSScore] = None
    optimizer: Optional[OptimizerResult] = None
    assembler: Optional[AssemblerResult] = None
    renderer: Optional[RendererResult] = None


class ScoreResponse(BaseModel):
    ats_score: float
    keywords: List[str]
    gaps: List[str]
    extraction: Optional[KeywordExtractionResult] = None
    mapping: Optional[KeywordMapping] = None
    score_detail: Optional[ATSScore] = None
    optimizer: Optional[OptimizerResult] = None
    assembler: Optional[AssemblerResult] = None
    renderer: Optional[RendererResult] = None


class WorkflowStatus(BaseModel):
    run_id: str
    status: str
    ats_score: Optional[float] = None
    message: Optional[str] = None
