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

A static node map and direct packet send/receive are a permanent supported baseline. 802.11s, BATMAN, HaLow, additional radio bearers, LTE, Starlink, VPNs, multi-bearer policy, constrained profiles, fragmentation, store-and-forward, and other communications work may be added behind the same interface without changing application semantics above it.

**OCCID is the data model. HiveLink is delivery.** HiveLink does not define a competing command/state/network ontology. Operationally meaningful link, node, network, topology, reachability, quality, delivery, and communications observations are represented with OCCID models when another component needs to know, store, display, or reason about them.

HiveLink is still experimental. The direct-IP baseline is deliberately kept small so applications do not need the entire communications roadmap merely to use the correct boundary.

## OCCID wire payload

HiveLink does not wrap OCCID in a second class-name schema.

```python
from hivelink.protocol import encode_message, decode_message
from occid import AddressKind, NetworkAddress

payload = NetworkAddress(kind=AddressKind.IPV4, value="192.168.0.230", port=5555)
encoded = encode_message(payload)   # OCCIDModel.encode()
decoded = decode_message(encoded)   # occid.decode_model()
assert type(decoded) is NetworkAddress
```

The payload inside a HiveLink frame is exactly OCCID's canonical transient encoding: schema version, permanent model ID, and named fields.

HiveLink delivery addressing remains in the HiveLink bearer frame. For UDP the current frame is:

| payload length | CRC16 | source node | destination node | OCCID payload |
|---|---|---|---|---|

That addressing is delivery machinery, not a replacement for OCCID `Node`, `NetworkAddress`, `Link`, `DeliveryReceipt`, or other communications models.

## Minimal direct-IP use

`DatalinkInterface` is asynchronous because receivers run on the caller's event loop:

```python
import asyncio

from hivelink.datalinks import DatalinkInterface
from occid import AddressKind, NetworkAddress


async def main():
    link = DatalinkInterface(
        use_udp=True,
        socket_host="192.168.0.220",
        socket_port=5555,
        my_name="control",
        nodemap={
            "control": {"ip": ["192.168.0.220", 5555]},
            "uav1": {"ip": ["192.168.0.230", 5555]},
        },
    )
    link.start()
    try:
        payload = NetworkAddress(
            kind=AddressKind.IPV4,
            value="192.168.0.230",
            port=5555,
        )
        link.send_model(payload, "uav1")
        await asyncio.sleep(0.1)
        for message in link.receive_models():
            print(message["from"], type(message["model"]).__name__)
    finally:
        link.stop()


asyncio.run(main())
```

## Implemented bearers

- direct UDP unicast;
- UDP multicast;
- Meshtastic when the optional `frogtastic` dependency is installed.

The default package install contains only the direct core. Optional extras are explicit:

```bash
pip install -e .[meshtastic]
pip install -e .[cli]
pip install -e .[all]
```

Reference IP deployments can install only the direct core.

## Relationship to consuming systems

HiveLink is an independent delivery layer for OCCID traffic between control systems and independently deployed nodes. It is not owned by a particular consuming application.

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

## Example

`example_node.py` is the maintained interactive OCCID node example for direct UDP, with optional Meshtastic use when that extra is installed. Install the `cli` extra to run it.
