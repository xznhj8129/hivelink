#!/usr/bin/env python3

import asyncio
import msgpack
import socket
from unavlib.control import UAVControl
from unavlib.modules import geospatial
from unavlib.modules.utils import inavutil
from frogtastic import MeshtasticClient
import froggeolib
import frogcot
from message_structure import Messages
from datalinks import *
from protocol import *



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

my_name = "drone1"
TELEMETRY_PORT = "/dev/ttyUSB0"
nodemap = load_nodes_map()
my_id = nodemap[my_name]["meshid"]

link_config = {
    "meshtastic": {
        "use": False,
        "radio_serial": '/dev/ttyUSB1',
        "app_portnum": 260
    },
    "udp": {
        "use": True,
        "port": 5556,
        
    },

    "node_map": load_nodes_map()
}

# Set socket host and port based on this node's ID from nodemap
socket_host, socket_port = nodemap[my_name]["ip"]
USE_MESHTASTIC = link_config["meshtastic"]["use"]
USE_UDP = link_config["udp"]["use"]
MULTICAST_GROUP = "239.0.0.1"
MULTICAST_PORT = 5550


PRELOAD_MODES = [27, 10, 12, 38, 0, 1, 53, 11, 31, 47]
SEND_INTERVAL = 5
#PRELOAD_MODES = [27, 10, 12, 38]



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
        multicast_group=MULTICAST_GROUP,
        multicast_port=MULTICAST_PORT
    )

    datalinks.start()

    if USE_MESHTASTIC and datalinks.mesh_client:
        uav_id = datalinks.mesh_client.meshint.getMyNodeInfo()
        print(f"[INIT] My node ID: {uav_id}")

    # Initialize UAV
    mydrone = UAVControl(device=TELEMETRY_PORT, baudrate=115200, platform="AIRPLANE")
    mydrone.msp_receiver = False
    mini_modes = PRELOAD_MODES.copy()

    try:
        await mydrone.connect()
        await mydrone.telemetry_init()
        print("Connected to the flight controller")

        mydrone.load_modes_config()
        for mode_id in mydrone.modes:
            if mode_id not in mini_modes:
                mini_modes.append(mode_id)
        print('Modes bitmap:', mini_modes)

        while True:
            # Collect telemetry
            analog = mydrone.get_analog()
            modes = mydrone.get_board_modes()
            activemodes = [i for i, mode_id in enumerate(mini_modes) if mode_id in modes]
            modemap = list_to_int(activemodes)
            gpsd = mydrone.get_gps_data()
            speed = gpsd['speed']
            alt = mydrone.get_altitude()
            gps = froggeolib.GPSposition(gpsd['lat'], gpsd['lon'], alt)
            print(gps)
            if gps.lat == 0: gps.lat = 0.0001
            if gps.lon == 0: gps.lon = 0.0001
            if gps.alt == 0: gps.alt = 0.0001
            gyro = mydrone.get_attitude()
            full_mgrs = froggeolib.latlon_to_mgrs(gps.lat, gps.lon, precision=5)
            print(full_mgrs)
            pos = froggeolib.encode_mgrs_binary(full_mgrs, precision=5)

            msg_enum = Messages.Status.System.INAV
            
            msg_id = messageid(msg_enum)
            payload = msg_enum.payload(
                airspeed=int(speed),
                inavmodes=modemap,
                groundspeed=int(speed),
                heading=int(gyro["yaw"]),
                msl_alt=int(alt),
                packed_mgrs=pos
            )

            # Send telemetry
            encoded_message = encode_message(msg_enum, payload)
            datalinks.send(encoded_message, dest="gcs1", udp=USE_UDP)
            print(f"[SENT] Telemetry message, length: {len(encoded_message)} bytes")

            # Receive messages
            messages = datalinks.receive()
            for msg in messages:
                try:
                    category, subcategory, message, payload = decode_message(msg["data"])
                    print(f"[RECEIVED] Message from {msg['from']}: {category}.{subcategory}.{message}")

                    if category == Messages.Command.value:
                        print(f"Command payload: {payload}")
                        # Handle commands here

                except Exception as e:
                    print(f"[RECEIVED] Error decoding message: {e}")

            await asyncio.sleep(SEND_INTERVAL)

    except IOError as e:
        print(f"Node Error: {e}")
    except KeyboardInterrupt as e:
        print(f"Shut down")
    finally:
        mydrone.stop()
        datalinks.stop()
        print("Connection closed")

if __name__ == '__main__':
    asyncio.run(main())