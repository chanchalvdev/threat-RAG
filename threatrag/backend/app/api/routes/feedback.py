from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse

from app.api.identity import Identity, current_identity
from app.db import feedback as repo
from app.db.connection import get_pool, is_db_ready
from app.models.feedback_schemas import FeedbackRecord, FeedbackRequest, FeedbackSummary
from app.services.feedback_service import candidates_jsonl

router = APIRouter(prefix="/feedback", tags=["feedback"])


def _require_db() -> None:
    if not is_db_ready():
        raise HTTPException(status_code=503, detail="Feedback storage unavailable (PostgreSQL not connected)")


@router.post(
    "",
    response_model=FeedbackRecord,
    summary="Rate a chat answer or an investigation report",
    description="One vote per analyst and target: voting again replaces the earlier vote and note.",
)
async def submit(fb: FeedbackRequest, identity: Identity = Depends(current_identity)) -> FeedbackRecord:
    _require_db()
    async with get_pool().connection() as conn:
        return await repo.upsert(identity.sub, fb, conn)


@router.get("/summary", response_model=FeedbackSummary, summary="Vote counts and the latest down-votes")
async def summary() -> FeedbackSummary:
    if not is_db_ready():
        return FeedbackSummary()
    async with get_pool().connection() as conn:
        return await repo.summary(conn)


@router.get(
    "/candidates",
    response_class=PlainTextResponse,
    summary="Down-voted answers as golden-set drafts (JSONL)",
    description="One line per down-voted question, in the shape of eval/golden.jsonl with a `review` "
    "field. A person must check the expectations before adding a line to the golden set.",
)
async def candidates() -> PlainTextResponse:
    _require_db()
    return PlainTextResponse(await candidates_jsonl(), media_type="application/x-ndjson",
                             headers={"Content-Disposition": 'attachment; filename="golden-candidates.jsonl"'})
