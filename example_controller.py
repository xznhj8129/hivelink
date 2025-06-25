#!/usr/bin/env python3
# WARNING: outdated
import time
import socket
import asyncio
from frogtastic import MeshtasticClient
import froggeolib
from unavlib.modules.utils import inavutil
from message_structure import Messages
from protocol import *
from datalinks import *


# Helper function to convert bitmap to list of active bits
def int_to_list(bitmap):
    return [i for i in range(bitmap.bit_length()) if (bitmap & (1 << i)) != 0]

# Helper function to get node ID from mesh ID
def get_node_from_meshid(meshid):
    for node, info in nodemap.items():
        if info["meshid"] == meshid:
            return node
    return "unknown"

modemap = [27, 10, 12, 38, 0, 1, 53, 11, 31, 47]

my_name = "gcs1"
# Node map defining node IDs, mesh IDs, and IP addresses with ports
nodemap = load_nodes_map()
my_id = nodemap[my_name]["meshid"]
socket_host, socket_port = nodemap[my_name]["ip"]

link_config = {
    "meshtastic": {
        "use": False,
        "radio_serial": '/dev/ttyACM0',
        "app_portnum": 260
    },
    "udp": {
        "use": True,
        "port": socket_port,
        
    },

    "node_map": nodemap
}

USE_MESHTASTIC = link_config["meshtastic"]["use"]
USE_UDP = link_config["udp"]["use"]
MULTICAST_GROUP = "239.0.0.1"
MULTICAST_PORT = 5550

async def main():
    datalinks = DatalinkInterface(
        use_meshtastic=USE_MESHTASTIC,
        radio_port=link_config["meshtastic"]["radio_serial"],
        use_udp=USE_UDP,
        socket_host=socket_host,
        socket_port=socket_port,
        my_id=my_id,
        nodemap=nodemap,
        multicast_group=MULTICAST_GROUP,
        multicast_port=MULTICAST_PORT
    )

    datalinks.start()

    if USE_MESHTASTIC and datalinks.mesh_client:
        print(datalinks.mesh_client.meshint.getMyNodeInfo())

    # Command queue with a command to send to drone1
    command_queue = [
        {
            "dest": "drone1",
            "msgid": messageid(Messages.Command.Mission.NAVIGATE_TO),
            "data": {"mgrs": "18TWL12345678"},
            "frequency": None  # Send once if frequency is None
        }
    ]

    # Send commands from the command_queue at startup (not yet)
    #for command in command_queue:
    #    if command["frequency"] is None:
    #        encoded_data = encode_message(command["msgid"], command["data"])
    #        datalinks.send(encoded_data, dest=command["dest"])
    #        print(f"Sent command to {command['dest']}: {command['msgid']}")

    try:
        while True:
            # Receive messages from the datalinks
            msgs = datalinks.receive()
            if msgs:
                for msg in msgs:
                    try:
                        
                        print(f"\n[RECEIVED] Message at {time.time():.1f}")
                        if "senderid" in msg:
                            sender_meshid = msg["senderid"]
                            sender = get_node_from_meshid(sender_meshid)
                        elif "from" in msg:
                            sender = msg["from"]
                        else:
                            sender = "unknown"
                        print(f"From: {sender}")
                        print(msg)

                        msgid, data = decode_message(msg["data"])
                        print("MSG ID:", msgid)

                        if "packed_mgrs" in data:
                            data["mgrs"] = froggeolib.decode_mgrs_binary(data["packed_mgrs"], precision=5)
                            data["pos"] = froggeolib.mgrs_to_latlon(data["mgrs"])

                        for key, value in data.items():
                            print(f"\t{key}: {value}")

                        if "inavmodes" in data:
                            modes = int_to_list(data["inavmodes"])
                            activemodes = [modemap[i] for i in modes]
                            print('Modes:', [inavutil.modesID.get(i) for i in activemodes])
                    except Exception as e:
                        print(f"Error decoding message: {e}")

            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Shut down")
    finally:
        # Properly stop the datalinks to clean up resources
        datalinks.stop()
        print("Connection closed")


if __name__ == "__main__":
    asyncio.run(main())