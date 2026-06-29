import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile

from app.api.deps import get_store
from app.core.logging import get_logger
from app.models.schemas import IngestAccepted, IngestJob, IngestStats
from app.rag.embedder import get_embedder
from app.rag.ingestion import ingest_mitre_attack, ingest_owasp_llm, ingest_pdf
from app.rag.store import QdrantStore

log = get_logger(__name__)
router = APIRouter(prefix="/ingest", tags=["ingest"])

_jobs: dict[str, IngestJob] = {}
DATA_DIR = Path("data/sources")


async def _run_pdf(job_id: str, path: str, doc_type: str, store: QdrantStore) -> None:
    _jobs[job_id] = IngestJob(job_id=job_id, status="processing")
    try:
        embedder = get_embedder()
        count = await ingest_pdf(path, doc_type, store, embedder)
        _jobs[job_id] = IngestJob(job_id=job_id, status="completed", chunks_processed=count, total_chunks=count)
    except Exception as exc:
        log.error("ingest_failed", job_id=job_id, error=str(exc))
        _jobs[job_id] = IngestJob(job_id=job_id, status="failed", error=str(exc))


async def _run_mitre(job_id: str, store: QdrantStore) -> None:
    _jobs[job_id] = IngestJob(job_id=job_id, status="processing")
    try:
        embedder = get_embedder()
        path = str(DATA_DIR / "mitre_attack.json")
        count = await ingest_mitre_attack(path, store, embedder)
        _jobs[job_id] = IngestJob(job_id=job_id, status="completed", chunks_processed=count, total_chunks=count)
    except Exception as exc:
        _jobs[job_id] = IngestJob(job_id=job_id, status="failed", error=str(exc))


async def _run_owasp(job_id: str, store: QdrantStore) -> None:
    _jobs[job_id] = IngestJob(job_id=job_id, status="processing")
    try:
        embedder = get_embedder()
        count = await ingest_owasp_llm(store, embedder)
        _jobs[job_id] = IngestJob(job_id=job_id, status="completed", chunks_processed=count, total_chunks=count)
    except Exception as exc:
        _jobs[job_id] = IngestJob(job_id=job_id, status="failed", error=str(exc))


@router.post("/pdf", response_model=IngestAccepted, status_code=202)
async def ingest_pdf_route(
    bg: BackgroundTasks,
    file: UploadFile = File(...),
    doc_type: str = Form(default="custom"),
    store: QdrantStore = Depends(get_store),
) -> IngestAccepted:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    dest = DATA_DIR / (file.filename or "upload.pdf")
    dest.write_bytes(await file.read())
    job_id = str(uuid.uuid4())
    bg.add_task(_run_pdf, job_id, str(dest), doc_type, store)
    return IngestAccepted(job_id=job_id, filename=file.filename or "")


@router.post("/mitre", response_model=IngestAccepted, status_code=202)
async def ingest_mitre_route(bg: BackgroundTasks, store: QdrantStore = Depends(get_store)) -> IngestAccepted:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    job_id = str(uuid.uuid4())
    bg.add_task(_run_mitre, job_id, store)
    return IngestAccepted(job_id=job_id)


@router.post("/owasp", response_model=IngestAccepted, status_code=202)
async def ingest_owasp_route(bg: BackgroundTasks, store: QdrantStore = Depends(get_store)) -> IngestAccepted:
    job_id = str(uuid.uuid4())
    bg.add_task(_run_owasp, job_id, store)
    return IngestAccepted(job_id=job_id)


@router.get("/status/{job_id}", response_model=IngestJob)
async def get_status(job_id: str) -> IngestJob:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/stats", response_model=IngestStats)
async def get_stats(store: QdrantStore = Depends(get_store)) -> IngestStats:
    info = await store._client.get_collection(store.collection)
    return IngestStats(
        collection=store.collection,
        total_vectors=info.points_count or 0,
        doc_type_counts={},
    )
