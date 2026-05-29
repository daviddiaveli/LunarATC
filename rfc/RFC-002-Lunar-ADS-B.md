# RFC-002: Lunar-ADS-B State Vector Protocol

**Status:** Draft  
**Author:** David Pěkník  
**Date:** May 2026  
**Category:** Data Link Specification  

## 1. Abstract
This document defines the Lunar Automatic Dependent Surveillance-Broadcast (L-ADS-B) protocol. It specifies the telemetry payload required for autonomous traffic deconfliction in the lunar vacuum, replacing terrestrial transponder architectures.

## 2. The Vacuum Trajectory Problem
Terrestrial ADS-B transmits 3D position and velocity, assuming aerodynamic stability and continuous maneuverability. In the lunar vacuum, course alterations require propellant ignition (Delta-V). A spacecraft's trajectory is strictly deterministic unless a burn occurs. 

Therefore, broadcasting only current position and velocity is insufficient for collision avoidance algorithms. The L-ADS-B protocol mandates the inclusion of maneuvering intent to enable precise 4D trajectory prediction.

## 3. L-ADS-B Packet Structure
To ensure high-integrity tracking, the standard L-ADS-B broadcast packet consists of three primary data blocks.

### 3.1. Identification & Timing Block
* **L-HEX Code:** A unique 24-bit hexadecimal spacecraft identifier.
* **Mission Callsign:** Alphanumeric identifier (maximum 8 characters).
* **Atomic Timestamp:** Precise transmission time using Lunar Coordinate Time (LCT) to account for signal propagation delay and relativistic effects.

### 3.2. Kinematic State Vector Block
Position is derived geometrically from the Lunar Reference Ellipsoid (LRE) as defined in RFC-001.
* **X, Y, Z Coordinates:** 3D spatial position relative to the lunar center of mass.
* **Vx, Vy, Vz Velocity:** The current 3D velocity vector (expressed in meters per second).
* **Current LFL:** Lunar Flight Level, representing the immediate geometric altitude above the LRE.

### 3.3. Intent & Delta-V Block (The Core of L-ATC)
To allow the central L-ATC engine to forecast potential conflicts, spacecraft MUST broadcast upcoming orbital maneuvers.
* **T-Burn (Time of Ignition):** The exact planned timestamp of the next engine ignition.
* **Delta-V Vector:** The planned change in velocity in 3D space.
* **Burn Duration:** The expected length of the maneuver in seconds.