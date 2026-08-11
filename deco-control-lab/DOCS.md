# Operating contract

## First deployment: read-only identity proof

1. Factory-reset a spare M9 Plus and create a separate one-node Deco network.
2. Connect only its WAN/uplink Ethernet to the existing LAN.
3. Configure `host`, `production_host`, credentials and `expected_mac`.
4. Set `lab_enabled` and `isolated_single_node_acknowledged` true.
5. Keep `firmware_write_compatibility_acknowledged` and `writes_enabled` false.
6. Start the App and open Ingress. Continue only if identity is `VERIFIED`, the
   node count is one, controller role is true, and channel/width are recognized.

## Write gate

First compare the reported lab firmware with the firmware-derived write contract.
Only after that review may `firmware_write_compatibility_acknowledged` and
`writes_enabled` be changed as a separate operational decision. The App must be
restarted after the options change. The Ingress action then permits one fixed
channel 11 / HT20 transaction and one automatic rollback transaction using the
immediate pre-change values.

The App's sanitized audit is in-memory and contains only timestamps, action
categories, result categories, channel and recognized width. It never contains
credentials, SSIDs, raw responses, IPs or complete hardware identifiers.

## Recovery

If rollback cannot be verified, stop further API work. Keep the spare isolated,
inspect it through the Deco app, and factory-reset it if required. A production
mesh must never be used to recover or validate this lab package.
