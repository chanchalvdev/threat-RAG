"""Unit tests never reach the developer's real services, whatever `.env` holds.

Environment variables win over `.env` in pydantic-settings, so blanking them here keeps state
in-process (no local Redis) and every external source unkeyed. Tests that need a key pass it
explicitly through `Settings(...)` or a patched `get_settings`.
"""
import os

for _name in (
    "REDIS_URL", "JWT_SECRET", "API_KEY",
    "OPENROUTER_API_KEY", "GROQ_API_KEY", "CEREBRAS_API_KEY",
    "TAVILY_API_KEY", "ABUSEIPDB_API_KEY", "OTX_API_KEY", "ABUSECH_AUTH_KEY", "NVD_API_KEY",
    "VIRUSTOTAL_API_KEY", "GREYNOISE_API_KEY", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY",
    "SLACK_WEBHOOK_URL", "TEAMS_WEBHOOK_URL", "TAXII_URL",
):
    os.environ[_name] = ""
os.environ["LLM_ORDER"] = "openrouter,groq,cerebras,gemini,kimchi"
