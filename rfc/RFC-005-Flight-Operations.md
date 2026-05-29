# RFC-005: Flight Dynamics, Vectoring, and Restricted Airspace Operations

**Status:** Draft  
**Author:** David Pěkník  
**Date:** May 2026  
**Category:** Operational Specification  

## 1. Abstract
This document defines advanced flight operations within the Lunar Air Traffic Control (L-ATC) system. It specifies the 6 Degrees of Freedom (6-DOF) kinematic requirements, tactical vectoring protocols, the implementation of Flight Assist (Anti-Gravity) systems for low-velocity maneuvers, and the governance of Restricted Airspace Zones.

## 2. 6-DOF Kinematics and Orientation
Traditional 3D positioning (x, y, z) is insufficient for vacuum operations where thrust vectoring determines future trajectory.
All vessels MUST broadcast their orientation and angular velocities via the Lunar-ADS-B protocol:
*   **Pitch, Yaw, Roll (Degrees):** Absolute orientation relative to the Lunar Reference Ellipsoid (LRE).
*   **Angular Velocities (Deg/s):** The rate of rotation along each axis.

ATC separation engines MUST project the 4D trajectory using both the translational velocity vector and the vessel's current rotational alignment prior to any scheduled engine burns.

## 3. Flight Assist (Anti-Gravity/Hover Protocol)
High-velocity orbital mechanics dictate that objects below orbital velocity ($v < \sqrt{\mu / r}$) will impact the surface.
*   **Definition:** "Flight Assist" is an operational mode where a vessel's Reaction Control System (RCS) or main thrusters continuously output a vertical delta-V that exactly cancels local lunar gravitational acceleration.
*   **Usage:** Authorized strictly for Terminal Maneuvering Areas (TMA), surface inspection drones, and landing operations.
*   **Telemetry:** Vessels operating in this mode MUST flag `flight_assist=True` in their ADS-B packets. ATC algorithms will subsequently project their trajectory without gravitational decay.

## 4. Tactical Vectoring
ATC controllers are authorized to issue direct Vectoring Commands to deconflict airspace or guide inbound traffic.
*   **Execution:** A vector command consists of a target Pitch and Yaw. The vessel's automated systems MUST smoothly align the craft to the requested vector.
*   **Pilot Override:** Human-crewed vessels (Classification: HMD) retain a standard 20% override authority where the commander can reject an ATC vector due to onboard safety constraints. In such events, ATC MUST recalculate separation using the vessel's original trajectory.

## 5. Restricted Airspace Zones
To protect historical sites, military installations, and sensitive scientific arrays, L-ATC defines fixed Restricted Zones.
*   **Parameters:** Defined by a center point (Latitude, Longitude), a horizontal radius, and an altitude limit (e.g., Apollo 11 Heritage Site: 50km radius, up to LFL 15.0).
*   **Enforcement:** Any trajectory prediction intersecting a restricted zone MUST trigger an immediate `SECURITY ALERT`. ATC is authorized to issue mandatory retrograde or vector burns to divert the offending vessel.

## 6. Communication Blackouts (LOS)
Vessels operating on the lunar far side without relay satellite line-of-sight (LOS) will experience communication dropouts.
*   **ATC Handling:** When `comms_active=False` is detected, ATC MUST freeze the vessel's last known trajectory, expand the safety separation minimums by 300%, and gray-out the vessel on tactical displays.
*   **Pilot Responsibility:** During a blackout, the vessel MUST NOT execute unscheduled delta-V burns unless collision is imminent.