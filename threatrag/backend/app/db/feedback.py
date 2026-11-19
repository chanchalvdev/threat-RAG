"""Persistence for analyst feedback. One row per (subject, target, target_id): re-voting replaces."""
from psycopg import AsyncConnection

from app.models.feedback_schemas import FeedbackRecord, FeedbackRequest, FeedbackSummary, TargetCounts

ANSWER_EXCERPT = 4000
_COLUMNS = "id::text, target, target_id, rating, note, question, created_at::text"


def _record(row: tuple) -> FeedbackRecord:
    return FeedbackRecord(id=row[0], target=row[1], target_id=row[2], rating=row[3], note=row[4],
                          question=row[5], created_at=row[6])


async def upsert(subject: str, fb: FeedbackRequest, conn: AsyncConnection) -> FeedbackRecord:
    cur = await conn.execute(
        f"""
        INSERT INTO feedback (subject, target, target_id, rating, note, question, answer)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (subject, target, target_id) DO UPDATE
            SET rating = EXCLUDED.rating, note = EXCLUDED.note, question = EXCLUDED.question,
                answer = EXCLUDED.answer, created_at = NOW()
        RETURNING {_COLUMNS}
        """,
        (subject, fb.target, fb.target_id, fb.rating, fb.note, fb.question, fb.answer[:ANSWER_EXCERPT]),
    )
    row = await cur.fetchone()
    assert row is not None  # RETURNING always yields the written row
    return _record(row)


async def summary(conn: AsyncConnection, recent: int = 10) -> FeedbackSummary:
    cur = await conn.execute("SELECT target, rating, count(*) FROM feedback GROUP BY target, rating")
    counts = {"answer": TargetCounts(), "report": TargetCounts()}
    for target, rating, n in await cur.fetchall():
        if rating > 0:
            counts[target].up = n
        else:
            counts[target].down = n
    cur = await conn.execute(
        f"SELECT {_COLUMNS} FROM feedback WHERE rating < 0 ORDER BY created_at DESC LIMIT %s", (recent,),
    )
    return FeedbackSummary(answer=counts["answer"], report=counts["report"],
                           recent_down=[_record(r) for r in await cur.fetchall()])


async def down_voted_answers(conn: AsyncConnection, limit: int = 500) -> list[tuple[str, str, str, str]]:
    """(id, question, answer, note) of down-voted chat answers, newest first, one per question."""
    cur = await conn.execute(
        """
        SELECT DISTINCT ON (lower(question)) id::text, question, answer, note
        FROM feedback WHERE target = 'answer' AND rating < 0 AND question <> ''
        ORDER BY lower(question), created_at DESC LIMIT %s
        """,
        (limit,),
    )
    return [(r[0], r[1], r[2], r[3]) for r in await cur.fetchall()]
