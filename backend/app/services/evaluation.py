"""Evaluation service — persists scores locally and pushes to LangFuse."""

import uuid

from app.core.database import async_session
from app.core.langfuse import create_score
from app.models.evaluation import Evaluation


async def create_evaluation(
    consultation_id: uuid.UUID,
    trace_id: str,
    score_name: str = "answer_quality",
    score_value: float = 0,
    evaluated_by: uuid.UUID | None = None,
    comment: str | None = None,
) -> Evaluation:
    """Persist evaluation locally and push to LangFuse."""
    async with async_session() as db:
        evaluation = Evaluation(
            consultation_id=consultation_id,
            trace_id=trace_id,
            score_name=score_name,
            score_value=score_value,
            data_type="NUMERIC",
            evaluated_by=evaluated_by,
            comment=comment,
        )
        db.add(evaluation)
        await db.commit()
        await db.refresh(evaluation)

    await create_score(
        trace_id=trace_id,
        name=score_name,
        value=score_value,
        data_type="NUMERIC",
        comment=comment,
    )

    return evaluation
