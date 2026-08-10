# hivelink/datalinks.py
from __future__ import annotations

import asyncio
import json
import socket
import time
import warnings
from typing import Any, Dict, List, Optional, Tuple

import crcmod
import msgpack

import hivelink.protocol as hl_proto
from occid import OCCIDModel

try:
    from frogtastic import MeshtasticClient
except ImportError:  # Optional bearer.
    MeshtasticClient = None


PROTOCOL_VERSION = 2
crc16 = crcmod.predefined.mkCrcFun("crc-ccitt-false")

encode_message = hl_proto.encode_message
decode_message = hl_proto.decode_message


# HiveLink delivery frame for UDP/multicast. The payload is canonical OCCID
# bytes; source/destination here are delivery addressing, not a second ontology.
def encode_udp_packet(source: str, destination: Optional[str], payload: bytes) -> bytes:
    source_bytes = source.encode("utf-8")
    destination_bytes = (destination or "").encode("utf-8")
    checksum = crc16(source_bytes + destination_bytes + payload)
    return msgpack.packb(
        [len(payload), checksum, source_bytes, destination_bytes, payload],
        use_bin_type=True,
    )


def decode_udp_packet(packet: bytes) -> Tuple[str, str, bytes]:
    data = msgpack.unpackb(packet, use_list=True, raw=False)
    if len(data) != 5:
        raise ValueError("Protocol Error: packet field count mismatch")
    length, checksum, source, destination, payload = data
    source_bytes = source.encode("utf-8") if isinstance(source, str) else bytes(source)
    destination_bytes = (
        destination.encode("utf-8") if isinstance(destination, str) else bytes(destination)
    )
    payload_bytes = bytes(payload)
    if len(payload_bytes) != int(length):
        raise ValueError("Protocol Error: payload length mismatch")
    if crc16(source_bytes + destination_bytes + payload_bytes) != int(checksum):
        raise ValueError("Protocol Error: checksum mismatch")
    return (
        source_bytes.decode("utf-8"),
        destination_bytes.decode("utf-8"),
        payload_bytes,
    )


class DatalinkInterface:
    """Deliver OCCID over the currently implemented HiveLink bearers.

    Direct UDP with a static node map is the permanent minimum. Meshtastic is an
    optional bearer behind the same send/receive model.
    """

    def __init__(
        self,
        use_meshtastic: bool = False,
        use_udp: bool = False,
        use_multicast: bool = False,
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
        incumbent_window: int = 600,
    ) -> None:
        if not (use_meshtastic or use_udp):
            raise ValueError("At least one HiveLink bearer must be enabled")
        if not my_name:
            raise ValueError("HiveLink my_name is required")

        self.nodemap = dict(nodemap or {})
        self.use_udp = bool(use_udp)
        self.use_multicast = bool(use_multicast)
        self.my_name = str(my_name)
        self.socket_host = str(socket_host)
        self.socket_port = int(socket_port)
        self.udp_sock: socket.socket | None = None
        self.multicast_sock: socket.socket | None = None
        self.rx_buffer: List[Dict[str, Any]] = []
        self.running = False
        self.loop: asyncio.AbstractEventLoop | None = None
        self._listen_tasks: list[asyncio.Task] = []

        self.use_meshtastic = bool(use_meshtastic)
        self.meshid = int(my_id)
        self.mesh_client = None
        self.radio_port = radio_port
        self.link_port = int(meshtastic_dataport)
        self.meshtastic_channel = int(meshtastic_channel)
        self.meshmap: Dict[int, str] = {}

        self.multicast_group = str(multicast_group)
        self.multicast_port = int(
            multicast_port if multicast_port is not None else self.socket_port
        )

        self.localnodes: Dict[str, Dict[str, Any]] = {}
        self.incumbent_window = int(incumbent_window)

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
        info = self.localnodes.get(dest_id)
        if not info:
            return False
        return (time.time() - float(info["last_seen"])) <= self.incumbent_window

    def map_mesh_nodes(self) -> None:
        self.meshmap.clear()
        for name, info in self.nodemap.items():
            meshid = info.get("meshid", 0)
            if meshid:
                self.meshmap[int(meshid)] = name

    async def _listen_socket(self, sock: socket.socket, intf: str) -> None:
        assert self.loop is not None
        while self.running:
            try:
                packet, _addr = await self.loop.sock_recvfrom(sock, 65535)
                source, dest, payload = decode_udp_packet(packet)
                if dest not in ("", self.my_name):
                    continue
                self.rx_buffer.append(
                    {
                        "intf": intf,
                        "data": payload,
                        "from": source,
                        "to": dest,
                        "time": time.time(),
                    }
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
            self._listen_tasks.append(
                self.loop.create_task(self._listen_socket(self.udp_sock, "udp"))
            )

            if self.use_multicast:
                if not self.multicast_group:
                    raise ValueError(
                        "multicast_group is required when multicast is enabled"
                    )
                self.multicast_sock = socket.socket(
                    socket.AF_INET,
                    socket.SOCK_DGRAM,
                    socket.IPPROTO_UDP,
                )
                self.multicast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    self.multicast_sock.setsockopt(
                        socket.SOL_SOCKET,
                        socket.SO_REUSEPORT,
                        1,
                    )
                except (AttributeError, OSError):
                    pass
                self.multicast_sock.bind(("", self.multicast_port))
                interface_addr = (
                    self.socket_host
                    if self.socket_host not in ("", "0.0.0.0")
                    else "0.0.0.0"
                )
                membership = socket.inet_aton(self.multicast_group) + socket.inet_aton(
                    interface_addr
                )
                self.multicast_sock.setsockopt(
                    socket.IPPROTO_IP,
                    socket.IP_ADD_MEMBERSHIP,
                    membership,
                )
                self.multicast_sock.setblocking(False)
                self._listen_tasks.append(
                    self.loop.create_task(
                        self._listen_socket(self.multicast_sock, "multicast")
                    )
                )

        if self.use_meshtastic:
            if MeshtasticClient is None:
                raise RuntimeError(
                    "frogtastic is required when the Meshtastic bearer is enabled"
                )
            if not self.radio_port:
                raise ValueError("radio_port is required when Meshtastic is enabled")
            self.mesh_client = MeshtasticClient(self.radio_port)
            self.meshid = self.mesh_client.meshint.getMyNodeInfo()["num"]

        self.map_mesh_nodes()
        print("HiveLink interfaces started")

    def stop(self) -> None:
        self.running = False
        for task in self._listen_tasks:
            task.cancel()
        self._listen_tasks.clear()

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
            raise KeyError(
                f"HiveLink destination {dest!r} has no static IP mapping"
            ) from exc
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
                    with socket.socket(
                        socket.AF_INET,
                        socket.SOCK_DGRAM,
                        socket.IPPROTO_UDP,
                    ) as send_sock:
                        if self.socket_host not in ("", "0.0.0.0"):
                            send_sock.setsockopt(
                                socket.IPPROTO_IP,
                                socket.IP_MULTICAST_IF,
                                socket.inet_aton(self.socket_host),
                            )
                        send_sock.setsockopt(
                            socket.IPPROTO_IP,
                            socket.IP_MULTICAST_TTL,
                            2,
                        )
                        send_sock.sendto(
                            encode_udp_packet(self.my_name, dest, payload),
                            (self.multicast_group, self.multicast_port),
                        )
                        sent = True
                elif udp and dest:
                    addr = self._udp_destination(dest)
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as send_sock:
                        send_sock.sendto(
                            encode_udp_packet(self.my_name, dest, payload),
                            addr,
                        )
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
