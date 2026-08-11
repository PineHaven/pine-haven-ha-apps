"""Model Pine Haven's 2.4 GHz Wi-Fi/Zigbee coexistence trade-offs."""

from typing import Any

ZIGBEE_NETWORKS = (
    {"id": "perimeter", "name": "PERIMETER", "channel": 11},
    {"id": "core", "name": "CORE", "channel": 15},
    {"id": "ambience", "name": "AMBIENCE", "channel": 20},
)

CANDIDATE_PLANS = (
    {
        "id": "protect_core_and_ambience",
        "name": "Protect CORE + AMBIENCE",
        "channel": 1,
        "width_mhz": 20,
        "tradeoff": (
            "Widest modeled separation from Zigbee 15 and 20; direct overlap "
            "with PERIMETER channel 11."
        ),
    },
    {
        "id": "balanced_middle",
        "name": "Balanced middle",
        "channel": 6,
        "width_mhz": 20,
        "tradeoff": (
            "No direct modeled Zigbee overlap, but adjacent-channel pressure "
            "remains near CORE 15 and AMBIENCE 20."
        ),
    },
    {
        "id": "protect_core_and_perimeter",
        "name": "Protect CORE + PERIMETER",
        "channel": 11,
        "width_mhz": 20,
        "tradeoff": (
            "Widest modeled separation from Zigbee 11 and 15; edge/adjacent "
            "pressure remains near AMBIENCE channel 20."
        ),
    },
)

RISK_WEIGHT = {
    "primary_overlap": 3,
    "possible_40mhz_extension": 2,
    "adjacent": 1,
    "separated": 0,
    "unknown": 4,
}


def build_coexistence_diagnostics(band2: object) -> dict[str, Any]:
    """Return bounded RF geometry and a deliberately disarmed control preflight."""

    radio = band2 if isinstance(band2, dict) else {}
    channel = _integer(radio.get("channel"))
    width = _integer(radio.get("configured_width_mhz"))
    current = _assess_plan(channel, width)
    current["automatic_channel"] = _optional_boolean(radio.get("automatic_channel"))
    current["automatic_width"] = _optional_boolean(radio.get("automatic_width"))
    current["firmware_width_token"] = radio.get("firmware_width_token")

    width_only = _assess_plan(channel, 20) if channel is not None else None
    reduced = 0
    if width_only is not None:
        current_exposure = sum(
            row["risk"] in {"possible_40mhz_extension", "adjacent"}
            for row in current["zigbee_networks"]
        )
        width_only_exposure = sum(
            row["risk"] in {"possible_40mhz_extension", "adjacent"}
            for row in width_only["zigbee_networks"]
        )
        reduced = max(current_exposure - width_only_exposure, 0)

    candidates = []
    for plan in CANDIDATE_PLANS:
        assessment = _assess_plan(plan["channel"], plan["width_mhz"])
        assessment.update(
            {
                "id": plan["id"],
                "name": plan["name"],
                "tradeoff": plan["tradeoff"],
            }
        )
        candidates.append(assessment)
    candidates.sort(key=lambda item: (item["aggregate_score"], item["channel"]))
    for rank, candidate in enumerate(candidates, start=1):
        candidate["geometry_rank"] = rank

    return {
        "model": "conservative_frequency_geometry_v1",
        "limitations": (
            "Geometry does not measure neighbouring access points, airtime, "
            "signal strength or interference at each Zigbee device."
        ),
        "current": current,
        "width_only_20mhz": {
            "assessment": width_only,
            "possible_extension_exposures_removed": reduced,
            "core_direct_overlap_remains": _network_risk(width_only, "core")
            == "primary_overlap",
        },
        "candidate_plans": candidates,
        "control_readiness": {
            "state": "disarmed",
            "writes_enabled": False,
            "firmware_contract": {
                "endpoint": "admin/wireless",
                "form": "wlan",
                "operation": "write",
                "channel_field": "band2_4.host.channel",
                "bandwidth_field": "band2_4.host.bandwidth",
                "known_bandwidth_tokens": ["HT20", "HT40"],
                "commit_observed": True,
                "mesh_restart_possible": True,
            },
            "live_validation": "not_tested",
            "rollback": "capture current channel and width immediately before change",
            "required_next_step": (
                "Validate on an isolated Deco, or explicitly approve a timed "
                "production experiment with an out-of-band rollback path."
            ),
        },
    }


def _assess_plan(channel: int | None, width_mhz: int | None) -> dict[str, Any]:
    if channel is None or width_mhz not in {20, 40}:
        rows = [
            dict(network, risk="unknown", separation_mhz=None)
            for network in ZIGBEE_NETWORKS
        ]
        return {
            "channel": channel,
            "width_mhz": width_mhz,
            "risk": "unknown",
            "aggregate_score": sum(RISK_WEIGHT[row["risk"]] for row in rows),
            "zigbee_networks": rows,
        }

    wifi_center = _wifi_center_mhz(channel)
    rows = []
    for network in ZIGBEE_NETWORKS:
        zigbee_center = 2405 + (network["channel"] - 11) * 5
        separation = abs(wifi_center - zigbee_center)
        if separation <= 10:
            risk = "primary_overlap"
        elif width_mhz == 40 and separation <= 30:
            # The passive Deco reply reports HT40 but not extension direction.
            risk = "possible_40mhz_extension"
        elif separation <= 15:
            risk = "adjacent"
        else:
            risk = "separated"
        rows.append(
            {
                **network,
                "center_mhz": zigbee_center,
                "separation_mhz": separation,
                "risk": risk,
            }
        )

    score = sum(RISK_WEIGHT[row["risk"]] for row in rows)
    if any(row["risk"] == "primary_overlap" for row in rows):
        overall = "high"
    elif any(row["risk"] == "possible_40mhz_extension" for row in rows):
        overall = "elevated"
    elif any(row["risk"] == "adjacent" for row in rows):
        overall = "guarded"
    else:
        overall = "lower"
    return {
        "channel": channel,
        "width_mhz": width_mhz,
        "center_mhz": wifi_center,
        "risk": overall,
        "aggregate_score": score,
        "zigbee_networks": rows,
    }


def _wifi_center_mhz(channel: int) -> int:
    return 2484 if channel == 14 else 2407 + channel * 5


def _network_risk(assessment: dict[str, Any] | None, network_id: str) -> str | None:
    if assessment is None:
        return None
    for network in assessment["zigbee_networks"]:
        if network["id"] == network_id:
            return str(network["risk"])
    return None


def _integer(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _optional_boolean(value: object) -> bool | None:
    return value if isinstance(value, bool) else None
