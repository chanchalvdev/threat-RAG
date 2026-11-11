"""LangChain tools over the external threat-intel sources, one per indicator type."""
import ipaddress
from typing import Any, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.agent import intel_sources as src
from app.agent.investigation_models import IOC_PATTERNS
from app.core.config import get_settings


class _IntelTool(BaseTool):  # type: ignore[override]  # pydantic __replace__ stub quirk
    def _run(self, *args: Any, **kwargs: Any) -> str:
        raise NotImplementedError("Use async only")


class IPInput(BaseModel):
    ip: str = Field(..., description="Public IPv4 or IPv6 address")


class DomainInput(BaseModel):
    domain: str = Field(..., description="Domain name, e.g. example.com")


class HashInput(BaseModel):
    file_hash: str = Field(..., description="MD5, SHA-1 or SHA-256 file hash")


class CVEExploitInput(BaseModel):
    cve_id: str = Field(..., description="CVE ID in format CVE-YYYY-NNNNN")


class IPIntelTool(_IntelTool):  # type: ignore[override]  # pydantic __replace__ stub quirk
    name: str = "ip_intel_lookup"
    description: str = "Check a public IP's open ports, known CVEs, abuse reports and threat reports."
    args_schema: Type[BaseModel] = IPInput

    async def _arun(self, ip: str) -> str:
        try:
            addr = ipaddress.ip_address(ip.strip())
        except ValueError:
            return f"Invalid IP address: {ip[:50]}"
        if not addr.is_global:
            return f"{addr} is not a public address, so it was not sent to external services."
        s, value = get_settings(), str(addr)
        section = "IPv4" if addr.version == 4 else "IPv6"
        return await src.gather_evidence(value, {
            "Shodan InternetDB": src.internetdb(value),
            "AbuseIPDB": src.abuseipdb(value, s.abuseipdb_api_key) if s.abuseipdb_api_key else None,
            "AlienVault OTX": src.otx(section, value, s.otx_api_key) if s.otx_api_key else None,
            "ThreatFox": src.threatfox(value, s.abusech_auth_key) if s.abusech_auth_key else None,
        })


class DomainIntelTool(_IntelTool):  # type: ignore[override]  # pydantic __replace__ stub quirk
    name: str = "domain_intel_lookup"
    description: str = "Check a domain against malware URL feeds and threat reports."
    args_schema: Type[BaseModel] = DomainInput

    async def _arun(self, domain: str) -> str:
        value = domain.strip().lower()
        if not IOC_PATTERNS["domain"].match(value):
            return f"Invalid domain: {domain[:50]}"
        s = get_settings()
        return await src.gather_evidence(value, {
            "AlienVault OTX": src.otx("domain", value, s.otx_api_key) if s.otx_api_key else None,
            "URLhaus": src.urlhaus(value, s.abusech_auth_key) if s.abusech_auth_key else None,
            "ThreatFox": src.threatfox(value, s.abusech_auth_key) if s.abusech_auth_key else None,
        })


class HashIntelTool(_IntelTool):  # type: ignore[override]  # pydantic __replace__ stub quirk
    name: str = "hash_intel_lookup"
    description: str = "Check a file hash against known malware samples and threat reports."
    args_schema: Type[BaseModel] = HashInput

    async def _arun(self, file_hash: str) -> str:
        value = file_hash.strip().lower()
        if not IOC_PATTERNS["hash"].match(value):
            return f"Invalid hash: {file_hash[:70]}"
        s = get_settings()
        return await src.gather_evidence(value, {
            "AlienVault OTX": src.otx("file", value, s.otx_api_key) if s.otx_api_key else None,
            "MalwareBazaar": src.malwarebazaar(value, s.abusech_auth_key) if s.abusech_auth_key else None,
            "ThreatFox": src.threatfox(value, s.abusech_auth_key) if s.abusech_auth_key else None,
        })


class CVEExploitationTool(_IntelTool):  # type: ignore[override]  # pydantic __replace__ stub quirk
    name: str = "cve_exploitation_lookup"
    description: str = "Check whether a CVE is actively exploited (CISA KEV) and its exploit probability (EPSS)."
    args_schema: Type[BaseModel] = CVEExploitInput

    async def _arun(self, cve_id: str) -> str:
        value = cve_id.strip().upper()
        if not IOC_PATTERNS["cve"].match(value):
            return f"Invalid CVE ID format: {cve_id[:50]}"
        return await src.gather_evidence(value, {"CISA KEV": src.kev(value), "FIRST EPSS": src.epss(value)})


def intel_tools() -> list[BaseTool]:
    return [IPIntelTool(), DomainIntelTool(), HashIntelTool(), CVEExploitationTool()]
