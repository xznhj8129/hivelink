# hivelink/datalinks.py
import asyncio
import socket
import warnings
import json
from typing import Optional, Dict, Any, List, Tuple
import time
import crcmod
import sys
import msgpack
from frogtastic import MeshtasticClient
import traceback
import logging, base64, faulthandler

# at top of file (once)
import base64, enum, math, sys, traceback

B64_TAG = "__b64__"

def _to_jsonable(obj):
    if obj is None or isinstance(obj, (str, int, bool)):
        return obj
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, (bytes, bytearray, memoryview)):
        return {B64_TAG: base64.b64encode(bytes(obj)).decode("ascii")}
    if isinstance(obj, enum.IntEnum):
        return int(obj)
    if isinstance(obj, enum.Enum):
        return obj.name
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_to_jsonable(v) for v in obj]
    raise TypeError(f"Not JSON-serializable: {type(obj).__name__}")


# MQTT is optional
try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None

# Pull the message schema and codec in here so MQTT routing can live here
from hivelink.protocol import *
from hivelink.msglib import *

PROTOCOL_VERSION = 1
MAX_MESH_PACKET_SIZE = 220  # Total packet size (bytes)
SYNC_BYTE = 0xFA
crc16 = crcmod.predefined.mkCrcFun('crc-ccitt-false')


# --- UDP Packet Structure Definition ---
# [SYNC_BYTE, payload length, checksum, source id, destination id, payload]
def encode_udp_packet(source: str, destination: Optional[str], payload: bytes) -> bytes:
    s = source.encode("utf-8")
    d = (destination or "").encode("utf-8")
    checksum = crc16(s + d + payload)
    plen = len(payload)
    packet = msgpack.packb([SYNC_BYTE, plen, checksum, s, d, payload])
    return packet


def decode_udp_packet(packet: bytes) -> Tuple[str, str, bytes]:
    data = msgpack.unpackb(packet, use_list=True)
    if len(data) != 6:
        raise ValueError("Protocol Error: Packet length mismatch.")
    else:
        syncbyte, length, checksum, source, destination, payload = data

    if syncbyte != SYNC_BYTE:
        raise ValueError("Protocol Error: Sync byte mismatch")

    plen = len(payload)
    if plen != length:
        raise ValueError("Protocol Error: Length mismatch")

    # Verify checksum
    calc_checksum = crc16(source + destination + payload)
    if calc_checksum != checksum:
        raise ValueError("Protocol Error: Checksum mismatch.")

    return source.decode("utf-8"), destination.decode("utf-8"), payload


class DatalinkInterface:
    def __init__(
        self,
        use_meshtastic: bool = False,
        use_udp: bool = False,
        use_multicast: bool = False,
        wlan_device: Optional[str] = None,
        radio_port: Optional[str] = None,
        meshtastic_dataport: int = 260,
        socket_host: str = "127.0.0.1",
        socket_port: int = 5555,
        my_name: str = "",
        my_id: int = 0,
        nodemap: Dict[str, Dict[str, Any]] = {},
        multicast_group: str = "",
        multicast_port: Optional[int] = None,
        # MQTT config (all optional)
        mqtt_enable: bool = False,
        mqtt_broker: str = "",
        mqtt_port: int = 1883,
        mqtt_client_id: str = "",
        mqtt_username: Optional[str] = None,
        mqtt_password: Optional[str] = None,
        mqtt_base: str = "/hivelink/v1",
        incumbent_window: int = 600,
    ):
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

        # Do not override host/port from nodemap here; caller passes the right ones
        self.socket_host = socket_host
        self.socket_port = socket_port

        self.udp_sock = None
        self.multicast_sock = None
        self.mesh_client = None
        self.rx_buffer: List[Dict[str, Any]] = []
        self.running = False
        self.loop = asyncio.get_event_loop()
        self.meshmap: Dict[int, str] = {}

        self.multicast_group = multicast_group
        self.multicast_port = multicast_port if multicast_port is not None else self.socket_port

        # Presence/incumbent tracking
        self.localnodes: Dict[str, Dict[str, Any]] = {}
        self.incumbent_window = int(incumbent_window)

        # MQTT
        self.mqtt_enable = bool(mqtt_enable and mqtt is not None and mqtt_broker)
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = int(mqtt_port)
        self.mqtt_client_id = mqtt_client_id or self.my_name or "hivelink-node"
        self.mqtt_username = mqtt_username
        self.mqtt_password = mqtt_password
        self.mqtt_base = mqtt_base.rstrip("/")
        self.mqtt_client = None
        self._mqtt_connected = False

    # ---------- Presence / incumbent ----------
    def update_localnode_seen(self, src: str, intf: str, rssi=None, latency=None, ts: Optional[float] = None):
        self.localnodes[src] = {
            "last_seen": int(ts if ts is not None else time.time()),
            "intf": intf,
            "rssi": rssi,
            "latency": latency,
        }

    def is_incumbent_for(self, dest_id: str) -> bool:
        nfo = self.localnodes.get(dest_id)
        if not nfo:
            return False
        return (time.time() - nfo["last_seen"]) <= self.incumbent_window

    # ---------- Mesh node id mapping ----------
    def map_mesh_nodes(self):
        for name, info in self.nodemap.items():
            meshid = info.get("meshid", 0)
            if meshid:
                self.meshmap[meshid] = name

    # ---------- MQTT helpers ----------
    def _topic_from_msg(self, enum_member) -> str:
        # "Status.System.FLIGHT" style
        path = message_str_from_id(messageid(enum_member))
        category, typ, subtype = path.split(".")
        return f"{self.mqtt_base}/from/{self.my_name}/{category}/{typ}/{subtype}"


    def _from_jsonable(obj):
        if isinstance(obj, dict):
            if B64_TAG in obj and isinstance(obj[B64_TAG], str):
                return base64.b64decode(obj[B64_TAG].encode("ascii"))
            return {k: _from_jsonable(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_from_jsonable(v) for v in obj]
        return obj

    # inside class DatalinkInterface — make sure you have ONLY THIS version
    def _json_envelope(self, intf: str, enum_member, decoded_payload: dict, source: str, tstamp: float) -> bytes:
        body = {
            "intf": intf,
            "msgid": message_str_from_id(messageid(enum_member)),
            "data": _to_jsonable(decoded_payload),   # bytes-safe
            "from": source,
            "time": int(tstamp),
        }
        return json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


    def _setup_mqtt(self):
        if not self.mqtt_enable:
            return
        try:
            self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.mqtt_client_id)
            if self.mqtt_username or self.mqtt_password:
                self.mqtt_client.username_pw_set(self.mqtt_username or "", self.mqtt_password or "")

            self.mqtt_client.on_connect = self._on_mqtt_connect
            self.mqtt_client.on_message = self._on_mqtt_message
            self.mqtt_client.on_disconnect = self._on_mqtt_disconnect

            self.mqtt_client.connect(
                self.mqtt_broker,
                self.mqtt_port,
                keepalive=30,
                clean_start=mqtt.MQTT_CLEAN_START_FIRST_ONLY,
            )
            self.mqtt_client.loop_start()
        except Exception as e:
            warnings.warn(f"MQTT setup failed: {e}")
            self.mqtt_enable = False
            self.mqtt_client = None

    def _on_mqtt_connect(self, _client, _userdata, _flags, rc, _properties=None):
        self._mqtt_connected = (rc == 0)
        if not self._mqtt_connected:
            warnings.warn(f"MQTT connect error rc={rc}")
            return
        # Subscribe to commands to any dest; incumbent gating happens in handler
        self.mqtt_client.subscribe(f"{self.mqtt_base}/to/+/+/+/+")
        # Presence
        try:
            self.mqtt_client.publish(f"{self.mqtt_base}/from/{self.my_name}/status", b"online", qos=1, retain=True)
        except Exception:
            pass

    def _on_mqtt_disconnect(self, *_args, **_kwargs):
        self._mqtt_connected = False

    def _on_mqtt_message(self, _client, _userdata, m):
        try:
            # Topic: /hivelink/v1/to/<dest>/<Category>/<Type>/<Subtype>
            parts = m.topic.strip("/").split("/")
            if len(parts) < 7:
                return
            _, _, direction, dest_id, category, typ, subtype = parts[:7]
            if direction != "to":
                return

            body = json.loads(m.payload.decode("utf-8"))
            if not isinstance(body, dict):
                return
            data = body.get("data", body)

            # Optional: allow external systems to update presence
            src_hint = body.get("from")
            if src_hint:
                self.update_localnode_seen(src_hint, "mqtt")

            # Gate on incumbent
            if not self.is_incumbent_for(dest_id):
                return

            # Build enum and encode
            enum_member = getattr(getattr(getattr(Messages, category), typ), subtype)
            payload_obj = enum_member.payload(**data)
            encoded = encode_message(enum_member, payload_obj)

            sent = False
            try:
                if self.use_udp and dest_id in self.nodemap:
                    sent |= self.send(encoded, dest=dest_id, udp=True)
            except Exception:
                pass
            try:
                if self.use_meshtastic and dest_id in self.nodemap:
                    sent |= self.send(encoded, dest=dest_id, meshtastic=True)
            except Exception:
                pass

            if not sent:
                try:
                    if self.use_udp and self.multicast_group:
                        self.send(encoded, dest=None, multicast=True)
                except Exception:
                    pass

        except Exception as e:
            # keep the short warning if you want
            warnings.warn(f"[MQTT] inbound error: {e!r}")
            try:
                tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))
                sys.__stderr__.write(tb)
                sys.__stderr__.flush()
            except Exception:
                pass


    # ---------- Lifecycle ----------
    def start(self):
        if self.use_udp:
            print("Interface using UDP")
            self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.udp_sock.setblocking(False)
            self.udp_sock.bind((self.socket_host, self.socket_port))

            if self.use_multicast:
                if self.multicast_group == "" or not self.multicast_port:
                    raise ValueError("Group+port must be specified when using Multicast.")
                print(f"Interface using UDP Multicast on group {self.multicast_group} port {self.multicast_port}")
                self.multicast_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                self.multicast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    self.multicast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                except AttributeError:
                    pass
                self.multicast_sock.bind(("", self.multicast_port))
                self.multicast_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(self.socket_host))
                mreq = socket.inet_aton(self.multicast_group) + socket.inet_aton(self.socket_host)
                self.multicast_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
                self.multicast_sock.setblocking(False)

        if self.use_meshtastic:
            print("Interface using Meshtastic")
            if not self.radio_port:
                raise ValueError("Radio port must be specified when using Meshtastic.")
            self.mesh_client = MeshtasticClient(self.radio_port)

        # MQTT after interfaces so we can publish presence
        self._setup_mqtt()

        self.running = True
        if self.use_udp:
            asyncio.create_task(self._listen())
        self.map_mesh_nodes()
        print("Connected to interfaces")
        if self.use_meshtastic and self.mesh_client:
            try:
                meshid = self.mesh_client.meshint.getMyNodeInfo()
                print(f"[INIT] My node ID: {meshid}")
            except Exception:
                pass

    def stop(self):
        self.running = False

        # MQTT offline notice
        if self.mqtt_enable and self.mqtt_client is not None:
            try:
                if self._mqtt_connected:
                    self.mqtt_client.publish(f"{self.mqtt_base}/from/{self.my_name}/status", b"offline", qos=1, retain=True)
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            except Exception:
                pass
            finally:
                self.mqtt_client = None
                self._mqtt_connected = False

        if self.udp_sock:
            try:
                self.udp_sock.close()
            except Exception:
                pass
            self.udp_sock = None

        if self.multicast_sock:
            try:
                # Best effort drop membership
                try:
                    mreq = socket.inet_aton(self.multicast_group) + socket.inet_aton(self.socket_host)
                    self.multicast_sock.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, mreq)
                except Exception:
                    pass
                self.multicast_sock.close()
            except Exception:
                pass
            self.multicast_sock = None

        if self.mesh_client:
            try:
                self.mesh_client.meshint.close()
            except Exception:
                pass
            self.mesh_client = None

        print("Interfaces stopped")

    # ---------- I/O ----------
    async def _listen(self):
        print(f"UDP Listening on {self.socket_host}:{self.socket_port}")
        while self.running:
            if self.use_udp and self.udp_sock:
                try:
                    data, addr = await self.loop.run_in_executor(None, self.udp_sock.recvfrom, 1024)
                    source, dest, data = decode_udp_packet(data)
                    if data:
                        self.rx_buffer.append({"intf": "udp", "data": data, "from": source, "time": time.time()})
                except Exception as e:
                    err = str(e)
                    if "[Errno 11] Resource temporarily unavailable" not in err:
                        warnings.warn(f"Datalink UDP listen error: {str(e)}")

            if self.multicast_sock:
                try:
                    data, addr = await self.loop.run_in_executor(None, self.multicast_sock.recvfrom, 1024)
                    source, dest, data = decode_udp_packet(data)
                    if data:
                        self.rx_buffer.append({"intf": "multicast", "data": data, "from": source, "time": time.time()})
                except Exception as e:
                    err = str(e)
                    if "[Errno 11] Resource temporarily unavailable" not in err:
                        warnings.warn(f"Datalink Multicast listen error: {str(e)}")
            await asyncio.sleep(0.1)

    def send(
        self,
        data: bytes,
        dest: Optional[str] = None,
        udp: bool = False,
        meshtastic: bool = False,
        multicast: bool = False,
    ) -> bool:
        # UDP and Multicast
        try:
            if self.use_udp:
                if multicast and self.multicast_group != "":
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as send_sock:
                        send_sock.settimeout(2.0)
                        send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(self.socket_host))
                        send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
                        send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
                        encdat = encode_udp_packet(source=self.my_name, destination=dest, payload=data)
                        send_sock.sendto(encdat, (self.multicast_group, self.multicast_port))
                        return True
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

        # Meshtastic
        try:
            if self.use_meshtastic and self.mesh_client and meshtastic:
                dest_meshid = "^all" if dest is None or dest == "" else self.nodemap[dest]["meshid"]
                self.mesh_client.meshint.sendData(
                    data,
                    destinationId=dest_meshid,
                    portNum=self.link_port,
                    wantAck=True,
                )
                return True
        except Exception as e:
            warnings.warn(f"Datalink Meshtastic send failed: {str(e)}")
            return False

        return False

    def _publish_to_mqtt(self, src: str, intf: str, enum_member, decoded_payload: dict, tstamp: float):
        if not (self.mqtt_enable and self.mqtt_client and self._mqtt_connected):
            return
        try:
            topic = self._topic_from_msg(enum_member)
            env = self._json_envelope(intf, enum_member, decoded_payload, src, tstamp)
            self.mqtt_client.publish(topic, env, qos=0, retain=False)
        except Exception as e:
            sys.__stderr__.write(f"MQTT publish failed: {e}\n")
            traceback.print_exc(file=sys.__stderr__)
            sys.__stderr__.flush()

    def receive(self) -> List[Dict[str, Any]]:
        # Pull from Meshtastic mailbox
        if self.mesh_client is not None:
            try:
                for msg in self.mesh_client.checkMail():
                    if msg.get("port") == self.link_port:
                        try:
                            senderid_hex = msg.get("senderid", "").lstrip("!")
                            senderid = int(senderid_hex, 16) if senderid_hex else 0
                            source = self.meshmap.get(senderid, str(senderid))
                        except Exception:
                            source = "unknown"
                        self.rx_buffer.append(
                            {"intf": "meshtastic", "data": msg["data"], "from": source, "time": msg.get("time", time.time())}
                        )
            except Exception as e:
                warnings.warn(f"Meshtastic receive error: {e}")

        # Drain buffer (single shot)
        messages = self.rx_buffer.copy()
        self.rx_buffer.clear()

        # Presence update and optional MQTT publish (decoded here; the caller still gets raw)
        for msg in messages:
            try:
                self.update_localnode_seen(msg["from"], msg["intf"], ts=msg.get("time", time.time()))
                enum_member, decoded_payload = decode_message(msg["data"])
                self._publish_to_mqtt(msg["from"], msg["intf"], enum_member, decoded_payload, msg.get("time", time.time()))
            except Exception:
                # Keep receive resilient; decoding for MQTT is optional
                pass

        return messages


def load_nodes_map(path: str = "nodes.json") -> Dict[str, Any]:
    with open(path, "r") as file:
        return json.loads(file.read())
