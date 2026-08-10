# HiveLink

HiveLink delivers OCCID between independently deployed nodes.

The smallest valid deployment is intentionally boring:

```text
control     192.168.0.220:5555
    |
    | direct UDP/IP
    v
autonomous  192.168.0.230:5555
```

A static node map and direct packet send/receive are a permanent supported baseline. 802.11s, BATMAN, HaLow, Meshtastic, LTE, Starlink, VPNs, multiple bearers, constrained profiles, path policy, fragmentation, store-and-forward, and other communications work may be added behind the same interface without changing the application semantics above it.

**OCCID is the data model. HiveLink is delivery.** HiveLink does not define a competing command/state/network ontology. Operationally meaningful link, node, network, topology, reachability, quality, delivery, and communications observations are represented with OCCID models when another component needs to know, store, display, or reason about them.

HiveLink is still experimental and its advanced delivery machinery will remain in flux. The direct-IP baseline is deliberately kept small so applications do not need the entire communications roadmap merely to use the correct boundary.

## OCCID wire payload

HiveLink does not wrap OCCID in a second class-name schema.

```python
from hivelink.protocol import encode_message, decode_message
from occid import HumanTextMessage

payload = HumanTextMessage(
    sender_id="node1",
    destination_id="node2",
    message="hello",
    targets=[],
)

encoded = encode_message(payload)   # OCCIDModel.encode()
decoded = decode_message(encoded)   # occid.decode_model()
assert type(decoded) is HumanTextMessage
```

The payload inside a HiveLink frame is exactly OCCID's canonical transient encoding: schema version, permanent model ID, and named fields.

HiveLink delivery addressing remains in the HiveLink bearer frame. For UDP the current frame is:

| payload length | CRC16 | source node | destination node | OCCID payload |
|---|---|---|---|---|

That addressing is delivery machinery, not a replacement for OCCID `Node`, `NetworkAddress`, `Link`, `DeliveryReceipt`, or other communications models.

## Minimal direct-IP use

`DatalinkInterface` hides the bearer. A node map can be as small as:

```json
{
  "control": {"ip": ["192.168.0.220", 5555]},
  "uav1": {"ip": ["192.168.0.230", 5555]}
}
```

Then:

```python
from hivelink.datalinks import DatalinkInterface

link = DatalinkInterface(
    use_udp=True,
    socket_host="0.0.0.0",
    socket_port=5555,
    my_name="control",
    nodemap={
        "control": {"ip": ["192.168.0.220", 5555]},
        "uav1": {"ip": ["192.168.0.230", 5555]},
    },
)

link.start()
link.send_model(payload, "uav1")

for message in link.receive_models():
    print(message["from"], type(message["model"]).__name__)
```

`frogtastic` is only required when the Meshtastic bearer is actually enabled. A direct UDP/IP installation does not require it.

## Bearers

Current/experimental bearer surfaces include:

- direct UDP unicast;
- UDP multicast;
- Meshtastic;
- MQTT gateway/bearer integration.

These are HiveLink implementation choices. An OCCID-native application should address a HiveLink node and send OCCID rather than select a vehicle protocol or inspect another process's private IPC.

## Relationship to Conqueror Frog

Conqueror Frog is a HiveLink client, not the owner of HiveLink's communications roadmap.

For an autonomous MPFC node the intended boundary is:

```text
Sigma / control system
    -> OCCID
    -> HiveLink
    -> network
    -> HiveLink
    -> MPFC node-local OCCID bridge
    -> MPFC private IPC
    -> local execution / endpoint adapters
```

MPFC's MQTT bus is private node-local IPC. Exposing that broker or its topic names to Sigma bypasses HiveLink and is not the OCCID-native system interface.

## Examples

`example_node.py` is the small interactive node example. Older MAVLink/INAV direct-control examples are historical integration experiments; they are not the architecture for OCCID-native autonomous tasking and should not be treated as Conqueror Frog control-path examples.
