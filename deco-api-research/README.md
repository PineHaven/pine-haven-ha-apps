# Deco API Research App

Experimental Home Assistant App for bounded, read-only Stage 2 research.

Version 0.1.0 is a connection smoke probe. It is disarmed by default and cannot
contact a Deco until the operator supplies a target and credentials and sets
`probe_enabled` to `true`.

Because Deco owner login is exclusive, arming also requires an explicit session
acknowledgement. Version 0.1.0 performs one two-read cycle and then remains idle;
the normal Deco integration must be paused during that bounded cycle.

When armed, it performs only these authenticated API reads:

- mesh device inventory;
- controller CPU and memory performance.

The App never returns raw responses. Its ingress status endpoint contains only
counts, model/firmware categories and aggregate performance. Names, addresses,
hardware identifiers, cookies and credentials are discarded.

See [DOCS.md](DOCS.md) for the exact operating procedure and safety boundary.
