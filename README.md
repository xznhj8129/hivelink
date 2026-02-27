# HiveLink Flexible mesh network communication library
The protocol is built for autonomous drone swarming where each node (drone, robot or ground station) communicates over a variety of mesh networked high (e.g., 802.11s) and low-bandwidth link (e.g., LoRa).\
Uses defined protocol and msgpack to send data over flexible links\
Significantly simplified and integrated with my other libraries\

**Warnings:**
- Not even pre-alpha, barely proof of concept, this will be in flux constantly
- Protocol messages not even slightly close to decided, basically just fluff to test functions
- Use this only in simulator!

## Planned Features:
- ☑ Uses Msgpack for simple binary packing and maximum byte efficiency
- ☑ MQTT support
- ☐ Cursor-on-Target (CoT) support: Dedicated support for transparent CoT routing
- ☐ MAVLink and MSP support
- ☐ Mesh/Swarm Architecture: Explicit support for routing in a multi-hop mesh network

## Supported (*soon) Transport Layers:
- ☑ UDP Uni/Multicast
- ☑ TCP
- ☑ Meshtastic
- ☐ APRS

## Requirements:
- [FrogGeoLib](https://github.com/xznhj8129/froggeolib)
- [FrogTastic](https://github.com/xznhj8129/frogtastic)
- [FrogProto](https://github.com/xznhj8129/frogproto)

### Usage:
- Define messages in `protocol.json` (root of this repo).
- On import, `hivelink.protocol` loads that JSON via frogproto’s runtime; call `frogproto.load("<path>")` yourself to point at a different schema if needed.
- `frogproto/msglib.py` defines encoding/decoding helpers; Hivelink re-exports the loaded enums in `hivelink.protocol`.

## Message definitions
Central piece of the library is *parametric and flexible* definition and generation of protocol messages that are hierarchized and categorized; loaded at runtime without hard-coding and used simply with enums.\
Messages and payload enums live in `protocol.json`. Each enum represents a message and exposes a `.payload()` helper which validates and orders the fields.
**Messages not fixed, only for testing right now**

### Example Usage:
```python
import hivelink
from hivelink.protocol import Proto, Messages, PayloadEnum

msg = Messages.Testing.System.TEXTMSG(textdata="hello")
encoded = msg.encode()
enum_member, decoded = Proto.decode_message(encoded)
print(Proto.message_str_from_id(Proto.messageid(enum_member)), decoded)
```

## Protocol helpers
`frogproto/msglib.py` contains helpers to create and parse messages:
- `encode_message` and `decode_message` work with the message enums and payload lists.
- `messageid` / `message_str_from_id` convert between enums and integer IDs.

##### UDP Packet Structure
| payload length | CRC16 | source id | destination id | payload |
|----|--------|---------|-------|-----|

### Link Configuration:
- **links_config.json** is node-specific provides information on it's identities, devices, addresses, keys, etc.
- **nodes.json** is pre-shared across nodes and provides network mapping, public keys, etc

## Datalinks
`datalinks.py` provides the `DatalinkInterface` which hides the underlying transport. Node information such as IDs and
IP addresses is loaded from `nodes.json`.

Basic usage: TODO
Call `link.receive()` to read incoming messages and `link.stop()` when finished.

## Example nodes
- `example_node.py` – simple terminal chat using udp, multicast or Meshtastic.
- `example_mavlink_uav.py` – Mavlink integration
- `example_msp_uav.py` – MSP integration
- `example_uav_controller.py` – ground station style receiver for telemetry/commands.
