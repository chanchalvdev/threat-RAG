"""Unit tests for ingestion pipeline."""
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from qdrant_client.models import PointStruct

from app.rag.ingestion import ingest_mitre_attack, ingest_pdf


MOCK_STIX = {
    "objects": [
        {
            "type": "attack-pattern",
            "name": "Password Guessing",
            "description": "Adversaries may attempt to guess passwords.",
            "external_references": [
                {"source_name": "mitre-attack", "external_id": "T1110.001"}
            ],
            "kill_chain_phases": [{"phase_name": "credential-access"}],
            "x_mitre_platforms": ["Windows", "Linux"],
        },
        {
            "type": "attack-pattern",
            "name": "Process Injection",
            "description": "Adversaries may inject code into processes.",
            "external_references": [
                {"source_name": "mitre-attack", "external_id": "T1055"}
            ],
            "kill_chain_phases": [{"phase_name": "defense-evasion"}],
            "x_mitre_platforms": ["Windows"],
        },
        {
            "type": "identity",  # non-attack-pattern — should be skipped
            "name": "MITRE",
        },
    ]
}


@pytest.mark.asyncio
async def test_ingest_mitre_attack_chunks(mock_store, mock_embedder, tmp_path):
    stix_file = tmp_path / "mitre_attack.json"
    stix_file.write_text(json.dumps(MOCK_STIX))

    count = await ingest_mitre_attack(str(stix_file), mock_store, mock_embedder)

    assert count == 2
    assert mock_embedder.embed.call_count == 2
    assert mock_store.upsert.call_count >= 1


@pytest.mark.asyncio
async def test_ingest_mitre_attack_payload_fields(mock_store, mock_embedder, tmp_path):
    stix_file = tmp_path / "mitre_attack.json"
    stix_file.write_text(json.dumps(MOCK_STIX))

    upserted_points: list[PointStruct] = []

    async def capture_upsert(points):
        upserted_points.extend(points)

    mock_store.upsert.side_effect = capture_upsert

    await ingest_mitre_attack(str(stix_file), mock_store, mock_embedder)

    assert len(upserted_points) == 2
    p = upserted_points[0]
    assert "technique_id" in p.payload
    assert "tactic" in p.payload
    assert p.payload["doc_type"] == "mitre_attack"
    assert p.payload["technique_id"] == "T1110.001"


@pytest.mark.asyncio
async def test_ingest_mitre_batch_size(mock_store, mock_embedder, tmp_path):
    many_techniques = [
        {
            "type": "attack-pattern",
            "name": f"Technique {i}",
            "description": "Description",
            "external_references": [{"source_name": "mitre-attack", "external_id": f"T{i:04d}"}],
            "kill_chain_phases": [],
            "x_mitre_platforms": [],
        }
        for i in range(150)
    ]
    stix_file = tmp_path / "big.json"
    stix_file.write_text(json.dumps({"objects": many_techniques}))

    await ingest_mitre_attack(str(stix_file), mock_store, mock_embedder)
    assert mock_store.upsert.call_count == 2


@pytest.mark.asyncio
async def test_ingest_pdf_basic(mock_store, mock_embedder, tmp_path):
    pdf_path = tmp_path / "test.pdf"
    fake_doc = MagicMock()
    fake_doc.page_content = "This is a security document about threats."
    fake_doc.metadata = {"page": 0}

    with patch("app.rag.ingestion.PyPDFLoader") as mock_loader, \
         patch("app.rag.ingestion._splitter") as mock_splitter:
        mock_loader.return_value.load.return_value = [fake_doc]
        splitter_instance = MagicMock()
        splitter_instance.split_documents.return_value = [fake_doc, fake_doc]
        mock_splitter.return_value = splitter_instance

        count = await ingest_pdf(str(pdf_path), "custom", mock_store, mock_embedder)

    assert count == 2
    assert mock_embedder.embed.call_count == 2


@pytest.mark.asyncio
async def test_ingest_pdf_payload_fields(mock_store, mock_embedder, tmp_path):
    pdf_path = tmp_path / "test.pdf"
    fake_doc = MagicMock()
    fake_doc.page_content = "Sample text content."
    fake_doc.metadata = {"page": 1}

    captured: list[PointStruct] = []

    async def cap(pts):
        captured.extend(pts)

    mock_store.upsert.side_effect = cap

    with patch("app.rag.ingestion.PyPDFLoader") as ml, patch("app.rag.ingestion._splitter") as ms:
        ml.return_value.load.return_value = [fake_doc]
        s = MagicMock()
        s.split_documents.return_value = [fake_doc]
        ms.return_value = s

        await ingest_pdf(str(pdf_path), "owasp_llm", mock_store, mock_embedder)

    assert len(captured) == 1
    p = captured[0]
    for field in ("text", "source", "doc_type", "chunk_index"):
        assert field in p.payload
    assert p.payload["doc_type"] == "owasp_llm"
