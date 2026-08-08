# Pine Haven Zigbee2MQTT - AMBIENCE

A thin Home Assistant App definition for Pine Haven's AMBIENCE Zigbee network.

It deliberately uses the official stable Zigbee2MQTT pre-built image:
`ghcr.io/zigbee2mqtt/zigbee2mqtt-{arch}`

## Important
- This repository contains NO Pine Haven MQTT passwords, Zigbee network keys, PAN IDs, device databases or other secrets.
- Runtime configuration remains in Home Assistant.
- The existing AMBIENCE data path is `/config/zigbee2mqtt_ambience`.
- Never run this App at the same time as the old Zigbee2MQTT Edge App while both point at the AMBIENCE coordinator.
