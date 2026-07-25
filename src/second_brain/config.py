"""Settings for Second Brain++ - vault location and link/graph defaults.

Env-overridable with the SECOND_BRAIN_ prefix (e.g. SECOND_BRAIN_VAULT_DIR).
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class SecondBrainSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SECOND_BRAIN_", env_file=".env", extra="ignore")

    vault_dir: Path = Path("sample-vault")
    manifest_path: Path = Path("data/vault_manifest.json")
    graph_html_path: Path = Path("data/graph.html")
    merge_proposals_dir: Path = Path("data/merge-proposals")
    related_top_k: int = 5
    # Local model the graph uses for triple extraction when no OLLAMA_MODEL / Gemini key is set.
    # qwen2.5:3b-instruct is the strongest small model that stays fast on a 4 GB GPU.
    ollama_model: str = "qwen2.5:3b-instruct"


_settings: SecondBrainSettings | None = None


def get_settings() -> SecondBrainSettings:
    global _settings
    if _settings is None:
        _settings = SecondBrainSettings()
    return _settings
