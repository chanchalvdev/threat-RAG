import re
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile

from app.api.deps import get_store
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import IngestAccepted, IngestJob, IngestStats
from app.rag.embedder import get_embedder
from app.rag.ingest_mitre import ingest_mitre_attack
from app.rag.ingest_owasp import ingest_owasp_llm
from app.rag.ingestion import ingest_pdf
from app.rag.store import QdrantStore

log = get_logger(__name__)
router = APIRouter(prefix="/ingest", tags=["ingest"])

_jobs: dict[str, IngestJob] = {}
DATA_DIR = Path("data/sources")
_DOC_TYPE_RE = re.compile(r"^[a-z0-9_]{1,32}$")
_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")


def _safe_pdf_name(filename: str | None) -> str:
    """Basename only, no traversal, restricted charset, must end in .pdf."""
    name = _UNSAFE_CHARS.sub("_", Path(filename or "upload.pdf").name).lstrip(".") or "upload.pdf"
    if not name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only .pdf files are accepted")
    return name


async def _run(job_id: str, work: Callable[[], Awaitable[int]]) -> None:
    _jobs[job_id] = IngestJob(job_id=job_id, status="processing")
    try:
        count = await work()
        _jobs[job_id] = IngestJob(job_id=job_id, status="completed", chunks_processed=count, total_chunks=count)
    except Exception as exc:
        log.error("ingest_failed", job_id=job_id, error=str(exc))
        _jobs[job_id] = IngestJob(job_id=job_id, status="failed", error=str(exc))


def _start(bg: BackgroundTasks, work: Callable[[], Awaitable[int]]) -> str:
    job_id = str(uuid.uuid4())
    _jobs[job_id] = IngestJob(job_id=job_id, status="pending")  # visible to /status before the task starts
    bg.add_task(_run, job_id, work)
    return job_id


@router.post(
    "/pdf",
    response_model=IngestAccepted,
    status_code=202,
    summary="Ingest a custom PDF document",
    description="Uploads a PDF (multipart/form-data), chunks and embeds it in the background, "
    "and returns a job_id to poll via GET /ingest/status/{job_id}.",
)
async def ingest_pdf_route(
    bg: BackgroundTasks,
    file: UploadFile = File(..., description="PDF file to ingest"),
    doc_type: str = Form(default="custom", description="Label stored alongside each chunk, e.g. 'custom', 'threat_report'"),
    store: QdrantStore = Depends(get_store),
) -> IngestAccepted:
    if not _DOC_TYPE_RE.match(doc_type):
        raise HTTPException(status_code=400, detail="doc_type must match ^[a-z0-9_]{1,32}$")
    name = _safe_pdf_name(file.filename)
    max_bytes = get_settings().max_upload_mb * 1024 * 1024
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds {get_settings().max_upload_mb} MB")
    if not data.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="File is not a valid PDF")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    dest = DATA_DIR / name
    dest.write_bytes(data)
    job_id = _start(bg, lambda: ingest_pdf(str(dest), doc_type, store, get_embedder()))
    return IngestAccepted(job_id=job_id, filename=name)


@router.post(
    "/mitre",
    response_model=IngestAccepted,
    status_code=202,
    summary="Ingest MITRE ATT&CK Enterprise",
    description="Downloads the STIX bundle if it is not cached, then indexes every live technique with its "
    "mitigations, detections and known users in the background.",
)
async def ingest_mitre_route(bg: BackgroundTasks, store: QdrantStore = Depends(get_store)) -> IngestAccepted:
    path = str(DATA_DIR / "mitre_attack.json")
    return IngestAccepted(job_id=_start(bg, lambda: ingest_mitre_attack(path, store, get_embedder())))


@router.post(
    "/owasp",
    response_model=IngestAccepted,
    status_code=202,
    summary="Ingest the OWASP Top 10 for LLM Applications (2025)",
    description="Fetches the ten risk pages from the OWASP project repository and indexes them in the background.",
)
async def ingest_owasp_route(bg: BackgroundTasks, store: QdrantStore = Depends(get_store)) -> IngestAccepted:
    return IngestAccepted(job_id=_start(bg, lambda: ingest_owasp_llm(store, get_embedder())))


@router.get(
    "/status/{job_id}",
    response_model=IngestJob,
    summary="Poll an ingestion job's status",
    responses={404: {"description": "Job not found", "content": {"application/json": {"example": {"detail": "Job not found"}}}}},
)
async def get_status(job_id: str) -> IngestJob:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get(
    "/stats",
    response_model=IngestStats,
    summary="Get vector store statistics",
    description="Returns the total vector count and per-document-type breakdown in the collection.",
)
async def get_stats(store: QdrantStore = Depends(get_store)) -> IngestStats:
    try:
        counts = await store.count_by_doc_type()
    except Exception as exc:  # facet unsupported on old Qdrant servers
        log.warning("facet_failed", error=str(exc))
        counts = {}
    return IngestStats(collection=store.collection, total_vectors=await store.total(), doc_type_counts=counts)
