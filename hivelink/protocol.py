import struct
import time
import json
from typing import List, Dict, Tuple, Optional, Any
from enum import Enum, IntEnum, auto, IntFlag
import msgpack
from .message_structure import * #leave as *
from .payload_enums import *
import crcmod

type_mapping = {
    "int": int,
    "float": float,
    "string": str,
    "bool": bool,
    "enum": IntEnum,
    "bytes": bytes,
}

bin_type_map = {
    "enum": "B",
    "uint8_t": "B",
    "uint16_t": "H",
    "uint32_t": "I",
    "uint64_t": "Q",
    "int8_t": "b",
    "int16_t": "h",
    "int32_t": "i",
    "int64_t": "q",
    "float": "f",
    "double": "d",
    "char": "c",
    "bool": "?"
}


class MessageDefinitions:
    def __init__(self):
        """Loads the pre-generated JSON into messages."""
        with open("message_definitions.json") as f:
            self.messages = json.load(f)

def messageid(msg):
    """Extracts category, subcategory, and message values from a message enum."""
    enum_class = msg.__class__
    qualname = enum_class.__qualname__
    parts = qualname.split('.')
    if len(parts) != 3 or parts[0] != 'Messages':
        raise ValueError("Invalid message enum")
    category_name = parts[1]
    subcategory_name = parts[2]
    category_enum = getattr(MessageCategory, category_name)
    category_value = category_enum.value
    category_class = getattr(Messages, category_name)
    subcategory_class = getattr(category_class, subcategory_name)
    subcategory_value = subcategory_class.value_subcat
    message_value = msg.value
    return (category_value, subcategory_value, message_value)

def message_str_from_id(msg_id):
    category_value, subcategory_value, message_value = msg_id
    try:
        category_enum = MessageCategory(category_value)
        category_name = category_enum.name
    except ValueError as e:
        raise ValueError(f"Protocol Error: Invalid category value: {category_value}")
    
    category_class = getattr(Messages, category_name)
    subcategory_name = None
    for attr in dir(category_class):
        if not attr.startswith('_'):
            subcategory_class = getattr(category_class, attr)
            if hasattr(subcategory_class, 'value_subcat') and isinstance(subcategory_class.value_subcat, int):
                if subcategory_class.value_subcat == subcategory_value:
                    subcategory_name = attr
                    break
    if subcategory_name is None:
        raise ValueError(f"Protocol Error: No subcategory found with value {subcategory_value} in category {category_name}")
    
    message_enum = getattr(category_class, subcategory_name)
    message_name = None
    for member in message_enum:
        if member.value == message_value:
            message_name = member.name
            break
    if message_name is None:
        raise ValueError(f"Protocol Error: No message found with value {message_value} in {category_name}.{subcategory_name}")
    
    return f"{category_name}.{subcategory_name}.{message_name}"


def get_message_enum(category_value, subcategory_value, message_value):
    try:
        category_enum = MessageCategory(category_value)
        category_name = category_enum.name
    except ValueError as e:
        raise ValueError(f"Protocol Error: Invalid category value: {category_value}")

    category_class = getattr(Messages, category_name)
    for attr in dir(category_class):
        if not attr.startswith('_'):
            subcategory_class = getattr(category_class, attr)
            if hasattr(subcategory_class, 'value_subcat') and subcategory_class.value_subcat == subcategory_value:
                break
    else:
        raise ValueError(f"Protocol Error: No subcategory found with value {subcategory_value} in category {category_name}")

    try:
        enum_member = subcategory_class(message_value)
    except ValueError as e:
        raise ValueError(f"Protocol Error: No message found with value {message_value} in {category_name}.{subcategory_class.__name__}")

    return enum_member


def create_payload(self, **kwargs):
    if not hasattr(self, 'payload_def'):
        raise ValueError(f"Protocol Error: No payload definition for {self}")

    field_defs = {}
    for field in self.payload_def:
        field_name = field["name"]
        if field_name.startswith("PayloadEnum_"):
            key_name = field_name[len("PayloadEnum_"):]
            enum_name = field.get("datatype", field_name)
            field_defs[key_name] = {"type": enum_name, "is_enum": True}
        else:
            key_name = field_name
            field_defs[key_name] = {"type": field.get("datatype"), "is_enum": False}

    required_keys = set(field_defs.keys())
    provided_keys = set(kwargs.keys())
    if required_keys != provided_keys:
        missing = required_keys - provided_keys
        extra = provided_keys - required_keys
        if missing:
            raise ValueError(f"Protocol Error: Missing required fields: {missing}")
        if extra:
            raise ValueError(f"Protocol Error: Extra fields provided: {extra}")

    plist = []
    for field in self.payload_def:
        field_name = field["name"]
        key = field_name[len("PayloadEnum_"):] if field_name.startswith("PayloadEnum_") else field_name
        value = kwargs[key]
        field_info = field_defs[key]

        if field_info["is_enum"]:
            try:
                enum_class = getattr(PayloadEnum, field_info["type"])
                if not isinstance(value, enum_class):
                    raise TypeError(f"Protocol Error: Field '{key}' expects an instance of {field_info['type']}, got {type(value).__name__}")
            except AttributeError as e:
                raise ValueError(f"Protocol Error: Enum class {field_info['type']} not found in PayloadEnum")
        else:
            expected_type = type_mapping.get(field_info["type"])
            if expected_type is None:
                raise ValueError(f"Protocol Error: Unknown datatype '{field_info['type']}' for field '{key}'")
            if not isinstance(value, expected_type):
                raise TypeError(f"Protocol Error: Field '{key}' expects {expected_type.__name__}, got {type(value).__name__}")

        plist.append(value)

    return plist

def encode_message(msg_enum, payload):
    category, subcategory, msgtype = messageid(msg_enum)
    return msgpack.packb([category, subcategory, msgtype, payload])

def decode_message(data):
    category, subcategory, msgtype, payload_list = msgpack.unpackb(data, use_list=True)
    enum_member = get_message_enum(category, subcategory, msgtype)
    if not hasattr(enum_member, 'payload_def'):
        raise ValueError(f"Protocol Error: No payload definition for {enum_member}")

    payload_def = enum_member.payload_def

    payload_def = enum_member.payload_def
    if len(payload_def) != len(payload_list):
        raise ValueError(f"Protocol Error: Payload list length {len(payload_list)} does not match definition {len(payload_def)}")

    payload_dict = {}
    for field, value in zip(payload_def, payload_list):
        field_name = field["name"]
        key = field_name[len("PayloadEnum_"):] if field_name.startswith("PayloadEnum_") else field_name
        if field_name.startswith("PayloadEnum_"):
            datatype = field.get("datatype")
            if datatype:
                try:
                    enum_class = getattr(PayloadEnum, datatype)
                    value = enum_class(value)
                except ValueError as e:
                    raise ValueError(f"Protocol Error: Invalid value {value} for enum {datatype}")
                except AttributeError as e:
                    raise ValueError(f"Protocol Error: Enum class {datatype} not found in PayloadEnum")

        payload_dict[key] = value

    return enum_member, payload_dict

# Attach the payload method
for category_name in dir(Messages):
    if not category_name.startswith('_'):
        category = getattr(Messages, category_name)
        for subcategory_name in dir(category):
            if not subcategory_name.startswith('_'):
                subcategory = getattr(category, subcategory_name)
                if isinstance(subcategory, type) and issubclass(subcategory, Enum):
                    setattr(subcategory, 'payload', create_payload)
