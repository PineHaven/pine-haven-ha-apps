# Changelog

## 2.0.0

- Add a separate experimental Home Assistant App for one physically isolated
  Deco M9 Plus.
- Require a one-node controller identity match before control can be armed.
- Require the exact lab firmware to be read and separately acknowledged as
  write-compatible; do not inherit compatibility from the production mesh.
- Admit one fixed channel 11 / HT20 experiment per App start.
- Capture, restore and verify a recognized channel/width baseline automatically.
- Keep writes disabled by default and expose no generic API runner.
