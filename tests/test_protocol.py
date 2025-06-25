import struct
import time
import json
from typing import List, Dict, Tuple, Optional, Any
from enum import Enum, IntEnum, auto, IntFlag
import msgpack
from .protocol import *
from .payload_enums import *
#ImportError: attempted relative import with no known parent package
import crcmod

# Usage Example
if __name__ == "__main__":
    from .datalinks import encode_udp_packet, decode_udp_packet
    from .message_structure import Messages, MessageCategory
    from froggeolib import *

    print("Status.System.FLIGHT:", Messages.Status.System.FLIGHT.value)      # Should be 1
    print("Status.System.POSITION:", Messages.Status.System.POSITION.value)  # Should be 2
    print("Status.System.NAVIGATION:", Messages.Status.System.NAVIGATION.value)  # Should be 3
    print("Command.System.ACTIVATE:", Messages.Command.System.ACTIVATE.value)      # Should be 1
    print("Command.System.SHUTDOWN:", Messages.Command.System.SHUTDOWN.value)  # Should be 2
    print("Command.System.SET_FLIGHT_MODE:", Messages.Command.System.SET_FLIGHT_MODE.value)  # Should be 3

    gps = GPSposition(lat=15.83345500, lon=20.89884100, alt=0)
    full_mgrs = latlon_to_mgrs(gps.lat, gps.lon, precision=5)
    pos = encode_mgrs_binary(full_mgrs, precision=5) # you don't have to do this, i'm just testing stuff

    print(gps)
    print(full_mgrs)
    print(pos)

    msg_enum = Messages.Status.System.FLIGHT
    msg_id = messageid(msg_enum)
    payload = msg_enum.payload(
        airspeed=100,
        FlightMode=PayloadEnum.FlightMode.LOITER,
        groundspeed=100,
        heading=0,
        msl_alt=100,
        packed_mgrs=pos
    )
    encoded_msg = encode_message(msg_enum, payload)
    # for meshtastic, send encoded_msg directly
    eudp = encode_udp_packet(source="me", destination="you", payload=encoded_msg)

    print()
    print("#" * 16)
    print(message_str_from_id(msg_id))
    print('msgid:', msg_id)
    print("Payload list:", payload)
    print("FLIGHT encoded:", encoded_msg)
    print("Length:", len(encoded_msg))
    print('UDP packet:', eudp)


    dudp = decode_udp_packet(eudp)
    enum_member, decoded_payload = decode_message(dudp[2]) # for meshtastic, decode data directly
    decoded_payload["packed_mgrs"] = decode_mgrs_binary(decoded_payload["packed_mgrs"])

    print()
    print("#" * 16)
    print('Decoded UDP packet:', dudp)
    print("Decoded enum:", enum_member)
    print("Decoded payload:", decoded_payload)
    print("Message string:", message_str_from_id(messageid(enum_member)))


    
    msg_enum = Messages.Testing.System.TEXTMSG
    msg_id = messageid(msg_enum)
    payload = msg_enum.payload(
        textdata=b"testing"
    )
    encoded_msg = encode_message(msg_enum, payload)
    # for meshtastic, send encoded_msg directly
    eudp = encode_udp_packet(source="me", destination="you", payload=encoded_msg)

    print()
    print("#" * 16)
    print(message_str_from_id(msg_id))
    print('msgid:', msg_id)
    print("Payload list:", payload)
    print("Encoded:", encoded_msg)
    print("Length:", len(encoded_msg))
    print('UDP packet:', eudp)


    dudp = decode_udp_packet(eudp)
    enum_member, decoded_payload = decode_message(dudp[2])

    print()
    print("#" * 16)
    print('Decoded UDP packet:', dudp)
    print("Decoded enum:", enum_member)
    print("Decoded payload:", decoded_payload)
    print("Message string:", message_str_from_id(messageid(enum_member)))
