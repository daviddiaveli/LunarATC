import time
import random
from core.dataclasses import LunarADSBPacket
from core.engine import LunarEngine

def generate_initial_traffic(engine: LunarEngine):
    """Generates a fleet of active spacecraft orbiting the Moon."""
    
    # Spacecraft 1: Apollo-style Lander preparing for descent
    engine.process_adsb_packet(LunarADSBPacket(
        hex_code="4A3F12", callsign="LUNAR-01", timestamp=time.time(),
        x=1737400.0 + 15000.0, y=0.0, z=200.0,  # low orbit (15km)
        vx=-10.0, vy=1630.0, vz=0.0,            # high orbital velocity
        t_burn=0.0, delta_vx=0.0, delta_vy=0.0, delta_vz=0.0, burn_duration=0.0
    ))

    # Spacecraft 2: Heavy cargo transport arriving from Earth
    engine.process_adsb_packet(LunarADSBPacket(
        hex_code="8B9E44", callsign="CRG-ARES", timestamp=time.time(),
        x=1737400.0 + 120000.0, y=10000.0, z=-500.0, # high orbit (120km)
        vx=-5.0, vy=1500.0, vz=5.0,
        t_burn=0.0, delta_vx=0.0, delta_vy=0.0, delta_vz=0.0, burn_duration=0.0
    ))

    # Spacecraft 3: Telecommunications Satellite in polar orbit
    engine.process_adsb_packet(LunarADSBPacket(
        hex_code="1C7D99", callsign="SAT-COMM", timestamp=time.time(),
        x=0.0, y=0.0, z=1736000.0 + 300000.0,   # high polar orbit (300km)
        vx=0.0, vy=0.0, vz=-1450.0,
        t_burn=0.0, delta_vx=0.0, delta_vy=0.0, delta_vz=0.0, burn_duration=0.0
    ))

def run_live_simulation():
    """Runs a real-time tracking loop, updating positions every second."""
    engine = LunarEngine()
    generate_initial_traffic(engine)
    
    print("\n==================================================")
    print("🛰️  LUNAR AIR TRAFFIC CONTROL - LIVE SIMULATION  🛰️")
    print("==================================================")
    
    sim_second = 0
    time_step = 1.0 # 1 simulated second = 1 real second
    
    try:
        while True:
            sim_second += 1
            print(f"\n[TIME T+{sim_second}s] Scanning lunar airspace...")
            
            # Update positions of all tracked vehicles based on their velocity vector
            for hex_code, data in list(engine.tracked_targets.items()):
                pkt = data["packet"]
                
                # Move the spacecraft: Position = Position + (Velocity * TimeStep)
                pkt.x += pkt.vx * time_step
                pkt.y += pkt.vy * time_step
                pkt.z += pkt.vz * time_step
                
                # Introduce slight orbital perturbation/randomness for realism
                pkt.vx += random.uniform(-0.1, 0.1)
                pkt.vy += random.uniform(-0.1, 0.1)
                
                # Reprocess the updated packet through the ATC engine
                engine.process_adsb_packet(pkt)
            
            # Execute tactical Short-Term Conflict Alert scan
            engine.run_stca_scan()
            
            # Wait for 1 second before the next radar sweep
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Simulation terminated by operator. Core engine shutting down.")

if __name__ == "__main__":
    run_live_simulation()