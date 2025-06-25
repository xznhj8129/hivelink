import asyncio
import socket
import warnings
import json
from typing import Optional, Dict, Any
import time
import crcmod
import msgpack
from frogtastic import MeshtasticClient


PROTOCOL_VERSION = 1 
MAX_MESH_PACKET_SIZE = 220  # Total packet size (bytes)
SYNC_BYTE = 0xFA
crc16 = crcmod.predefined.mkCrcFun('crc-ccitt-false')
    
# --- UDP Packet Structure Definition ---
#[SYNC_BYTE, payload length, checksum, source id, destination id, payload]

def encode_udp_packet(source: str, destination: str, payload: bytes) -> bytes:
    s = bytes(source,'utf-8')
    d = bytes(destination,'utf-8')
    checksum = crc16(s + d + payload)
    plen = len(payload)
    packet = msgpack.packb([SYNC_BYTE, plen, checksum, s, d, payload])
    return packet

def decode_udp_packet(packet: bytes) -> dict:
    data = msgpack.unpackb(packet, use_list=True)
    if len(data) != 6:  # Minimum: StartByte, Length, Version, BinaryFlags, Routing, Checksum
        raise ValueError("Protocol Error: Packet length mismatch.")
        #return None
    else:
        syncbyte, length, checksum, source, destination, payload = data

    if syncbyte != SYNC_BYTE:
        raise ValueError("Protocol Error: Sync byte mismatch")
        
    plen = len(payload)
    if plen!=length:
        raise ValueError("Protocol Error: Length mismatch")

    # Verify checksum
    calc_checksum = crc16(source + destination + payload)
    if calc_checksum != checksum:
        raise ValueError("Protocol Error: Checksum mismatch.")

    return [source.decode('utf-8'), destination.decode('utf-8'), payload]

class DatalinkInterface:
    def __init__(self, 
                 use_meshtastic: bool = False,
                 use_udp: bool = False,
                 use_multicast: bool = False,
                 wlan_device: Optional[str] = None,
                 radio_port: Optional[str] = None,
                 meshtastic_dataport: int = 260,
                 socket_host: str = '127.0.0.1',  # Default, will be overridden by nodemap
                 socket_port: int = 5555,         # Default, will be overridden by nodemap
                 my_name: str = "",
                 my_id: int = 0,
                 nodemap: Dict[str, Dict] = {},
                 multicast_group: str = "",       # New parameter for multicast group
                 multicast_port: int = None):       # New parameter for multicast port
                 
        if not (use_meshtastic or use_udp):
            raise ValueError("At least one datalinks mode must be enabled.")
        
        self.use_meshtastic = use_meshtastic
        self.use_multicast = use_multicast
        self.use_udp = use_udp
        self.radio_port = radio_port
        self.link_port = meshtastic_dataport
        self.my_name = my_name
        self.my_id = my_id
        self.nodemap = nodemap
        
        # Set socket host and port based on my_id from nodemap
        if my_id and my_id in nodemap:
            self.socket_host, self.socket_port = nodemap[my_id]["ip"]
        else:
            self.socket_host = socket_host
            self.socket_port = socket_port

        self.udp_sock = None
        self.multicast_sock = None  # Multicast socket
        self.mesh_client = None
        self.rx_buffer = []
        self.running = False
        self.loop = asyncio.get_event_loop()
        self.meshmap = {}
        
        self.multicast_group = multicast_group  # Save the multicast group
        # Use separate multicast port if provided; otherwise default to socket_port
        self.multicast_port = multicast_port if multicast_port is not None else self.socket_port

    def map_mesh_nodes(self):
        for i in self.nodemap:
            meshid = self.nodemap[i]["meshid"]
            if meshid!=0:
                self.meshmap[self.nodemap[i]["meshid"]] = i

    def start(self):
        if self.use_udp:
            print("Interface using UDP")
            self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.udp_sock.setblocking(False)
            self.udp_sock.bind((self.socket_host, self.socket_port))
            
            # Create multicast socket if multicast_group is provided
            if self.use_multicast:
                if self.multicast_group=="" or not self.multicast_port:
                    raise ValueError("Group+port must be specified when using Multicast.")
                print(f"Interface using UDP Multicast on group {self.multicast_group} port {self.multicast_port}")
                self.multicast_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                self.multicast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    self.multicast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                except AttributeError:
                    pass
                # Bind multicast socket to the separate multicast port
                
                self.multicast_sock.bind(('', self.multicast_port))
                self.multicast_sock.setsockopt(
                    socket.IPPROTO_IP,
                    socket.IP_MULTICAST_IF,
                    socket.inet_aton(self.socket_host)
                )
                mreq = socket.inet_aton(self.multicast_group) + socket.inet_aton(self.socket_host)
                self.multicast_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
                self.multicast_sock.setblocking(False)

        if self.use_meshtastic:
            print("Interface using Meshtastic")
            if not self.radio_port:
                raise ValueError("Radio port must be specified when using Meshtastic.")
            self.mesh_client = MeshtasticClient(self.radio_port)
        
        self.running = True
        if self.use_udp:
            asyncio.create_task(self._listen())
        self.map_mesh_nodes()
        print("Connected to interfaces")

    def stop(self):
        self.running = False
        if self.udp_sock:
            self.udp_sock.close()
        if self.multicast_sock:
            self.multicast_sock.close()
        if self.mesh_client:
            self.mesh_client.meshint.close()
        print("Interfaces stopped")

    async def _listen(self):
        print(f"UDP Listening on {self.socket_host}:{self.socket_port}")
        while self.running:
            if self.use_udp and self.udp_sock:
                try:
                    #if hasattr(self.loop, 'sock_recvfrom'):
                    #    data, addr = await self.loop.sock_recvfrom(self.udp_sock, 1024)
                    #else:
                    data, addr = await self.loop.run_in_executor(None, self.udp_sock.recvfrom, 1024)
                    #print(data)
                    source, dest, data = decode_udp_packet(data)
                    if data:
                        self.rx_buffer.append(
                            {
                                "intf": "udp", 
                                "data": data, 
                                "from": source,
                                "time": time.time()
                                })
                except Exception as e:
                    err = str(e)
                    if "[Errno 11] Resource temporarily unavailable" not in err:
                        warnings.warn(f"Datalink UDP listen error: {str(e)}")

            if self.multicast_sock:
                try:
                    data, addr = await self.loop.run_in_executor(None, self.multicast_sock.recvfrom, 1024)
                    source, dest, data = decode_udp_packet(data)
                    if data:
                        self.rx_buffer.append({
                            "intf": "multicast", 
                            "data": data, 
                            "from": source,
                            "time": time.time()
                            })
                except Exception as e:
                    err = str(e)
                    if "[Errno 11] Resource temporarily unavailable" not in err:
                        warnings.warn(f"Datalink Multicast listen error: {str(e)}")
            await asyncio.sleep(0.1)


    def send(self, data: bytes, dest: Optional[str] = None, udp: bool = False, meshtastic: bool = False, multicast: bool = False) -> bool:
        try:
            if self.use_udp:
                # Send multicast if requested and a group is defined.
                if multicast and self.multicast_group != "":
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as send_sock:
                        send_sock.settimeout(2.0)
                        send_sock.setsockopt(
                            socket.IPPROTO_IP,
                            socket.IP_MULTICAST_IF,
                            socket.inet_aton(self.socket_host)
                        )
                        send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
                        send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
                        encdat = encode_udp_packet(source=self.my_name, destination=dest, payload=data)
                        send_sock.sendto(encdat, (self.multicast_group, self.multicast_port))
                        return True
                # Otherwise send unicast.
                elif dest in self.nodemap and udp:
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as send_sock:
                        send_sock.settimeout(2.0)
                        addr = self.nodemap[dest]["ip"]
                        encdat = encode_udp_packet(source=self.my_name, destination=dest, payload=data)
                        send_sock.sendto(encdat, tuple(addr))
                        return True
        except Exception as e:
            warnings.warn(f"Datalink UDP Send failed: {str(e)}")
            return False

        try:
            if self.use_meshtastic and self.mesh_client and meshtastic:
                dest_meshid = "^all" if dest is None else self.nodemap[dest]["meshid"]
                self.mesh_client.meshint.sendData(
                    data,
                    destinationId=dest_meshid,
                    portNum=self.link_port,
                    wantAck=True
                )
                return True
        except Exception as e:
            warnings.warn(f"Datalink Meshtastic send failed: {str(e)}")
            return False

        return False

    def receive(self) -> list:
        if self.mesh_client is not None:
            for msg in self.mesh_client.checkMail():
                if msg.get("port") == self.link_port:
                    senderid = int(msg.get("senderid").lstrip("!"), 16)
                    source = self.meshmap[senderid]
                    self.rx_buffer.append(
                        {
                            "intf": "meshtastic", 
                            "data": msg['data'], 
                            "from": source,
                            "time": msg["time"]
                        })
        messages = self.rx_buffer.copy()
        self.rx_buffer.clear()
        return messages

def load_nodes_map():
    with open("nodes.json", 'r') as file:
        return json.loads(file.read())


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