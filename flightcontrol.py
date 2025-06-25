#!/usr/bin/env python3
#WARNING: Outdated

import asyncio
from mavsdk import System
import time
from unavlib.control import UAVControl
from unavlib.modules import geospatial
from unavlib.modules.utils import inavutil


class UAVmeta():
    def __init__(self, protocol="msp", firmware="betaflight", vehicle_type="copter"):
        p = protocol.lower()
        f = firmware.lower()
        if p!="msp" and p!="mavlink":
            raise Exception("Protocol must be MSP or Mavlink")
        
        if (p=="msp" and f not in ["inav", "betaflight"]) or (p=="mavlink" and f not in ["inav", "ardupilot", "px4"]):
            raise Exception(f"Invalid autopilot {firmware} for protocol {protocol}")
 
        self.client = ""

# MSP functions


# Mavlink functions
