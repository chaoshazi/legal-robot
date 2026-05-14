from pydantic import BaseModel, Field


class CreateEvaluationRequest(BaseModel):
    score_name: str = Field(default="answer_quality", description="评分维度")
    score_value: float = Field(ge=0, le=10, description="评分值（0-10）")
    score_comment: str | None = None


class EvaluationInfo(BaseModel):
    id: int
    consultation_id: str
    trace_id: str
    score_name: str
    score_value: float
    data_type: str
    comment: str | None
    evaluated_by: str | None
    created_at: str


class EvaluationListData(BaseModel):
    items: list[EvaluationInfo]
    total: int
    page: int
    page_size: int
