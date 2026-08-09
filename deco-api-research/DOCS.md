# FREE THE DECO - API Research

## Version 0.5.x contract

This experimental Home Assistant App is disarmed by default. When explicitly
enabled, it performs one bounded discovery cycle and then remains idle.

The authenticated capability set is fixed at four `read` operations: mesh
inventory, controller performance, connected-client summary, and passive
wireless status. There is no generic endpoint runner or user-selectable payload.

The wireless reply is reduced to validated channel, configured-width and
automatic-selection values. SSIDs, passwords, BSSIDs and all other raw wireless
fields are discarded. Firmware analysis found that the separate
network-optimisation read starts a scan and writes temporary state, so that call
is intentionally not present.

The status endpoint returns aggregate mesh/client information, a values-free
schema map, anonymous backhaul/signal/internet health, and aggregate
traffic/policy counts. Individual field values and raw records are not exposed.
Unexpected telemetry strings are counted as unparsed and are never returned.

Backhaul speeds are reported in megabits per second, matching the upstream
integration's sensor definition. Traffic numbers retain the firmware's native
units because the response does not declare one.
