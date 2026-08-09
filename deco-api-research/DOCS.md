# FREE THE DECO - API Research

## Version 0.4.x contract

This experimental Home Assistant App is disarmed by default. When explicitly
enabled, it performs one bounded discovery cycle and then remains idle.

The authenticated capability set remains fixed at three `read` operations:
mesh inventory, controller performance, and connected-client summary. There is
no generic endpoint runner or user-selectable payload.

The status endpoint returns aggregate mesh/client information, a values-free
schema map, anonymous backhaul/signal/internet health, and aggregate
traffic/policy counts. Individual field values and raw records are not exposed.
Unexpected telemetry strings are counted as unparsed and are never returned.

Traffic and backhaul numbers retain the firmware's native units because the
response does not declare a unit.
