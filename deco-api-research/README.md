# Deco API Research App

Experimental Home Assistant App for bounded, read-only Stage 2 research.

Version 0.3.x is a bounded schema-discovery probe. It is disarmed by default and cannot
contact a Deco until the operator supplies a target and credentials and sets
`probe_enabled` to `true`.

Because Deco owner login is exclusive, arming also requires an explicit session
acknowledgement. Version 0.3.x performs one three-read cycle and then remains idle;
the normal Deco integration must be paused during that bounded cycle.

When armed, it performs only these authenticated API reads:

- mesh device inventory;
- controller CPU and memory performance;
- current connected-client inventory.

The App never returns raw responses. Its ingress status endpoint contains only
counts, model/firmware categories, aggregate performance, anonymous client
connection/interface totals, and the names/types of fields present in each
response. Field values that could identify a person, client or node are
discarded.

See [DOCS.md](DOCS.md) for the exact operating procedure and safety boundary.
