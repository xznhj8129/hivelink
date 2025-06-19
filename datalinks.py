import asyncio
import socket
import warnings
import json
from typing import Optional, Dict, Any
import time
import crcmod
from protocol import SYNC_BYTE, crc16, encode_udp_packet, decode_udp_packet

class DatalinkInterface:
    def __init__(self, 
                 use_meshtastic: bool = False,
                 use_udp: bool = False,
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
        
        self.multicast_group = multicast_group  # Save the multicast group
        # Use separate multicast port if provided; otherwise default to socket_port
        self.multicast_port = multicast_port if multicast_port is not None else self.socket_port

    def start(self):
        if self.use_udp:
            print("DatalinkInterface using UDP")
            self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.udp_sock.setblocking(False)
            self.udp_sock.bind((self.socket_host, self.socket_port))
            
            # Create multicast socket if multicast_group is provided
            if self.multicast_group != "":
                print(f"DatalinkInterface using UDP Multicast on group {self.multicast_group} port {self.multicast_port}")
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
            print("DatalinkInterface using Meshtastic")
            if not self.radio_port:
                raise ValueError("Radio port must be specified when using Meshtastic.")
            self.mesh_client = MeshtasticClient(self.radio_port)
        
        self.running = True
        asyncio.create_task(self._listen())
        print("Connected to datalinkss")

    def stop(self):
        self.running = False
        if self.udp_sock:
            self.udp_sock.close()
        if self.multicast_sock:
            self.multicast_sock.close()
        if self.mesh_client:
            self.mesh_client.meshint.close()
        print("DatalinkInterfaces stopped")

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
                        self.rx_buffer.append({"data": data, "from": source})
                except Exception as e:
                    err = str(e)
                    if "[Errno 11] Resource temporarily unavailable" not in err:
                        warnings.warn(f"Datalink Multicast listen error: {str(e)}")
            if self.multicast_sock:
                try:
                    #if hasattr(self.loop, 'sock_recvfrom'):
                    #    data, addr = await self.loop.sock_recvfrom(self.multicast_sock, 1024)
                    #else:
                    data, addr = await self.loop.run_in_executor(None, self.multicast_sock.recvfrom, 1024)
                    #print(data)
                    source, dest, data = decode_udp_packet(data)
                    if data:
                        self.rx_buffer.append({"data": data, "from": source})
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
                    self.rx_buffer.append(msg)
        messages = self.rx_buffer.copy()
        self.rx_buffer.clear()
        return messages

def load_nodes_map():
    with open("nodes.json", 'r') as file:
        return json.loads(file.read())



async def main():
    my_name = "gcs1"
    nodemap = load_nodes_map()
    my_id = nodemap[my_name][meshid]


    link_config = {
        "meshtastic": {
            "use": False,
            "radio_serial": '/dev/ttyACM0',
            "app_portnum": 260
        },
        "udp": {
            "use": True,
            "port": 5555,
            
        },

        "node_map": load_nodes_map()
    }
 
    datalinks = DatalinkInterface(
        use_meshtastic=link_config["meshtastic"]["use"],
        use_udp=link_config["udp"]["use"],
        my_id=my_id,
        nodemap=nodemap
    )

    datalinks.start()

    try:
        while True:
            msgs = datalinks.receive()
            if msgs:
                for msg in msgs:
                    print(f"Processed: {msg}")
            await asyncio.sleep(1)
    finally:
        datalinks.stop()

if __name__ == "__main__":
    asyncio.run(main())
