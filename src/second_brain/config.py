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
    related_top_k: int = 5


_settings: SecondBrainSettings | None = None


def get_settings() -> SecondBrainSettings:
    global _settings
    if _settings is None:
        _settings = SecondBrainSettings()
    return _settings
