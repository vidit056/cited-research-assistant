from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class SubQuestionPlan(BaseModel):
    sub_questions: List[str] = Field(
        ...,
        description="3 to 5 targeted sub-questions decomposing the main research query."
    )

class CitationItem(BaseModel):
    source_id: str
    citation_num: int
    quote: str
    char_span: List[int] = Field(default_factory=list, description="Start and end character indices in raw_text [start, end]")
    status: str = Field(default="verified", description="'verified' or 'unverified'")

class RawCitationClaim(BaseModel):
    citation_num: int
    quote: str = Field(..., description="Exact quoted sentence or passage from the retrieved text that supports this claim.")

class ContradictionItem(BaseModel):
    claim_a: str = Field(..., description="Statement or claim from the first source.")
    source_a_num: int = Field(..., description="Citation index of the first source.")
    claim_b: str = Field(..., description="Contradicting statement or claim from the second source.")
    source_b_num: int = Field(..., description="Citation index of the second source.")
    explanation: str = Field(..., description="Concise explanation of the conflict/discrepancy.")

class VerificationOutput(BaseModel):
    claims_with_citations: List[RawCitationClaim] = Field(
        default_factory=list,
        description="List of factual claims with their cited source numbers and exact quotes."
    )
    contradictions: List[ContradictionItem] = Field(
        default_factory=list,
        description="Any conflicting facts, dates, numbers, or conclusions discovered across sources."
    )

class SourceItem(BaseModel):
    id: str
    citation_num: int
    title: str
    url: str
    domain: str
    published_date: Optional[str] = None
    raw_text: str

class ResearchRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000, description="The research question to investigate.")

class ResearchResponse(BaseModel):
    run_id: str
    question: str
    status: str
    report_md: str
    sub_questions: List[str] = Field(default_factory=list)
    sources: List[SourceItem] = Field(default_factory=list)
    citations: List[CitationItem] = Field(default_factory=list)
    contradictions: List[ContradictionItem] = Field(default_factory=list)
    created_at: str

class EvalScoreItem(BaseModel):
    id: str
    run_id: str
    faithfulness: float
    citation_acc: float
    retrieval_rel: float
    created_at: str
