# Changelog

## 0.4.1

- Remove the misleading `is_wired` and `wired_port_list` aggregates after the
  M9 Plus proved those fields do not represent usable node/physical-port counts.
- Rely on the independently consistent connection-type, Ethernet-backhaul-port
  and backhaul-speed fields instead.
- Label backhaul speed as megabits per second, matching the upstream
  integration's sensor definition.
- Keep the fixed three-read wire allowlist unchanged.

## 0.4.0

- Add anonymous backhaul, signal and internet-health summaries from the existing
  device-inventory reply.
- Add aggregate traffic, mesh-membership, priority and restriction counts from
  the existing connected-client reply.
- Flatten the M9 Plus array-shaped node `connection_type` field.
- Count unexpected telemetry formats as unparsed rather than exposing their raw
  values.
- Make no change to the fixed three-read wire allowlist.

## 0.3.0

- Add a values-free schema map for the three already-approved response families.
- Report only field names and broad data types; do not expose nested or raw
  values.
- Make no change to the fixed three-read wire allowlist.

## 0.2.0

- Add the existing integration's proven global connected-client read.
- Return only anonymous client counts grouped by connection type and interface.
- Keep the armed App single-cycle, disarmed by default, and closed to any
  user-selected endpoint or payload.

## 0.1.1

- Read Supervisor's root-only options file before entering the restricted
  `deco-research` runtime account.
- Fail closed if the process cannot permanently drop its startup privileges.
- Add regression tests for the privilege transition and startup ordering.

## 0.1.0

- Add disarmed-by-default Home Assistant App shell.
- Add the two-call read-only Deco connection smoke probe.
- Add redacted status/health ingress endpoints.
- Add source-level wire-operation and redaction tests.
- Require explicit acknowledgement of Deco's exclusive owner session.
- Limit the armed smoke test to one two-read cycle.
