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
                             QPushButton, QVBoxLayout, QStackedWidget)
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
        self.loading_widget.setStyleSheet("background-color: #020305;")
        self.setup_loading_screen()
        self.stacked.addWidget(self.loading_widget)

        self.view = gl.GLViewWidget()
        self.view.setBackgroundColor('#04060a') 
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
        self.log_msg(f"ATC: Locked telemetry on vector {pkt.callsign}.")
        self.ui_callsign.setText(pkt.callsign)
        self.ui_class.setText(pkt.classification)

        if self.engine.tracked_targets[hex_code].get("autopilot", False):
            self.btn_ai.setText("🛑 DISENGAGE AI AUTOPILOT")
            self.btn_ai.setStyleSheet("QPushButton { background-color: #331111; color: #ff3333; font-weight: bold; padding: 10px; border: 2px solid #ff3333; margin-top: 15px; }")
        else:
            self.btn_ai.setText("🧠 ENGAGE AI AUTOPILOT")
            self.btn_ai.setStyleSheet("QPushButton { background-color: #113311; color: #00ff66; font-weight: bold; padding: 10px; border: 2px solid #00ff66; margin-top: 15px; }")

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
            text = gl.GLTextItem(pos=np.array([x, y, z + 50000]), text=f"[{b['name']}]", font=font, color=c_qt)
            self.view.addItem(text)

    def setup_loading_screen(self):
        layout = QVBoxLayout(self.loading_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("LunarATC Core")
        title.setStyleSheet("color: #00aaff; font-family: 'Consolas', monospace; font-size: 80px; font-weight: 900; letter-spacing: 5px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("LLM DISCOVERY ENGINE INITIALIZATION")
        subtitle.setStyleSheet("color: #aa55ff; font-family: 'Consolas', monospace; font-size: 20px; letter-spacing: 8px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spinner = TacticalSpinner()
        self.loading_status = QLabel("BOOTING KINEMATIC CORE...")
        self.loading_status.setStyleSheet("color: #00aaff; font-family: 'Consolas', monospace; font-size: 14px; margin-top: 30px;")
        self.loading_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(60)
        layout.addWidget(self.spinner, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.loading_status)
        layout.addStretch()

    def start_loading(self):
        self.loading_status.setText("MAPPING LUNAR TOPOGRAPHY (1.9M VERTICES)...")
        self.loader_thread = MoonLoaderThread()
        self.loader_thread.finished_signal.connect(self.on_moon_loaded)
        self.loader_thread.start()

    def on_moon_loaded(self, verts, faces, colors):
        self.loading_status.setText("UPLOADING TEXTURES TO GPU...")
        QApplication.processEvents()

        md = gl.MeshData(vertexes=verts, faces=faces, vertexColors=colors)
        moon = gl.GLMeshItem(meshdata=md, smooth=True, shader='shaded')
        moon.scale(self.engine.R_EQ, self.engine.R_EQ, self.engine.R_EQ)
        self.view.addItem(moon)
        
        grid = gl.GLGridItem()
        grid.setSize(x=20000000, y=20000000)
        grid.setSpacing(x=2000000, y=2000000)
        grid.setColor((100, 150, 200, 25)) 
        self.view.addItem(grid)

        self.stacked.setCurrentWidget(self.view)
        self.term_dock.show()
        self.dock.show()
        
        self.timer.start(50)
        self.log_msg("SYSTEM BOOT: LLM Discovery Engine ready.", "#aa55ff")

    def setup_terminal_ui(self):
        self.term_dock = QDockWidget("SYSTEM COMMUNICATIONS LOG", self)
        self.term_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        self.term_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setStyleSheet("background-color: #030408; color: #00ff88; font-family: 'Consolas', monospace; font-size: 14px; border-top: 2px solid #005588; padding: 5px;")
        self.term_dock.setWidget(self.terminal)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.term_dock)
        self.term_dock.setMinimumHeight(280) # Zvětšeno pro lepší čtení LLM reportů
        self.term_dock.setMaximumHeight(280)

    def log_msg(self, message, color="#00ff88"):
        time_str = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f'<span style="color: #445566;">[{time_str}]</span> <span style="color: {color};">{message}</span>'
        self.terminal.append(formatted_msg)
        scrollbar = self.terminal.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def get_sector(self, x, y):
        angle = math.degrees(math.atan2(y, x))
        if angle < 0: angle += 360
        if angle < 90: return "ALPHA (Sunward)"
        elif angle < 180: return "BETA (Darkside)"
        elif angle < 270: return "GAMMA (Darkside)"
        else: return "DELTA (Sunward)"

    def setup_sidebar_ui(self):
        self.dock = QDockWidget("FLIGHT PLANNER", self)
        self.dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        self.dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetFloatable | QDockWidget.DockWidgetFeature.DockWidgetMovable)

        self.panel_widget = QFrame()
        self.panel_widget.setStyleSheet("QFrame { background-color: #05080f; border-left: 2px solid #00aaff; margin: 2px; } QLabel { color: #7a8c9e; font-family: 'Consolas', monospace; font-size: 14px; padding: 2px; }")
        self.panel_layout = QFormLayout(self.panel_widget)
        self.panel_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        val_sty = "color: #e0e6ed; font-weight: bold; font-size: 14px; border: none;"
        
        self.ui_callsign = QLabel("AWAITING SELECTION...")
        self.ui_callsign.setStyleSheet("color: #ffffff; font-weight: 900; font-size: 20px; border: none;")
        self.ui_class = QLabel("--"); self.ui_class.setStyleSheet(val_sty)
        self.ui_fuel = QLabel("--"); self.ui_fuel.setStyleSheet("color: #ffaa00; font-weight: bold; font-size: 14px; border: none;")
        self.ui_alt = QLabel("--"); self.ui_alt.setStyleSheet(val_sty)
        self.ui_vel = QLabel("--"); self.ui_vel.setStyleSheet(val_sty)

        btn_sty = "QPushButton { background-color: #111822; color: #00aaff; font-weight: bold; padding: 6px; border: 1px solid #005588; } QPushButton:hover { background-color: #00aaff; color: black; }"
        
        self.btn_speed_up = QPushButton("+20 m/s VELOCITY (Prograde)")
        self.btn_speed_up.setStyleSheet(btn_sty)
        self.btn_speed_up.clicked.connect(lambda: self.apply_vector_burn(speed_dv=20.0))

        self.btn_speed_dn = QPushButton("-20 m/s VELOCITY (Retrograde)")
        self.btn_speed_dn.setStyleSheet(btn_sty.replace("#00aaff", "#ff8800").replace("#005588", "#aa5500"))
        self.btn_speed_dn.clicked.connect(lambda: self.apply_vector_burn(speed_dv=-20.0))

        self.btn_ai = QPushButton("🧠 ENGAGE AI AUTOPILOT")
        self.btn_ai.setStyleSheet("QPushButton { background-color: #113311; color: #00ff66; font-weight: bold; padding: 10px; border: 2px solid #00ff66; margin-top: 15px; }")
        self.btn_ai.clicked.connect(self.toggle_ai_autopilot)
        if not self.ai_model:
            self.btn_ai.setEnabled(False)
            self.btn_ai.setText("🧠 AI MODULE OFFLINE")
            self.btn_ai.setStyleSheet("QPushButton { background-color: #111111; color: #555555; font-weight: bold; padding: 10px; border: 2px solid #555555; margin-top: 15px; }")

        # Nové LLM Tlačítko
        self.btn_llm = QPushButton("🔮 RUN LLM SYSTEM DIAGNOSTIC")
        self.btn_llm.setStyleSheet("QPushButton { background-color: #220033; color: #cc66ff; font-weight: bold; padding: 12px; border: 2px solid #cc66ff; margin-top: 25px; } QPushButton:hover { background-color: #cc66ff; color: white; }")
        self.btn_llm.clicked.connect(self.run_llm_diagnostic)

        self.panel_layout.addRow(self.ui_callsign)
        self.panel_layout.addRow("CLASS:", self.ui_class)
        self.panel_layout.addRow("DELTA-V:", self.ui_fuel)
        self.panel_layout.addRow("ALTITUDE:", self.ui_alt)
        self.panel_layout.addRow("VELOCITY:", self.ui_vel)
        self.panel_layout.addRow(QLabel(" ")) 
        self.panel_layout.addRow(self.btn_speed_up)
        self.panel_layout.addRow(self.btn_speed_dn)
        self.panel_layout.addRow(self.btn_ai)
        self.panel_layout.addRow(self.btn_llm)

        self.dock.setWidget(self.panel_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock)

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

    def apply_vector_burn(self, speed_dv=0.0):
        callsign = self.ui_callsign.text()
        if callsign == "AWAITING SELECTION...": return
        for hex_code, data in self.engine.tracked_targets.items():
            if data["packet"].callsign == callsign:
                pkt = data["packet"]
                if data.get("landed", False) or pkt.fuel_dv < 40.0: return
                if data.get("autopilot", False): self.toggle_ai_autopilot()
                
                current_vel = math.sqrt(pkt.vx**2 + pkt.vy**2 + pkt.vz**2)
                factor = (current_vel + speed_dv) / current_vel
                pkt.vx *= factor; pkt.vy *= factor; pkt.vz *= factor
                pkt.fuel_dv -= 40.0
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
        alt_1 = 300000.0
        v_1 = math.sqrt(self.MU / (self.engine.R_EQ + alt_1))
        bad_v = v_1 * 0.85 
        
        self.engine.process_adsb_packet(LunarADSBPacket(
            hex_code="4A3F12", callsign="LUNAR-01", timestamp=0.0,
            classification="HMD (Manned)", mission_type="Orbital", fuel_dv=2000.0,
            x=self.engine.R_EQ + alt_1, y=0.0, z=0.0,
            vx=0.0, vy=bad_v, vz=150.0,
            t_burn=0.0, delta_vx=0.0, delta_vy=0.0, delta_vz=0.0, burn_duration=0.0
        ))
        
        alt_2 = 150000.0
        v_2 = math.sqrt(self.MU / (self.engine.R_EQ + alt_2))
        self.engine.process_adsb_packet(LunarADSBPacket(
            hex_code="8B9E44", callsign="CRG-HEAVY", timestamp=0.0,
            classification="CRG (Cargo)", mission_type="Supply", fuel_dv=5000.0,
            x=0.0, y=self.engine.R_EQ + alt_2, z=0.0,
            vx=-v_2, vy=0.0, vz=-50.0,
            t_burn=0.0, delta_vx=0.0, delta_vy=0.0, delta_vz=0.0, burn_duration=0.0
        ))

        self.scatter = gl.GLScatterPlotItem(pos=np.zeros((1, 3)), size=16, pxMode=True)
        self.view.addItem(self.scatter)

    def calculate_gravity(self, x, y, z):
        r = math.sqrt(x**2 + y**2 + z**2)
        if r == 0: return 0, 0, 0
        a = -self.MU / (r**2)
        return a * (x/r), a * (y/r), a * (z/r)

    def update_radar_loop(self):
        time_step = 20.0 
        self.tick_counter += 1
        
        positions = []
        colors = []

        for hex_code, data in list(self.engine.tracked_targets.items()):
            pkt = data["packet"]
            
            # --- ZÁCHRANNÁ BRZDA PROTI SPAMU ---
            if hex_code in self.crashed_ships:
                data["landed"] = True
            
            # AI Mozek
            if data.get("autopilot", False) and self.ai_model and not data.get("landed", False):
                if self.tick_counter % 20 == 0:
                    obs = np.array([pkt.x, pkt.y, pkt.z, pkt.vx, pkt.vy, pkt.vz, pkt.fuel_dv], dtype=np.float32)
                    action, _ = self.ai_model.predict(obs, deterministic=True)
                    if action == 1 and pkt.fuel_dv >= 10.0:
                        v_mag = math.sqrt(pkt.vx**2 + pkt.vy**2 + pkt.vz**2)
                        if v_mag > 0:
                            factor = (v_mag + 10.0) / v_mag
                            pkt.vx *= factor; pkt.vy *= factor; pkt.vz *= factor
                        pkt.fuel_dv -= 10.0
                    elif action == 2 and pkt.fuel_dv >= 10.0:
                        v_mag = math.sqrt(pkt.vx**2 + pkt.vy**2 + pkt.vz**2)
                        if v_mag > 0:
                            factor = max(0.1, (v_mag - 10.0)) / v_mag
                            pkt.vx *= factor; pkt.vy *= factor; pkt.vz *= factor
                        pkt.fuel_dv -= 10.0

            if not data.get("landed", False):
                gx, gy, gz = self.calculate_gravity(pkt.x, pkt.y, pkt.z)
                pkt.vx += gx * time_step; pkt.vy += gy * time_step; pkt.vz += gz * time_step
                pkt.x += pkt.vx * time_step; pkt.y += pkt.vy * time_step; pkt.z += pkt.vz * time_step

                current_radius = math.sqrt(pkt.x**2 + pkt.y**2 + pkt.z**2)
                
                # Detekce pádu na povrch
                if current_radius <= self.engine.R_EQ:
                    data["landed"] = True
                    self.crashed_ships.add(hex_code) # TRVALÝ ZÁPIS DO ČERNÉ LISTINY (Brání spamu)
                    
                    if data.get("autopilot"): self.toggle_ai_autopilot()
                    
                    # Záznam pro LLM Analýzu
                    current_sector = self.get_sector(pkt.x, pkt.y)
                    self.incident_logs.append({
                        "callsign": pkt.callsign,
                        "fuel": pkt.fuel_dv,
                        "sector": current_sector
                    })
                    
                    pkt.vx, pkt.vy, pkt.vz = 0, 0, 0
                    scale = self.engine.R_EQ / current_radius
                    pkt.x *= scale; pkt.y *= scale; pkt.z *= scale
                    self.log_msg(f"⚠ CRITICAL: {pkt.callsign} IMPACT DETECTED. Log stored.", "#ff3333")

            self.engine.process_adsb_packet(pkt)
            self.history_paths[hex_code].append([pkt.x, pkt.y, pkt.z])
            positions.append([pkt.x, pkt.y, pkt.z])
            
            base_color = (255, 150, 0, 255) if "CRG" in pkt.callsign else (0, 150, 255, 255)
            if data.get("autopilot", False): base_color = (0, 255, 100, 255)
            if data.get("landed", False): base_color = (100, 100, 100, 255)
            colors.append([c/255.0 for c in base_color])

            hist_pts = np.array(self.history_paths[hex_code])
            if len(hist_pts) > 1:
                if hex_code not in self.history_lines:
                    line = gl.GLLinePlotItem(color=[c/255.0 for c in base_color], width=2.0, antialias=True)
                    self.view.addItem(line)
                    self.history_lines[hex_code] = line
                self.history_lines[hex_code].setData(pos=hist_pts, color=[c/255.0 for c in base_color])

            if data.get("landed", False):
                if hex_code in self.prediction_lines: self.prediction_lines[hex_code].setData(pos=np.empty((0,3)))
                if hex_code in self.prediction_10m_markers: self.prediction_10m_markers[hex_code].setData(pos=np.array([0,0,0]), text="", color=QColor(0,0,0,0))
            else:
                pred_pts = []
                px, py, pz = pkt.x, pkt.y, pkt.z
                pvx, pvy, pvz = pkt.vx, pkt.vy, pkt.vz
                p10_pos = None 
                for step in range(180):
                    pred_pts.append([px, py, pz])
                    if step == 30: p10_pos = [px, py, pz]
                    gx, gy, gz = self.calculate_gravity(px, py, pz)
                    pvx += gx * 20.0; pvy += gy * 20.0; pvz += gz * 20.0
                    px += pvx * 20.0; py += pvy * 20.0; pz += pvz * 20.0
                    if math.sqrt(px**2 + py**2 + pz**2) <= self.engine.R_EQ: break 
                
                if hex_code not in self.prediction_lines:
                    pred_line = gl.GLLinePlotItem(color=(1.0, 1.0, 1.0, 0.4), width=1.0, mode='line_strip')
                    self.view.addItem(pred_line)
                    self.prediction_lines[hex_code] = pred_line
                self.prediction_lines[hex_code].setData(pos=np.array(pred_pts))
                
                if p10_pos:
                    c_qt_marker = QColor(255, 255, 255, 200)
                    if hex_code not in self.prediction_10m_markers:
                        marker = gl.GLTextItem(pos=np.array(p10_pos), text="X (10m)", font=QFont("Consolas", 10), color=c_qt_marker)
                        self.view.addItem(marker)
                        self.prediction_10m_markers[hex_code] = marker
                    self.prediction_10m_markers[hex_code].setData(pos=np.array(p10_pos), text="X (10m)", color=c_qt_marker)

            speed = int(math.sqrt(pkt.vx**2 + pkt.vy**2 + pkt.vz**2))
            ai_flag = "[AI]" if data.get("autopilot", False) else ""
            alt_text = "LANDED" if data.get("landed", False) else f"FL{int(data['current_lfl'])}"
            label_text = f"[{pkt.callsign}] {ai_flag}\nALT:{alt_text} | {speed} m/s\nFUEL:{int(pkt.fuel_dv)} DV"
            
            c_qt_label = QColor(*base_color)
            if hex_code not in self.ship_labels:
                label = gl.GLTextItem(pos=np.array([pkt.x, pkt.y, pkt.z]), text=label_text, font=QFont("Consolas", 10, QFont.Weight.Bold), color=c_qt_label)
                self.view.addItem(label)
                self.ship_labels[hex_code] = label
            offset_z = pkt.z + 100000 if not data.get("landed", False) else pkt.z + 20000
            self.ship_labels[hex_code].setData(pos=np.array([pkt.x + 50000, pkt.y, offset_z]), text=label_text, color=c_qt_label)

        if positions:
            self.scatter.setData(pos=np.array(positions), color=np.array(colors))
        
        if self.ui_callsign.text() != "AWAITING SELECTION...":
            for target_data in self.engine.tracked_targets.values():
                if target_data["packet"].callsign == self.ui_callsign.text():
                    pkt = target_data["packet"]
                    total_vel = math.sqrt(pkt.vx**2 + pkt.vy**2 + pkt.vz**2)
                    self.ui_fuel.setText(f"{max(0, int(pkt.fuel_dv))} m/s")
                    if target_data.get("landed", False):
                        self.ui_alt.setText("SURFACE (LANDED)")
                        self.ui_vel.setText("0.0 m/s")
                    else:
                        self.ui_alt.setText(f"LFL {target_data['current_lfl']}")
                        self.ui_vel.setText(f"{round(total_vel, 1)} m/s")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    radar = LunarRadar3D()
    radar.showMaximized()
    QTimer.singleShot(1000, radar.start_loading)
    sys.exit(app.exec())