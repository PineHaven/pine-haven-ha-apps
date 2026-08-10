# FREE THE DECO

Pine Haven's local-first TP-Link Deco mesh monitor and Stage 2 research platform.

Version 1.0 promotes the former bounded research probe into the primary Home
Assistant App for Deco telemetry. It polls a fixed four-read allowlist, renders a
self-contained Ingress dashboard, and publishes sanitized mesh-health entities to
Home Assistant. It is still read-only: no Deco setting or generic API operation is
available.

The live monitor reports:

- each named Deco's online, internet, backhaul and signal state;
- mesh totals and controller CPU/memory load;
- anonymous connected-client totals by band and network interface;
- current Wi-Fi channels and configured widths;
- last successful poll, publishing health and safe error categories.

Client names, client addresses, SSIDs, Wi-Fi passwords, BSSIDs, node MACs and raw
API replies are never exposed or published. Node display names are permitted only
inside the authenticated local Ingress UI and Home Assistant telemetry.

Because the Deco owner login is exclusive, continuous monitoring must not run at
the same time as another Deco integration using that login. Enabling the monitor
therefore still requires an explicit session acknowledgement.

The firmware's network-optimisation read remains excluded because it starts a scan
and writes temporary runtime state even though its wire operation is labelled
`read`.

See [DOCS.md](DOCS.md) for the operating and safety contract.
