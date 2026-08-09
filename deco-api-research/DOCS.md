# FREE THE DECO - API Research

## Version 0.2.x contract

This experimental Home Assistant App is disarmed by default. When explicitly
enabled, it performs one bounded discovery cycle and then remains idle.

The authenticated capability set is fixed in source:

| Capability | Form | Operation |
|---|---|---|
| Mesh inventory | `device_list` | `read` |
| Controller performance | `performance` | `read` |
| Connected-client summary | `client_list` | `read` |

There is no generic endpoint runner or user-selectable payload. Source
guardrails fail if a wire operation other than protocol login or read is added.

The status endpoint returns only aggregate mesh health, version categories,
controller load, and anonymous client connection/interface totals. Individual
client and node records are not exposed.
