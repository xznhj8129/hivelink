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
- Meshtastic
- MeshCore*
- APRS*
- ???

## Requirements:
- [FrogCoT](https://github.com/xznhj8129/frogcot)
- [FrogGeoLib](https://github.com/xznhj8129/froggeolib)
- [FrogTastic](https://github.com/xznhj8129/frogtastic) (probably will change)

## Communications module:

### Usage:
- datalinks.py defines transport interface
- nodes.json is your network map

### Function:
- If message is sent throigh Meshtastic, the straight payload is sent as data to the app port, as Meshtastic already provides error checking and routing data such as sender, time, etc.
- If message is sent through UDP or other type of lower level protocol, payload is wrapped in a more structured packet

##### UDP Packet Structure
| sync byte | payload length | CRC16 | source id | destination id | payload |
|--|----|--------|---------|-------|-----|

### Link Configuration:
- **links_config.json** is node-specific provides information on it's identities, devices, addresses, keys, etc.
- **nodes.json** is pre-shared across nodes and provides network mapping, public keys, etc

### Nested MessageID Enum Tree:

Instead of a flat list, message identifiers are organized in a nested tree structure for ease of programming:

- **Telemetry:**  
  - `MessageID.Telemetry.POSITION`  
  - `MessageID.Telemetry.BATTERY`  
  - `MessageID.Telemetry.ATTITUDE`
- **Command:**  
  - `MessageID.Command.SET_MISSION`  
  - `MessageID.Command.SET_POSITION`  
  - `MessageID.Command.PHASE`
- **Routing:**  
  - `MessageID.Routing.HEARTBEAT`  
  - `MessageID.Routing.STATUS`

The `encode_message_id` function packs these components into a single 16-bit integer, and the `decode_message_id` function decodes it back into a tuple `(category, message type, subtype)`.


## Flight Control module:

### Usage:
- Define messages in message_definitions.csv (for now)
- run gen_definitions.py, generates .json and enums file
- payload_enums.py defines enums of packed binary enum values
- protocol.py defines usage and structure

### Test:
- right now just uses an INAV MSP flight controller, mavlink soon for primary focus