import time
import random
import math
from core.dataclasses import LunarADSBPacket
from core.engine import LunarEngine

def generate_initial_traffic(engine: LunarEngine):
    """Generates a fleet of active spacecraft with 6-DOF movement and diverse, stable orbits."""
    
    # Calculate stable velocities
    r_lunar01 = engine.R_EQ + 50000.0
    v_lunar01 = math.sqrt(engine.MU / r_lunar01)
    
    r_crg = engine.R_EQ + 55000.0
    v_crg = math.sqrt(engine.MU / r_crg)
    
    r_sat = engine.R_EQ + 100000.0
    v_sat = math.sqrt(engine.MU / r_sat)
    
    # 1. LUNAR-01: Orbital Station with slow rotation (Prograde)
    engine.process_adsb_packet(LunarADSBPacket(
        hex_code="4A3F12", callsign="LUNAR-01", timestamp=time.time(),
        classification="HMD", mission_type="Orbital Station", fuel_dv=2500.0,
        x=r_lunar01, y=0.0, z=0.0, 
        vx=0.0, vy=v_lunar01, vz=0.0,
        pitch=0.0, yaw=45.0, roll=0.0,
        v_pitch=0.0, v_yaw=2.0, v_roll=0.0,
        t_burn=0.0, delta_vx=0.0, delta_vy=0.0, delta_vz=0.0, burn_duration=0.0
    ))

    # 2. CRG-ARES: Maneuvering Cargo (Retrograde)
    engine.process_adsb_packet(LunarADSBPacket(
        hex_code="8B9E44", callsign="CRG-ARES", timestamp=time.time(),
        classification="CRG", mission_type="Cargo Delivery", fuel_dv=1200.0,
        x=0.0, y=r_crg, z=0.0, 
        vx=-v_crg, vy=0.0, vz=0.0,
        pitch=180.0, yaw=0.0, roll=0.0, 
        v_pitch=0.0, v_yaw=0.0, v_roll=5.0,
        t_burn=0.0, delta_vx=0.0, delta_vy=0.0, delta_vz=0.0, burn_duration=0.0
    ))

    # 3. SAT-POLAR: Polar Orbit
    engine.process_adsb_packet(LunarADSBPacket(
        hex_code="1C7D99", callsign="SAT-POLAR", timestamp=time.time(),
        classification="PRB", mission_type="Mapping", fuel_dv=800.0,
        x=r_sat, y=0.0, z=0.0,   
        vx=0.0, vy=0.0, vz=v_sat,
        pitch=-90.0, yaw=0.0, roll=0.0, 
        v_pitch=0.0, v_yaw=0.0, v_roll=0.0,
        t_burn=0.0, delta_vx=0.0, delta_vy=0.0, delta_vz=0.0, burn_duration=0.0
    ))

    # 4. ORION-EXP: Incoming vessel from Earth (Deep Space)
    engine.process_adsb_packet(LunarADSBPacket(
        hex_code="99FF11", callsign="ORION-XP", timestamp=time.time(),
        classification="HMD", mission_type="Lunar Arrival", fuel_dv=4500.0,
        x=50000000.0, y=10000000.0, z=0.0,   
        vx=-800.0, vy=-200.0, vz=0.0, 
        pitch=0.0, yaw=260.0, roll=0.0,
        v_pitch=0.0, v_yaw=0.0, v_roll=0.0,
        t_burn=0.0, delta_vx=0.0, delta_vy=0.0, delta_vz=0.0, burn_duration=0.0
    ))

    # 5. VOYAGER-L: High-velocity flyby (Gravity Assist)
    engine.process_adsb_packet(LunarADSBPacket(
        hex_code="ACDC00", callsign="VOY-FLY", timestamp=time.time(),
        classification="PRB", mission_type="Flyby", fuel_dv=100.0,
        x=-10000000.0, y=30000000.0, z=5000000.0,   
        vx=2500.0, vy=-1500.0, vz=0.0, 
        pitch=0.0, yaw=0.0, roll=0.0,
        v_pitch=0.5, v_yaw=0.5, v_roll=0.5,
        t_burn=0.0, delta_vx=0.0, delta_vy=0.0, delta_vz=0.0, burn_duration=0.0
    ))

    # 6. HOVER-1: Low speed inspection drone with Anti-Gravity
    engine.process_adsb_packet(LunarADSBPacket(
        hex_code="HV8811", callsign="HOVER-1", timestamp=time.time(),
        classification="PRB", mission_type="Surface Inspection", fuel_dv=800.0,
        x=0.0, y=0.0, z=engine.R_EQ + 10000.0, # Just 10km above surface
        vx=50.0, vy=50.0, vz=0.0, # Very slow speed, would normally crash instantly
        pitch=0.0, yaw=45.0, roll=0.0,
        v_pitch=0.0, v_yaw=0.0, v_roll=0.0,
        t_burn=0.0, delta_vx=0.0, delta_vy=0.0, delta_vz=0.0, burn_duration=0.0,
        flight_assist=True # MAGIC! Doesn't fall.
    ))

def run_live_simulation():
    """Runs a real-time tracking loop, updating positions using 6-DOF orbital physics."""
    engine = LunarEngine()
    generate_initial_traffic(engine)
    
    print("\n==================================================")
    print("🛰️  LUNAR AIR TRAFFIC CONTROL - 6-DOF SIMULATION")
    print("==================================================")
    
    sim_second = 0
    time_step = 1.0 
    
    try:
        while True:
            sim_second += 1
            print(f"\n[TIME T+{sim_second}s] Scanning lunar airspace...")
            
            # Update positions using the engine's 6-DOF physics
            for hex_code, data in list(engine.tracked_targets.items()):
                pkt = data["packet"]
                
                # Propagate forward (Translation + Rotation)
                nx, ny, nz, nvx, nvy, nvz, np, nyw, nr = engine.propagate_state(pkt, time_step)
                
                pkt.x, pkt.y, pkt.z = nx, ny, nz
                pkt.vx, pkt.vy, pkt.vz = nvx, nvy, nvz
                pkt.pitch, pkt.yaw, pkt.roll = np, nyw, nr
                
                engine.process_adsb_packet(pkt)
            
            # STCA Scan
            resolutions = engine.run_stca_scan()
            
            for pkt, dv in resolutions:
                print(f"🚀 [PILOT] {pkt.callsign} performing corrective burn + reorientation...")
                pkt.vx += dv[0]; pkt.vy += dv[1]; pkt.vz += dv[2]
                pkt.fuel_dv -= 50.0
                # Simulate reorientation for the burn
                pkt.pitch += 10.0; pkt.v_roll = 15.0 
                engine.process_adsb_packet(pkt)
            
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\n🛑 Simulation terminated.")
            
    except KeyboardInterrupt:
        print("\n🛑 Simulation terminated by operator.")

if __name__ == "__main__":
    run_live_simulation()