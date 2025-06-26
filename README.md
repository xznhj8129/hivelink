# Flexible mesh network UAV communication library
The protocol is built for autonomous drone swarming where each node (drone or ground station) communicates over a variety of mesh networked high (e.g., 802.11s) and low-bandwidth link (e.g., LoRa).\
Uses defined protocol and msgpack to send data over flexible links\
Significantly simplified and integrated with my other libraries\

**Warnings:**
- Not even pre-alpha, barely proof of concept, this will be in flux constantly
- Protocol messages not even slightly close to decided, basically just fluff to test functions
- Use this only in simulator!

## Planned Features:
- Mesh/Swarm Architecture: Explicit support for routing in a multi-hop mesh network
- Uses Msgpack for simple binary packing and maximum byte efficiency
- Cursor-on-Target (CoT) Support: Dedicated support for CoT
- Optional Authentification and Security
- MAVLink and MSP support

## Supported (*soon) Transport Layers:
- UDP Uni/Multicast
- TCP
- Meshtastic
- APRS*
- ???

## Requirements:
- [FrogCoT](https://github.com/xznhj8129/frogcot)
- [FrogGeoLib](https://github.com/xznhj8129/froggeolib)
- [FrogTastic](https://github.com/xznhj8129/frogtastic) (probably will change)

### Usage:
- Define messages in the csv files
- run gen_definitions.py, generates .json and enums file
- payload.py defines enums of messages and packed binary enum values
- msglib.py defines usage and structure

## Message definitions
Messages and payloads are defined in the CSV files in protocol/. Run gen_definitions.py to generate hivelink/protocol.py from which the whole module will run on. Each enum represents a message and exposes a `.payload()` helper which validates and orders the fields.

Example:
```python
from hivelink.protocol import Messages

payload = Messages.Testing.System.TEXTMSG.payload(textdata=b"hello")
```

## Protocol helpers
`msglib.py` contains helpers to create and parse messages:
- `encode_message` and `decode_message` work with the message enums and payload lists.
- `encode_udp_packet` and `decode_udp_packet` wrap messages for raw UDP links.
- `messageid` / `message_str_from_id` convert between enums and integer IDs.

##### UDP Packet Structure
| sync byte | payload length | CRC16 | source id | destination id | payload |
|--|----|--------|---------|-------|-----|

### Link Configuration:
- **links_config.json** is node-specific provides information on it's identities, devices, addresses, keys, etc.
- **nodes.json** is pre-shared across nodes and provides network mapping, public keys, etc

## Datalinks
`datalinks.py` provides the `DatalinkInterface` which hides the underlying transport. Node information such as IDs and
IP addresses is loaded from `nodes.json`.

Basic usage: TODO
Call `link.receive()` to read incoming messages and `link.stop()` when finished.

## Example nodes
- `test_node.py` – simple terminal chat using udp, multicast or Meshtastic.
- `test_node_controller.py` – ground station style receiver for telemetry/commands.
- `test_uav.py` – sends INAV telemetry using `unavlib`.

These demonstrate how the protocol and datalink layers fit together.
## Flight Control module:

### Test:
- right now just uses an INAV MSP flight controller, mavlink soon for primary focus