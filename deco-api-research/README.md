# Deco API Research App

Experimental Home Assistant App for bounded, read-only Stage 2 research.

Version 0.5.x is a bounded radio-status probe. It is disarmed by default and cannot
contact a Deco until the operator supplies a target and credentials and sets
`probe_enabled` to `true`.

Because Deco owner login is exclusive, arming also requires an explicit session
acknowledgement. Version 0.5.x performs one four-read cycle and then remains idle;
the normal Deco integration must be paused during that bounded cycle.

When armed, it performs only these authenticated API reads:

- mesh device inventory;
- controller CPU and memory performance;
- current connected-client inventory.
- passive wireless channel and configured-width status.

The App never returns raw responses. Its ingress status endpoint contains only
counts, model/firmware categories, aggregate performance, anonymous client
connection/interface totals, anonymous backhaul/signal/internet health,
aggregate traffic/policy counts, and the names/types of fields present in each
response. Wireless output is limited to validated channel, width and automatic
selection values. Field values that could identify a person, client or node are
discarded. Unexpected telemetry strings are counted as unparsed and are never
returned.

The firmware's network-optimisation read is not used because it starts a scan
and writes temporary runtime state even though the wire operation is labelled
`read`.

See [DOCS.md](DOCS.md) for the exact operating procedure and safety boundary.
