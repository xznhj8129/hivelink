# HiveLink Flexible mesh network communication library

Hivelink is a transport layer for autonomous nodes over mesh networked high-bandwidth links such as 802.11s and low-bandwidth links such as LoRa/Meshtastic.

Protocol data is OCCID. Hivelink wraps an OCCID `MessageEnvelope` and one OCCID schema payload in msgpack, then sends those bytes over UDP, multicast, Meshtastic, or MQTT.

**Warnings:**
- Not even pre-alpha, barely proof of concept, this will be in flux constantly
- Use this only in simulator!

## Planned Features
- ☑ Uses Msgpack for simple binary packing and maximum byte efficiency
- ☑ MQTT support
- ☐ Cursor-on-Target (CoT) support: Dedicated support for transparent CoT routing
- ☐ MAVLink and MSP support
- ☐ Mesh/Swarm Architecture: Explicit support for routing in a multi-hop mesh network

## Supported (*soon) Transport Layers
- ☑ UDP Uni/Multicast
- ☑ TCP
- ☑ Meshtastic
- ☐ APRS

## Requirements
- OCCID schema package from `../occid/schema`
- [FrogGeoLib](https://github.com/xznhj8129/froggeolib)
- [FrogTastic](https://github.com/xznhj8129/frogtastic)

## Protocol Usage

```python
from hivelink.protocol import build_envelope, encode_message, decode_message
from occid.schema import HumanTextMessage

payload = HumanTextMessage(sender_id="node1", destination_id="node2", message="hello")
encoded = encode_message(build_envelope(payload, src="node1", dst="node2"), payload)
envelope, decoded = decode_message(encoded)
print(envelope.msg_type, decoded.message)
```

Common payloads:
- `HumanTextMessage` for text chat.
- `NodeHeartbeat` for online/presence.
- `VehicleCommand` for vehicle control commands.
- `LocationState`, `FlightControlState`, and `TelemetryState` for vehicle state.
- OCCID task models for tasking.

## UDP Packet Structure
| payload length | CRC16 | source id | destination id | payload |
|----|--------|---------|-------|-----|

The UDP payload is the msgpack OCCID message from `hivelink.protocol.encode_message`.

## Link Configuration
- **links_config.json** is node-specific and provides identities, devices, addresses, keys, etc.
- **nodes.json** is pre-shared across nodes and provides network mapping, public keys, etc.

## Datalinks
`datalinks.py` provides the `DatalinkInterface` which hides the underlying transport. Node information such as IDs and
IP addresses is loaded from `nodes.json`.

Call `link.receive()` to read incoming messages and `link.stop()` when finished.

## Example Nodes
- `example_node.py` - simple terminal chat using UDP, multicast or Meshtastic.
- `example_mavlink_uav.py` - MAVLink integration.
- `example_inav_uav.py` - INAV/MSP integration.
- `example_controller.py` - ground station style receiver for telemetry/commands.
