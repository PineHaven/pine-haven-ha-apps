"""Load and validate App options without exposing their values."""

import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


class OptionsError(ValueError):
    """Raised when armed probe options are incomplete or unsafe."""


@dataclass(frozen=True)
class ProbeOptions:
    """Validated runtime configuration."""

    probe_enabled: bool
    host: str | None
    username: str | None
    password: str | None
    exclusive_session_acknowledged: bool
    verify_ssl: bool

    @classmethod
    def from_dict(cls, data: dict) -> "ProbeOptions":
        enabled = data.get("probe_enabled") is True
        host = _normalize_host(data.get("host"))
        username = _optional_text(data.get("username"))
        password = _optional_text(data.get("password"))
        session_acknowledged = data.get("exclusive_session_acknowledged") is True
        verify_ssl = data.get("verify_ssl") is True

        if enabled and not all((host, username, password)):
            raise OptionsError("armed_probe_requires_target_and_credentials")
        if enabled and not session_acknowledged:
            raise OptionsError("armed_probe_requires_exclusive_session_acknowledgement")

        return cls(
            enabled,
            host,
            username,
            password,
            session_acknowledged,
            verify_ssl,
        )


def load_options(path: str | Path = "/data/options.json") -> ProbeOptions:
    """Read Supervisor options from the standard persistent-data mount."""

    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise OptionsError("options_must_be_an_object")
    return ProbeOptions.from_dict(data)


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _normalize_host(value: object) -> str | None:
    value = _optional_text(value)
    if value is None:
        return None

    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise OptionsError("target_must_be_http_or_https")
    if parsed.username is not None or parsed.password is not None:
        raise OptionsError("target_must_not_contain_credentials")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise OptionsError("target_must_not_contain_path_query_or_fragment")

    try:
        parsed_port = parsed.port
    except ValueError as err:
        raise OptionsError("invalid_target_port") from err
    if parsed_port is not None and not 1 <= parsed_port <= 65535:
        raise OptionsError("invalid_target_port")

    return urlunsplit((parsed.scheme, parsed.netloc, "", "", "")).rstrip("/")
