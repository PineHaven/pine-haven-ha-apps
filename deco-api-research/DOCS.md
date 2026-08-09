# FREE THE DECO - API Research

## Version 0.1.x purpose

Prove the Home Assistant App lifecycle and, only after explicit arming, confirm
that the established local Deco authentication flow can perform two known read
operations.

## Safe first start

1. Install the App.
2. Leave `probe_enabled` set to `false`.
3. Start the App.
4. Open its ingress page or request `/api/v1/status`.
5. Confirm the mode is `disarmed` and no target is configured.

No Deco request is possible in this state.

## Arming a live smoke probe

1. Enter the controller URL and the same owner credentials used by the existing
   integration. The protocol username is normally `admin`; Deco manager-account
   credentials do not work for this local API.
2. Temporarily disable the existing TP-Link Deco integration. Deco owner login
   is exclusive, so two active clients can repeatedly invalidate each other's
   sessions.
3. Set `exclusive_session_acknowledged` and `probe_enabled` to `true`, then
   restart the App.
4. Version 0.1.x performs one two-read cycle and then remains idle. Inspect only
   the sanitized status endpoint and App logs.
5. Set `probe_enabled` and `exclusive_session_acknowledged` back to `false`,
   restart or stop the App, then re-enable the existing Deco integration.
6. Confirm the normal integration has resumed before closing the experiment.

Set `probe_enabled` back to `false` before any later App restart. The
acknowledgement is an experiment gate, not a persistent operating mode.

The App must be stopped or disarmed before the standard Deco integration is
restored. This prevents authentication churn even though the probe itself
contains no configuration-changing request.

If the normal integration does not recover immediately, leave the probe
disarmed and reload the integration. Do not retry both clients concurrently.

The App's status data remains in memory only and is lost when the container is
restarted.

Do not copy App options, raw container data or credentials into GitHub.

## Network actions

Authentication performs the protocol's key/auth reads and session login. Once
authenticated, the only available research calls are:

| Capability | Path family | Form | Operation |
|---|---|---|---|
| Device inventory | `admin/device` | `device_list` | `read` |
| Performance | `admin/network` | `performance` | `read` |

The source contains no reboot method, generic request runner, configuration
mutation or user-selectable path/form/payload.

## Returned data

The ingress endpoint may return:

- App mode and timestamps;
- generic error category;
- node/online/offline/master counts;
- unique model, hardware, firmware and connection-type categories;
- aggregate controller CPU and memory percentages.

It never returns target address, usernames, passwords, cookies, tokens, names,
client records, node addresses or hardware identifiers.
