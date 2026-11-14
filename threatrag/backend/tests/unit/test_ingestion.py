"""Ingestion: MITRE parsing and chunking, OWASP Markdown chunking, PDF, and the shared indexer."""
import json
from unittest.mock import MagicMock, patch

from app.rag.ingest_mitre import ingest_mitre_attack, technique_chunks
from app.rag.ingest_owasp import owasp_chunks
from app.rag.ingestion import Chunk, index_chunks, ingest_pdf, point_id
from app.rag.mitre_parser import parse_techniques

AP, COA, GROUP, DET = "attack-pattern--1", "course-of-action--1", "intrusion-set--1", "x-mitre-detection-strategy--1"
STIX = {"objects": [
    {"type": "attack-pattern", "id": AP, "name": "Password Guessing",
     "description": "Adversaries may guess passwords.(Citation: Foo 2020) See [T1110](https://attack.mitre.org/T1110).",
     "external_references": [{"source_name": "mitre-attack", "external_id": "T1110.001"}],
     "kill_chain_phases": [{"phase_name": "credential-access"}], "x_mitre_platforms": ["Windows", "Linux"]},
    {"type": "attack-pattern", "id": "attack-pattern--2", "name": "Old Technique", "revoked": True,
     "external_references": [{"source_name": "mitre-attack", "external_id": "T9999"}]},
    {"type": "attack-pattern", "id": "attack-pattern--3", "name": "Deprecated", "x_mitre_deprecated": True,
     "external_references": [{"source_name": "mitre-attack", "external_id": "T9998"}]},
    {"type": "course-of-action", "id": COA, "name": "Multi-factor Authentication",
     "external_references": [{"source_name": "mitre-attack", "external_id": "M1032"}]},
    {"type": "intrusion-set", "id": GROUP, "name": "APT28"},
    {"type": "malware", "id": "malware--1", "name": "Mimikatz"},
    {"type": "x-mitre-detection-strategy", "id": DET, "name": "Detect guessing", "x_mitre_analytic_refs": ["x-mitre-analytic--1"]},
    {"type": "x-mitre-analytic", "id": "x-mitre-analytic--1", "description": "Many failed logons.", "x_mitre_platforms": ["Windows"]},
    {"type": "relationship", "relationship_type": "mitigates", "source_ref": COA, "target_ref": AP, "description": "Use MFA."},
    {"type": "relationship", "relationship_type": "uses", "source_ref": GROUP, "target_ref": AP},
    {"type": "relationship", "relationship_type": "uses", "source_ref": "malware--1", "target_ref": AP},
    {"type": "relationship", "relationship_type": "detects", "source_ref": DET, "target_ref": AP},
    {"type": "relationship", "relationship_type": "uses", "source_ref": GROUP, "target_ref": "malware--1"},
    {"type": "campaign", "id": "campaign--1", "name": "SolarWinds Compromise",
     "external_references": [{"source_name": "mitre-attack", "external_id": "C0024"}]},
    {"type": "intrusion-set", "id": "intrusion-set--2", "name": "APT29"},
    {"type": "relationship", "relationship_type": "uses", "source_ref": "campaign--1", "target_ref": AP},
    {"type": "relationship", "relationship_type": "attributed-to", "source_ref": "campaign--1", "target_ref": "intrusion-set--2"},
    {"type": "identity", "id": "identity--1", "name": "MITRE"},
]}


def test_parser_skips_retired_techniques_and_joins_related_objects():
    (t,) = parse_techniques(STIX)
    assert (t.technique_id, t.tactics, t.platforms) == ("T1110.001", ["credential-access"], ["Windows", "Linux"])
    assert t.mitigations == ["M1032 Multi-factor Authentication: Use MFA."]
    assert t.detections == ["[Windows] Many failed logons."]
    assert (t.groups, t.software) == (["APT28"], ["Mimikatz"])
    assert t.campaigns == ["C0024 SolarWinds Compromise (attributed to APT29)"]


def test_technique_chunks_repeat_the_header_and_strip_citation_noise():
    chunks = technique_chunks(parse_techniques(STIX)[0])
    assert [c.payload["section"] for c in chunks] == ["description", "mitigations", "detection", "usage"]
    assert all("ID: T1110.001" in c.text and c.payload["technique_id"] == "T1110.001" for c in chunks)
    assert "Citation" not in chunks[0].text and "https://" not in chunks[0].text and "See T1110." in chunks[0].text
    assert "APT28" in chunks[3].text and "Mimikatz" in chunks[3].text and "attributed to APT29" in chunks[3].text
    assert len({c.key for c in chunks}) == len(chunks)


def test_long_descriptions_are_split_not_truncated():
    stix = {"objects": [{**STIX["objects"][0], "description": "Sentence about credential access. " * 150}]}
    chunks = technique_chunks(parse_techniques(stix)[0])
    assert len(chunks) > 3 and sum(len(c.text) for c in chunks) > 4000


async def test_ingest_mitre_is_idempotent_and_writes_both_vectors(mock_store, mock_embedder, tmp_path):
    path = tmp_path / "mitre.json"
    path.write_text(json.dumps(STIX))
    assert await ingest_mitre_attack(str(path), mock_store, mock_embedder) == 4
    await ingest_mitre_attack(str(path), mock_store, mock_embedder)
    first, second = (call.args[0] for call in mock_store.upsert.call_args_list)
    assert [p.id for p in first] == [p.id for p in second]
    point = first[0]
    assert set(point.vector) == {"dense", "sparse"} and point.vector["sparse"].indices
    assert point.payload["doc_type"] == "mitre_attack" and point.payload["embedding_model"]


async def test_index_chunks_batches_upserts(mock_store, mock_embedder):
    chunks = [Chunk(key=f"k{i}", text=f"text {i}", payload={"source": "s", "doc_type": "custom"}) for i in range(150)]
    assert await index_chunks(chunks, mock_store, mock_embedder) == 150
    assert mock_store.upsert.call_count == 2
    assert mock_store.upsert.call_args_list[1].args[0][0].payload["chunk_index"] == 100
    assert point_id("k1") == point_id("k1") != point_id("k2")


def test_owasp_link_list_sections_are_not_indexed():
    md = "## LLM01:2025 Prompt Injection\n\n### Description\n\nText.\n\n### Reference Links\n\n1. https://x\n\n### Related Frameworks and Taxonomies\n\n- AML.T0051"
    assert [c.payload["section"] for c in owasp_chunks(md, "LLM01_PromptInjection.md")] == ["Description"]


def test_owasp_chunks_carry_risk_id_and_section():
    md = "## LLM07:2025 System Prompt Leakage\n\n### Description\n\nPrompts may leak.\n\n### Prevention\n\nNo secrets in prompts."
    chunks = owasp_chunks(md, "LLM07_SystemPromptLeakage.md")
    assert [c.payload["section"] for c in chunks] == ["Description", "Prevention"]
    assert all(c.payload["owasp_id"] == "LLM07" and "LLM07: System Prompt Leakage" in c.text for c in chunks)


async def test_ingest_pdf_payload(mock_store, mock_embedder, tmp_path):
    page = MagicMock(page_content="Sample threat report text.", metadata={"page": 1})
    with patch("app.rag.ingestion.PyPDFLoader") as loader:
        loader.return_value.load.return_value = [page]
        assert await ingest_pdf(str(tmp_path / "report.pdf"), "custom", mock_store, mock_embedder) == 1
    payload = mock_store.upsert.call_args.args[0][0].payload
    assert payload["source"] == "report.pdf" and payload["doc_type"] == "custom" and payload["page"] == 1
    assert payload["text"] == "Sample threat report text."
