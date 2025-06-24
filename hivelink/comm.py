from typing import Dict, Any, List
from .datalinks import DatalinkInterface
from .protocol import encode_message, decode_message
from .message_structure import Messages

class CommNode:
    """High level wrapper around DatalinkInterface with message helpers."""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.link = DatalinkInterface(
            use_meshtastic=config.get("meshtastic", {}).get("use", False),
            radio_port=config.get("meshtastic", {}).get("radio_serial"),
            meshtastic_dataport=config.get("meshtastic", {}).get("app_portnum", 260),
            use_udp=config.get("udp", {}).get("use", False),
            socket_host=config.get("udp", {}).get("host", "127.0.0.1"),
            socket_port=config.get("udp", {}).get("port", 5555),
            my_name=config.get("my_name", ""),
            my_id=config.get("my_id", 0),
            nodemap=config.get("nodemap", {}),
            multicast_group=config.get("udp", {}).get("multicast_group", ""),
            multicast_port=config.get("udp", {}).get("multicast_port"),
        )

    def start(self) -> None:
        self.link.start()

    def stop(self) -> None:
        self.link.stop()

    def send_message(self, msg_enum: Messages, payload: Dict[str, Any], *, dest: str, udp: bool=False, meshtastic: bool=False, multicast: bool=False) -> None:
        packed = msg_enum.payload(**payload)
        encoded = encode_message(msg_enum, packed)
        self.link.send(encoded, dest=dest, udp=udp, meshtastic=meshtastic, multicast=multicast)

    def receive_messages(self) -> List[Dict[str, Any]]:
        messages = []
        for msg in self.link.receive():
            try:
                msg_enum, payload = decode_message(msg["data"])
                msg.update({"msg_enum": msg_enum, "payload": payload})
                messages.append(msg)
            except Exception:
                continue
        return messages

