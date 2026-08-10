# hivelink/datalinks.py
from __future__ import annotations

import asyncio
import base64
import enum
import json
import math
import socket
import sys
import time
import traceback
import warnings
from typing import Any, Dict, List, Optional, Tuple

import crcmod
import msgpack

import hivelink.protocol as hl_proto
from occid import OCCIDModel

try:
    import paho.mqtt.client as mqtt
except ImportError:  # Optional bearer.
    mqtt = None

try:
    from frogtastic import MeshtasticClient
except ImportError:  # Optional bearer.
    MeshtasticClient = None


PROTOCOL_VERSION = 2
MAX_MESH_PACKET_SIZE = 220
crc16 = crcmod.predefined.mkCrcFun("crc-ccitt-false")
B64_TAG = "__b64__"

encode_message = hl_proto.encode_message
decode_message = hl_proto.decode_message


def _to_jsonable(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, bool)):
        return obj
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, (bytes, bytearray, memoryview)):
        return {B64_TAG: base64.b64encode(bytes(obj)).decode("ascii")}
    if isinstance(obj, enum.IntEnum):
        return int(obj)
    if isinstance(obj, enum.Enum):
        return obj.value
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_to_jsonable(v) for v in obj]
    raise TypeError(f"Not JSON-serializable: {type(obj).__name__}")


def _from_jsonable(obj: Any) -> Any:
    if isinstance(obj, dict):
        if B64_TAG in obj and isinstance(obj[B64_TAG], str):
            return base64.b64decode(obj[B64_TAG].encode("ascii"))
        return {k: _from_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_from_jsonable(v) for v in obj]
    return obj


# HiveLink delivery frame for UDP/multicast. The payload is canonical OCCID
# bytes; source/destination here are delivery addressing, not a second ontology.
def encode_udp_packet(source: str, destination: Optional[str], payload: bytes) -> bytes:
    s = source.encode("utf-8")
    d = (destination or "").encode("utf-8")
    checksum = crc16(s + d + payload)
    return msgpack.packb([len(payload), checksum, s, d, payload], use_bin_type=True)


def decode_udp_packet(packet: bytes) -> Tuple[str, str, bytes]:
    data = msgpack.unpackb(packet, use_list=True, raw=False)
    if len(data) != 5:
        raise ValueError("Protocol Error: packet field count mismatch")
    length, checksum, source, destination, payload = data
    if isinstance(source, str):
        source_b = source.encode("utf-8")
    else:
        source_b = bytes(source)
    if isinstance(destination, str):
        destination_b = destination.encode("utf-8")
    else:
        destination_b = bytes(destination)
    payload_b = bytes(payload)
    if len(payload_b) != int(length):
        raise ValueError("Protocol Error: payload length mismatch")
    if crc16(source_b + destination_b + payload_b) != int(checksum):
        raise ValueError("Protocol Error: checksum mismatch")
    return source_b.decode("utf-8"), destination_b.decode("utf-8"), payload_b


class DatalinkInterface:
    """Small delivery facade over HiveLink bearers.

    The permanent baseline is intentionally boring: a static node map plus UDP
    is sufficient. Other bearers remain optional implementations behind this
    same interface.
    """

    def __init__(
        self,
        use_meshtastic: bool = False,
        use_udp: bool = False,
        use_multicast: bool = False,
        wlan_device: Optional[str] = None,
        radio_port: Optional[str] = None,
        meshtastic_dataport: int = 260,
        meshtastic_channel: int = 0,
        socket_host: str = "0.0.0.0",
        socket_port: int = 5555,
        my_name: str = "",
        my_id: int = 0,
        nodemap: Optional[Dict[str, Dict[str, Any]]] = None,
        multicast_group: str = "",
        multicast_port: Optional[int] = None,
        mqtt_enable: bool = False,
        mqtt_broker: str = "",
        mqtt_port: int = 1883,
        mqtt_client_id: str = "",
        mqtt_username: Optional[str] = None,
        mqtt_password: Optional[str] = None,
        mqtt_base: str = "/hivelink/v2",
        incumbent_window: int = 600,
    ) -> None:
        if not (use_meshtastic or use_udp or mqtt_enable):
            raise ValueError("At least one HiveLink bearer must be enabled")

        self.nodemap = dict(nodemap or {})
        self.use_multicast = bool(use_multicast)
        self.use_udp = bool(use_udp)
        self.my_name = str(my_name)
        self.socket_host = str(socket_host)
        self.socket_port = int(socket_port)
        self.udp_sock: socket.socket | None = None
        self.multicast_sock: socket.socket | None = None
        self.rx_buffer: List[Dict[str, Any]] = []
        self.running = False
        self.loop: asyncio.AbstractEventLoop | None = None
        self._listen_tasks: list[asyncio.Task] = []
        self.meshmap: Dict[int, str] = {}

        self.use_meshtastic = bool(use_meshtastic)
        self.meshid = int(my_id)
        self.mesh_client = None
        self.radio_port = radio_port
        self.link_port = int(meshtastic_dataport)
        self.meshtastic_channel = int(meshtastic_channel)

        self.multicast_group = str(multicast_group)
        self.multicast_port = int(multicast_port if multicast_port is not None else self.socket_port)

        self.localnodes: Dict[str, Dict[str, Any]] = {}
        self.incumbent_window = int(incumbent_window)

        self.mqtt_enable = bool(mqtt_enable and mqtt is not None and mqtt_broker)
        self.mqtt_broker = str(mqtt_broker)
        self.mqtt_port = int(mqtt_port)
        self.mqtt_client_id = str(mqtt_client_id)
        self.mqtt_username = mqtt_username
        self.mqtt_password = mqtt_password
        self.mqtt_base = mqtt_base.rstrip("/")
        self.mqtt_client = None
        self._mqtt_connected = False

    def update_localnode_seen(
        self,
        src: str,
        intf: str,
        rssi: Any = None,
        latency: Any = None,
        ts: Optional[float] = None,
    ) -> None:
        self.localnodes[src] = {
            "last_seen": float(time.time() if ts is None else ts),
            "intf": intf,
            "rssi": rssi,
            "latency": latency,
        }

    def is_incumbent_for(self, dest_id: str) -> bool:
        nfo = self.localnodes.get(dest_id)
        if not nfo:
            return False
        return (time.time() - float(nfo["last_seen"])) <= self.incumbent_window

    def map_mesh_nodes(self) -> None:
        for name, info in self.nodemap.items():
            meshid = info.get("meshid", 0)
            if meshid:
                self.meshmap[int(meshid)] = name

    def _topic_from_model(self, source: str, model: OCCIDModel) -> str:
        return f"{self.mqtt_base}/from/{source}/{type(model).__name__}"

    def _json_model(self, intf: str, source: str, model: OCCIDModel, tstamp: float) -> bytes:
        body = {
            "intf": intf,
            "from": source,
            "time": float(tstamp),
            "model_type": type(model).__name__,
            "payload": _to_jsonable(model.model_dump(mode="json", exclude_none=True)),
        }
        return json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    def _setup_mqtt(self) -> None:
        if not self.mqtt_enable:
            return
        if mqtt is None:
            raise RuntimeError("paho-mqtt is required when the MQTT bearer is enabled")
        try:
            self.mqtt_client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2,
                client_id=self.mqtt_client_id,
            )
            if self.mqtt_username or self.mqtt_password:
                self.mqtt_client.username_pw_set(self.mqtt_username or "", self.mqtt_password or "")
            self.mqtt_client.on_connect = self._on_mqtt_connect
            self.mqtt_client.on_message = self._on_mqtt_message
            self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, keepalive=30)
            self.mqtt_client.loop_start()
        except Exception as exc:
            warnings.warn(f"HiveLink MQTT setup failed: {exc}")
            self.mqtt_enable = False
            self.mqtt_client = None

    def _on_mqtt_connect(self, _client, _userdata, _flags, rc, _properties=None) -> None:
        self._mqtt_connected = int(rc) == 0
        if not self._mqtt_connected:
            warnings.warn(f"HiveLink MQTT connect error rc={rc}")
            return
        self.mqtt_client.subscribe(f"{self.mqtt_base}/to/+/+")
        self.mqtt_client.publish(
            f"{self.mqtt_base}/from/{self.my_name}/status",
            b"online",
            qos=1,
            retain=True,
        )

    def _on_mqtt_disconnect(self, *_args, **_kwargs) -> None:
        self._mqtt_connected = False

    def _on_mqtt_message(self, _client, _userdata, message) -> None:
        """Optional MQTT-to-HiveLink bridge for existing installations.

        MQTT is merely another HiveLink bearer/gateway here. It is unrelated to
        MPFC's private node-local MQTT IPC.
        """
        try:
            parts = message.topic.strip("/").split("/")
            if len(parts) < 5:
                return
            _, _, direction, dest_id, _model_name = parts[:5]
            if direction != "to":
                return
            body = json.loads(message.payload.decode("utf-8"))
            source = str(body.get("from") or "mqtt")
            encoded_b64 = body.get("occid_b64")
            if not encoded_b64:
                return
            encoded = base64.b64decode(str(encoded_b64), validate=True)
            decode_message(encoded)
            self.update_localnode_seen(source, "mqtt")
            self.send(encoded, dest=dest_id, udp=self.use_udp, meshtastic=self.use_meshtastic)
        except Exception as exc:
            warnings.warn(f"[HiveLink MQTT] inbound error: {exc!r}")

    async def _listen_socket(self, sock: socket.socket, intf: str) -> None:
        assert self.loop is not None
        while self.running:
            try:
                packet, _addr = await self.loop.sock_recvfrom(sock, 65535)
                source, dest, payload = decode_udp_packet(packet)
                if dest not in ("", self.my_name):
                    continue
                self.rx_buffer.append(
                    {"intf": intf, "data": payload, "from": source, "to": dest, "time": time.time()}
                )
            except asyncio.CancelledError:
                return
            except Exception as exc:
                if self.running:
                    warnings.warn(f"HiveLink {intf} receive error: {exc}")
                    await asyncio.sleep(0.05)

    def start(self) -> None:
        self.loop = asyncio.get_running_loop()
        self.running = True

        if self.use_udp:
            self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.udp_sock.setblocking(False)
            self.udp_sock.bind((self.socket_host, self.socket_port))
            print(f"HiveLink UDP listening on {self.socket_host}:{self.socket_port}")
            self._listen_tasks.append(self.loop.create_task(self._listen_socket(self.udp_sock, "udp")))

            if self.use_multicast:
                if not self.multicast_group:
                    raise ValueError("multicast_group is required when multicast is enabled")
                self.multicast_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                self.multicast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    self.multicast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                except (AttributeError, OSError):
                    pass
                self.multicast_sock.bind(("", self.multicast_port))
                interface_addr = self.socket_host if self.socket_host not in ("", "0.0.0.0") else "0.0.0.0"
                mreq = socket.inet_aton(self.multicast_group) + socket.inet_aton(interface_addr)
                self.multicast_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
                self.multicast_sock.setblocking(False)
                self._listen_tasks.append(
                    self.loop.create_task(self._listen_socket(self.multicast_sock, "multicast"))
                )

        if self.use_meshtastic:
            if MeshtasticClient is None:
                raise RuntimeError("frogtastic is required when the Meshtastic bearer is enabled")
            if not self.radio_port:
                raise ValueError("radio_port is required when Meshtastic is enabled")
            self.mesh_client = MeshtasticClient(self.radio_port)
            self.meshid = self.mesh_client.meshint.getMyNodeInfo()["num"]

        self.map_mesh_nodes()
        self._setup_mqtt()
        print("HiveLink interfaces started")

    def stop(self) -> None:
        self.running = False
        for task in self._listen_tasks:
            task.cancel()
        self._listen_tasks.clear()

        if self.mqtt_client is not None:
            try:
                if self._mqtt_connected:
                    self.mqtt_client.publish(
                        f"{self.mqtt_base}/from/{self.my_name}/status",
                        b"offline",
                        qos=1,
                        retain=True,
                    )
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            except Exception:
                pass
            self.mqtt_client = None
            self._mqtt_connected = False

        for sock_name in ("udp_sock", "multicast_sock"):
            sock = getattr(self, sock_name)
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass
                setattr(self, sock_name, None)

        if self.mesh_client is not None:
            try:
                self.mesh_client.meshint.close()
            except Exception:
                pass
            self.mesh_client = None
        print("HiveLink interfaces stopped")

    def _udp_destination(self, dest: str) -> tuple[str, int]:
        try:
            value = self.nodemap[dest]["ip"]
        except KeyError as exc:
            raise KeyError(f"HiveLink destination {dest!r} has no static IP mapping") from exc
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise ValueError(f"HiveLink nodemap[{dest!r}].ip must be [host, port]")
        return str(value[0]), int(value[1])

    def send(
        self,
        data: bytes,
        dest: Optional[str] = None,
        udp: bool = False,
        meshtastic: bool = False,
        multicast: bool = False,
    ) -> bool:
        payload = bytes(data)
        sent = False

        try:
            if self.use_udp:
                if multicast and self.multicast_group:
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as send_sock:
                        if self.socket_host not in ("", "0.0.0.0"):
                            send_sock.setsockopt(
                                socket.IPPROTO_IP,
                                socket.IP_MULTICAST_IF,
                                socket.inet_aton(self.socket_host),
                            )
                        send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
                        send_sock.sendto(
                            encode_udp_packet(self.my_name, dest, payload),
                            (self.multicast_group, self.multicast_port),
                        )
                        sent = True
                elif udp and dest:
                    addr = self._udp_destination(dest)
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as send_sock:
                        send_sock.sendto(encode_udp_packet(self.my_name, dest, payload), addr)
                    sent = True
        except Exception as exc:
            warnings.warn(f"HiveLink UDP send failed: {exc}")
            return False

        try:
            if self.use_meshtastic and self.mesh_client is not None and meshtastic:
                destination_id = "^all" if not dest else self.nodemap[dest]["meshid"]
                self.mesh_client.meshint.sendData(
                    payload,
                    destinationId=destination_id,
                    portNum=self.link_port,
                    channelIndex=self.meshtastic_channel,
                    hopLimit=None,
                    wantAck=True,
                )
                sent = True
        except Exception as exc:
            warnings.warn(f"HiveLink Meshtastic send failed: {exc}")
            return False

        return sent

    def send_model(
        self,
        model: OCCIDModel,
        dest: str,
        *,
        udp: bool = True,
        meshtastic: bool = False,
        multicast: bool = False,
    ) -> bool:
        """Encode and send one OCCID model to a HiveLink node."""
        return self.send(
            encode_message(model),
            dest=dest,
            udp=udp,
            meshtastic=meshtastic,
            multicast=multicast,
        )

    def _publish_to_mqtt(self, msg: Dict[str, Any], model: OCCIDModel) -> None:
        if not (self.mqtt_enable and self.mqtt_client and self._mqtt_connected):
            return
        try:
            topic = self._topic_from_model(str(msg["from"]), model)
            body = self._json_model(
                str(msg["intf"]),
                str(msg["from"]),
                model,
                float(msg.get("time", time.time())),
            )
            self.mqtt_client.publish(topic, body, qos=0, retain=False)
        except Exception as exc:
            sys.__stderr__.write(f"HiveLink MQTT publish failed: {exc}\n")
            traceback.print_exc(file=sys.__stderr__)
            sys.__stderr__.flush()

    def receive(self) -> List[Dict[str, Any]]:
        if self.mesh_client is not None:
            try:
                for msg in self.mesh_client.checkMail():
                    if msg.get("port") != self.link_port:
                        continue
                    try:
                        sender_hex = str(msg.get("senderid", "")).lstrip("!")
                        sender_num = int(sender_hex, 16) if sender_hex else 0
                        source = self.meshmap.get(sender_num, str(sender_num))
                    except Exception:
                        source = "unknown"
                    self.rx_buffer.append(
                        {
                            "intf": "meshtastic",
                            "data": msg["data"],
                            "from": source,
                            "to": self.my_name,
                            "time": msg.get("time", time.time()),
                        }
                    )
            except Exception as exc:
                warnings.warn(f"HiveLink Meshtastic receive error: {exc}")

        messages = self.rx_buffer.copy()
        self.rx_buffer.clear()
        for msg in messages:
            self.update_localnode_seen(
                str(msg["from"]),
                str(msg["intf"]),
                ts=float(msg.get("time", time.time())),
            )
            try:
                model = decode_message(msg["data"])
            except Exception:
                continue
            self._publish_to_mqtt(msg, model)
        return messages

    def receive_models(self) -> List[Dict[str, Any]]:
        """Receive frames with canonical OCCID models already decoded."""
        decoded: List[Dict[str, Any]] = []
        for msg in self.receive():
            model = decode_message(msg["data"])
            decoded.append({**msg, "model": model})
        return decoded


def load_nodes_map(path: str = "nodes.json") -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)
