"""HiveLink OCCID payload encoding.

HiveLink is a delivery layer, not a second semantic or serialization system.
The payload placed inside a HiveLink delivery frame is therefore exactly the
canonical transient encoding produced by ``OCCIDModel.encode()``. Receivers use
``occid.decode_model()`` to recover the concrete model by its permanent OCCID
model ID.

Source/destination addressing and bearer mechanics belong to the HiveLink
delivery frame (see ``hivelink.datalinks``), not to an invented parallel
message ontology.
"""

from __future__ import annotations

from occid import OCCIDModel, decode_model


PROTOCOL_NAME = "hivelink-occid"
PROTOCOL_VERSION = (0, 0, 1)


def message_type(payload: OCCIDModel) -> str:
    """Return the human-readable OCCID model name for diagnostics only."""
    if not isinstance(payload, OCCIDModel):
        raise TypeError(f"expected OCCIDModel, got {type(payload).__name__}")
    return type(payload).__name__


def encode_message(payload: OCCIDModel) -> bytes:
    """Encode one OCCID model using OCCID's canonical transient wire profile."""
    if not isinstance(payload, OCCIDModel):
        raise TypeError(f"expected OCCIDModel, got {type(payload).__name__}")
    return payload.encode()


def decode_message(data: bytes) -> OCCIDModel:
    """Decode one canonical OCCID payload without prior knowledge of its type."""
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError(f"expected bytes-like payload, got {type(data).__name__}")
    return decode_model(bytes(data))


__all__ = [
    "PROTOCOL_NAME",
    "PROTOCOL_VERSION",
    "message_type",
    "encode_message",
    "decode_message",
]
