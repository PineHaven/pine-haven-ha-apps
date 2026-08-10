# FREE THE DECO operating contract

## Version 1.0

FREE THE DECO is a continuously running Home Assistant App. When monitoring is
enabled, it performs four fixed authenticated `read` operations at a configurable
30–3600 second interval:

1. mesh device inventory;
2. controller performance;
3. global connected-client inventory;
4. passive wireless status.

There is no generic endpoint runner or user-selectable Deco payload. Reboot,
optimisation and every configuration write remain absent.

## Home Assistant output

The App uses Home Assistant's scoped API token only to publish state telemetry.
It does not request the Supervisor API, Docker, host networking, mapped host files,
full access or privileged container capabilities. Unchanged entity payloads are
not republished.

Published entities cover overall monitor health, last success, online/offline node
counts, connected-client totals, 2.4/5 GHz/wired client counts, controller load,
2.4 GHz channel/width and per-node online/backhaul state.

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
