# Uloženo jako core/dataclasses.py
from dataclasses import dataclass

@dataclass
class LunarADSBPacket:
    # 1. Identification (RFC-002)
    hex_code: str
    callsign: str
    timestamp: float
    
    # NOVÉ: Rozšířená Metadata pro UI
    classification: str  # e.g., "HMD" (Human), "CRG" (Cargo), "PRB" (Probe)
    mission_type: str    # e.g., "Lunar Descent", "Orbital Transfer"
    fuel_dv: float       # Remaining Delta-V budget in m/s
    
    # 2. Kinematic State Vector (RFC-002)
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float
    
    # 3. Maneuver Intent
    t_burn: float
    delta_vx: float
    delta_vy: float
    delta_vz: float
    burn_duration: float