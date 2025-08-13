#!/usr/bin/env python3
# example_mavlink_node.py
#
# Control an onboard ArduPilot instance via pymavlink using Hivelink messages.
# Supports: ARM, DISARM, SET_MODE, TAKEOFF, LAND, SELECT_MISSION
# Publishes slow, high-latency telemetry (Status.AP.HL_TELEM).
#
# CSV must define the Command.AP.* and Status.AP.HL_TELEM messages as listed above.

import asyncio
import argparse
import sys
import time

from hivelink.protocol import *
from hivelink.datalinks import *
from hivelink.msglib import *
import froggeolib
import msgpack
import traceback

from pymavlink import mavutil


class MavlinkAP:
    def __init__(self, conn_str: str):
        self.conn_str = conn_str
        self.master: mavutil.mavlink_connection | None = None
        self.last_hb = 0.0

        # Telemetry snapshot (ints as requested)
        self.mode_str = "UNKNOWN"
        self.airspeed = 0          # m/s
        self.groundspeed = 0       # m/s
        self.heading = 0           # deg
        self.msl_alt = 0           # m (VFR_HUD.alt)
        self.lat = None            # deg
        self.lon = None            # deg

        self._running = False

    # ----- connection / pump -----
    def connect(self):
        # autoreconnect makes it resilient to restarts
        self.master = mavutil.mavlink_connection(self.conn_str, autoreconnect=True)
        try:
            self.master.wait_heartbeat(timeout=5)
            self.last_hb = time.time()
            self._update_mode_from_master()
            print(f"[MAV] Connected, sysid={self.master.target_system} compid={self.master.target_component} mode={self.mode_str}")
        except Exception:
            print("[MAV] No heartbeat yet; will continue trying.")

    async def pump(self):
        """Poll MAVLink and maintain a telemetry snapshot."""
        self._running = True
        if self.master is None:
            self.connect()

        while self._running:
            try:
                if self.master is None:
                    self.connect()

                if self.master is None:
                    await asyncio.sleep(0.5)
                    continue

                m = self.master.recv_match(blocking=False)
                if m is None:
                    await asyncio.sleep(0.05)
                    continue

                mtype = m.get_type()

                if mtype == "BAD_DATA":
                    continue
                elif mtype == "HEARTBEAT":
                    self.last_hb = time.time()
                    self._update_mode_from_master()
                elif mtype == "VFR_HUD":
                    # VFR_HUD.alt is meters in ArduPilot
                    self.groundspeed = int(m.groundspeed or 0)
                    self.airspeed = int(m.airspeed or 0)
                    self.heading = int(m.heading or 0)
                    self.msl_alt = int(m.alt or 0)
                elif mtype == "GLOBAL_POSITION_INT":
                    self.lat = (m.lat or 0) / 1e7
                    self.lon = (m.lon or 0) / 1e7
                # Extend as needed
            except Exception as e:
                print(f"[MAV] pump error: {e}")
                await asyncio.sleep(0.5)

    def stop(self):
        self._running = False
        try:
            if self.master is not None:
                self.master.close()
        except Exception:
            pass
        self.master = None

    def _update_mode_from_master(self):
        try:
            if self.master is None:
                return
            # pymavlink tracks .flightmode for ArduPilot
            self.mode_str = str(getattr(self.master, "flightmode", None) or "UNKNOWN")
        except Exception:
            self.mode_str = "UNKNOWN"

    # ----- commands -----
    def _ensure_connected(self):
        if self.master is None:
            raise RuntimeError("MAVLink not connected")

    def arm(self, arm: bool):
        self._ensure_connected()
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,
            1 if arm else 0, 0, 0, 0, 0, 0, 0,
        )

    def set_mode(self, mode_str: str) -> bool:
        """Set ArduPilot custom flight mode by name (e.g., GUIDED, AUTO, LOITER, LAND)."""
        self._ensure_connected()
        mode = mode_str.strip().upper()
        mapping = self.master.mode_mapping()
        if not mapping or mode not in mapping:
            print(f"[MAV] Mode '{mode}' unsupported by vehicle mapping: {mapping}")
            return False
        mode_id = mapping[mode]
        self.master.mav.set_mode_send(
            self.master.target_system,
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            mode_id,
        )
        return True

    def takeoff(self, alt_m: int, yaw_deg: float = float("nan")):
        """GUIDED takeoff to altitude (meters AGL in most ArduPilot frames)."""
        self._ensure_connected()
        # make sure we are armed + GUIDED
        self.arm(True)
        self.set_mode("GUIDED")
        # MAV_CMD_NAV_TAKEOFF: param7 = altitude (m), param4 = yaw deg
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            0,
            0, 0, 0, (0.0 if not (yaw_deg == yaw_deg) else yaw_deg), 0, 0, float(alt_m),
        )

    def land(self):
        """Switch to LAND mode (simple and robust)."""
        self._ensure_connected()
        self.set_mode("LAND")

    def select_mission(self, seq: int):
        """Set current mission sequence and switch to AUTO."""
        self._ensure_connected()
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_DO_SET_MISSION_CURRENT,
            0,
            float(seq), 0, 0, 0, 0, 0, 0,
        )
        # Start mission by switching to AUTO
        self.set_mode("AUTO")


# ----- Hivelink loops -----
async def hivelink_command_loop(datalinks: DatalinkInterface, ap: MavlinkAP):
    """Receive Hivelink commands and apply to ArduPilot."""
    while True:
        try:
            for msg in datalinks.receive():
                try:
                    msgtype, payload = decode_message(msg["data"])
                except Exception as e:
                    print(f"[HL] decode error: {e}")
                    continue

                # Command handlers
                try:
                    if msgtype == Messages.Command.AP.ARM:
                        arm = int(payload.get("arm", 1)) != 0
                        ap.arm(arm)
                        print(f"[CMD] ARM={arm}")
                    elif msgtype == Messages.Command.AP.DISARM:
                        ap.arm(False)
                        print(f"[CMD] DISARM")
                    elif msgtype == Messages.Command.AP.SET_MODE:
                        mbytes = payload.get("mode_str", b"")
                        mode = (mbytes.decode("utf-8", errors="ignore") if isinstance(mbytes, (bytes, bytearray)) else str(mbytes)).strip()
                        ok = ap.set_mode(mode)
                        print(f"[CMD] SET_MODE {mode} -> {ok}")
                    elif msgtype == Messages.Command.AP.TAKEOFF:
                        alt_m = int(payload.get("alt_m", 10))
                        ap.takeoff(alt_m)
                        print(f"[CMD] TAKEOFF alt={alt_m}m")
                    elif msgtype == Messages.Command.AP.LAND:
                        ap.land()
                        print(f"[CMD] LAND")
                    elif msgtype == Messages.Command.AP.SELECT_MISSION:
                        seq = int(payload.get("seq", 0))
                        ap.select_mission(seq)
                        print(f"[CMD] SELECT_MISSION seq={seq}")
                except Exception as e:
                    print(f"[CMD] error: {e}")

            await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            return
        except Exception as e:
            print(f"[HL] command loop error: {e}")
            await asyncio.sleep(0.2)


async def hivelink_telem_loop(datalinks: DatalinkInterface, ap: MavlinkAP, rate_hz: float = 1.0):
    """Publish slow, high-latency telemetry."""
    period = 1.0 / max(rate_hz, 0.1)
    while True:
        try:
            # Build HL_TELEM
            msg = Messages.Status.AP.HL_TELEM
            lat = ap.lat if ap.lat else 0
            lon = ap.lon if ap.lon else 0
            full_mgrs = froggeolib.latlon_to_mgrs(lat, lon, precision=5)
            pos = froggeolib.encode_mgrs_binary(full_mgrs, precision=5)
            payload = msg.payload(
                mode_str=ap.mode_str.encode("utf-8", errors="ignore"),
                airspeed=int(ap.airspeed),
                groundspeed=int(ap.groundspeed),
                heading=int(ap.heading),
                msl_alt=int(ap.msl_alt),
                packed_mgrs=pos,
            )
            encoded = encode_message(msg, payload)
            # Broadcast over all available links; adapt as you like
            datalinks.send(encoded, dest="", meshtastic=True)
        except Exception as e:
            print(f"[HL] telem error: {e}")
            print(traceback.format_exception(type(e), e, e.__traceback__))
        await asyncio.sleep(period)


async def main():
    parser = argparse.ArgumentParser(description="Hivelink ↔ ArduPilot bridge (high-latency control)")
    parser.add_argument("--my_id", required=True, help="Node id as defined in nodes.json")
    parser.add_argument("--meshtastic_device", default="", help="Serial path to Meshtastic device")
    parser.add_argument("--mavlink", default="udp:127.0.0.1:14550", help="pymavlink connection string")
    parser.add_argument("--hl_rate", type=float, default=1.0, help="high-latency telemetry rate Hz")

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
        incumbent_window=600,
    )

    # Bring up links
    datalinks.start()

    # MAVLink side
    ap = MavlinkAP(args.mavlink)
    pump_task = asyncio.create_task(ap.pump(), name="mav_pump")
    cmd_task = asyncio.create_task(hivelink_command_loop(datalinks, ap), name="hl_cmd")
    telem_task = asyncio.create_task(hivelink_telem_loop(datalinks, ap, rate_hz=args.hl_rate), name="hl_telem")

    try:
        # Wait forever; Ctrl+C will fall to except
        await asyncio.gather(pump_task, cmd_task, telem_task)
    except KeyboardInterrupt:
        pass
    finally:
        for t in (telem_task, cmd_task, pump_task):
            if t and not t.done():
                t.cancel()
                try:
                    await t
                except asyncio.CancelledError:
                    pass
        ap.stop()
        datalinks.stop()
        print("Connection closed")


if __name__ == "__main__":
    asyncio.run(main())
