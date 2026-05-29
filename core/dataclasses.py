# Uloženo jako core/dataclasses.py
from dataclasses import dataclass

@dataclass
class LunarADSBPacket:
    # 1. Identification (RFC-002)
    hex_code: str
    callsign: str
    timestamp: float
    
    # Metadata for UI
    classification: str  # e.g., "HMD", "CRG", "PRB", "BASE", "SNS" (Sensor)
    mission_type: str    
    fuel_dv: float       
    
    # 2. Kinematic State Vector (RFC-002) - 6-DOF Extension
    x: float; y: float; z: float
    vx: float; vy: float; vz: float
    
    # 3. Maneuver & Comms Intent
    t_burn: float
    delta_vx: float; delta_vy: float; delta_vz: float
    burn_duration: float

    # Fields with DEFAULTS must come last
    pitch: float = 0.0
    yaw: float = 0.0
    roll: float = 0.0
    v_pitch: float = 0.0
    v_yaw: float = 0.0
    v_roll: float = 0.0
    comms_active: bool = True
    channel_freq: str = "14.2 GHz"
    flight_assist: bool = False # Anti-Gravity / Hover capability