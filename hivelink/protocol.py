"""Hivelink OCCID message encoding.

Usage:
python3 - <<'PY'
from hivelink.protocol import build_envelope, encode_message, decode_message
from occid.schema import HumanTextMessage

payload = HumanTextMessage(sender_id="node1", destination_id="node2", message="hello")
packet = encode_message(build_envelope(payload, src="node1", dst="node2"), payload)
envelope, decoded = decode_message(packet)
print(envelope.msg_type, decoded.message)
PY
"""

from time import time
from uuid import uuid4

import msgpack
import occid.schema as occid_schema
from occid.schema import MessageEnvelope, OCCIDModel


PROTOCOL_NAME = "hivelink-occid"
PROTOCOL_VERSION = (1, 0, 0)

PAYLOAD_MODELS: dict[str, type[OCCIDModel]] = {
    name: model
    for name in occid_schema.__all__
    for model in [getattr(occid_schema, name)]
    if OCCIDModel in getattr(model, "__mro__", ()) and model is not OCCIDModel
}


def message_type(payload: OCCIDModel) -> str:
    return payload.__class__.__name__


def build_envelope(
    payload: OCCIDModel,
    src: str,
    dst: str,
    *,
    msg_id: str | None = None,
    ts: float | None = None,
    **kwargs,
) -> MessageEnvelope:
    return MessageEnvelope(
        msg_id=msg_id if msg_id is not None else uuid4().hex,
        msg_type=message_type(payload),
        src=src,
        dst=dst,
        ts=ts if ts is not None else time(),
        **kwargs,
    )


def encode_message(envelope: MessageEnvelope, payload: OCCIDModel) -> bytes:
    packet = {
        "envelope": envelope.model_dump(mode="json", exclude_none=True),
        "payload": payload.model_dump(mode="json", exclude_none=True),
    }
    return msgpack.packb(packet, use_bin_type=True)


def decode_message(data: bytes) -> tuple[MessageEnvelope, OCCIDModel]:
    packet = msgpack.unpackb(data, raw=False)
    envelope = MessageEnvelope.model_validate(packet["envelope"])
    payload_model = PAYLOAD_MODELS[envelope.msg_type]
    payload = payload_model.model_validate(packet["payload"])
    return envelope, payload


__all__ = [
    "PROTOCOL_NAME",
    "PROTOCOL_VERSION",
    "PAYLOAD_MODELS",
    "message_type",
    "build_envelope",
    "encode_message",
    "decode_message",
]
