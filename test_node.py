#!/usr/bin/env python3

import asyncio
import msgpack
import socket
from frogtastic import MeshtasticClient
import froggeolib
import frogcot
from message_structure import Messages
from datalinks import *
from protocol import *
import traceback
import argparse
import sys

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

# Helper function to convert bitmap to list of active bits
def int_to_list(bitmap):
    return [i for i in range(bitmap.bit_length()) if (bitmap & (1 << i)) != 0]

def list_to_int(indices):
    bitmap = 0
    for i in indices:
        bitmap |= (1 << i)
    return bitmap

# Helper function to get node ID from IP address
def get_node_from_ip(ip):
    for node, info in nodemap.items():
        if info["ip"] == ip:
            return node
    return "unknown"

# Helper function to get node ID from mesh ID
def get_node_from_meshid(meshid):
    for node, info in nodemap.items():
        if info["meshid"] == meshid:
            return node
    return "unknown"

# Create a PromptSession with a simple caret prompt
session = PromptSession("> ")

# Async loop to read user input and send messages
async def send_loop(datalinks):
    # For testing, if this node is "gcs1", send to "drone1", else send to "gcs1"
    default_dest = "gcs1" if my_name != "gcs1" else "drone1"
    while True:
        try:
            # Using prompt_toolkit's asynchronous input
            message_text = await session.prompt_async()
        except EOFError:
            break
        if not message_text.strip():
            continue
        msg_enum = Messages.Testing.System.TEXTMSG
        payload = msg_enum.payload(textdata=message_text.encode('utf-8'))
        encoded_message = encode_message(msg_enum, payload)
        datalinks.send(encoded_message, dest=default_dest, multicast=True, udp=USE_UDP)
        #print(f"[SENT] {message_text} ({len(encoded_message)} bytes)")

# Async loop to receive and display messages
async def receive_loop(datalinks):
    while True:
        messages = datalinks.receive()
        for msg in messages:
            try:
                msg_enum, payload = decode_message(msg["data"])
                if msg_enum == Messages.Testing.System.TEXTMSG:
                    print(f"{msg['from']}: {payload['textdata'].decode('utf-8')}")
                elif msg_enum.category == Messages.Command:
                    print(f"Command payload: {payload}")
                else:
                    print(f"[RECEIVED] Unhandled message type: {msg_enum}")
            except Exception as e:
                print(f"[RECEIVED] Error decoding message: {e}")
                print(traceback.format_exc())
        await asyncio.sleep(0.1)

async def main():
    datalinks = DatalinkInterface(
        use_meshtastic=USE_MESHTASTIC,
        radio_port=link_config["meshtastic"]["radio_serial"],
        use_udp=USE_UDP,
        socket_host=socket_host,
        socket_port=socket_port,
        my_name=my_name,
        my_id=my_id,
        nodemap=nodemap,
        multicast_group="239.0.0.1",
        multicast_port=5550
    )

    datalinks.start()

    if USE_MESHTASTIC and datalinks.mesh_client:
        uav_id = datalinks.mesh_client.meshint.getMyNodeInfo()
        print(f"[INIT] My node ID: {uav_id}")

    try:
        # patch_stdout lets prompt_toolkit manage prints so that input is preserved.
        with patch_stdout():
            send_task = asyncio.create_task(send_loop(datalinks))
            recv_task = asyncio.create_task(receive_loop(datalinks))
            await asyncio.gather(send_task, recv_task)
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        datalinks.stop()
        print("Connection closed")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Terminal chat program")
    parser.add_argument("--my_id", required=True, help="Node id as defined in nodes.json")
    args = parser.parse_args()

    nodemap = load_nodes_map()
    if args.my_id not in nodemap:
        print(f"Error: Node id '{args.my_id}' not found in nodes.json")
        exit(1)
    my_name = args.my_id
    my_id = nodemap[my_name]["meshid"]
    socket_host, socket_port = nodemap[my_name]["ip"]

    link_config = {
        "meshtastic": {
            "use": False,
            "radio_serial": '/dev/ttyUSB1',
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

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Program terminated by user.")
