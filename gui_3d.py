import sys
import os
import numpy as np
import math
import collections
import random
from datetime import datetime
import pyqtgraph.opengl as gl

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, 
                             QDockWidget, QFrame, QFormLayout, QTextEdit, 
                             QPushButton, QVBoxLayout, QStackedWidget, QLineEdit, QHBoxLayout)
from PyQt6.QtCore import QTimer, Qt, QThread, pyqtSignal, QRectF
from PyQt6.QtGui import QPainter, QPen, QColor, QFont
from PIL import Image

from core.dataclasses import LunarADSBPacket
from core.engine import LunarEngine

try:
    from stable_baselines3 import PPO
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

# =====================================================================
# 1. SPINNER
# =====================================================================
class TacticalSpinner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(100, 100)
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_angle)
        self.timer.start(15) 

    def update_angle(self):
        self.angle = (self.angle + 5) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(0, 150, 200, 40)) 
        pen.setWidth(4)
        painter.setPen(pen)
        painter.drawArc(QRectF(10, 10, 80, 80), 0, 360 * 16)
        pen_head = QPen(QColor("#00aaff")) 
        pen_head.setWidth(4)
        painter.setPen(pen_head)
        painter.drawArc(QRectF(10, 10, 80, 80), -self.angle * 16, 90 * 16)

# =====================================================================
# 2. MOON LOADER THREAD
# =====================================================================
class MoonLoaderThread(QThread):
    finished_signal = pyqtSignal(object, object, object) 

    def run(self):
        md = gl.MeshData.sphere(rows=1400, cols=1400)
        verts = md.vertexes() if callable(getattr(md, 'vertexes', None)) else md.vertexes
        faces = md.faces() if callable(getattr(md, 'faces', None)) else md.faces

        x, y, z = verts[:, 0], verts[:, 1], verts[:, 2]
        lon = np.arctan2(y, x)
        r = np.sqrt(x**2 + y**2 + z**2)
        lat = np.arcsin(z / r)
        u = (lon + np.pi) / (2 * np.pi)
        v = 1.0 - ((lat + np.pi / 2) / np.pi)

        try:
            img = Image.open("moon_texture_high_res.jpg").convert('RGBA')
            img_np = np.array(img)
            h, w = img_np.shape[:2]
            px = np.clip((u * w).astype(int), 0, w - 1)
            py = np.clip((v * h).astype(int), 0, h - 1)
            colors = img_np[py, px] / 255.0
        except Exception:
            colors = np.ones((len(verts), 4)) * 0.5

        self.finished_signal.emit(verts, faces, colors)

# =====================================================================
# 3. HLAVNÍ APLIKACE LUNAR ATC
# =====================================================================
class LunarRadar3D(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LunarATC - Autonomous Systems Integration & LLM Engine")
        self.resize(1920, 1080)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.stacked = QStackedWidget()
        self.layout.addWidget(self.stacked)

        self.loading_widget = QWidget()
        self.loading_widget.setStyleSheet("background-color: #010203;")
        self.setup_loading_screen()
        self.stacked.addWidget(self.loading_widget)

        self.view = gl.GLViewWidget()
        self.view.setBackgroundColor('#020408') 
        self.view.setCameraPosition(distance=6000000) 
        self.stacked.addWidget(self.view)
        
        self.stacked.setCurrentWidget(self.loading_widget)

        # --- ENGINE & STATE ---
        self.engine = LunarEngine()
        self.MU = 4.9048695e12 
        self.history_paths = collections.defaultdict(lambda: collections.deque(maxlen=300))
        
        self.history_lines = {}
        self.prediction_lines = {}
        self.prediction_10m_markers = {} 
        self.ship_labels = {} 
        
        self.tick_counter = 0

        # --- ZÁCHRANNÁ BRZDA PROTI SPAMU ---
        self.crashed_ships = set()

        # --- DISCOVERY ENGINE (Black Box Logs) ---
        self.incident_logs = []

        # --- AI MOZEK (PPO) ---
        self.ai_model = None
        self.load_ai_brain()

        self.view.mousePressEvent = self.on_mouse_click

        self.setup_surface_infrastructure()
        self.setup_mock_traffic()
        
        self.setup_terminal_ui() 
        self.setup_sidebar_ui()  
        self.term_dock.hide()
        self.dock.hide()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_radar_loop)

    def load_ai_brain(self):
        if AI_AVAILABLE and os.path.exists("lunar_autopilot_v1.zip"):
            try:
                self.ai_model = PPO.load("lunar_autopilot_v1")
                print("🧠 AI Brain loaded.")
            except Exception as e:
                print(f"Error loading model: {e}")

    def on_mouse_click(self, ev):
        super(gl.GLViewWidget, self.view).mousePressEvent(ev)
        if ev.button() != Qt.MouseButton.LeftButton or not self.engine.tracked_targets:
            return
            
        import random
        selected_hex = random.choice(list(self.engine.tracked_targets.keys()))
        self.select_vessel(selected_hex)

    def select_vessel(self, hex_code):
        pkt = self.engine.tracked_targets[hex_code]["packet"]
        self.log_msg(f"ATC: Locked telemetry on vector {pkt.callsign}.", "#00ccff")
        
        # Identify flight phase
        phase = self.engine.get_flight_phase(pkt)
        self.log_msg(f"STATUS_ALERT: {pkt.callsign} identified in phase: {phase}.", "#ffff00")
        
        self.ui_callsign.setText(pkt.callsign)
        self.ui_class.setText(f"{pkt.classification} // {phase}")

        if self.engine.tracked_targets[hex_code].get("autopilot", False):
            self.btn_ai.setText("🛑 DISENGAGE NEURAL PILOT")
            self.btn_ai.setStyleSheet("QPushButton { background-color: #220000; color: #ff3333; font-weight: bold; padding: 10px; border: 2px solid #ff3333; margin-top: 15px; }")
        else:
            self.btn_ai.setText("🧠 ENGAGE NEURAL PILOT")
            self.btn_ai.setStyleSheet("QPushButton { background-color: #002211; color: #00ff66; font-weight: bold; padding: 10px; border: 2px solid #00ff66; margin-top: 15px; }")

    def setup_surface_infrastructure(self):
        bases = [
            {"name": "ARTEMIS BASE", "lat": -89.5, "lon": 0.0, "color": (0,255,150,200)},
            {"name": "TRANQUILITY PORT", "lat": 0.67, "lon": 23.47, "color": (0,255,150,200)},
            {"name": "COPERNICUS RADAR", "lat": 9.6, "lon": -20.0, "color": (255,150,0,200)}
        ]
        for b in bases:
            lat_r = math.radians(b["lat"])
            lon_r = math.radians(b["lon"])
            R = self.engine.R_EQ
            x = R * math.cos(lat_r) * math.cos(lon_r)
            y = R * math.cos(lat_r) * math.sin(lon_r)
            z = R * math.sin(lat_r)
            c_qt = QColor(*b["color"])
            pt = gl.GLScatterPlotItem(pos=np.array([[x, y, z]]), color=np.array([b["color"]])/255.0, size=15, pxMode=True)
            self.view.addItem(pt)
            font = QFont("Consolas", 12, QFont.Weight.Bold)
            text = gl.GLTextItem(pos=np.array([x, y, z + 50000]), text=f"⬢ {b['name']}", font=font, color=c_qt)
            self.view.addItem(text)

    def setup_loading_screen(self):
        layout = QVBoxLayout(self.loading_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("LUNAR ATC")
        title.setStyleSheet("color: #00f2ff; font-family: 'Consolas', monospace; font-size: 100px; font-weight: 900; letter-spacing: 15px; text-shadow: 0 0 20px #00f2ff;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("DECONFLICTION OPERATING SYSTEM v2.0")
        subtitle.setStyleSheet("color: #aa55ff; font-family: 'Consolas', monospace; font-size: 18px; letter-spacing: 10px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spinner = TacticalSpinner()
        self.loading_status = QLabel("INITIALIZING KINEMATIC CORE...")
        self.loading_status.setStyleSheet("color: #00f2ff; font-family: 'Consolas', monospace; font-size: 14px; margin-top: 30px; text-transform: uppercase;")
        self.loading_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(60)
        layout.addWidget(self.spinner, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.loading_status)
        layout.addStretch()

    def start_loading(self):
        self.loading_status.setText("MAP_TOPOGRAPHY: RESOLVING 1.9M VERTICES...")
        self.loader_thread = MoonLoaderThread()
        self.loader_thread.finished_signal.connect(self.on_moon_loaded)
        self.loader_thread.start()

    def on_moon_loaded(self, verts, faces, colors):
        self.loading_status.setText("GPU_UPLINK: TRANSMITTING TEXTURE BUFFERS...")
        QApplication.processEvents()

        md = gl.MeshData(vertexes=verts, faces=faces, vertexColors=colors)
        moon = gl.GLMeshItem(meshdata=md, smooth=True, shader='shaded')
        moon.scale(self.engine.R_EQ, self.engine.R_EQ, self.engine.R_EQ)
        self.view.addItem(moon)
        
        # --- ORBITAL BOUNDARIES ---
        self.draw_orbital_boundary(self.engine.R_EQ + self.engine.ZONE_LLO, (0, 242, 255, 40), "LLO_BOUNDARY")
        self.draw_orbital_boundary(self.engine.R_EQ + self.engine.ZONE_MLO, (0, 100, 255, 30), "MLO_BOUNDARY")
        self.draw_orbital_boundary(self.engine.SOI_RADIUS, (255, 50, 50, 20), "SOI_BOUNDARY")

        # --- RESTRICTED ZONES ---
        for zone in self.engine.RESTRICTED_ZONES:
            self.draw_restricted_zone(zone)

        grid = gl.GLGridItem()
        grid.setSize(x=20000000, y=20000000)
        grid.setSpacing(x=2000000, y=2000000)
        grid.setColor((0, 242, 255, 20)) 
        self.view.addItem(grid)

        self.stacked.setCurrentWidget(self.view)
        self.term_dock.show()
        self.dock.show()
        
        self.timer.start(50)
        self.log_msg("SYSTEM_READY: KINEMATIC CORE ONLINE.", "#00f2ff")

    def draw_restricted_zone(self, zone):
        lat_r = math.radians(zone["lat"])
        lon_r = math.radians(zone["lon"])
        R = self.engine.R_EQ
        cx = R * math.cos(lat_r) * math.cos(lon_r)
        cy = R * math.cos(lat_r) * math.sin(lon_r)
        cz = R * math.sin(lat_r)

        pts = []
        for i in range(51):
            angle = 2 * math.pi * i / 50
            # Rough circle on the surface
            dx = zone["radius"] * math.cos(angle)
            dy = zone["radius"] * math.sin(angle)
            pts.append([cx + dx, cy + dy, cz])

        line = gl.GLLinePlotItem(pos=np.array(pts), color=(1.0, 0.2, 0.2, 0.5), width=2.0, antialias=True)
        self.view.addItem(line)
        text = gl.GLTextItem(pos=np.array([cx, cy, cz + zone["alt_limit"]]), text=f"[RESTRICTED]\n{zone['name']}", font=QFont("Consolas", 8), color=QColor(255, 50, 50, 200))
        self.view.addItem(text)

    def draw_orbital_boundary(self, radius, color, label):
        pts = []
        for i in range(101):
            angle = 2 * math.pi * i / 100
            pts.append([radius * math.cos(angle), radius * math.sin(angle), 0])
        line = gl.GLLinePlotItem(pos=np.array(pts), color=np.array(color)/255.0, width=1.5, antialias=True)
        self.view.addItem(line)
        text = gl.GLTextItem(pos=np.array([radius, 0, 0]), text=label, font=QFont("Consolas", 8), color=QColor(*color))
        self.view.addItem(text)

    def setup_terminal_ui(self):
        self.term_dock = QDockWidget("TACTICAL LOG // SELENOCENTRIC_COMMS", self)
        self.term_dock.setStyleSheet("QDockWidget { color: #00f2ff; font-family: 'Consolas'; font-weight: bold; }")
        self.term_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setStyleSheet("background-color: #010204; color: #00ff88; font-family: 'Consolas', monospace; font-size: 13px; border: 1px solid #004466; padding: 10px;")
        self.term_dock.setWidget(self.terminal)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.term_dock)
        self.term_dock.setFixedHeight(250)

    def log_msg(self, message, color="#00ff88"):
        time_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        formatted_msg = f'<span style="color: #224466;">[{time_str}]</span> <span style="color: {color}; font-weight: bold;">{message}</span>'
        self.terminal.append(formatted_msg)
        scrollbar = self.terminal.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def get_sector(self, x, y):
        angle = math.degrees(math.atan2(y, x))
        if angle < 0: angle += 360
        if angle < 90: return "SEC_ALPHA"
        elif angle < 180: return "SEC_BETA"
        elif angle < 270: return "SEC_GAMMA"
        else: return "SEC_DELTA"

    def setup_sidebar_ui(self):
        self.dock = QDockWidget("TACTICAL COMMAND CENTER", self)
        self.dock.setStyleSheet("QDockWidget { color: #00f2ff; font-family: 'Consolas'; font-weight: bold; }")
        self.dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)

        self.panel_widget = QFrame()
        self.panel_widget.setStyleSheet("QFrame { background-color: #020408; border-left: 1px solid #00f2ff; } QLabel { color: #447799; font-family: 'Consolas'; font-size: 13px; text-transform: uppercase; }")
        self.panel_layout = QVBoxLayout(self.panel_widget)
        self.panel_layout.setContentsMargins(15, 15, 15, 15)

        val_sty = "color: #ffffff; font-weight: bold; font-size: 14px; border: none; font-family: 'Consolas';"
        header_sty = "color: #00f2ff; font-weight: bold; font-size: 16px; border-bottom: 1px solid #00f2ff; padding-bottom: 5px; margin-top: 10px;"
        
        # --- TITLE ---
        self.ui_callsign = QLabel("SCANNING...")
        self.ui_callsign.setStyleSheet("color: #00f2ff; font-weight: 900; font-size: 28px; border: none; letter-spacing: 2px;")
        self.panel_layout.addWidget(self.ui_callsign)
        self.panel_layout.addSpacing(10)

        # --- TELEMETRY & NETWORK ---
        lbl_net = QLabel("NETWORK & TELEMETRY"); lbl_net.setStyleSheet(header_sty)
        self.panel_layout.addWidget(lbl_net)
        
        form_net = QFormLayout()
        self.ui_class = QLabel("--"); self.ui_class.setStyleSheet(val_sty)
        self.ui_comms = QLabel("--"); self.ui_comms.setStyleSheet(val_sty)
        self.ui_signal = QLabel("100%"); self.ui_signal.setStyleSheet("color: #00ff66; font-weight: bold; font-size: 14px; font-family: 'Consolas';")
        form_net.addRow("IDENTIFICATION:", self.ui_class)
        form_net.addRow("COMMS_LINK:", self.ui_comms)
        form_net.addRow("SIGNAL_INTEGRITY:", self.ui_signal)
        self.panel_layout.addLayout(form_net)

        # --- FLIGHT DYNAMICS ---
        lbl_dyn = QLabel("FLIGHT DYNAMICS (6-DOF)"); lbl_dyn.setStyleSheet(header_sty)
        self.panel_layout.addWidget(lbl_dyn)

        form_dyn = QFormLayout()
        self.ui_alt = QLabel("--"); self.ui_alt.setStyleSheet(val_sty)
        self.ui_vel = QLabel("--"); self.ui_vel.setStyleSheet(val_sty)
        self.ui_escape = QLabel("--"); self.ui_escape.setStyleSheet("color: #ff5555; font-weight: bold; font-size: 14px; font-family: 'Consolas';")
        self.ui_orient = QLabel("--"); self.ui_orient.setStyleSheet("color: #00ffcc; font-family: 'Consolas'; font-size: 13px;")
        
        form_dyn.addRow("ALT_LFL:", self.ui_alt)
        form_dyn.addRow("VELOCITY_MAG:", self.ui_vel)
        form_dyn.addRow("V_ESCAPE_LOCAL:", self.ui_escape)
        form_dyn.addRow("ORIENTATION:", self.ui_orient)
        self.panel_layout.addLayout(form_dyn)

        # --- PROPULSION & OPERATIONS ---
        lbl_prop = QLabel("PROPULSION & OPERATIONS"); lbl_prop.setStyleSheet(header_sty)
        self.panel_layout.addWidget(lbl_prop)

        form_prop = QFormLayout()
        self.ui_fuel = QLabel("--"); self.ui_fuel.setStyleSheet("color: #ffaa00; font-weight: bold; font-size: 15px; border: none;")
        form_prop.addRow("DELTA-V_BUDGET:", self.ui_fuel)
        self.panel_layout.addLayout(form_prop)

        self.panel_layout.addStretch()

        # --- COMMAND BUTTONS ---
        btn_sty = "QPushButton { background-color: #001122; color: #00f2ff; font-family: 'Consolas'; font-weight: bold; padding: 10px; border: 1px solid #00f2ff; } QPushButton:hover { background-color: #00f2ff; color: #000000; }"
        
        # EXACT DELTA-V INPUT
        input_layout = QHBoxLayout()
        self.input_dv = QLineEdit("0.0")
        self.input_dv.setStyleSheet("QLineEdit { background-color: #010204; color: #00f2ff; font-family: 'Consolas'; font-size: 16px; font-weight: bold; border: 1px solid #00f2ff; padding: 5px; }")
        self.input_dv.setFixedWidth(80)
        lbl_dv = QLabel("m/s ΔV")
        lbl_dv.setStyleSheet("color: #447799; font-family: 'Consolas'; font-size: 13px; font-weight: bold;")
        
        self.btn_execute_dv = QPushButton("EXECUTE EXACT BURN")
        self.btn_execute_dv.setStyleSheet(btn_sty)
        self.btn_execute_dv.clicked.connect(self.apply_exact_vector_burn)
        
        input_layout.addWidget(self.input_dv)
        input_layout.addWidget(lbl_dv)
        input_layout.addWidget(self.btn_execute_dv)
        self.panel_layout.addLayout(input_layout)

        self.btn_send_vector = QPushButton("📡 TRANSMIT NEW FLIGHT VECTOR")
        self.btn_send_vector.setStyleSheet("QPushButton { background-color: #221100; color: #ffcc00; font-family: 'Consolas'; font-weight: bold; padding: 12px; border: 1px solid #ffcc00; margin-top: 5px; } QPushButton:hover { background-color: #ffcc00; color: black; }")
        self.btn_send_vector.clicked.connect(self.transmit_vector_command)
        self.panel_layout.addWidget(self.btn_send_vector)

        self.btn_ai = QPushButton("🧠 NEURAL AUTOPILOT [OFF]")
        self.btn_ai.setStyleSheet("QPushButton { background-color: #051105; color: #00ff66; font-weight: bold; padding: 12px; border: 1px solid #00ff66; margin-top: 15px; }")
        self.btn_ai.clicked.connect(self.toggle_ai_autopilot)
        self.panel_layout.addWidget(self.btn_ai)

        self.btn_llm = QPushButton("🔮 RUN SYSTEM_AUDIT (LLM)")
        self.btn_llm.setStyleSheet("QPushButton { background-color: #110022; color: #cc66ff; font-weight: bold; padding: 12px; border: 1px solid #cc66ff; margin-top: 15px; } QPushButton:hover { background-color: #cc66ff; color: white; }")
        self.btn_llm.clicked.connect(self.run_llm_diagnostic)
        self.panel_layout.addWidget(self.btn_llm)

        self.dock.setWidget(self.panel_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock)

    def transmit_vector_command(self):
        callsign = self.ui_callsign.text()
        if callsign == "AWAITING SELECTION...": return
        for hex_code, data in self.engine.tracked_targets.items():
            if data["packet"].callsign == callsign:
                if random.random() < 0.2: # 20% chance to reject
                    self.log_msg(f"⚠ ATC UPLINK FAILED: Vector command REJECTED by {callsign} (Pilot Override).", "#ff5555")
                else:
                    target_yaw = random.choice([0, 90, 180, 270])
                    target_pitch = random.choice([-30, 0, 30])
                    data["target_pitch"] = target_pitch
                    data["target_yaw"] = target_yaw
                    self.log_msg(f"ATC UPLINK: Vector ACCEPTED by {callsign}. Re-aligning to Y:{target_yaw}° P:{target_pitch}°...", "#00ffcc")
                break

    def toggle_ai_autopilot(self):
        callsign = self.ui_callsign.text()
        if callsign == "AWAITING SELECTION...": return

        for hex_code, data in self.engine.tracked_targets.items():
            if data["packet"].callsign == callsign:
                if data.get("landed", False):
                    return
                current_state = data.get("autopilot", False)
                data["autopilot"] = not current_state
                if data["autopilot"]:
                    self.log_msg(f"⚠ SYSTEM OVERRIDE: AI Copilot taking control of {callsign}.", "#00ff66")
                    self.btn_ai.setText("🛑 DISENGAGE AI AUTOPILOT")
                    self.btn_ai.setStyleSheet("QPushButton { background-color: #331111; color: #ff3333; font-weight: bold; padding: 10px; border: 2px solid #ff3333; margin-top: 15px; }")
                else:
                    self.log_msg(f"ATC: Manual control restored for {callsign}.", "#ffaa00")
                    self.btn_ai.setText("🧠 ENGAGE AI AUTOPILOT")
                    self.btn_ai.setStyleSheet("QPushButton { background-color: #113311; color: #00ff66; font-weight: bold; padding: 10px; border: 2px solid #00ff66; margin-top: 15px; }")
                break

    def apply_exact_vector_burn(self):
        try:
            dv = float(self.input_dv.text())
            self.apply_vector_burn(dv)
        except ValueError:
            self.log_msg("ATC UPLINK ERROR: Invalid Delta-V input. Must be a numeric value.", "#ff3333")

    def apply_vector_burn(self, speed_dv=0.0):
        callsign = self.ui_callsign.text()
        if callsign == "AWAITING SELECTION...": return
        for hex_code, data in self.engine.tracked_targets.items():
            if data["packet"].callsign == callsign:
                pkt = data["packet"]
                if data.get("landed", False) or pkt.fuel_dv < abs(speed_dv): return
                if data.get("autopilot", False): self.toggle_ai_autopilot()
                
                current_vel = math.sqrt(pkt.vx**2 + pkt.vy**2 + pkt.vz**2)
                
                if current_vel > 0:
                    factor = (current_vel + speed_dv) / current_vel
                    pkt.vx *= factor; pkt.vy *= factor; pkt.vz *= factor
                else:
                    # If stationary, boost directly "up" (z-axis) relative to Moon center
                    r = math.sqrt(pkt.x**2 + pkt.y**2 + pkt.z**2)
                    if r > 0:
                        pkt.vx += speed_dv * (pkt.x/r)
                        pkt.vy += speed_dv * (pkt.y/r)
                        pkt.vz += speed_dv * (pkt.z/r)
                        
                pkt.fuel_dv -= abs(speed_dv)
                self.log_msg(f"ATC: Manual vector updated for {callsign}.", "#ffffff")
                break

    # =====================================================================
    # THE LLM DISCOVERY ENGINE
    # =====================================================================
    def run_llm_diagnostic(self):
        if not self.incident_logs:
            self.log_msg("LLM DIAGNOSTIC: System Nominal. Insufficient incident data for analysis.", "#888888")
            return
            
        self.log_msg(f"LLM UPLINK: Compiling {len(self.incident_logs)} black box records...", "#cc66ff")
        self.log_msg("LLM UPLINK: Transmitting data to Engineering AI via secure API...", "#cc66ff")
        
        # Simulujeme síťové zpoždění
        QTimer.singleShot(2500, self.display_llm_response)

    def display_llm_response(self):
        crashes = len(self.incident_logs)
        avg_fuel = sum([log['fuel'] for log in self.incident_logs]) / crashes if crashes > 0 else 0
        darkside_crashes = sum(1 for log in self.incident_logs if "Darkside" in log['sector'])
        
        # Jednoduchá analytika simulující inteligenci LLM
        if darkside_crashes > crashes / 2 and avg_fuel > 100:
            analysis = f"PATTERN DETECTED: {darkside_crashes}/{crashes} failures occurred in Darkside sectors with ample fuel ({int(avg_fuel)} DV).\nPROBABLE CAUSE: Loss of Signal (LOS) telemetry blackout preventing automated terminal burns."
            solution = "1. [INFRASTRUCTURE] Deploy Lunar Gateway relay satellites at Earth-Moon L2.\n2. [SOFTWARE UPDATE] Code autonomous Inertial Navigation System (INS) fallback."
        elif avg_fuel < 50:
            analysis = f"PATTERN DETECTED: Vessels impacting surface due to critically low fuel budget (Avg remaining: {int(avg_fuel)} DV).\nPROBABLE CAUSE: Inefficient orbital transfer profiles or excess manual maneuvering."
            solution = "1. [CORE ENGINE] Implement automated Hohmann transfer calculator in UI.\n2. [PROCEDURE] Restrict manual overrides to +/- 5 m/s adjustments."
        else:
            analysis = f"PATTERN DETECTED: Sporadic high-velocity impacts ({crashes} total).\nPROBABLE CAUSE: Unpredictable orbital decay caused by Lunar Mascon gravitational anomalies."
            solution = "1. [PHYSICS ENGINE] Implement precise spherical harmonic gravity models (Mascons).\n2. [SOFTWARE] Add automated Station-Keeping algorithm to AI Autopilot."

        report = (
            f"<br><span style='color:#ff55ff; font-weight:bold; font-size:14px;'>"
            f"====================================================<br>"
            f"  LLM ENGINEERING PROPOSAL & ANOMALY REPORT<br>"
            f"====================================================<br>"
            f"</span>"
            f"<span style='color:#e0e6ed;'>"
            f"{analysis}<br><br>"
            f"</span>"
            f"<span style='color:#00ffcc; font-weight:bold;'>"
            f"⚙ RECOMMENDED SYSTEM ARCHITECTURE UPGRADES:<br>"
            f"{solution}<br>"
            f"</span>"
            f"<span style='color:#ff55ff; font-weight:bold; font-size:14px;'>"
            f"====================================================</span><br>"
        )
        self.terminal.append(report)
        scrollbar = self.terminal.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        # Reset logů po analýze
        self.incident_logs = []

    def setup_mock_traffic(self):
        import simulation
        simulation.generate_initial_traffic(self.engine)
        
        # Simulate a comms blackout for one of the ships
        if "8B9E44" in self.engine.tracked_targets: # CRG-ARES
            self.engine.tracked_targets["8B9E44"]["packet"].comms_active = False

        self.scatter = gl.GLScatterPlotItem(pos=np.zeros((1, 3)), size=16, pxMode=True)
        self.view.addItem(self.scatter)

    def update_radar_loop(self):
        time_step = 20.0 
        self.tick_counter += 1
        
        positions = []
        colors = []

        for hex_code, data in list(self.engine.tracked_targets.items()):
            pkt = data["packet"]
            if pkt.classification == "BASE": continue 
            
            # AI Mozek logic omitted for simplicity
            
            if not data.get("landed", False):
                # --- ATC VECTOR COMMAND STEERING ---
                if "target_pitch" in data and "target_yaw" in data:
                    dp = data["target_pitch"] - pkt.pitch
                    dy = data["target_yaw"] - pkt.yaw
                    
                    # Normalize angles
                    dy = (dy + 180) % 360 - 180
                    
                    if abs(dp) > 1: pkt.pitch += 1.0 * (1 if dp > 0 else -1)
                    if abs(dy) > 1: pkt.yaw += 1.0 * (1 if dy > 0 else -1)
                    
                    # Apply vector to velocity if flight assist is ON
                    speed = math.sqrt(pkt.vx**2 + pkt.vy**2 + pkt.vz**2)
                    if speed > 0 and getattr(pkt, 'flight_assist', False):
                        pr = math.radians(pkt.pitch)
                        yr = math.radians(pkt.yaw)
                        pkt.vx = speed * math.cos(pr) * math.cos(yr)
                        pkt.vy = speed * math.cos(pr) * math.sin(yr)
                        pkt.vz = speed * math.sin(pr)

                # USE 6-DOF PROPAGATION FROM ENGINE
                nx, ny, nz, nvx, nvy, nvz, n_pitch, nyw, nr = self.engine.propagate_state(pkt, time_step)
                pkt.x, pkt.y, pkt.z = nx, ny, nz
                pkt.vx, pkt.vy, pkt.vz = nvx, nvy, nvz
                pkt.pitch, pkt.yaw, pkt.roll = n_pitch, nyw, nr

                current_radius = math.sqrt(pkt.x**2 + pkt.y**2 + pkt.z**2)
                
                # RESTRICTED ZONE CHECK
                zone = self.engine.check_restricted_zones(pkt)
                if zone and not data.get("in_restricted_zone", False):
                    self.log_msg(f"⚠ SECURITY ALERT: {pkt.callsign} entered RESTRICTED ZONE ({zone}).", "#ff5555")
                    data["in_restricted_zone"] = True
                elif not zone and data.get("in_restricted_zone", False):
                    data["in_restricted_zone"] = False

                # Detekce pádu na povrch
                if current_radius <= self.engine.R_EQ:
                    data["landed"] = True
                    self.crashed_ships.add(hex_code) 
                    
                    if data.get("autopilot"): self.toggle_ai_autopilot()
                    
                    current_sector = self.get_sector(pkt.x, pkt.y)
                    self.incident_logs.append({"callsign": pkt.callsign, "fuel": pkt.fuel_dv, "sector": current_sector})
                    
                    pkt.vx, pkt.vy, pkt.vz = 0, 0, 0
                    pkt.v_pitch, pkt.v_yaw, pkt.v_roll = 0, 0, 0
                    scale = self.engine.R_EQ / current_radius
                    pkt.x *= scale; pkt.y *= scale; pkt.z *= scale
                    self.log_msg(f"⚠ CRITICAL: {pkt.callsign} IMPACT DETECTED.", "#ff3333")

            self.engine.process_adsb_packet(pkt)
            self.history_paths[hex_code].append([pkt.x, pkt.y, pkt.z])
            positions.append([pkt.x, pkt.y, pkt.z])
            
            # Color logic based on status
            base_color = (0, 150, 255, 255)
            if not pkt.comms_active: base_color = (150, 150, 150, 100)
            if data.get("landed", False): base_color = (255, 50, 50, 255)
            colors.append([c/255.0 for c in base_color])

            # --- PATH & VECTOR DRAWING ---
            hist_pts = np.array(self.history_paths[hex_code])
            if len(hist_pts) > 1:
                if hex_code not in self.history_lines:
                    line = gl.GLLinePlotItem(color=[c/255.0 for c in base_color], width=2.0, antialias=True)
                    self.view.addItem(line)
                    self.history_lines[hex_code] = line
                self.history_lines[hex_code].setData(pos=hist_pts, color=[c/255.0 for c in base_color])

            if data.get("landed", False):
                if hex_code in self.prediction_lines: self.prediction_lines[hex_code].setData(pos=np.empty((0,3)))
            else:
                pred_pts = []
                temp_pkt = LunarADSBPacket(
                    hex_code=pkt.hex_code, callsign=pkt.callsign, timestamp=pkt.timestamp,
                    classification=pkt.classification, mission_type=pkt.mission_type, fuel_dv=pkt.fuel_dv,
                    x=pkt.x, y=pkt.y, z=pkt.z, vx=pkt.vx, vy=pkt.vy, vz=pkt.vz,
                    pitch=pkt.pitch, yaw=pkt.yaw, roll=pkt.roll,
                    v_pitch=0, v_yaw=0, v_roll=0, t_burn=0, delta_vx=0, delta_vy=0, delta_vz=0, burn_duration=0,
                    comms_active=pkt.comms_active, channel_freq=pkt.channel_freq
                )
                
                # Predict next 60 steps (60 * 20s = 20 minutes)
                for step in range(60):
                    pred_pts.append([temp_pkt.x, temp_pkt.y, temp_pkt.z])
                    nx, ny, nz, nvx, nvy, nvz, _, _, _ = self.engine.propagate_state(temp_pkt, 20.0)
                    temp_pkt.x, temp_pkt.y, temp_pkt.z = nx, ny, nz
                    temp_pkt.vx, temp_pkt.vy, temp_pkt.vz = nvx, nvy, nvz
                    if math.sqrt(temp_pkt.x**2 + temp_pkt.y**2 + temp_pkt.z**2) <= self.engine.R_EQ: break 
                
                if hex_code not in self.prediction_lines:
                    pred_line = gl.GLLinePlotItem(color=(1.0, 1.0, 1.0, 0.4), width=1.0, mode='line_strip')
                    self.view.addItem(pred_line)
                    self.prediction_lines[hex_code] = pred_line
                self.prediction_lines[hex_code].setData(pos=np.array(pred_pts))

            speed = int(math.sqrt(pkt.vx**2 + pkt.vy**2 + pkt.vz**2))
            alt_text = "LND" if data.get("landed", False) else f"FL{int(data['current_lfl'])}"
            label_text = f"[{pkt.callsign}]\nP:{int(pkt.pitch)} Y:{int(pkt.yaw)} R:{int(pkt.roll)}\n{alt_text} | {speed} m/s"
            
            c_qt_label = QColor(*base_color)
            if hex_code not in self.ship_labels:
                label = gl.GLTextItem(pos=np.array([pkt.x, pkt.y, pkt.z]), text=label_text, font=QFont("Consolas", 9), color=c_qt_label)
                self.view.addItem(label)
                self.ship_labels[hex_code] = label
            offset_z = 40000 if not data.get("landed", False) else 10000
            self.ship_labels[hex_code].setData(pos=np.array([pkt.x + 40000, pkt.y, pkt.z + offset_z]), text=label_text, color=c_qt_label)

        if positions:
            self.scatter.setData(pos=np.array(positions), color=np.array(colors))
        
        if self.ui_callsign.text() != "SCANNING...":
            for target_data in self.engine.tracked_targets.values():
                if target_data["packet"].callsign == self.ui_callsign.text():
                    pkt = target_data["packet"]
                    total_vel = math.sqrt(pkt.vx**2 + pkt.vy**2 + pkt.vz**2)
                    r = math.sqrt(pkt.x**2 + pkt.y**2 + pkt.z**2)
                    v_esc = self.engine.get_escape_velocity(r)

                    self.ui_fuel.setText(f"{int(pkt.fuel_dv)} m/s")
                    if target_data.get("landed", False):
                        self.ui_alt.setText("SURFACE")
                        self.ui_vel.setText("0.0 m/s")
                        self.ui_escape.setText("--")
                    else:
                        self.ui_alt.setText(f"LFL {target_data['current_lfl']}")
                        self.ui_vel.setText(f"{round(total_vel, 1)} m/s")
                        self.ui_escape.setText(f"{int(v_esc)} m/s")
                        
                        if total_vel >= v_esc:
                            self.ui_escape.setStyleSheet("color: #ff3333; font-weight: bold; font-size: 14px; font-family: 'Consolas';") # Warn
                        else:
                            self.ui_escape.setStyleSheet("color: #00ffcc; font-weight: bold; font-size: 14px; font-family: 'Consolas';") # Safe

                    self.ui_orient.setText(f"P: {int(pkt.pitch)}° | Y: {int(pkt.yaw)}° | R: {int(pkt.roll)}°")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    radar = LunarRadar3D()
    radar.showMaximized()
    QTimer.singleShot(1000, radar.start_loading)
    sys.exit(app.exec())