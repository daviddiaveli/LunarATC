# 🌑 LunarATC — The Operating System for Lunar Airspace

A next-generation Air Traffic Control (ATC) and Tactical Deconfliction framework engineered for the unique challenges of lunar orbital and suborbital operations.

---

### 🌍 The Core Problem: Why a New System?

In terrestrial aviation, aircraft maintain separation using barometric altimeters based on sea-level atmospheric pressure. This creates stable, shared flight levels. **The Moon has no atmosphere and no sea level.**

Furthermore, the lunar surface is highly irregular, punctuated by deep craters (e.g., Tycho) and massive mountain ranges. A radar altimeter pointing straight down would show wild, erratic altitude jumps even if the spacecraft were flying in a perfectly straight line, making standard separation impossible.

**The LunarATC Solution:**
LunarATC discards aerodynamic tracking in favor of pure astrodynamics. It introduces the **Lunar Reference Ellipsoid (LRE)** — a mathematically perfect virtual sphere. All spacecraft calculate their altitude (Lunar Flight Levels - LFL) purely geometrically against this invisible sphere. This ensures a stable, predictable, and universally shared 3D airspace grid in a vacuum.

---

### ⚙️ System Architecture & Features

LunarATC is a comprehensive suite featuring a fully realized 6-DOF (Degrees of Freedom) kinematic physics engine, real-time GUI radar, and an autonomous AI integration layer.

#### 1. The Core Physics Engine (`/core/engine.py`)
*   **True Orbital Mechanics:** Replaces linear movement with numerical integration of lunar gravity ($\mu = 4.904 \times 10^{12} \text{ m}^3/\text{s}^2$). Objects automatically maintain stable orbits ($v = \sqrt{\mu / r}$) or follow parabolic escape trajectories.
*   **6-DOF Kinematics:** Tracks not just X/Y/Z, but Pitch, Yaw, Roll, and their angular velocities.
*   **Flight Assist (Hover Mode):** Supports low-speed inspection drones or landing craft by calculating constant anti-gravity thrust vectors.
*   **STCA (Short-Term Conflict Alert):** Predicts 4D trajectories 10 minutes into the future to identify intersecting paths and automatically calculates evasive Delta-V maneuvers.

#### 2. Tactical Operations GUI (`gui_3d.py`)
A PyQt6/OpenGL high-performance tactical interface inspired by military airspace management.
*   **Orbital Zonations:** Visualizes Low Lunar Orbit (LLO), Medium Lunar Orbit (MLO), and the massive Sphere of Influence (SOI) boundary.
*   **Sensor Network:** Displays surface infrastructure including Radars, Optical Arrays, and Far-Side Radiotelescopes.
*   **Restricted Airspace:** Real-time monitoring of no-fly zones (e.g., Apollo 11 Heritage Site, Tycho Military Sector) with automated security alerts.
*   **Interactive Vectoring:** Controllers can manually input specific $\Delta V$ burns or transmit new Yaw/Pitch heading vectors to spacecraft, complete with simulated "Pilot Override" rejection probabilities.

#### 3. LLM Discovery Engine & AI Autopilot
*   **System Diagnostics:** Integrates a simulated LLM uplink that analyzes black-box crash data (fuel depletion, dark-side LOS dropouts) and generates high-level engineering recommendations.
*   **Neural Autopilot:** Hook for Reinforcement Learning (PPO) agents to take control of spacecraft and autonomously manage orbital transfers.

---

### 📚 RFC Documentation Library

The operational rules of LunarATC are codified in formal engineering specifications located in the `/rfc` directory:

1. **[RFC-001: Reference Frame & Geometric Altimetry](rfc/RFC-001-Reference-Frame.md)** — The mathematical baseline for vertical separation without atmospheric pressure.
2. **[RFC-002: Lunar-ADS-B State Vector Protocol](rfc/RFC-002-Lunar-ADS-B.md)** — The data packet format for autonomous broadcast telemetry in a vacuum.
3. **[RFC-003: Tactical Separation Minimums](rfc/RFC-003-Tactical%20Separation%20Minimums.md)** — Safety buffers and STCA calculation logic for high-velocity crossing trajectories.
4. **[RFC-004: Terminal Area Management](rfc/RFC-004-Terminal-Area-Management.md)** — Automated Descent Corridors (ADC) and priority routing near lunar bases.
5. **[RFC-005: Flight Operations & Restricted Airspace](rfc/RFC-005-Flight-Operations.md)** — 6-DOF tracking, ATC vectoring commands, Flight Assist protocols, and military/heritage no-fly zones.

---

### 🚀 Running the Simulation

**1. Launch the 3D Tactical Radar (Full Experience):**
```bash
python gui_3d.py
```
*Requires `PyQt6`, `pyqtgraph`, `numpy`, and `Pillow`. Use the mouse to rotate the Moon, and click on vessels or prediction lines to open the Tactical Command Center panel.*

**2. Run Headless Simulation (Terminal Only):**
```bash
python simulation.py
```
*Observe the STCA engine autonomously predicting and resolving conflicts in real-time.*