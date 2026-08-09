# FREE THE DECO - API Research

## Version 0.3.x contract

This experimental Home Assistant App is disarmed by default. When explicitly
enabled, it performs one bounded discovery cycle and then remains idle.

The authenticated capability set remains fixed at three `read` operations:
mesh inventory, controller performance, and connected-client summary. There is
no generic endpoint runner or user-selectable payload.

The status endpoint returns aggregate mesh/client information plus a values-free
schema map. The schema map contains only top-level response field names and
broad types such as string, number, boolean, object, array, or null. Individual
field values and raw records are not exposed.
