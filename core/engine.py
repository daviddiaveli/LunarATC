import math
from core.dataclasses import LunarADSBPacket

class LunarEngine:
    def __init__(self):
        # Constants defined in RFC-001 (expressed in meters)
        self.R_EQ = 1737400.0  
        self.R_POL = 1736000.0 
        self.MU = 4.9048695e12 # Lunar gravitational parameter (m^3/s^2)
        self.tracked_targets = {} 

        # Separation minimums defined in RFC-003 (expressed in meters)
        self.VERTICAL_MIN = 2500.0   # 2.5 km
        self.HORIZONTAL_MIN = 15000.0 # 15.0 km
        self.LOOKAHEAD_TIME = 600     # 10 minutes prediction window

        # ORBITAL ZONES (Meters above LRE)
        self.ZONE_LLO = 100000.0      # Low Lunar Orbit: 0 - 100km
        self.ZONE_MLO = 2000000.0     # Medium Lunar Orbit: 100km - 2000km
        self.SOI_RADIUS = 66000000.0  # Moon's Sphere of Influence (~66,000 km)

        # RESTRICTED AIRSPACE ZONES
        self.RESTRICTED_ZONES = [
            {"name": "APOLLO 11 HERITAGE", "lat": 0.674, "lon": 23.472, "radius": 50000.0, "alt_limit": 15000.0},
            {"name": "TYCHO MILITARY SECTOR", "lat": -43.3, "lon": -11.2, "radius": 150000.0, "alt_limit": 50000.0}
        ]

    def get_gravity_acceleration(self, x, y, z):
        """Calculates the gravity acceleration vector at a given position."""
        r = math.sqrt(x**2 + y**2 + z**2)
        if r == 0: return 0, 0, 0
        a_mag = -self.MU / (r**2)
        return a_mag * (x/r), a_mag * (y/r), a_mag * (z/r)

    def get_escape_velocity(self, r):
        """Calculates escape velocity at distance r from center."""
        if r == 0: return 0
        return math.sqrt(2 * self.MU / r)

    def get_flight_phase(self, packet: LunarADSBPacket):
        """
        Determines the current flight phase based on altitude and velocity.
        """
        r = math.sqrt(packet.x**2 + packet.y**2 + packet.z**2)
        v = math.sqrt(packet.vx**2 + packet.vy**2 + packet.vz**2)
        v_esc = self.get_escape_velocity(r)
        alt = r - self.R_EQ

        # 1. Check for Landing/Terminal Phase
        if alt < 50000.0: # Below 50km
            if v < 500.0: return "TERMINAL_DESCENT"
            return "LOW_LUNAR_ORBIT (LLO)"
        
        # 2. Check for Escape/Flyby
        if v >= v_esc:
            if r > self.SOI_RADIUS * 0.8: return "TRANS-EARTH_INJECTION"
            return "ESCAPE_TRAJECTORY / FLYBY"

        # 3. Check Orbital Zones
        if alt < self.ZONE_LLO: return "LLO_EN-ROUTE"
        if alt < self.ZONE_MLO: return "MEDIUM_ORBIT (MLO)"
        if r < self.SOI_RADIUS: return "HIGH_ORBIT (HLO)"
        
        return "DEEP_SPACE / INBOUND"

    def check_restricted_zones(self, packet: LunarADSBPacket):
        """Checks if a vessel is violating restricted airspace."""
        r = math.sqrt(packet.x**2 + packet.y**2 + packet.z**2)
        alt = r - self.R_EQ
        
        # Convert packet pos to lat/lon roughly
        lat_r = math.asin(packet.z / r) if r != 0 else 0
        lon_r = math.atan2(packet.y, packet.x)
        lat_deg = math.degrees(lat_r)
        lon_deg = math.degrees(lon_r)
        
        for zone in self.RESTRICTED_ZONES:
            if alt < zone["alt_limit"]:
                # calculate rough surface distance
                dlat = math.radians(lat_deg - zone["lat"])
                dlon = math.radians(lon_deg - zone["lon"])
                a = math.sin(dlat/2)**2 + math.cos(math.radians(zone["lat"])) * math.cos(lat_r) * math.sin(dlon/2)**2
                c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                distance = self.R_EQ * c
                if distance < zone["radius"]:
                    return zone["name"]
        return None

    def propagate_state(self, packet: LunarADSBPacket, seconds: float):
        """
        Predicts future state including 3D translation and rotation (6-DOF).
        """
        x, y, z = packet.x, packet.y, packet.z
        vx, vy, vz = packet.vx, packet.vy, packet.vz
        pitch, yaw, roll = packet.pitch, packet.yaw, packet.roll
        
        # Integration step
        step = 1.0 
        elapsed = 0.0
        
        while elapsed < seconds:
            dt = min(step, seconds - elapsed)
            
            # 1. Translation (Gravity-aware or Flight Assist)
            ax, ay, az = self.get_gravity_acceleration(x, y, z)
            
            if getattr(packet, 'flight_assist', False):
                # Anti-Gravity / Hover active: thrusters perfectly cancel gravity
                ax, ay, az = 0.0, 0.0, 0.0
                
            vx += ax * dt; vy += ay * dt; vz += az * dt
            x += vx * dt; y += vy * dt; z += vz * dt
            
            # 2. Rotation (Constant angular velocity)
            pitch = (pitch + packet.v_pitch * dt) % 360
            yaw = (yaw + packet.v_yaw * dt) % 360
            roll = (roll + packet.v_roll * dt) % 360
            
            elapsed += dt
            
        return x, y, z, vx, vy, vz, pitch, yaw, roll

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
        if packet.hex_code in self.tracked_targets:
            self.tracked_targets[packet.hex_code]["packet"] = packet
            self.tracked_targets[packet.hex_code]["current_lfl"] = current_lfl
        else:
            self.tracked_targets[packet.hex_code] = {
                "packet": packet,
                "current_lfl": current_lfl
            }

    def calculate_evasive_maneuver(self, evade_vessel: LunarADSBPacket, target_vessel: LunarADSBPacket, time_to_impact):
        """
        Computes a mandatory Delta-V vector to resolve the separation conflict.
        Returns (dv_x, dv_y, dv_z) tuple.
        """
        print(f"\n🤖 [RESOLVER] Computing automated evasion vector for {evade_vessel.callsign}...")
        
        required_clearance = self.VERTICAL_MIN + 500.0
        safe_time = max(1, time_to_impact)
        
        # Simple vertical evasion for now
        needed_dv_z = required_clearance / safe_time
        
        if evade_vessel.z < target_vessel.z:
            dv_vector = (0.0, 0.0, -needed_dv_z)
        else:
            dv_vector = (0.0, 0.0, needed_dv_z)

        print(f"  🎯 Resolution Plan: Adjust vertical vector by {round(dv_vector[2], 2)} m/s")
        return dv_vector

    def run_stca_scan(self):
        """
        Short-Term Conflict Alert (STCA) Scan.
        Returns a list of required resolutions: [(packet_to_evade, dv_vector), ...]
        """
        print("\n--- Running Tactical STCA Conflict Scan ---")
        target_ids = list(self.tracked_targets.keys())
        resolutions = []
        
        for i in range(len(target_ids)):
            for j in range(i + 1, len(target_ids)):
                t1_pkt = self.tracked_targets[target_ids[i]]["packet"]
                t2_pkt = self.tracked_targets[target_ids[j]]["packet"]
                
                if t1_pkt.classification == "BASE" or t2_pkt.classification == "BASE":
                    continue # Ignore surface bases for tactical orbital deconfliction

                for second in range(0, self.LOOKAHEAD_TIME, 10):
                    res = self.propagate_state(t1_pkt, second)
                    x1, y1, z1 = res[0], res[1], res[2]
                    
                    res2 = self.propagate_state(t2_pkt, second)
                    x2, y2, z2 = res2[0], res2[1], res2[2]

                    dx = abs(x1 - x2)
                    dy = abs(y1 - y2)
                    dz = abs(z1 - z2)
                    
                    horizontal_dist = math.sqrt(dx**2 + dy**2)
                    vertical_dist = dz

                    if horizontal_dist < self.HORIZONTAL_MIN and vertical_dist < self.VERTICAL_MIN:
                        print(f"⚠️ [STCA CONFLICT ALERT] Potential collision detected!")
                        print(f"  🚨 Targets: {t1_pkt.callsign} & {t2_pkt.callsign}")
                        print(f"  ⏱️ Time to Intersect: T+{second} seconds")
                        
                        # Resolve Conflict: Lower priority vessel must evade
                        if t1_pkt.callsign == "CRG-ARES":
                            dv = self.calculate_evasive_maneuver(t1_pkt, t2_pkt, second)
                            resolutions.append((t1_pkt, dv))
                        else:
                            dv = self.calculate_evasive_maneuver(t2_pkt, t1_pkt, second)
                            resolutions.append((t2_pkt, dv))
                        break # Move to next pair
                        
        if not resolutions:
            print("✅ Airspace Clear: No tactical conflicts detected within 10 minutes.")
        
        return resolutions

# --- CONFLICT ENGINE SIMULATION TEST ---
if __name__ == "__main__":
    engine = LunarEngine()
    print("--- LunarATC Tactical Conflict Engine Online ---")
    
    craft_a = LunarADSBPacket(
        hex_code="4A3F12", callsign="LUNAR-01", timestamp=1716973200.0,
        classification="HMD", mission_type="Orbital Station", fuel_dv=2000.0,
        x=1737400.0 + 10000.0, y=0.0, z=500.0,  
        vx=-50.0, vy=1600.0, vz=0.0,
        t_burn=0.0, delta_vx=0.0, delta_vy=0.0, delta_vz=0.0, burn_duration=0.0
    )
    
    craft_b = LunarADSBPacket(
        hex_code="8B9E44", callsign="CRG-ARES", timestamp=1716973200.0,
        classification="CRG", mission_type="Cargo Delivery", fuel_dv=1000.0,
        x=1737400.0 + 9800.0, y=48000.0, z=600.0, 
        vx=-45.0, vy=-10.0, vz=0.0,
        t_burn=0.0, delta_vx=0.0, delta_vy=0.0, delta_vz=0.0, burn_duration=0.0
    )
    
    engine.process_adsb_packet(craft_a)
    engine.process_adsb_packet(craft_b)
    engine.run_stca_scan()
