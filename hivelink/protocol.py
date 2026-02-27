"""Hivelink protocol runtime bindings built from frogproto JSON schema."""

from pathlib import Path
from frogproto import load

_PROTOCOL_PATH = Path(__file__).resolve().parent.parent / "protocol.json"

# Load the repo's protocol definition (call load(...) yourself to override)
Proto = load(_PROTOCOL_PATH)

MessageCategory = Proto.MessageCategory
Messages = Proto.msg
PayloadEnum = Proto.enum
PROTOCOL_NAME = Proto.name
PROTOCOL_VERSION = Proto.version

__all__ = [
    "Proto",
    "MessageCategory",
    "Messages",
    "PayloadEnum",
    "PROTOCOL_NAME",
    "PROTOCOL_VERSION",
]
