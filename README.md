# HiveLink

> **VERSION: `0.0.1`.** HiveLink package/protocol version remains independent of OCCID schema evolution.

HiveLink delivers OCCID between independently deployed nodes.

**OCCID is the data model. HiveLink is delivery.** HiveLink does not define a competing command/state/network ontology and does not own OCCID structural compatibility.

## Minimum useful deployment

The smallest valid deployment is intentionally boring:

```text
control node <---- direct UDP/IP ----> field/autonomous node
```

A static node map plus direct packet send/receive is a permanent supported baseline. More advanced underlays/bearers - 802.11s, BATMAN, HaLow, Meshtastic/LoRa, LTE, satellite, VPNs, multi-bearer policy, constrained profiles, fragmentation, store-and-forward, etc. - may evolve behind the same application boundary.

Applications above HiveLink should not change semantic behavior merely because the bearer changes.

## OCCID payload

HiveLink does not wrap OCCID in a second class-name schema.

```python
from hivelink.protocol import encode_message, decode_message
from occid import AddressKind, NetworkAddress

payload = NetworkAddress(kind=AddressKind.IPV4, value="192.0.2.10", port=5555)
encoded = encode_message(payload)
decoded = decode_message(encoded)
assert type(decoded) is NetworkAddress
```

The payload inside a HiveLink frame is OCCID's transient encoding:

```text
{
  model_id,
  fields
}
```

The permanent model ID identifies the concrete OCCID model. Structural compatibility belongs to each consumer's generated `OCCID_CONTRACT`; no OCCID schema version is carried in every HiveLink payload.

HiveLink source/destination addressing remains in the delivery frame. That delivery addressing is machinery, not a replacement for OCCID `Node`, `NetworkAddress`, `Link`, delivery evidence, or other operational communications models.

## Direct-IP use

`DatalinkInterface` is asynchronous because receivers run on the caller's event loop:

```python
import asyncio

from hivelink.datalinks import DatalinkInterface
from occid import AddressKind, NetworkAddress

async def main():
    link = DatalinkInterface(
        use_udp=True,
        socket_host="127.0.0.1",
        socket_port=5555,
        my_name="control",
        nodemap={
            "control": {"ip": ["127.0.0.1", 5555]},
            "uav1": {"ip": ["127.0.0.1", 5556]},
        },
    )
    link.start()
    try:
        link.send_model(
            NetworkAddress(kind=AddressKind.IPV4, value="127.0.0.1", port=5556),
            "uav1",
        )
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

Optional extras are explicit:

```bash
pip install -e .[meshtastic]
pip install -e .[cli]
pip install -e .[all]
```

Reference IP deployments can install only the direct core.

## Relationship to consuming systems

HiveLink is independent delivery infrastructure, not owned by Sigma or MPFC.

For an autonomous MPFC node:

```text
Sigma / control
    -> OCCID
    -> HiveLink
    -> network
    -> HiveLink
    -> MPFC
    -> private node-local IPC
    -> local execution / endpoint adapters
```

MPFC's MQTT broker is private local IPC. Exposing the broker or its topic names to Sigma bypasses the intended HiveLink boundary.

The normal Conqueror Frog Block 1 direct-IP path has been empirically exercised end to end. Advanced communications work remains independent and must not become a prerequisite for unrelated application capability.

## Example

`example_node.py` is the maintained interactive OCCID node example for direct UDP, with optional Meshtastic use when that extra is installed. Install the `cli` extra to run it.
