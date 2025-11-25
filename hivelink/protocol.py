PROTOCOL_VERSION = 1
PROTOCOL_NAME = "test"

from enum import Enum, IntEnum, auto

# This file is auto generated, refer to gen_definitions.py

class MessageCategory(Enum):
    Heartbeat = 1
    Testing = 2
    Network = 3
    Reply = 4
    Status = 5
    Command = 6

class Messages:
    class Heartbeat:
        class System(Enum):
            HEARTBEAT = auto()
    class Testing:
        class System(Enum):
            TEXTMSG = auto()
            BINMSG = auto()
    class Network:
        class System(Enum):
            ONLINE = auto()
            FIND = auto()
            PING = auto()
    class Reply:
        class Network(Enum):
            ACK = auto()
            FIND = auto()
        class Command(Enum):
            RESULT = auto()
    class Status:
        class System(Enum):
            FLIGHT = auto()
            POSITION = auto()
        class AP(Enum):
            HL_TELEM = auto()
        class INAV(Enum):
            TELEM = auto()
    class Command:
        class System(Enum):
            ACTIVATE = auto()
            SHUTDOWN = auto()
            SET_FLIGHT_MODE = auto()
            SWITCH_DATALINK = auto()
            DATALINK_CONFIG = auto()
        class AP(Enum):
            ARM = auto()
            DISARM = auto()
            SET_MODE = auto()
            TAKEOFF = auto()
            LAND = auto()
            SELECT_MISSION = auto()


Messages.Heartbeat.System.value_subcat = 1
Messages.Heartbeat.System.str = 'System'
Messages.Testing.System.value_subcat = 1
Messages.Testing.System.str = 'System'
Messages.Network.System.value_subcat = 1
Messages.Network.System.str = 'System'
Messages.Reply.Network.value_subcat = 1
Messages.Reply.Network.str = 'Network'
Messages.Reply.Command.value_subcat = 2
Messages.Reply.Command.str = 'Command'
Messages.Status.System.value_subcat = 1
Messages.Status.System.str = 'System'
Messages.Status.AP.value_subcat = 2
Messages.Status.AP.str = 'AP'
Messages.Status.INAV.value_subcat = 3
Messages.Status.INAV.str = 'INAV'
Messages.Command.System.value_subcat = 1
Messages.Command.System.str = 'System'
Messages.Command.AP.value_subcat = 2
Messages.Command.AP.str = 'AP'
Messages.Heartbeat.value_cat = 1
Messages.Heartbeat.str = 'Heartbeat'
Messages.Testing.value_cat = 2
Messages.Testing.str = 'Testing'
Messages.Network.value_cat = 3
Messages.Network.str = 'Network'
Messages.Reply.value_cat = 4
Messages.Reply.str = 'Reply'
Messages.Status.value_cat = 5
Messages.Status.str = 'Status'
Messages.Command.value_cat = 6
Messages.Command.str = 'Command'
Messages.Heartbeat.System.HEARTBEAT.payload_def = []
Messages.Testing.System.TEXTMSG.payload_def = [{'name': 'textdata', 'datatype': 'string', 'bitmask': False}]
Messages.Testing.System.BINMSG.payload_def = [{'name': 'data', 'datatype': 'bytes', 'bitmask': False}]
Messages.Network.System.ONLINE.payload_def = []
Messages.Network.System.FIND.payload_def = [{'name': 'id', 'datatype': 'bytes', 'bitmask': False}]
Messages.Network.System.PING.payload_def = []
Messages.Reply.Network.ACK.payload_def = []
Messages.Reply.Network.FIND.payload_def = [{'name': 'found', 'datatype': 'bool', 'bitmask': False}, {'name': 'intf', 'datatype': 'bytes', 'bitmask': True}, {'name': 'loss', 'datatype': 'int', 'bitmask': False}, {'name': 'latency', 'datatype': 'int', 'bitmask': False}, {'name': 'rssi', 'datatype': 'int', 'bitmask': False}, {'name': 'snr', 'datatype': 'int', 'bitmask': False}]
Messages.Reply.Command.RESULT.payload_def = [{'name': 'CommandResult', 'datatype': 'enum', 'bitmask': False}]
Messages.Status.System.FLIGHT.payload_def = [{'name': 'FlightMode', 'datatype': 'enum', 'bitmask': False}, {'name': 'airspeed', 'datatype': 'int', 'bitmask': False}, {'name': 'groundspeed', 'datatype': 'int', 'bitmask': False}, {'name': 'heading', 'datatype': 'int', 'bitmask': False}, {'name': 'msl_alt', 'datatype': 'int', 'bitmask': False}, {'name': 'lat', 'datatype': 'int', 'bitmask': False}, {'name': 'lon', 'datatype': 'int', 'bitmask': False}]
Messages.Status.System.POSITION.payload_def = [{'name': 'lat', 'datatype': 'int', 'bitmask': False}, {'name': 'lon', 'datatype': 'int', 'bitmask': False}]
Messages.Status.AP.HL_TELEM.payload_def = [{'name': 'mode_str', 'datatype': 'string', 'bitmask': False}, {'name': 'airspeed', 'datatype': 'int', 'bitmask': False}, {'name': 'groundspeed', 'datatype': 'int', 'bitmask': False}, {'name': 'heading', 'datatype': 'int', 'bitmask': False}, {'name': 'msl_alt', 'datatype': 'int', 'bitmask': False}, {'name': 'lat', 'datatype': 'int', 'bitmask': False}, {'name': 'lon', 'datatype': 'int', 'bitmask': False}]
Messages.Status.INAV.TELEM.payload_def = [{'name': 'inavmodes', 'datatype': 'int', 'bitmask': False}, {'name': 'airspeed', 'datatype': 'int', 'bitmask': False}, {'name': 'groundspeed', 'datatype': 'int', 'bitmask': False}, {'name': 'heading', 'datatype': 'int', 'bitmask': False}, {'name': 'msl_alt', 'datatype': 'int', 'bitmask': False}, {'name': 'lat', 'datatype': 'int', 'bitmask': False}, {'name': 'lon', 'datatype': 'int', 'bitmask': False}]
Messages.Command.System.ACTIVATE.payload_def = []
Messages.Command.System.SHUTDOWN.payload_def = []
Messages.Command.System.SET_FLIGHT_MODE.payload_def = []
Messages.Command.System.SWITCH_DATALINK.payload_def = []
Messages.Command.System.DATALINK_CONFIG.payload_def = []
Messages.Command.AP.ARM.payload_def = []
Messages.Command.AP.DISARM.payload_def = []
Messages.Command.AP.SET_MODE.payload_def = [{'name': 'mode_str', 'datatype': 'bytes', 'bitmask': False}]
Messages.Command.AP.TAKEOFF.payload_def = [{'name': 'alt_m', 'datatype': 'int', 'bitmask': False}]
Messages.Command.AP.LAND.payload_def = []
Messages.Command.AP.SELECT_MISSION.payload_def = [{'name': 'seq', 'datatype': 'int', 'bitmask': False}]

Messages.Heartbeat.System.category = Messages.Heartbeat
Messages.Heartbeat.System.category_name = 'Heartbeat'
Messages.Heartbeat.System.category_value = 1
Messages.Heartbeat.System.subcategory_name = 'System'
Messages.Heartbeat.System.subcategory_value = 1
Messages.Testing.System.category = Messages.Testing
Messages.Testing.System.category_name = 'Testing'
Messages.Testing.System.category_value = 2
Messages.Testing.System.subcategory_name = 'System'
Messages.Testing.System.subcategory_value = 1
Messages.Network.System.category = Messages.Network
Messages.Network.System.category_name = 'Network'
Messages.Network.System.category_value = 3
Messages.Network.System.subcategory_name = 'System'
Messages.Network.System.subcategory_value = 1
Messages.Reply.Network.category = Messages.Reply
Messages.Reply.Network.category_name = 'Reply'
Messages.Reply.Network.category_value = 4
Messages.Reply.Network.subcategory_name = 'Network'
Messages.Reply.Network.subcategory_value = 1
Messages.Reply.Command.category = Messages.Reply
Messages.Reply.Command.category_name = 'Reply'
Messages.Reply.Command.category_value = 4
Messages.Reply.Command.subcategory_name = 'Command'
Messages.Reply.Command.subcategory_value = 2
Messages.Status.System.category = Messages.Status
Messages.Status.System.category_name = 'Status'
Messages.Status.System.category_value = 5
Messages.Status.System.subcategory_name = 'System'
Messages.Status.System.subcategory_value = 1
Messages.Status.AP.category = Messages.Status
Messages.Status.AP.category_name = 'Status'
Messages.Status.AP.category_value = 5
Messages.Status.AP.subcategory_name = 'AP'
Messages.Status.AP.subcategory_value = 2
Messages.Status.INAV.category = Messages.Status
Messages.Status.INAV.category_name = 'Status'
Messages.Status.INAV.category_value = 5
Messages.Status.INAV.subcategory_name = 'INAV'
Messages.Status.INAV.subcategory_value = 3
Messages.Command.System.category = Messages.Command
Messages.Command.System.category_name = 'Command'
Messages.Command.System.category_value = 6
Messages.Command.System.subcategory_name = 'System'
Messages.Command.System.subcategory_value = 1
Messages.Command.AP.category = Messages.Command
Messages.Command.AP.category_name = 'Command'
Messages.Command.AP.category_value = 6
Messages.Command.AP.subcategory_name = 'AP'
Messages.Command.AP.subcategory_value = 2


class PayloadEnum:
    class CommandResult(IntEnum):
        # Reply to Command
        ACCEPTED = 1
        TEMPORARILY_REJECTED = 2
        DENIED = 3
        UNSUPPORTED = 4
        FAILED = 5
        IN_PROGRESS = 6
        CANCELLED = 7

    class DataError(IntEnum):
        # Reply to Data
        NOT_FOUND = 1
        DEVICE_UNAVAILABLE = 2
        HARDWARE_ERROR = 3
        SOFTWARE_ERROR = 4
        DATABASE_ERROR = 5

    class FlightMode(IntEnum):
        # 
        ACRO = 1
        ANGLE = 2
        POSHOLD = 3
        NAV_WP = 4
        LOITER = 5
        CRUSE = 6
        RTH = 7
        LANDING = 8
        DISARMED = 9

    class FlightPhase(IntEnum):
        # 
        PREFLIGHT = 1
        TAKEOFF = 2
        CRUISE = 3
        MISSION_OPERATION = 4
        RTB = 5
        LANDING = 6
        POSTFLIGHT = 7

    class MissionPhase(IntEnum):
        # 
        BOOTING = 1
        ONLINE = 2
        MISSION_RECEIVED = 3
        READY_TAKEOFF = 4
        TAKEOFF_COMPLETE = 5
        ENROUTE = 6
        AT_ASSEMBLY = 7
        HOLDING = 8
        PROCEEDING = 9
        BINGO = 10
        RTB = 11
        LANDING = 12
        LANDED = 13
        SHUTDOWN = 14

