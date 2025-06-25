#!/usr/bin/env python3

import asyncio
import msgpack
import socket
import froggeolib
import frogcot
from hivelink.message_structure import Messages
from hivelink.datalinks import *
from hivelink.protocol import *
import traceback
import argparse
import sys

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout


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

        send_mc = False
        send_mesh = False
        send_udp = False
        if message_text.startswith("/mesh "):
            message_text = message_text.strip("/mesh ")
            send_mesh = True
        elif message_text.startswith("/mc "):
            message_text = message_text.strip("/mc ")
            send_mc = True
        else:
            send_udp = True

        msg = Messages.Testing.System.TEXTMSG
        payload = msg.payload(textdata=message_text.encode('utf-8'))
        encoded_message = encode_message(msg, payload)
        datalinks.send(encoded_message, dest=default_dest, meshtastic=send_mesh, multicast=send_mc, udp=send_udp)
        #print(f"[SENT] {message_text} ({len(encoded_message)} bytes)")

# Async loop to receive and display messages
async def receive_loop(datalinks):
    while True:
        messages = datalinks.receive()

        for msg in messages:
            try:
                msgtype, payload = decode_message(msg["data"])
                if msgtype == Messages.Testing.System.TEXTMSG:
                    print(f"{msg['from']}({msg['intf']}): {payload['textdata'].decode('utf-8')}")
                elif msgtype.category == Messages.Command:
                    print(f"Command payload: {payload}")
                else:
                    print(f"[RECEIVED] Unhandled message type: {msgtype}")

            except Exception as e:
                print(f"[RECEIVED] Error decoding message: {e}")
                print(traceback.format_exc())
        await asyncio.sleep(0.1)

async def main():

    datalinks = DatalinkInterface(
        use_meshtastic=link_config["meshtastic"]["use"],
        radio_port=link_config["meshtastic"]["radio_serial"],
        use_udp=link_config["udp"]["use"],
        use_multicast=link_config["udp"]["use_multicast"],
        socket_host=link_config["udp"]["host"],
        socket_port=link_config["udp"]["port"],
        my_name=link_config["my_name"],
        my_id=link_config["my_id"],
        nodemap=link_config["nodemap"],
        multicast_group=link_config["udp"]["multicast_group"],
        multicast_port=link_config["udp"]["multicast_port"]
    )

    datalinks.start()

    if datalinks.use_meshtastic and datalinks.mesh_client:
        meshid = datalinks.mesh_client.meshint.getMyNodeInfo()
        print(f"[INIT] My node ID: {meshid}")

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
    parser.add_argument("--meshtastic_device", default="", help="Node id as defined in nodes.json")
    args = parser.parse_args()

    nodemap = load_nodes_map()
    if args.my_id not in nodemap:
        print(f"Error: Node id '{args.my_id}' not found in nodes.json")
        exit(1)
    my_name = args.my_id
    my_id = nodemap[my_name]["meshid"]
    socket_host, socket_port = nodemap[my_name]["ip"]

    link_config = {
        "my_name": my_name,
        "my_id": my_id,

        "meshtastic": {
            "use": args.meshtastic_device != "",
            "radio_serial": args.meshtastic_device,
            "app_portnum": 260
        },
        "udp": {
            "use": True,
            "host": socket_host,
            "port": socket_port,
            "use_multicast": True,
            "multicast_group": "239.0.0.1",
            "multicast_port": 5550
        },
        "nodemap": nodemap
    }


    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Program terminated by user.")
