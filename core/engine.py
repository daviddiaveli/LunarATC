import math
from core.dataclasses import LunarADSBPacket

class LunarEngine:
    def __init__(self):
        # Constants defined in RFC-001 (expressed in meters)
        self.R_EQ = 1737400.0  
        self.R_POL = 1736000.0 
        self.tracked_targets = {} 

        # Separation minimums defined in RFC-003 (expressed in meters)
        self.VERTICAL_MIN = 2500.0   # 2.5 km
        self.HORIZONTAL_MIN = 15000.0 # 15.0 km
        self.LOOKAHEAD_TIME = 600     # 10 minutes prediction window

    def get_ellipsoid_radius(self, latitude_rad):
        """Calculates the radius of the Lunar Reference Ellipsoid (LRE) at a specific latitude."""
        cos_lat = math.cos(latitude_rad)
        sin_lat = math.sin(latitude_rad)
        numerator = (self.R_EQ**2 * cos_lat)**2 + (self.R_POL**2 * sin_lat)**2
        denominator = (self.R_EQ * cos_lat)**2 + (self.R_POL * sin_lat)**2
        return math.sqrt(numerator / denominator)

    def calculate_lfl(self, x, y, z):
        """Computes corresponding Lunar Flight Level (LFL) from 3D Cartesian coordinates."""
        distance_from_center = math.sqrt(x**2 + y**2 + z**2)
        if distance_from_center == 0:
            return 0.0
            
        latitude_rad = math.asin(z / distance_from_center)
        lre_radius = self.get_ellipsoid_radius(latitude_rad)
        altitude_meters = distance_from_center - lre_radius
        
        return round(altitude_meters / 1000.0, 2)

    def process_adsb_packet(self, packet: LunarADSBPacket):
        """Ingests L-ADS-B packet and updates the local tracking database."""
        current_lfl = self.calculate_lfl(packet.x, packet.y, packet.z)
        self.tracked_targets[packet.hex_code] = {
            "packet": packet,
            "current_lfl": current_lfl
        }

    def calculate_evasive_maneuver(self, evade_vessel: LunarADSBPacket, target_vessel: LunarADSBPacket, time_to_impact):
        """
        Computes a mandatory Delta-V vector to resolve the separation conflict.
        Applies a vertical offset correction to push the vessel to a safe Lunar Flight Level.
        """
        print(f"\n🤖 [RESOLVER] Computing automated evasion vector for {evade_vessel.callsign}...")
        
        # We need to ensure a vertical separation of at least VERTICAL_MIN + 500m buffer
        required_clearance = self.VERTICAL_MIN + 500.0
        
        # Calculate how much Delta-V in Z axis is needed to change altitude over the given time
        # Basic physics approximation: dZ = dVz * t -> dVz = dZ / t
        needed_dv_z = required_clearance / time_to_impact
        
        # If evade_vessel is already higher, push it up. If lower, push it down.
        if evade_vessel.z < target_vessel.z:
            needed_dv_z = -needed_dv_z

        print(f"  🎯 Resolution Plan: Adjust vertical vector by {round(needed_dv_z, 2)} m/s")
        print(f"  📡 Broadcast Sent: {evade_vessel.callsign} execute Burn at T+0s | Duration: 5.0s")

    def run_stca_scan(self):
        """Short-Term Conflict Alert (STCA) Scan with integrated resolution logic."""
        print("\n--- Running Tactical STCA Conflict Scan ---")
        target_ids = list(self.tracked_targets.keys())
        
        for i in range(len(target_ids)):
            for j in range(i + 1, len(target_ids)):
                t1 = self.tracked_targets[target_ids[i]]["packet"]
                t2 = self.tracked_targets[target_ids[j]]["packet"]
                
                for second in range(self.LOOKAHEAD_TIME):
                    x1_pred = t1.x + t1.vx * second
                    y1_pred = t1.y + t1.vy * second
                    z1_pred = t1.z + t1.vz * second

                    x2_pred = t2.x + t2.vx * second
                    y2_pred = t2.y + t2.vy * second
                    z2_pred = t2.z + t2.vz * second

                    dx = abs(x1_pred - x2_pred)
                    dy = abs(y1_pred - y2_pred)
                    dz = abs(z1_pred - z2_pred)
                    
                    horizontal_dist = math.sqrt(dx**2 + dy**2)
                    vertical_dist = dz

                    if horizontal_dist < self.HORIZONTAL_MIN and vertical_dist < self.VERTICAL_MIN:
                        print(f"⚠️ [STCA CONFLICT ALERT] Potential collision detected!")
                        print(f"  🚨 Targets: {t1.callsign} & {t2.callsign}")
                        print(f"  ⏱️ Time to Intersect: T+{second} seconds")
                        
                        # Resolve Conflict: Lower priority vessel (CRG-ARES) must evade
                        if t1.callsign == "CRG-ARES":
                            self.calculate_evasive_maneuver(t1, t2, second)
                        else:
                            self.calculate_evasive_maneuver(t2, t1, second)
                        return 
                        
        print("✅ Airspace Clear: No tactical conflicts detected within 10 minutes.")

# --- CONFLICT ENGINE SIMULATION TEST ---
if __name__ == "__main__":
    engine = LunarEngine()
    print("--- LunarATC Tactical Conflict Engine Online ---")
    
    craft_a = LunarADSBPacket(
        hex_code="4A3F12", callsign="LUNAR-01", timestamp=1716973200.0,
        x=1737400.0 + 10000.0, y=0.0, z=500.0,  
        vx=-50.0, vy=1600.0, vz=0.0,
        t_burn=0.0, delta_vx=0.0, delta_vy=0.0, delta_vz=0.0, burn_duration=0.0
    )
    
    craft_b = LunarADSBPacket(
        hex_code="8B9E44", callsign="CRG-ARES", timestamp=1716973200.0,
        x=1737400.0 + 9800.0, y=48000.0, z=600.0, 
        vx=-45.0, vy=-10.0, vz=0.0,
        t_burn=0.0, delta_vx=0.0, delta_vy=0.0, delta_vz=0.0, burn_duration=0.0
    )
    
    engine.process_adsb_packet(craft_a)
    engine.process_adsb_packet(craft_b)
    engine.run_stca_scan()