PROTOCOL_VERSION = 1
PROTOCOL_NAME = "test"

from enum import Enum, IntEnum, auto

# This file is auto generated, refer to gen_definitions.py

class MessageCategory(Enum):
    Heartbeat = 1
    Testing = 2
    Status = 3
    Command = 4
    Event = 5
    Data = 6

class Messages:
    class Heartbeat:
        class System(Enum):
            HEARTBEAT = auto()
    class Testing:
        class System(Enum):
            TEXTMSG = auto()
            BINMSG = auto()
    class Status:
        class Mission(Enum):
            MISSION_PHASE = auto()
        class System(Enum):
            INAV = auto()
            FLIGHT = auto()
            POSITION = auto()
            NAVIGATION = auto()
            FUEL = auto()
            CONTROL = auto()
            SYSTEMS = auto()
            NAV = auto()
            RADIO = auto()
            PAYLOAD = auto()
        class AP(Enum):
            HL_TELEM = auto()
    class Command:
        class AP(Enum):
            ARM = auto()
            DISARM = auto()
            SET_MODE = auto()
            TAKEOFF = auto()
            LAND = auto()
            SELECT_MISSION = auto()
        class System(Enum):
            ACTIVATE = auto()
            SHUTDOWN = auto()
            SET_FLIGHT_MODE = auto()
            SWITCH_DATALINK = auto()
            DATALINK_CONFIG = auto()
            SET_FLIGHT_PARAMETERS = auto()
        class Mission(Enum):
            SET_MISSION = auto()
            SET_MISSION_MODE = auto()
            TAKEOFF = auto()
            ABORT = auto()
            HOLD = auto()
            PROCEED = auto()
            REROUTE = auto()
            REASSIGN = auto()
            SET_WAYPOINT = auto()
            SET_ZONE = auto()
            NAVIGATE_TO = auto()
            LOITER = auto()
            LAND = auto()
            ALLOW_DEPLOY = auto()
            SWARM_CONTROL = auto()
    class Event:
        class Mission(Enum):
            PHASE = auto()
        class System(Enum):
            ONLINE = auto()
            GPS_FIX = auto()
            ERROR = auto()
            RADIO = auto()
            RF_EVENT = auto()
            FAILSAFE = auto()
            HW_FAILURE = auto()
            ACK = auto()
    class Data:
        class Mission(Enum):
            QUERY_MISSION_ID = auto()
            QUERY_MISSION_PROGRESS = auto()
            QUERY_CONTACTS = auto()
            QUERY_SWARM_INFO = auto()
        class System(Enum):
            QUERY_SENSOR_DATA = auto()
            QUERY_LOG_DATA = auto()
            QUERY_DATALINK_STATUS = auto()
            QUERY_NETWORK_STATUS = auto()
            QUERY_SYSTEM_HEALTH = auto()
            QUERY_TELEMETRY = auto()


Messages.Heartbeat.System.value_subcat = 1
Messages.Heartbeat.System.str = 'System'
Messages.Testing.System.value_subcat = 1
Messages.Testing.System.str = 'System'
Messages.Status.Mission.value_subcat = 1
Messages.Status.Mission.str = 'Mission'
Messages.Status.System.value_subcat = 2
Messages.Status.System.str = 'System'
Messages.Status.AP.value_subcat = 3
Messages.Status.AP.str = 'AP'
Messages.Command.AP.value_subcat = 1
Messages.Command.AP.str = 'AP'
Messages.Command.System.value_subcat = 2
Messages.Command.System.str = 'System'
Messages.Command.Mission.value_subcat = 3
Messages.Command.Mission.str = 'Mission'
Messages.Event.Mission.value_subcat = 1
Messages.Event.Mission.str = 'Mission'
Messages.Event.System.value_subcat = 2
Messages.Event.System.str = 'System'
Messages.Data.Mission.value_subcat = 1
Messages.Data.Mission.str = 'Mission'
Messages.Data.System.value_subcat = 2
Messages.Data.System.str = 'System'
Messages.Heartbeat.value_cat = 1
Messages.Heartbeat.str = 'Heartbeat'
Messages.Testing.value_cat = 2
Messages.Testing.str = 'Testing'
Messages.Status.value_cat = 3
Messages.Status.str = 'Status'
Messages.Command.value_cat = 4
Messages.Command.str = 'Command'
Messages.Event.value_cat = 5
Messages.Event.str = 'Event'
Messages.Data.value_cat = 6
Messages.Data.str = 'Data'
Messages.Heartbeat.System.HEARTBEAT.payload_def = []
Messages.Testing.System.TEXTMSG.payload_def = [{'name': 'textdata', 'datatype': 'string', 'bitmask': False}]
Messages.Testing.System.BINMSG.payload_def = [{'name': 'data', 'datatype': 'bytes', 'bitmask': False}]
Messages.Status.Mission.MISSION_PHASE.payload_def = [{'name': 'MissionPhase', 'datatype': 'enum', 'bitmask': False}]
Messages.Status.System.INAV.payload_def = [{'name': 'inavmodes', 'datatype': 'int', 'bitmask': False}, {'name': 'airspeed', 'datatype': 'int', 'bitmask': False}, {'name': 'groundspeed', 'datatype': 'int', 'bitmask': False}, {'name': 'heading', 'datatype': 'int', 'bitmask': False}, {'name': 'msl_alt', 'datatype': 'int', 'bitmask': False}, {'name': 'packed_mgrs', 'datatype': 'bytes', 'bitmask': False}]
Messages.Status.System.FLIGHT.payload_def = [{'name': 'FlightMode', 'datatype': 'enum', 'bitmask': False}, {'name': 'airspeed', 'datatype': 'int', 'bitmask': False}, {'name': 'groundspeed', 'datatype': 'int', 'bitmask': False}, {'name': 'heading', 'datatype': 'int', 'bitmask': False}, {'name': 'msl_alt', 'datatype': 'int', 'bitmask': False}, {'name': 'packed_mgrs', 'datatype': 'bytes', 'bitmask': False}]
Messages.Status.System.POSITION.payload_def = [{'name': 'packed_mgrs', 'datatype': 'bytes', 'bitmask': False}]
Messages.Status.System.NAVIGATION.payload_def = []
Messages.Status.System.FUEL.payload_def = []
Messages.Status.System.CONTROL.payload_def = []
Messages.Status.System.SYSTEMS.payload_def = []
Messages.Status.System.NAV.payload_def = []
Messages.Status.System.RADIO.payload_def = []
Messages.Status.System.PAYLOAD.payload_def = []
Messages.Status.AP.HL_TELEM.payload_def = [{'name': 'mode_str', 'datatype': 'string', 'bitmask': False}, {'name': 'airspeed', 'datatype': 'int', 'bitmask': False}, {'name': 'groundspeed', 'datatype': 'int', 'bitmask': False}, {'name': 'heading', 'datatype': 'int', 'bitmask': False}, {'name': 'msl_alt', 'datatype': 'int', 'bitmask': False}, {'name': 'packed_mgrs', 'datatype': 'string', 'bitmask': False}]
Messages.Command.AP.ARM.payload_def = [{'name': 'arm', 'datatype': 'int', 'bitmask': False}]
Messages.Command.AP.DISARM.payload_def = []
Messages.Command.AP.SET_MODE.payload_def = [{'name': 'mode_str', 'datatype': 'bytes', 'bitmask': False}]
Messages.Command.AP.TAKEOFF.payload_def = [{'name': 'alt_m', 'datatype': 'int', 'bitmask': False}]
Messages.Command.AP.LAND.payload_def = []
Messages.Command.AP.SELECT_MISSION.payload_def = [{'name': 'seq', 'datatype': 'int', 'bitmask': False}]
Messages.Command.System.ACTIVATE.payload_def = []
Messages.Command.System.SHUTDOWN.payload_def = []
Messages.Command.System.SET_FLIGHT_MODE.payload_def = []
Messages.Command.System.SWITCH_DATALINK.payload_def = []
Messages.Command.System.DATALINK_CONFIG.payload_def = []
Messages.Command.System.SET_FLIGHT_PARAMETERS.payload_def = []
Messages.Command.Mission.SET_MISSION.payload_def = [{'name': 'mission_index', 'datatype': 'int', 'bitmask': False}]
Messages.Command.Mission.SET_MISSION_MODE.payload_def = []
Messages.Command.Mission.TAKEOFF.payload_def = []
Messages.Command.Mission.ABORT.payload_def = []
Messages.Command.Mission.HOLD.payload_def = []
Messages.Command.Mission.PROCEED.payload_def = []
Messages.Command.Mission.REROUTE.payload_def = []
Messages.Command.Mission.REASSIGN.payload_def = []
Messages.Command.Mission.SET_WAYPOINT.payload_def = []
Messages.Command.Mission.SET_ZONE.payload_def = []
Messages.Command.Mission.NAVIGATE_TO.payload_def = [{'name': 'packed_mgrs', 'datatype': 'bytes', 'bitmask': False}]
Messages.Command.Mission.LOITER.payload_def = []
Messages.Command.Mission.LAND.payload_def = []
Messages.Command.Mission.ALLOW_DEPLOY.payload_def = []
Messages.Command.Mission.SWARM_CONTROL.payload_def = []
Messages.Event.Mission.PHASE.payload_def = [{'name': 'MissionPhase', 'datatype': 'enum', 'bitmask': False}]
Messages.Event.System.ONLINE.payload_def = []
Messages.Event.System.GPS_FIX.payload_def = []
Messages.Event.System.ERROR.payload_def = []
Messages.Event.System.RADIO.payload_def = []
Messages.Event.System.RF_EVENT.payload_def = []
Messages.Event.System.FAILSAFE.payload_def = []
Messages.Event.System.HW_FAILURE.payload_def = []
Messages.Event.System.ACK.payload_def = [{'name': 'msgid', 'datatype': 'int', 'bitmask': False}, {'name': 'rxtime', 'datatype': 'int', 'bitmask': False}, {'name': 'rssi', 'datatype': 'int', 'bitmask': False}]
Messages.Data.Mission.QUERY_MISSION_ID.payload_def = []
Messages.Data.Mission.QUERY_MISSION_PROGRESS.payload_def = []
Messages.Data.Mission.QUERY_CONTACTS.payload_def = []
Messages.Data.Mission.QUERY_SWARM_INFO.payload_def = []
Messages.Data.System.QUERY_SENSOR_DATA.payload_def = []
Messages.Data.System.QUERY_LOG_DATA.payload_def = []
Messages.Data.System.QUERY_DATALINK_STATUS.payload_def = []
Messages.Data.System.QUERY_NETWORK_STATUS.payload_def = []
Messages.Data.System.QUERY_SYSTEM_HEALTH.payload_def = []
Messages.Data.System.QUERY_TELEMETRY.payload_def = []

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
Messages.Status.Mission.category = Messages.Status
Messages.Status.Mission.category_name = 'Status'
Messages.Status.Mission.category_value = 3
Messages.Status.Mission.subcategory_name = 'Mission'
Messages.Status.Mission.subcategory_value = 1
Messages.Status.System.category = Messages.Status
Messages.Status.System.category_name = 'Status'
Messages.Status.System.category_value = 3
Messages.Status.System.subcategory_name = 'System'
Messages.Status.System.subcategory_value = 2
Messages.Status.AP.category = Messages.Status
Messages.Status.AP.category_name = 'Status'
Messages.Status.AP.category_value = 3
Messages.Status.AP.subcategory_name = 'AP'
Messages.Status.AP.subcategory_value = 3
Messages.Command.AP.category = Messages.Command
Messages.Command.AP.category_name = 'Command'
Messages.Command.AP.category_value = 4
Messages.Command.AP.subcategory_name = 'AP'
Messages.Command.AP.subcategory_value = 1
Messages.Command.System.category = Messages.Command
Messages.Command.System.category_name = 'Command'
Messages.Command.System.category_value = 4
Messages.Command.System.subcategory_name = 'System'
Messages.Command.System.subcategory_value = 2
Messages.Command.Mission.category = Messages.Command
Messages.Command.Mission.category_name = 'Command'
Messages.Command.Mission.category_value = 4
Messages.Command.Mission.subcategory_name = 'Mission'
Messages.Command.Mission.subcategory_value = 3
Messages.Event.Mission.category = Messages.Event
Messages.Event.Mission.category_name = 'Event'
Messages.Event.Mission.category_value = 5
Messages.Event.Mission.subcategory_name = 'Mission'
Messages.Event.Mission.subcategory_value = 1
Messages.Event.System.category = Messages.Event
Messages.Event.System.category_name = 'Event'
Messages.Event.System.category_value = 5
Messages.Event.System.subcategory_name = 'System'
Messages.Event.System.subcategory_value = 2
Messages.Data.Mission.category = Messages.Data
Messages.Data.Mission.category_name = 'Data'
Messages.Data.Mission.category_value = 6
Messages.Data.Mission.subcategory_name = 'Mission'
Messages.Data.Mission.subcategory_value = 1
Messages.Data.System.category = Messages.Data
Messages.Data.System.category_name = 'Data'
Messages.Data.System.category_value = 6
Messages.Data.System.subcategory_name = 'System'
Messages.Data.System.subcategory_value = 2


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

