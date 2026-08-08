# Updating the Pine Haven Zigbee2MQTT wrappers

The App definition pins the Home Assistant App version to the official stable Zigbee2MQTT App release.

Before changing the version:
1. Check the official Zigbee2MQTT Home Assistant App `zigbee2mqtt/config.json`.
2. Review upstream release notes and migration notes.
3. Compare the full upstream App definition, not just the version number, in case the schema, mappings, permissions or image name changed.
4. Update this repository's matching App definitions.
5. Commit the change to GitHub.
6. Refresh the Home Assistant App Store.
7. Upgrade one Pine Haven network at a time, with a current Home Assistant backup.
8. Verify coordinator IEEE address, channel, PAN IDs, MQTT base topic, devices and groups after startup.
