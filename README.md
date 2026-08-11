# Pine Haven Home Assistant Apps

Private-purpose Home Assistant App definitions used at Pine Haven.

The repository is designed to hold multiple independently installable Home Assistant Apps while keeping runtime secrets and household configuration OUT of GitHub.

## Current Apps
- `zigbee2mqtt-ambience` — stable Zigbee2MQTT wrapper for PH-ZB-HOUSE-AMBIENCE.
- `deco-api-research` — stable, read-only TP-Link Deco monitor with Home Assistant MQTT Device Discovery.
- `deco-control-lab` — experimental, fail-closed channel/width laboratory for one physically isolated Deco.

## Planned naming pattern
Future Apps should each live in their own root-level folder, for example:
- `zigbee2mqtt-perimeter`
- other Pine Haven custom Apps as required

Each App must have its own unique `slug`.

## Security rule
Never commit:
- MQTT usernames/passwords
- Zigbee network keys
- PAN IDs / Extended PAN IDs
- Zigbee2MQTT `database.db`
- Home Assistant backups
- Home Assistant `secrets.yaml`
- live configuration files containing credentials

The Zigbee2MQTT wrappers use the official Zigbee2MQTT container image. This repository only supplies Home Assistant App metadata.

## Deco research App boundary

The public `deco-api-research` folder contains only the sanitized, installable App and its tests. Private experiment records, raw responses, credentials, device identifiers and Pine Haven network details remain outside this repository.
