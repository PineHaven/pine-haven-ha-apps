# FREE THE DECO operating contract

## Version 1.2

FREE THE DECO is a continuously running Home Assistant App. When monitoring is
enabled, it performs four fixed authenticated `read` operations at a configurable
30–3600 second interval:

1. mesh device inventory;
2. controller performance;
3. global connected-client inventory;
4. passive wireless status.

There is no generic endpoint runner or user-selectable Deco payload. Reboot,
optimisation and every configuration write remain absent.

## Coexistence laboratory

Version 1.2 compares the sanitized 2.4 GHz channel and width with Pine Haven's
three fixed Zigbee networks: PERIMETER channel 11, CORE channel 15 and AMBIENCE
channel 20. The model uses frequency separation only. It does not measure
neighbouring access points, airtime, received signal strength or interference at
individual Zigbee devices, so its candidate ranking is not a production channel
recommendation.

The UI compares three standard 20 MHz plans:

- channel 1 maximizes modeled separation from CORE and AMBIENCE but directly
  overlaps PERIMETER;
- channel 6 has no direct modeled overlap but remains adjacent to CORE and
  AMBIENCE;
- channel 11 maximizes modeled separation from CORE and PERIMETER but leaves
  edge/adjacent pressure near AMBIENCE.

The passive Deco reply reports an HT mode such as `HT40` without enough evidence
to determine the extension direction. The model therefore labels Zigbee networks
within either possible secondary-channel footprint as possible 40 MHz-extension
exposure.

Firmware analysis maps `admin/wireless`, form `wlan`, operation `write` to
`band2_4.host.channel` and `band2_4.host.bandwidth`, followed by a commit; the
radio scripts recognize `HT20` and `HT40`. This is evidence for a controlled lab,
not proof of production behaviour. Version 1.2 contains no write implementation.
An isolated-unit validation or an explicitly approved maintenance-window trial
must prove interruption, readback, persistence and rollback before a production
control can be considered.

## Home Assistant ownership and output

The App uses Home Assistant's scoped API token to call only the `mqtt.publish`
service. Retained MQTT Device Discovery documents create durable, registry-owned
entities grouped under one logical monitor device and one logical device per Deco.
One non-retained, sanitized state packet is refreshed every poll. Discovery sets
an expiry window one poll interval longer than the configured stale threshold, so
entities become unavailable if the App stops instead of restoring ghost data.

The App does not connect to the MQTT broker directly and stores no MQTT
credentials. It also does not write transient `/api/states` objects.

It does not request the Supervisor API, Docker, host networking, mapped host files,
full access or privileged container capabilities.

Published entities cover overall monitor health, last success, online/offline node
counts, connected-client totals, 2.4/5 GHz/wired client counts, controller load,
2.4 GHz channel/width and per-node online/backhaul state. Version 1.1 adds App
uptime, poll age, next poll, success/failure counters, consecutive failures,
read/session/publisher health, recovery, staleness and manual-refresh status.
Version 1.2 adds coexistence-risk and radio-control-readiness entities.

The established `free_the_deco_*` entity IDs remain the defaults. A display alias
changes a node's visible name but preserves the stable ID derived from its existing
Deco nickname. Discovery unique IDs and device identifiers are logical strings;
node MACs are never used as Home Assistant identifiers.

## Freshness, recovery and manual refresh

`stale_after_intervals` accepts 2–10 and defaults to 3. Data is stale when no
successful read has completed inside that many configured poll intervals. Read
health, exclusive-session health and Home Assistant publishing health are reported
separately so an MQTT problem cannot masquerade as a Deco authentication problem.

Cycle counters and safe categories survive until the App restarts. After any
categorized failure, the runtime drops the current Deco client, creates a clean
session for the next attempt, reports `retrying`, and records `recovered` after a
successful cycle.

Manual refresh does not create a new operation. It queues the same fixed four-read
cycle and reports `queued`, `running`, `succeeded`, or `failed`. A second request is
rejected while one is queued or running.

## Data boundary

The local authenticated UI may show configured Deco display names so an operator
can identify a failed room. It never exposes node MAC/IP/BSSID values. Client
names, MAC/IP addresses, SSIDs, wireless credentials and raw replies are discarded
before the snapshot is stored, rendered or published.

Unexpected telemetry strings are counted as unparsed and are never returned.
Backhaul speeds use megabits per second, matching the upstream integration's
definition. Traffic numbers retain the firmware's native units because the reply
does not declare one.

## Exclusive session rule

The M9 owner login is exclusive. `monitoring_enabled` may be set only when the
operator has acknowledged that no competing Deco integration is polling with the
same login. The App reuses one authenticated client during healthy operation and
creates a clean client session after a categorized failure.

## Credential storage and rotation

The Home Assistant App schema marks the Deco password as a password field. FREE
THE DECO reads the value once at startup and never includes it in status, logs,
MQTT, discovery, or the Ingress UI. Home Assistant administrator management APIs
may nevertheless return stored App options to an already authenticated
administrator. This is outside the App's redaction boundary.

After diagnostic access, rotate the Deco owner password in the TP-Link Deco app,
then update FREE THE DECO and any disabled rollback integration in one coordinated
maintenance window. Stop polling while values are inconsistent, restart the App,
and verify an authenticated read and a new MQTT state publication. Never paste the
old or new password into issue trackers, pull requests, dashboards, or logs.
