#!/usr/bin/env python3

import argparse
import asyncio
from typing import Any, Dict, List, Sequence

from mspapi2.lib import InavEnums
from mspapi2.msp_api import MSPApi

from hivelink.datalinks import DatalinkInterface, load_nodes_map
from hivelink.msglib import decode_message, encode_message, message_str_from_id, messageid
from hivelink.protocol import Messages

DEFAULT_BAUDRATE = 115200
DEFAULT_READ_TIMEOUT = 0.05
DEFAULT_WRITE_TIMEOUT = 0.25
DEFAULT_INTERVAL_S = 5.0
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

    def mask_from_active(self, active_modes: List[Dict[str, int]]) -> int:
        mask = 0
        for entry in active_modes:
            if "permanentId" not in entry:
                raise ValueError("Active mode entry missing permanentId")
            mode_id = int(entry["permanentId"])
            if mode_id not in self.index:
                self._extend([entry])
            bit = self.index[mode_id]
            mask |= 1 << bit
        return mask


def collect_telem_snapshot(api: MSPApi, mode_map: ModeMap) -> Dict[str, int]:
    _, raw_gps = api.get_raw_gps()
    if raw_gps["fixType"] == InavEnums.gpsFixType_e.GPS_NO_FIX:
        raise RuntimeError("GPS fix is not available")

    _, altitude = api.get_altitude()
    _, attitude = api.get_attitude()
    _, active_modes = api.get_active_modes()

    mask = mode_map.mask_from_active(active_modes)
    groundspeed = int(round(raw_gps["speed"]))
    heading = int(round(attitude["yaw"]))
    msl_alt = int(round(altitude["estimatedAltitude"]))
    lat = int(round(raw_gps["latitude"] * 1e7))
    lon = int(round(raw_gps["longitude"] * 1e7))

    return {
        "inavmodes": mask,
        "airspeed": groundspeed,
        "groundspeed": groundspeed,
        "heading": heading,
        "msl_alt": msl_alt,
        "lat": lat,
        "lon": lon,
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="Hivelink ↔ INAV bridge using MSPApi (direct)")
    parser.add_argument("--my_id", required=True, help="Node id as defined in nodes.json")
    parser.add_argument("--dest", default="gcs1", help="Telemetry destination node id")
    parser.add_argument("--port", help="Serial device path for MSP (e.g. /dev/ttyUSB0)")
    parser.add_argument("--baudrate", type=int, default=DEFAULT_BAUDRATE, help="Serial baud rate")
    parser.add_argument("--tcp", help="Connect to MSP over TCP, HOST:PORT")
    parser.add_argument("--read-timeout", type=float, default=DEFAULT_READ_TIMEOUT, help="MSP read timeout (seconds)")
    parser.add_argument("--write-timeout", type=float, default=DEFAULT_WRITE_TIMEOUT, help="MSP write timeout (seconds)")
    parser.add_argument("--meshtastic", default="", help="Optional Meshtastic serial device for radio link")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL_S, help="Telemetry interval seconds")
    args = parser.parse_args()

    if args.port and args.tcp:
        raise ValueError("Use only one of --port or --tcp for MSP transport")
    if not args.port and not args.tcp:
        raise ValueError("Provide --port or --tcp for MSP transport")
    if args.interval <= 0:
        raise ValueError("Telemetry interval must be positive")

    nodemap = load_nodes_map()
    if args.my_id not in nodemap:
        raise KeyError(f"Node id '{args.my_id}' not found in nodes.json")
    if args.dest not in nodemap:
        raise KeyError(f"Destination '{args.dest}' not found in nodes.json")

    socket_host, socket_port = nodemap[args.my_id]["ip"]
    my_mesh_id = nodemap[args.my_id]["meshid"]

    datalinks = DatalinkInterface(
        use_meshtastic=bool(args.meshtastic),
        radio_port=args.meshtastic or None,
        meshtastic_dataport=260,
        use_udp=True,
        socket_host=socket_host,
        socket_port=socket_port,
        my_name=args.my_id,
        my_id=my_mesh_id,
        nodemap=nodemap,
        multicast_group="239.0.0.1",
        multicast_port=5550,
    )
    port = None if args.tcp else args.port
    try:
        datalinks.start()
        with MSPApi(
            port=port,
            baudrate=args.baudrate,
            read_timeout=args.read_timeout,
            write_timeout=args.write_timeout,
            tcp_endpoint=args.tcp,
        ) as api:
            _, fc_variant = api.get_fc_variant()
            variant_name = fc_variant.get("fcVariantIdentifier")
            if variant_name != "INAV":
                raise RuntimeError(f"Flight controller variant '{variant_name}' is not INAV")
            print(f"[MSP] Connected to INAV via {'TCP ' + args.tcp if args.tcp else port} (baud {args.baudrate})")

            _, mode_ranges = api.get_mode_ranges()
            mode_map = ModeMap(PRELOAD_MODES, mode_ranges)
            known_modes = [f"{mode_map.names[mid]}({mid})" for mid in mode_map.ids]
            print(f"[MSP] Known mode ids: {', '.join(known_modes)}")

            while True:
                telemetry = await asyncio.to_thread(collect_telem_snapshot, api, mode_map)
                msg = Messages.Status.INAV.TELEM
                payload = msg.payload(**telemetry)
                encoded = encode_message(msg, payload)
                sent = datalinks.send(encoded, dest=args.dest, udp=True, meshtastic=bool(args.meshtastic))
                print(
                    f"[TX] dest={args.dest} mask={telemetry['inavmodes']} "
                    f"gs={telemetry['groundspeed']} heading={telemetry['heading']} "
                    f"lat={telemetry['lat']} lon={telemetry['lon']} alt={telemetry['msl_alt']} sent={sent}"
                )

                for incoming in datalinks.receive():
                    enum_member, payload_decoded = decode_message(incoming["data"])
                    msg_name = message_str_from_id(messageid(enum_member))
                    print(f"[RX] from={incoming['from']} id={msg_name} payload={payload_decoded}")

                await asyncio.sleep(args.interval)
    except KeyboardInterrupt:
        print("Telemetry stopped by user")
    finally:
        datalinks.stop()


if __name__ == "__main__":
    asyncio.run(main())
