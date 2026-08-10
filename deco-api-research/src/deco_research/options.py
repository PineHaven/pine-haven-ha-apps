"""Load and validate App options without exposing connection values."""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


class OptionsError(ValueError):
    """Raised when monitoring options are incomplete or unsafe."""


@dataclass(frozen=True)
class MonitorOptions:
    """Validated runtime configuration."""

    monitoring_enabled: bool
    host: str | None
    username: str | None
    password: str | None
    exclusive_session_acknowledged: bool
    verify_ssl: bool
    poll_interval_seconds: int
    publish_to_home_assistant: bool
    node_aliases: dict[str, str]

    @classmethod
    def from_dict(cls, data: dict) -> "MonitorOptions":
        enabled = data.get("monitoring_enabled") is True
        host = _normalize_host(data.get("host"))
        username = _optional_text(data.get("username"))
        password = _optional_text(data.get("password"))
        session_acknowledged = data.get("exclusive_session_acknowledged") is True
        verify_ssl = data.get("verify_ssl") is True
        poll_interval = _poll_interval(data.get("poll_interval_seconds", 60))
        publish = data.get("publish_to_home_assistant", True) is True
        node_aliases = _node_aliases(data.get("node_aliases_json", "{}"))

        if enabled and not all((host, username, password)):
            raise OptionsError("monitoring_requires_target_and_credentials")
        if enabled and not session_acknowledged:
            raise OptionsError("monitoring_requires_exclusive_session_acknowledgement")

        return cls(
            enabled,
            host,
            username,
            password,
            session_acknowledged,
            verify_ssl,
            poll_interval,
            publish,
            node_aliases,
        )


def load_options(path: str | Path = "/data/options.json") -> MonitorOptions:
    """Read Supervisor options from the standard persistent-data mount."""

    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise OptionsError("options_must_be_an_object")
    return MonitorOptions.from_dict(data)


def normalize_mac(value: object) -> str | None:
    """Return a canonical MAC for private in-memory alias lookup only."""

    if not isinstance(value, str):
        return None
    compact = re.sub(r"[^0-9a-fA-F]", "", value)
    if len(compact) != 12:
        return None
    return "-".join(compact[index : index + 2] for index in range(0, 12, 2)).upper()


def _poll_interval(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise OptionsError("poll_interval_must_be_an_integer")
    if not 30 <= value <= 3600:
        raise OptionsError("poll_interval_out_of_range")
    return value


def _node_aliases(value: object) -> dict[str, str]:
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as err:
            raise OptionsError("node_aliases_must_be_valid_json") from err
    else:
        decoded = value
    if not isinstance(decoded, dict) or len(decoded) > 64:
        raise OptionsError("node_aliases_must_be_an_object")

    aliases: dict[str, str] = {}
    for raw_mac, raw_name in decoded.items():
        mac = normalize_mac(raw_mac)
        name = _optional_text(raw_name)
        if mac is None or name is None or len(name) > 64:
            raise OptionsError("node_alias_is_invalid")
        if any(ord(character) < 32 for character in name):
            raise OptionsError("node_alias_is_invalid")
        aliases[mac] = name
    return aliases


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
