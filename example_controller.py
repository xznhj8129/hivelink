#!/usr/bin/env python3
"""
Ground-side receiver/monitor for Hivelink INAV telemetry.
- Uses the same PRELOAD_MODES / ModeMap logic as example_inav_uav so bitmasks decode correctly.
- Pulls link config from a JSON file (same shape as link_config*.json) or from nodes.json + CLI args.
- Expects INAV telemetry (Status.INAV.TELEM) with lat/lon (1e7 ints) and mode bitmask.
"""

import argparse
import asyncio
import json
from typing import Any, Dict, List, Sequence

from hivelink.datalinks import DatalinkInterface, load_nodes_map
from hivelink.msglib import decode_message, message_str_from_id, messageid
from hivelink.protocol import Messages

MULTICAST_GROUP = "239.0.0.1"
MULTICAST_PORT = 5550

PRELOAD_MODES: List[Dict[str, Any]] = [
    {"mode": "ARM", "boxIndex": 0, "permanentId": 0, "auxChannelIndex": 0, "pwmRange": (1800, 2100)},
    {"mode": "ANGLE", "boxIndex": 3, "permanentId": 1, "auxChannelIndex": 1, "pwmRange": (900, 1200)},
    {"mode": "NAV CRUISE", "boxIndex": 12, "permanentId": 53, "auxChannelIndex": 1, "pwmRange": (1300, 1700)},
    {"mode": "NAV POSHOLD", "boxIndex": 8, "permanentId": 11, "auxChannelIndex": 1, "pwmRange": (1800, 2100)},
    {"mode": "NAV RTH", "boxIndex": 10, "permanentId": 10, "auxChannelIndex": 3, "pwmRange": (1800, 2100)},
    {"mode": "NAV WP", "boxIndex": 11, "permanentId": 28, "auxChannelIndex": 3, "pwmRange": (1300, 1700)},
    {"mode": "GCS NAV", "boxIndex": 15, "permanentId": 31, "auxChannelIndex": 2, "pwmRange": (1300, 2100)},
    {"mode": "NAV ALTHOLD", "boxIndex": 19, "permanentId": 3, "auxChannelIndex": 2, "pwmRange": (1300, 1700)},
    {"mode": "FAILSAFE", "boxIndex": 30, "permanentId": 27, "auxChannelIndex": 4, "pwmRange": (1600, 2100)},
]


class ModeMap:
    def __init__(self, base_modes: Sequence[Dict[str, Any]], extra_modes: Sequence[Dict[str, Any]]):
        self.ids: List[int] = []
        self.names: Dict[int, str] = {}
        self.index: Dict[int, int] = {}
        self._extend(base_modes)
        self._extend(extra_modes)

    def _extend(self, mode_entries: Sequence[Dict[str, Any]]) -> None:
        for entry in mode_entries:
            if "permanentId" not in entry:
                raise ValueError("Mode entry missing permanentId")
            mode_id = int(entry["permanentId"])
            if mode_id in self.index:
                continue
            name = entry.get("mode") or entry.get("boxName") or f"ID_{mode_id}"
            idx = len(self.ids)
            self.ids.append(mode_id)
            self.index[mode_id] = idx
            self.names[mode_id] = name

    def names_for_mask(self, mask: int) -> List[str]:
        names: List[str] = []
        bitpos = 0
        remaining = mask
        while remaining:
            if remaining & 1:
                if bitpos >= len(self.ids):
                    raise ValueError(f"Bit {bitpos} set but no mode mapping available (mask={mask})")
                mode_id = self.ids[bitpos]
                names.append(self.names[mode_id])
            remaining >>= 1
            bitpos += 1
        return names


async def main() -> None:
    parser = argparse.ArgumentParser(description="Hivelink ground receiver for INAV telemetry")
    parser.add_argument("--config", help="JSON config (link_config*.json style)")
    parser.add_argument("--my_id", help="Node id from nodes.json (required if --config is not used)")
    parser.add_argument("--meshtastic", default="", help="Optional Meshtastic serial device (when not using --config)")
    parser.add_argument("--mode-ranges", required=True, help="JSON file with INAV mode ranges (from mspapi2 get_mode_ranges)")
    parser.add_argument("--poll", type=float, default=0.2, help="Poll interval seconds for receive loop")
    args = parser.parse_args()

    with open(args.mode_ranges, "r") as f:
        mode_ranges_data = json.load(f)
    if not isinstance(mode_ranges_data, list):
        raise ValueError("Mode ranges file must contain a list of mode range objects")
    for entry in mode_ranges_data:
        if "permanentId" not in entry:
            raise ValueError("Each mode range entry must include permanentId")
    mode_map = ModeMap(PRELOAD_MODES, mode_ranges_data)

    meshtastic_dev = args.meshtastic or None
    if args.config:
        with open(args.config, "r") as f:
            cfg = json.load(f)
        my_name = cfg["my_id"]
        nodemap_cfg = cfg.get("nodemap") or {}
        nodemap = nodemap_cfg if nodemap_cfg else load_nodes_map()
        if my_name not in nodemap:
            raise KeyError(f"Node id '{my_name}' not found in nodemap")
        socket_host = cfg["udp"]["host"]
        socket_port = int(cfg["udp"]["port"])
        datalinks = DatalinkInterface(
            use_meshtastic=bool(cfg["meshtastic"]["use"]),
            radio_port=cfg["meshtastic"]["radio_serial"],
            meshtastic_dataport=int(cfg["meshtastic"]["app_portnum"]),
            use_udp=bool(cfg["udp"]["use"]),
            use_multicast=bool(cfg["udp"]["use_multicast"]),
            socket_host=socket_host,
            socket_port=socket_port,
            my_name=my_name,
            my_id=nodemap[my_name]["meshid"],
            nodemap=nodemap,
            multicast_group=cfg["udp"]["multicast_group"],
            multicast_port=int(cfg["udp"]["multicast_port"]),
            mqtt_enable=bool(cfg["mqtt"]["use"]),
            mqtt_broker=cfg["mqtt"]["broker"],
            mqtt_port=int(cfg["mqtt"]["port"]),
            mqtt_client_id=cfg["mqtt"]["client_id"] or my_name,
            mqtt_username=cfg["mqtt"]["username"] or None,
            mqtt_password=cfg["mqtt"]["password"] or None,
            mqtt_base=cfg["mqtt"]["base"],
            incumbent_window=600,
        )
    else:
        if not args.my_id:
            raise ValueError("Provide --my_id when not using --config")
        nodemap = load_nodes_map()
        if args.my_id not in nodemap:
            raise KeyError(f"Node id '{args.my_id}' not found in nodes.json")
        socket_host, socket_port = nodemap[args.my_id]["ip"]
        datalinks = DatalinkInterface(
            use_meshtastic=bool(meshtastic_dev),
            radio_port=meshtastic_dev,
            meshtastic_dataport=260,
            use_udp=True,
            use_multicast=True,
            socket_host=socket_host,
            socket_port=socket_port,
            my_name=args.my_id,
            my_id=nodemap[args.my_id]["meshid"],
            nodemap=nodemap,
            multicast_group=MULTICAST_GROUP,
            multicast_port=MULTICAST_PORT,
            incumbent_window=600,
        )

    datalinks.start()
    try:
        while True:
            for msg in datalinks.receive():
                enum_member, payload = decode_message(msg["data"])
                msg_name = message_str_from_id(messageid(enum_member))
                print(f"[RX] from={msg['from']} via={msg['intf']} id={msg_name}")

                if enum_member == Messages.Status.INAV.TELEM:
                    modes = mode_map.names_for_mask(payload["inavmodes"])
                    print(
                        f"    modes={modes} "
                        f"gs={payload['groundspeed']} "
                        f"hdg={payload['heading']} "
                        f"alt={payload['msl_alt']} "
                        f"lat={payload['lat']} "
                        f"lon={payload['lon']}"
                    )
                else:
                    print(f"    payload={payload}")
            await asyncio.sleep(args.poll)
    except KeyboardInterrupt:
        print("Receiver stopped by user")
    finally:
        datalinks.stop()


if __name__ == "__main__":
    asyncio.run(main())
