from pydantic import BaseModel, Field


class StructuredIntake(BaseModel):
    chief_complaint: str
    hpi: dict = Field(default_factory=dict)
    relevant_negatives: list[str] = Field(default_factory=list)
    timeline: str = ""
    symptoms: list[str] = Field(default_factory=list)


class Citation(BaseModel):
    chunk_id: int
    source: str
    title: str
    excerpt: str


class DifferentialItem(BaseModel):
    name: str
    likelihood_bucket: str
    rationale: str
    citations: list[int] = Field(default_factory=list)
    no_evidence: bool = False


class RedFlagItem(BaseModel):
    flag: str
    why: str
    action: str
    citations: list[int] = Field(default_factory=list)
    no_evidence: bool = False


class FollowUpItem(BaseModel):
    question: str
    why: str
    citations: list[int] = Field(default_factory=list)
    no_evidence: bool = False


class TestItem(BaseModel):
    test: str
    why: str
    citations: list[int] = Field(default_factory=list)
    no_evidence: bool = False


class DecisionSupportOutput(BaseModel):
    differential: list[DifferentialItem]
    red_flags: list[RedFlagItem]
    followups: list[FollowUpItem]
    tests: list[TestItem]
    confidence: float = Field(ge=0, le=1)
    uncertainty_notes: str
    needs_human_review: bool = True
    citations: list[Citation]


class ExtractIntakeRequest(BaseModel):
    transcript: str = Field(min_length=5)
    specialty: str = "general"


class DecisionSupportRequest(BaseModel):
    transcript: str = Field(min_length=5)
    structured_intake: StructuredIntake
    specialty: str = "general"
    encounter_id: int | None = None


class TranscribeResponse(BaseModel):
    transcript: str
    mode: str
