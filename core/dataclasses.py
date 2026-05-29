from dataclasses import dataclass

@dataclass
class LunarADSBPacket:
    # RFC-002 Telemetry Payload Structure
    hex_code: str        # Unique 24-bit hexadecimal identifier
    callsign: str        # Alphanumeric mission identifier (max 8 chars)
    timestamp: float     # Atomic timestamp (Lunar Coordinate Time - LCT)
    
    # Kinematic State Vector
    x: float             # X coordinate relative to lunar center (meters)
    y: float             # Y coordinate relative to lunar center (meters)
    z: float             # Z coordinate relative to lunar center (meters)
    vx: float            # Velocity vector X component (m/s)
    vy: float            # Velocity vector Y component (m/s)
    vz: float            # Velocity vector Z component (m/s)
    
    # Intent / Maneuver Data Block
    t_burn: float        # Planned timestamp of next ignition (0.0 if none)
    delta_vx: float      # Planned Delta-V X component (m/s)
    delta_vy: float      # Planned Delta-V Y component (m/s)
    delta_vz: float      # Planned Delta-V Z component (m/s)
    burn_duration: float # Expected burn runtime in seconds

    def has_active_intent(self) -> bool:
        """Checks if the spacecraft has a scheduled maneuver pending."""
        return self.t_burn > 0.0 and (self.delta_vx != 0.0 or self.delta_vy != 0.0 or self.delta_vz != 0.0)