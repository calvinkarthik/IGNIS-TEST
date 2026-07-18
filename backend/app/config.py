from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    if raw.strip().lower() in {"1", "true", "yes", "on"}:
        return True
    if raw.strip().lower() in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be true or false")


def _int(name: str, default: int, minimum: int, maximum: int) -> int:
    value = int(os.getenv(name, str(default)))
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def _csv(name: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in os.getenv(name, "").split(",") if item.strip())


@dataclass(slots=True)
class Settings:
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    frontend_origin: str = "http://localhost:5173"
    qnx_tcp_host: str = "0.0.0.0"
    qnx_tcp_port: int = 9001
    device_token: str = "replace-me"
    expected_device_id: str = "ignis-qnxpi-01"
    database_url: str = "sqlite:///./data/ignis.db"
    incident_storage_root: Path = Path("./data/incidents")
    elevenlabs_api_key: str = ""
    occupant_agent_id: str = ""
    dispatch_agent_id: str = ""
    phone_number_id: str = ""
    elevenlabs_environment: str = "production"
    demo_calls_enabled: bool = False
    demo_dispatch_number: str = ""
    demo_allowed_numbers: tuple[str, ...] = field(default_factory=tuple)
    global_call_cooldown_seconds: int = 60
    max_calls_per_incident: int = 1
    call_provider: str = "elevenlabs"
    enable_simulator_endpoints: bool = True
    provider_webhook_secret: str = ""
    log_level: str = "INFO"
    max_payload_bytes: int = 2_097_152
    action_rate_limit_per_minute: int = 30
    response_timeout_seconds: int = 10

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv(override=False)
        settings = cls(
            app_env=os.getenv("APP_ENV", "development"),
            app_host=os.getenv("APP_HOST", "0.0.0.0"),
            app_port=_int("APP_PORT", 8000, 1, 65535),
            frontend_origin=os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").rstrip("/"),
            qnx_tcp_host=os.getenv("QNX_TCP_HOST", "0.0.0.0"),
            qnx_tcp_port=_int("QNX_TCP_PORT", 9001, 0, 65535),
            device_token=os.getenv("IGNIS_DEVICE_TOKEN", "replace-me"),
            expected_device_id=os.getenv("IGNIS_EXPECTED_DEVICE_ID", "ignis-qnxpi-01"),
            database_url=os.getenv("DATABASE_URL", "sqlite:///./data/ignis.db"),
            incident_storage_root=Path(os.getenv("INCIDENT_STORAGE_ROOT", "./data/incidents")),
            elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY", ""),
            occupant_agent_id=os.getenv("ELEVENLABS_OCCUPANT_AGENT_ID", ""),
            dispatch_agent_id=os.getenv("ELEVENLABS_DISPATCH_AGENT_ID", ""),
            phone_number_id=os.getenv("ELEVENLABS_PHONE_NUMBER_ID", ""),
            elevenlabs_environment=os.getenv("ELEVENLABS_ENVIRONMENT", "production"),
            demo_calls_enabled=_bool("DEMO_CALLS_ENABLED", False),
            demo_dispatch_number=os.getenv("DEMO_DISPATCH_NUMBER", "").strip(),
            demo_allowed_numbers=_csv("DEMO_ALLOWED_NUMBERS"),
            global_call_cooldown_seconds=_int(
                "DEMO_GLOBAL_CALL_COOLDOWN_SECONDS", 60, 0, 86_400
            ),
            max_calls_per_incident=_int("DEMO_MAX_CALLS_PER_INCIDENT", 1, 1, 3),
            call_provider=os.getenv("DEMO_CALL_PROVIDER", "elevenlabs").strip().lower(),
            enable_simulator_endpoints=_bool("ENABLE_SIMULATOR_ENDPOINTS", True),
            provider_webhook_secret=os.getenv("PROVIDER_WEBHOOK_SECRET", ""),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            response_timeout_seconds=_int("IGNIS_RESPONSE_TIMEOUT_SECONDS", 10, 2, 300),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if not self.device_token or len(self.device_token) > 512:
            raise ValueError("IGNIS_DEVICE_TOKEN must contain 1 to 512 characters")
        if self.app_env == "production" and self.device_token == "replace-me":
            raise ValueError("The development device token is forbidden in production")
        if self.call_provider not in {"elevenlabs", "mock"}:
            raise ValueError("DEMO_CALL_PROVIDER must be elevenlabs or mock")
        if self.call_provider == "mock" and self.app_env == "production":
            raise ValueError("The mock call provider is forbidden in production")
        if self.demo_calls_enabled and not self.demo_dispatch_number:
            raise ValueError("DEMO_DISPATCH_NUMBER is required when demo calls are enabled")

    @property
    def database_path(self) -> Path:
        prefix = "sqlite:///"
        if not self.database_url.startswith(prefix):
            raise ValueError("Only sqlite:/// database URLs are supported")
        return Path(self.database_url[len(prefix) :]).expanduser().resolve()
