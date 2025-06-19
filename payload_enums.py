from enum import Enum, IntEnum, auto

# ========== Reply PAYLOAD BYTE DEFINITIONS ==========
class PayloadEnum:
    class FlightMode(IntEnum):
        ACRO = auto()
        ANGLE = auto()
        CRUISE = auto()
        AUTO = auto()
        
    class CommandResult(IntEnum):
        # Reply to Command
        ACCEPTED = auto()
        TEMPORARILY_REJECTED = auto()
        DENIED = auto()
        UNSUPPORTED = auto()
        FAILED = auto()
        IN_PROGRESS = auto()
        CANCELLED = auto()

    class DataError(IntEnum):
        # Reply to Data
        NOT_FOUND = auto()
        DEVICE_UNAVAILABLE = auto()
        HARDWARE_ERROR = auto()
        SOFTWARE_ERROR = auto()
        DATABSE_ERROR = auto()

    class FlightMode(IntEnum):
        ACRO = auto()
        ANGLE = auto()
        POSHOLD = auto()
        NAV_WP = auto()
        LOITER = auto()
        CRUSE = auto()
        RTH = auto()
        LANDING = auto()
        DISARMED = auto()

    class FlightPhase(IntEnum):
        PREFLIGHT = auto()
        TAKEOFF = auto()
        CRUISE = auto()
        MISSION_OPERATION = auto()
        RTB = auto()
        LANDING = auto()
        POSTFLIGHT = auto()

    class MissionPhase(IntEnum):
        BOOTING = auto()
        ONLINE = auto()
        MISSION_RECEIVED = auto()
        READY_TAKEOFF = auto()
        TAKEOFF_COMPLETE = auto()
        ENROUTE = auto()
        AT_ASSEMBLY = auto()
        HOLDING = auto()
        PROCEEDING = auto()
        BINGO = auto()
        RTB = auto()
        LANDING = auto()
        LANDED = auto()
        SHUTDOWN = auto()

