"""Real Postgres: migration 003, a re-vote replacing the first, and a send-back report's lineage."""
import uuid

import pytest

from app.agent.investigation_models import InvestigationReport
from app.db import feedback as fb_repo
from app.db import reports as repo
from app.models.feedback_schemas import FeedbackRequest
from tests.integration.test_reports_db import _vector, conn  # noqa: F401  (fixture)

pytestmark = pytest.mark.integration


async def test_second_vote_replaces_the_first_and_counts_follow(conn):  # noqa: F811
    target = f"it-{uuid.uuid4().hex[:8]}:1"
    before = await fb_repo.summary(conn)
    await fb_repo.upsert("alice", FeedbackRequest(target="answer", target_id=target, rating=1), conn)
    second = await fb_repo.upsert("alice", FeedbackRequest(target="answer", target_id=target, rating=-1,
                                                             note="wrong", question="What is T1110?"), conn)
    await fb_repo.upsert("bob", FeedbackRequest(target="answer", target_id=target, rating=-1), conn)
    after = await fb_repo.summary(conn)
    assert second.rating == -1 and second.note == "wrong"
    assert after.answer.up == before.answer.up and after.answer.down == before.answer.down + 2
    assert any(q == "What is T1110?" for _, q, _, _ in await fb_repo.down_voted_answers(conn))


async def test_send_back_report_links_to_its_parent(conn):  # noqa: F811
    parent_id = await repo.save_report(InvestigationReport(ioc="CVE-2021-44228", ioc_type="cve", final_report="v1"),
                                       _vector(1), conn)
    child = InvestigationReport(ioc="CVE-2021-44228", ioc_type="cve", final_report="v2",
                                parent_id=parent_id, analyst_gaps="no EPSS score")
    loaded = await repo.get_report(await repo.save_report(child, _vector(2), conn), conn)
    assert loaded is not None and (loaded.parent_id, loaded.analyst_gaps) == (parent_id, "no EPSS score")
