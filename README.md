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
- [FrogCoT](https://github.com/xznhj8129/frogcot)
- [FrogGeoLib](https://github.com/xznhj8129/froggeolib)
- [FrogTastic](https://github.com/xznhj8129/frogtastic)

### Usage:
- Define messages in the csv files
- run gen_definitions.py, generates .json and enums file
- payload.py defines enums of messages and packed binary enum values
- msglib.py defines usage and structure

## Message definitions
Central piece of the library is *parametric and flexible* definition and generation of protocol messages that are hierarchized and categorized; loaded at runtime without hard-coding and used simply with enums.\
Messages and payloads are defined in the CSV files in protocol/. Run gen_definitions.py to generate hivelink/protocol.py (ugly, WIP) from which the whole module will run on. Each enum represents a message and exposes a `.payload()` helper which validates and orders the fields.
**Messages not fixed, only for testing right now**
### Example message_definiton.csv:
| Category | Type | Subtype | FieldName | FieldType | FieldBitmask |
|----|--------|---------|-------|-----|-----|
|UAV|GenericTelemetry|FLIGHT|
||||FlightMode|enum|FALSE
||||StatusMask|int|TRUE
||||airspeed|int|FALSE
||||groundspeed|int|FALSE
||||heading|int|FALSE
||||msl_alt|int|FALSE
||||lat|int|FALSE
||||lat|int|FALSE

### Example payload_enums.csv
| Payload | Field | Value |
|---|---|---|
|FlightMode||3|
||_info| Generic Flight modes |
||ACRO|1|
||ANGLE|2|
||POSHOLD|3|
||NAV_WP|4|
||LOITER|5|
||CRUSE|6|
||RTH|7|
||LANDING|8|
||DISARMED|9|

### Example Usage:
```python
from hivelink.protocol import Messages

payload = Messages.Testing.System.TEXTMSG.payload(textdata=b"hello")
msgflags = BinaryFlag.ACK_REQUEST
msg = Messages.UAV.GenericTelemetry.FLIGHT
payload = msg.payload(
    FlightMode=PayloadEnum.FlightMode.LOITER,
    airspeed=int(ap.airspeed),
    groundspeed=int(ap.groundspeed),
    heading=int(ap.heading),
    msl_alt=int(ap.msl_alt),
    lat=int(ap.lat * 1e7),
    lon=int(ap.lat * 1e7),
)
encoded = encode_message(msg, payload)
```

## Protocol helpers
`msglib.py` contains helpers to create and parse messages:
- `encode_message` and `decode_message` work with the message enums and payload lists.
- `encode_udp_packet` and `decode_udp_packet` wrap messages for raw UDP links.
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