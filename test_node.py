#!/usr/bin/env python3

import asyncio
import froggeolib
import frogcot
from hivelink import Messages, CommNode, load_nodes_map
import traceback
import argparse
import sys

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout


# Create a PromptSession with a simple caret prompt
session = PromptSession("> ")

# Async loop to read user input and send messages
async def send_loop(node):
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

        msg = Messages.Testing.System.TEXTMSG
        payload = {"textdata": message_text.encode("utf-8")}
        node.send_message(msg, payload, dest=default_dest, meshtastic=True)
        #print(f"[SENT] {message_text} ({len(encoded_message)} bytes)")

# Async loop to receive and display messages
async def receive_loop(node):
    while True:
        messages = node.receive_messages()

        for msg in messages:
            try:
                msgtype = msg["msg_enum"]
                payload = msg["payload"]
                if msgtype == Messages.Testing.System.TEXTMSG:
                    print(f"{msg['from']}: {payload['textdata'].decode('utf-8')}")
                elif msgtype.category == Messages.Command:
                    print(f"Command payload: {payload}")
                else:
                    print(f"[RECEIVED] Unhandled message type: {msgtype}")

            except Exception as e:
                print(f"[RECEIVED] Error decoding message: {e}")
                print(traceback.format_exc())
        await asyncio.sleep(0.1)

async def main():

    node = CommNode(link_config)
    node.start()

    if node.link.use_meshtastic and node.link.mesh_client:
        meshid = node.link.mesh_client.meshint.getMyNodeInfo()
        print(f"[INIT] My node ID: {meshid}")

    try:
        # patch_stdout lets prompt_toolkit manage prints so that input is preserved.
        with patch_stdout():
            send_task = asyncio.create_task(send_loop(node))
            recv_task = asyncio.create_task(receive_loop(node))
            await asyncio.gather(send_task, recv_task)
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        node.stop()
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
            "multicast_group": "239.0.0.1",
            "multicast_port": 5550
        },
        "nodemap": nodemap
    }


    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Program terminated by user.")
