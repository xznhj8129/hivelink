#!/usr/bin/env python3
# example_node.py
# simple example node with text chat + MQTT I/O relay handled inside datalinks (NOT a transport)

import asyncio
import argparse
import sys
import time

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

from hivelink.protocol import *
from hivelink.datalinks import *
from hivelink.msglib import *
import froggeolib
import frogcot
import msgpack

session = PromptSession("> ")


async def send_loop(datalinks: DatalinkInterface, my_name: str):
    default_dest = "gcs1" if my_name != "gcs1" else "drone1"
    while True:
        try:
            text = await session.prompt_async()
        except (EOFError, KeyboardInterrupt, asyncio.CancelledError):
            return

        if not text.strip():
            continue
        if text.strip().lower() in {"/q", "/quit", "/exit"}:
            return

        send_mc = False
        send_mesh = False
        send_udp = False

        if text.startswith("/mesh "):
            text = text.strip("/mesh ")
            send_mesh = True
        elif text.startswith("/mc "):
            text = text.strip("/mc ")
            send_mc = True
        else:
            send_udp = True

        msg = Messages.Testing.System.TEXTMSG
        payload = msg.payload(textdata=text)
        encoded = encode_message(msg, payload)
        datalinks.send(encoded, dest=default_dest, meshtastic=send_mesh, multicast=send_mc, udp=send_udp)


async def receive_loop(datalinks: DatalinkInterface):
    try:
        while True:
            for msg in datalinks.receive():
                try:
                    enum_member, decoded = decode_message(msg["data"])
                    if enum_member == Messages.Testing.System.TEXTMSG:
                        print(f"{msg['from']}({msg['intf']}): {decoded.get('textdata','')}")
                    else:
                        print(f"[RECEIVED] {message_str_from_id(messageid(enum_member))} from {msg['from']} via {msg['intf']}")
                        print(decoded)
                except Exception as e:
                    print(f"[RECEIVED] Error decoding message: {e}")
            await asyncio.sleep(0.1)
    except (asyncio.CancelledError, KeyboardInterrupt):
        return


async def main():
    parser = argparse.ArgumentParser(description="Terminal chat program")
    parser.add_argument("--my_id", required=True, help="Node id as defined in nodes.json")
    parser.add_argument("--meshtastic_device", default="", help="Serial path to Meshtastic device")

    # MQTT (optional I/O)
    parser.add_argument("--mqtt_broker", default="", help="MQTT broker host (enables MQTT I/O if set)")
    parser.add_argument("--mqtt_port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--mqtt_client_id", default="", help="MQTT client id (defaults to my_id if empty)")
    parser.add_argument("--mqtt_user", default=None, help="MQTT username")
    parser.add_argument("--mqtt_pass", default=None, help="MQTT password")

    args = parser.parse_args()

    nodemap = load_nodes_map()
    if args.my_id not in nodemap:
        print(f"Error: Node id '{args.my_id}' not found in nodes.json")
        sys.exit(1)

    my_name = args.my_id
    my_id = nodemap[my_name]["meshid"]
    socket_host, socket_port = nodemap[my_name]["ip"]

    datalinks = DatalinkInterface(
        use_meshtastic=(args.meshtastic_device != ""),
        radio_port=args.meshtastic_device,
        meshtastic_dataport=260,
        use_udp=True,
        use_multicast=True,
        socket_host=socket_host,
        socket_port=socket_port,
        my_name=my_name,
        my_id=my_id,
        nodemap=nodemap,
        multicast_group="239.0.0.1",
        multicast_port=5550,
        mqtt_enable=bool(args.mqtt_broker),
        mqtt_broker=args.mqtt_broker,
        mqtt_port=args.mqtt_port,
        mqtt_client_id=(args.mqtt_client_id if args.mqtt_client_id else my_name),
        mqtt_username=args.mqtt_user,
        mqtt_password=args.mqtt_pass,
        mqtt_base="/hivelink/v1",
        incumbent_window=600,
    )

    datalinks.start()

    # fire an ONLINE if your codec allows empty payload
    try:
        msg = Messages.Status.System.ONLINE
        datalinks.send(encode_message(msg), dest="", meshtastic=True, multicast=True, udp=True)
    except Exception:
        pass

    send_task = recv_task = None
    try:
        with patch_stdout():
            send_task = asyncio.create_task(send_loop(datalinks, my_name), name="send_loop")
            recv_task = asyncio.create_task(receive_loop(datalinks), name="recv_loop")

            # Wait until first task finishes, then cancel the other
            done, pending = await asyncio.wait({send_task, recv_task}, return_when=asyncio.FIRST_COMPLETED)
            for t in pending:
                t.cancel()
                try:
                    await t
                except asyncio.CancelledError:
                    pass
    except KeyboardInterrupt:
        # Ctrl+C anywhere => cancel both and exit clean
        for t in (send_task, recv_task):
            if t and not t.done():
                t.cancel()
                try:
                    await t
                except asyncio.CancelledError:
                    pass
    finally:
        datalinks.stop()
        print("Connection closed")


if __name__ == "__main__":
    asyncio.run(main())
