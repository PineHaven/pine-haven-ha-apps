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

## Operational ownership

PERIMETER has completed its controlled cutover and is now an operational
Zigbee2MQTT-owned network.

This App is therefore shipped with:

- `boot: auto`
- no MQTT username or password in Git
- no coordinator address in Git
- no Zigbee network key, PAN ID or extended PAN ID in Git
- no pre-seeded Zigbee database in Git

Runtime credentials, coordinator endpoint and preserved Zigbee-network identity
remain deployment/runtime configuration and are not stored in this repository.

### Critical single-owner rule

**Never run another Zigbee stack against the PERIMETER coordinator while this
Zigbee2MQTT instance owns it.**

In particular, do not re-enable or commission ZHA against the live PERIMETER
coordinator without a separately controlled ownership cutover.

## Runtime plan

Expected runtime data directory:

`/config/zigbee2mqtt_perimeter`

Expected MQTT base topic:

`ph_zb_perimeter`

Expected adapter family:

`zstack`

## Repository placement

Place this entire directory at the root of the existing Pine Haven Home Assistant Apps
repository, alongside `zigbee2mqtt-ambience/`.

No changes to the existing AMBIENCE App are required.
