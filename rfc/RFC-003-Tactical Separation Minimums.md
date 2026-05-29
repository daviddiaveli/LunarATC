# RFC-003: Tactical Separation Minimums and Conflict Alerting

**Status:** Draft  
**Author:** David Pěkník  
**Date:** May 2026  
**Category:** Safety Specification  

## 1. Abstract
This document defines the minimum allowable spatial separation between spacecraft operating within the Lunar Air Traffic Control (L-ATC) jurisdiction. It establishes the Lunar Separation Volume (LSV) and the deterministic Short-Term Conflict Alert (STCA) time thresholds necessary for vacuum collision avoidance.

## 2. The Velocity-Gravity Paradigm
Terrestrial separation standards (e.g., 5 NM horizontal, 1000 ft vertical) rely on atmospheric braking and relatively low closure rates. Lunar orbital velocity at low altitudes is approximately 1.6 km/s. Two counter-orbiting spacecraft have a closure rate exceeding 3.2 km/s. 

Furthermore, the 1/6th Earth gravity significantly alters the Delta-V (propellant) requirements for evasive maneuvers. Static, distance-based rules are insufficient; separation must be managed as a dynamic 4D spatio-temporal volume.

## 3. Lunar Separation Volume (LSV)
Every spacecraft broadcasting L-ADS-B telemetry (as per RFC-002) is computationally enclosed in a dynamic safety bubble known as the LSV. If the LSV of two spacecraft intersect, a separation loss occurs.

* **Radial Buffer (Vertical):** Minimum 2.5 kilometers from the center of mass.
* **Along-Track Buffer (Forward):** Minimum 15 kilometers in the direction of the velocity vector.
* **Cross-Track Buffer (Lateral):** Minimum 5 kilometers perpendicular to the trajectory.

## 4. Trajectory Prediction and STCA
The L-ATC central engine continuously extrapolates the 4D state vectors and Delta-V intent.

* **Detection Horizon:** The system MUST project trajectories a minimum of 600 seconds (10 minutes) into the future based on pure astrodynamics.
* **Conflict Alert Threshold:** If a predicted intersection of two LSVs is detected within a 300-second (5-minute) horizon, the system MUST autonomously issue a Delta-V evasion vector to the lower-priority spacecraft.