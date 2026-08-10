#!/usr/bin/env python3
"""Small interactive HiveLink node using the direct OCCID model API."""

import argparse
import asyncio
from datetime import datetime, timezone
import json
import sys

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

from hivelink.datalinks import DatalinkInterface, load_nodes_map
from occid import (
    HumanTextMessage,
    IdentifierType,
    MessagePriority,
    MessageTarget,
    StringID,
    Timestamp,
)

session = PromptSession("> ")


def sid(value: str) -> StringID:
    return StringID(id_type=IdentifierType.DB_ID, value=value)


def timestamp_now() -> Timestamp:
    now = datetime.now(timezone.utc)
    return Timestamp(
        seconds=now.second + now.microsecond / 1_000_000.0,
        minutes=now.minute,
        hours=now.hour,
        day=now.day,
        month=now.month,
        year=now.year,
        tz=0,
    )


async def send_loop(datalinks: DatalinkInterface, my_name: str):
    destination = "gcs1" if my_name != "gcs1" else "drone1"
    seq = 0
    while True:
        try:
            text = await session.prompt_async()
        except (EOFError, KeyboardInterrupt, asyncio.CancelledError):
            return

        text = text.strip()
        if not text:
            continue
        if text.lower() in {"/q", "/quit", "/exit"}:
            return
        if text.startswith("/dest "):
            destination = text.split(maxsplit=1)[1].strip()
            print("Set destination:", destination)
            continue

        send_mesh = text.startswith("/mesh ")
        send_mc = text.startswith("/mc ")
        if send_mesh:
            text = text[len("/mesh "):]
        elif send_mc:
            text = text[len("/mc "):]

        seq += 1
        src = MessageTarget(target_id=sid(my_name))
        dst = MessageTarget(target_id=sid(destination))
        payload = HumanTextMessage(
            src=src,
            dst=dst,
            ts=timestamp_now(),
            priority=MessagePriority.ROUTINE,
            seq=seq,
            sender_id=sid(my_name),
            sender_name=my_name,
            destination_id=sid(destination),
            message=text,
            targets=[dst],
        )
        sent = datalinks.send_model(
            payload,
            destination,
            udp=not send_mesh and not send_mc,
            meshtastic=send_mesh,
            multicast=send_mc,
        )
        if not sent:
            print(f"Send failed: {destination}")


async def receive_loop(datalinks: DatalinkInterface):
    try:
        while True:
            for msg in datalinks.receive_models():
                payload = msg["model"]
                if isinstance(payload, HumanTextMessage):
                    print(f"{msg['from']}({msg['intf']}): {payload.message}")
                else:
                    print(
                        f"[RECEIVED] {type(payload).__name__} "
                        f"from {msg['from']} via {msg['intf']}"
                    )
                    print(payload.model_dump(mode="json", exclude_none=True))
            await asyncio.sleep(0.1)
    except (asyncio.CancelledError, KeyboardInterrupt):
        return


async def main():
    parser = argparse.ArgumentParser(description="HiveLink terminal node")
    parser.add_argument("--config", default="", help="Use JSON config file")
    parser.add_argument("--my_id", help="Node id as defined in nodes.json")
    parser.add_argument("--meshtastic_device", default="")
    args = parser.parse_args()

    nodemap = load_nodes_map()
    if args.config:
        with open(args.config, "r", encoding="utf-8") as handle:
            cfg = json.load(handle)
        my_name = cfg["my_name"]
        my_id = int(cfg.get("my_id", 0))
        mesh = cfg.get("meshtastic", {})
        udp = cfg.get("udp", {})
        use_meshtastic = bool(mesh.get("use", False))
        radio_serial = mesh.get("radio_serial")
        app_portnum = int(mesh.get("app_portnum", 260))
        use_udp = bool(udp.get("use", True))
        socket_host = str(udp.get("host", "0.0.0.0"))
        socket_port = int(udp.get("port", 5555))
        use_multicast = bool(udp.get("use_multicast", False))
        multicast_group = str(udp.get("multicast_group", ""))
        multicast_port = int(udp.get("multicast_port", socket_port))
    else:
        if not args.my_id or args.my_id not in nodemap:
            print(f"Error: Node id '{args.my_id}' not found in nodes.json")
            sys.exit(1)
        my_name = args.my_id
        my_id = int(nodemap[my_name].get("meshid", 0))
        socket_host = "0.0.0.0"
        socket_port = int(nodemap[my_name]["ip"][1])
        use_udp = True
        use_multicast = False
        multicast_group = ""
        multicast_port = socket_port
        use_meshtastic = bool(args.meshtastic_device)
        radio_serial = args.meshtastic_device or None
        app_portnum = 260

    datalinks = DatalinkInterface(
        use_meshtastic=use_meshtastic,
        radio_port=radio_serial,
        meshtastic_dataport=app_portnum,
        use_udp=use_udp,
        use_multicast=use_multicast,
        socket_host=socket_host,
        socket_port=socket_port,
        my_name=my_name,
        my_id=my_id,
        nodemap=nodemap,
        multicast_group=multicast_group,
        multicast_port=multicast_port,
    )

    datalinks.start()
    send_task = recv_task = None
    try:
        with patch_stdout():
            send_task = asyncio.create_task(send_loop(datalinks, my_name))
            recv_task = asyncio.create_task(receive_loop(datalinks))
            _, pending = await asyncio.wait(
                {send_task, recv_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
    finally:
        datalinks.stop()
        print("Connection closed")


if __name__ == "__main__":
    asyncio.run(main())
