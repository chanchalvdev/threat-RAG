from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from app.api.routes.investigate import get_report
from app.core.logging import get_logger
from app.services import notify
from app.services.pdf_export import build_pdf, serial

log = get_logger(__name__)
router = APIRouter(prefix="/investigate", tags=["investigate"])


class ExportOptions(BaseModel):
    pdf: bool = True
    slack: bool
    teams: bool


class NotifyRequest(BaseModel):
    channel: notify.Channel


@router.get("/exports", response_model=ExportOptions, summary="Which report exports and channels are configured")
async def exports() -> ExportOptions:
    return ExportOptions(slack=bool(notify.configured("slack")), teams=bool(notify.configured("teams")))


@router.get(
    "/reports/{report_id}/pdf",
    summary="Export a saved report as a PDF",
    responses={200: {"content": {"application/pdf": {}}}, 404: {"description": "Report not found"}},
)
async def export_pdf(report_id: str) -> Response:
    report = await get_report(report_id)
    name = f"threatrag-{serial(report_id)}.pdf"
    return Response(build_pdf(report), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.post(
    "/reports/{report_id}/notify",
    summary="Post a saved report's summary to Slack or Teams",
    description="Sends the IOC, its type and the executive summary to the configured webhook. "
    "409 when that channel is not configured; 502 when the webhook rejects the message.",
)
async def notify_channel(report_id: str, req: NotifyRequest) -> dict[str, str]:
    report = await get_report(report_id)
    try:
        await notify.send(report, req.channel)
    except notify.ChannelNotConfigured as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        log.warning("notify_failed", channel=req.channel, error=type(exc).__name__)
        raise HTTPException(status_code=502, detail=f"{req.channel} webhook did not accept the message") from exc
    return {"sent": req.channel}
