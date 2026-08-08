# Future Pine Haven Apps

Recommended conventions:

| Purpose | Folder | App slug | Suggested data path | Suggested socat host port |
|---|---|---|---|---|
| AMBIENCE | zigbee2mqtt-ambience | zigbee2mqtt_ambience | /config/zigbee2mqtt_ambience | 8486 |
| PERIMETER | zigbee2mqtt-perimeter | zigbee2mqtt_perimeter | /config/zigbee2mqtt_perimeter | 8487 |

CORE should remain on the official Zigbee2MQTT Home Assistant App unless there is a later reason to move it.

For every additional Zigbee2MQTT instance:
1. Use a unique App slug.
2. Use a unique Zigbee2MQTT data path.
3. Use a unique MQTT base topic.
4. Use a dedicated coordinator.
5. Keep any exposed host ports unique.
6. Use the same upstream stable Zigbee2MQTT version across Pine Haven networks where practical.
7. Keep Home Assistant App auto-update disabled until release notes and compatibility have been reviewed.
