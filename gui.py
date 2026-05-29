import tkinter as tk
import math
import random
from core.dataclasses import LunarADSBPacket
from core.engine import LunarEngine

class LunarRadarGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("LunarATC - Tactical Radar Display")
        self.root.geometry("800x850")
        self.root.configure(bg="#0a0f1d")

        # Initialize our core mathematical engine
        self.engine = LunarEngine()
        self.setup_mock_traffic()

        # Radar Configuration Variables
        self.CENTER_X = 400
        self.CENTER_Y = 400
        self.SCALE = 0.0015  # Scale factor to fit lunar orbits into an 800x800 canvas

        # Create GUI Components
        self.create_widgets()

        # Start the live radar refresh loop (every 100ms for smooth UI)
        self.update_radar_loop()

    def create_widgets(self):
        """Creates the visual layout of the ATC radar screen."""
        # Main Radar Canvas
        self.canvas = tk.Canvas(self.root, width=800, height=800, bg="#050811", highlightthickness=0)
        self.canvas.pack()

        # Lower Status/Control Bar
        self.status_frame = tk.Frame(self.root, bg="#0a0f1d", height=50)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = tk.Label(
            self.status_frame, 
            text="SYSTEM ONLINE | SCANNING LUNAR AIRSPACE (RFC-003 COMPLIANT)", 
            fg="#00ff66", bg="#0a0f1d", font=("Courier", 10, "bold")
        )
        self.status_label.pack(pady=15)

    def setup_mock_traffic(self):
        """Populates the engine with initial traffic moving on close orbital paths."""
        # Spacecraft A
        self.engine.process_adsb_packet(LunarADSBPacket(
            hex_code="4A3F12", callsign="LUNAR-01", timestamp=0.0,
            x=1737400.0 + 30000.0, y=-40000.0, z=0.0,
            vx=-40.0, vy=1550.0, vz=1.0,
            t_burn=0.0, delta_vx=0.0, delta_vy=0.0, delta_vz=0.0, burn_duration=0.0
        ))
        # Spacecraft B - heading towards a conflict with A
        self.engine.process_adsb_packet(LunarADSBPacket(
            hex_code="8B9E44", callsign="CRG-ARES", timestamp=0.0,
            x=1737400.0 + 28000.0, y=40000.0, z=500.0,
            vx=-45.0, vy=-1520.0, vz=0.0,
            t_burn=0.0, delta_vx=0.0, delta_vy=0.0, delta_vz=0.0, burn_duration=0.0
        ))

    def draw_radar_background(self):
        """Draws radar sweeping grids and the physical Moon profile at the center."""
        self.canvas.delete("all")

        # Draw concentric radar range rings
        for radius_km in [50, 100, 200]:
            pixel_r = (radius_km * 1000) * self.SCALE
            self.canvas.create_oval(
                self.CENTER_X - pixel_r, self.CENTER_Y - pixel_r,
                self.CENTER_X + pixel_r, self.CENTER_Y + pixel_r,
                outline="#112244", width=1, dash=(4, 4)
            )

        # Draw the central body: Moon surface boundary based on RFC-001 Equatorial Radius
        moon_pixel_r = self.engine.R_EQ * self.SCALE
        self.canvas.create_oval(
            self.CENTER_X - moon_pixel_r, self.CENTER_Y - moon_pixel_r,
            self.CENTER_X + moon_pixel_r, self.CENTER_Y + moon_pixel_r,
            fill="#161f33", outline="#334466", width=2
        )
        self.canvas.create_text(self.CENTER_X, self.CENTER_Y, text="LUNA", fill="#556688", font=("Courier", 10, "bold"))

    def update_radar_loop(self):
        """Simulates physics movement and updates the graphical display."""
        time_step = 0.5  # Accelerated time step for visualization stability
        
        # Redraw background and grid
        self.draw_radar_background()

        # Update position and draw targets from the core engine database
        for hex_code, data in list(self.engine.tracked_targets.items()):
            pkt = data["packet"]

            # Linear vacuum physics propagation
            pkt.x += pkt.vx * time_step
            pkt.y += pkt.vy * time_step
            pkt.z += pkt.vz * time_step

            # Feed updated data back into math engine to recalculate LFL
            self.engine.process_adsb_packet(pkt)
            current_lfl = data["current_lfl"]

            # Convert 3D space coordinates to 2D UI screen pixels
            screen_x = self.CENTER_X + (pkt.x - self.engine.R_EQ) * self.SCALE
            screen_y = self.CENTER_Y - (pkt.y * self.SCALE) # Invert Y for standard screen coordinates

            # Draw a vector block representing the spacecraft blip
            self.canvas.create_oval(screen_x - 4, screen_y - 4, screen_x + 4, screen_y + 4, fill="#00ffcc", outline="#ffffff")
            
            # Draw Data Block (Callsign and Flight Level) next to the blip
            self.canvas.create_text(
                screen_x + 12, screen_y - 12, 
                text=f"{pkt.callsign}\nLFL {current_lfl}", 
                fill="#00ffcc", font=("Courier", 9), anchor=tk.NW
            )

        # Run tactical conflict calculations behind the scenes
        self.engine.run_stca_scan()

        # Schedule the next screen refresh in 100 milliseconds
        self.root.after(100, self.update_radar_loop)

if __name__ == "__main__":
    root = tk.Tk()
    app = LunarRadarGUI(root)
    root.mainloop()