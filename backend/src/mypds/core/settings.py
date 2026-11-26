"""Configuration de l'application, lue depuis l'environnement (préfixe MYPDS_)."""

from functools import lru_cache
from ipaddress import ip_network
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MYPDS_", env_file=None, extra="ignore")

    # Base de données (socket Unix recommandé : postgresql+asyncpg:///mypds?host=/var/run/postgresql)
    database_url: str = "postgresql+asyncpg://mypds@/mypds?host=/var/run/postgresql"

    # Clé maîtresse de chiffrement des secrets (32 octets, hors base)
    secret_key_file: Path = Path("/etc/mypds/secret.key")

    # Réseau HTTP
    host: str = "0.0.0.0"  # noqa: S104 - écoute volontaire sur le VLAN, derrière NPM
    port: int = 8080
    trusted_proxies: list[str] = Field(default_factory=list)  # IP/CIDR de Nginx Proxy Manager
    public_origin: str | None = None  # ex. https://space.example.lan (contrôle Origin)

    # Sessions
    cookie_secure: bool = True  # False uniquement en développement HTTP local
    session_days_trusted: int = 30
    session_hours_default: int = 12

    # Fichiers
    static_dir: Path | None = None  # frontend compilé
    data_dir: Path = Path("/var/lib/mypds")

    # Sortant : hôtes internes explicitement autorisés pour RSS/ICS (anti-SSRF)
    outbound_allow_hosts: list[str] = Field(default_factory=list)

    # Planification
    rss_refresh_minutes: int = 30
    calendar_refresh_minutes: int = 15
    scheduler_enabled: bool = True

    log_level: str = "INFO"
    dev_mode: bool = False

    @field_validator("trusted_proxies")
    @classmethod
    def _check_cidr(cls, v: list[str]) -> list[str]:
        for item in v:
            ip_network(item, strict=False)
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
