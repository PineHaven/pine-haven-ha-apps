# FREE THE DECO

Pine Haven's local-first TP-Link Deco mesh monitor and Stage 2 research platform.

Version 1.1 hardens the primary Home Assistant App for Deco telemetry. It polls a
fixed four-read allowlist, renders a responsive Ingress dashboard, and registers
sanitized mesh-health entities and logical devices with MQTT Device Discovery.
It is still read-only: no Deco setting or generic API operation is available.

The live monitor reports:

- each named Deco's online, internet, backhaul and signal state;
- mesh totals and controller CPU/memory load;
- anonymous connected-client totals by band and network interface;
- current Wi-Fi channels and configured widths;
- read, session and Home Assistant publishing health;
- freshness, poll timing, cycle counters, recovery state and safe error categories;
- explicit queued, running, succeeded and failed manual-refresh states.

Discovery preserves the established `free_the_deco_*` entity IDs. Display aliases
such as Workshop and Gym change presentation only; they do not rename entities.
Discovery identifiers are logical App identifiers and never hardware identifiers.

Client names, client addresses, SSIDs, Wi-Fi passwords, BSSIDs, node MACs and raw
API replies are never exposed or published. Node display names are permitted only
inside the authenticated local Ingress UI and Home Assistant telemetry.

Because the Deco owner login is exclusive, continuous monitoring must not run at
the same time as another Deco integration using that login. Enabling the monitor
therefore still requires an explicit session acknowledgement.

Home Assistant masks the password in the App configuration form, and FREE THE
DECO never logs, renders or publishes it. An authenticated Home Assistant
administrator may still be able to retrieve stored App options through management
APIs. Keep administrator access tightly controlled and follow the coordinated
credential-rotation procedure in [DOCS.md](DOCS.md) after diagnostic work.

The firmware's network-optimisation read remains excluded because it starts a scan
and writes temporary runtime state even though its wire operation is labelled
`read`.

See [DOCS.md](DOCS.md) for the operating and safety contract.
