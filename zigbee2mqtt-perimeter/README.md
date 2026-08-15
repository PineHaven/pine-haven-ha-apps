# Pine Haven Zigbee2MQTT - PERIMETER

A thin Home Assistant App definition for Pine Haven's **PERIMETER** Zigbee network.

It deliberately uses the official stable Zigbee2MQTT pre-built image:

`ghcr.io/zigbee2mqtt/zigbee2mqtt-{arch}`

## Intended Pine Haven role

`PH-ZB-PERIMETER` owns:

- Pine Haven exterior / estate Zigbee lighting and related exterior Zigbee devices
- Gym Zigbee devices
- Workshop Zigbee devices

Main-house CORE or AMBIENCE devices do **not** belong on this network.

## Safety design

This App is deliberately shipped with:

- `boot: manual`
- no MQTT username or password
- no coordinator address
- no Zigbee network key, PAN ID or extended PAN ID
- no pre-seeded Zigbee database

This means committing/installing the App does **not** by itself take control of a Zigbee radio.

### Critical rule

**Never start this App while ZHA is still using the PERIMETER coordinator.**

The live PERIMETER coordinator is currently owned by ZHA. The actual coordinator and
preserved Zigbee-network identity are configured only during the controlled cutover.

## Runtime plan

Expected runtime data directory:

`/config/zigbee2mqtt_perimeter`

Expected MQTT base topic:

`ph_zb_perimeter`

Expected adapter family:

`zstack`

The coordinator endpoint, MQTT credentials, and preserved Zigbee network identity are
intentionally configured at deployment/cutover time rather than stored in this repository.

## Repository placement

Place this entire directory at the root of the existing Pine Haven Home Assistant Apps
repository, alongside `zigbee2mqtt-ambience/`.

No changes to the existing AMBIENCE App are required.
