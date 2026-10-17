"""Persistence for RAG evaluation scores (Analytics page)."""
from psycopg import AsyncConnection

from app.evaluation.ragas_eval import RagasScores


class EvaluationRecord(RagasScores):
    id: str
    question: str
    created_at: str


async def save_evaluation(question: str, answer: str, scores: RagasScores, conn: AsyncConnection) -> None:
    await conn.execute(
        """
        INSERT INTO evaluations (question, answer, faithfulness, answer_relevancy,
                                 context_precision, context_recall, overall)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            question, answer, scores.faithfulness, scores.answer_relevancy,
            scores.context_precision, scores.context_recall, scores.overall,
        ),
    )


async def list_evaluations(limit: int, conn: AsyncConnection) -> list[EvaluationRecord]:
    cur = await conn.execute(
        """
        SELECT id::text, question, faithfulness, answer_relevancy, context_precision,
               context_recall, overall, created_at::text
        FROM evaluations ORDER BY created_at DESC LIMIT %s
        """,
        (limit,),
    )
    rows = await cur.fetchall()
    return [
        EvaluationRecord(
            id=r[0], question=r[1], faithfulness=r[2], answer_relevancy=r[3],
            context_precision=r[4], context_recall=r[5], overall=r[6], created_at=r[7],
        )
        for r in reversed(rows)  # oldest → newest for charting
    ]
