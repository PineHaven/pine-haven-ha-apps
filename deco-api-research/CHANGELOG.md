# Changelog

## 1.2.0

- Add a Pine Haven-specific coexistence model for the observed Deco 2.4 GHz
  channel/width and Zigbee CORE 15, AMBIENCE 20 and PERIMETER 11.
- Show conservative direct, possible 40 MHz-extension, adjacent and separated
  assessments without claiming passive spectrum-occupancy evidence.
- Compare channel 1, 6 and 11 at 20 MHz as explicit trade-off plans and label the
  ranking as frequency geometry rather than a production recommendation.
- Preserve a recognized firmware HT-mode token such as `HT40` while continuing
  to discard all unexpected strings and every wireless secret.
- Add durable Home Assistant entities for coexistence risk and radio-control
  readiness.
- Document the firmware-derived `admin/wireless` / `wlan` write contract, known
  `HT20`/`HT40` tokens, possible mesh restart, and the remaining live-validation
  and rollback gates.
- Keep the control laboratory disarmed: the wire allowlist remains the same four
  reads, with no write, optimiser, reboot or generic operation.

## 1.1.0

- Replace transient Home Assistant state objects with retained MQTT Device
  Discovery and non-retained sanitized state updates.
- Preserve all established `free_the_deco_*` entity IDs while grouping the monitor
  and each Deco under logical, hardware-identifier-free devices.
- Add a three-interval freshness threshold, MQTT expiry, App uptime, poll age,
  next-poll timing, cycle duration and success/failure counters.
- Report Deco-read, exclusive-session and Home Assistant publishing health
  independently, with safe error categories and explicit recovery state.
- Add queued, running, succeeded and failed manual-refresh states and reject
  duplicate pending requests.
- Expand the responsive Ingress UI with operational-health and diagnostics panels.
- Allow display aliases such as Workshop and Gym without changing established
  entity IDs.
- Document Home Assistant administrator-management visibility of stored App
  options and the coordinated Deco credential-rotation procedure.
- Keep the wire boundary at the same four fixed read operations; configuration
  writes, scans, optimisation, reboot and generic endpoints remain absent.

## 1.0.0

- Promote the bounded research probe into Pine Haven's primary continuous Deco
  telemetry App while keeping all Deco operations read-only.
- Add a responsive Home Assistant Ingress UI for monitor health, named mesh nodes,
  client distribution, radio status, known Zigbee overlap and capability status.
- Publish sanitized summary and per-node telemetry through Home Assistant's scoped
  API, skipping unchanged state payloads.
- Add configurable 30–3600 second polling, manual refresh, safe retry behavior,
  automatic boot support and named-node aliases.
- Continue discarding client identifiers, addresses, wireless secrets, BSSIDs,
  node MACs and raw API replies.
- Keep network optimisation, reboot and all configuration writes absent.

## 0.5.0

- Add one fixed `wireless` / `wlan` read discovered in the M9 Plus V2 1.9.1
  firmware.
- Return only validated channel, configured-width and automatic-selection
  values; discard SSIDs, passwords, BSSIDs and every other raw wireless field.
- Deliberately exclude the network-optimisation read because firmware analysis
  shows that it starts a channel scan and writes temporary runtime state.
- Keep the App disarmed by default and the armed run limited to one four-read
  cycle.

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
