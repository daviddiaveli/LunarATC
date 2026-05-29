# RFC-001: Lunar Reference Frame and Geometric Altimetry

**Status:** Draft  
**Author:** David Pěkník  
**Date:** May 2026  
**Category:** Core Specification  

## 1. Abstract
This Request for Comments (RFC) establishes the foundational framework for vertical separation within the Lunar Air Traffic Control (L-ATC) protocol. It deprecates terrestrial barometric altimetry and introduces a standardized Geometric Altimetry system based on the Lunar Reference Ellipsoid (LRE).

## 2. The Atmospheric Dependency Problem
Terrestrial Air Traffic Control relies on the International Standard Atmosphere (ISA) and barometric pressure (QNH / 1013.25 hPa) to define Flight Levels (FL). Aircraft calculate their vertical separation by measuring the weight of the air column above them. 

The Moon lacks an atmosphere. Furthermore, utilizing radar/LiDAR to measure distance directly to the surface (Above Ground Level - AGL) is inherently flawed for en-route traffic. The lunar crust features extreme topological variance (craters and peaks exceeding 8,000 meters in differential). An AGL-based altitude tracking system would cause rapid, unpredictable oscillations in telemetry, rendering algorithmic collision prediction impossible.

## 3. The Lunar Reference Ellipsoid (LRE)
To establish a stable "Altitude Zero", the L-ATC protocol mandates the use of a fixed mathematical volumetric model: the Lunar Reference Ellipsoid.

All en-route altitudes MUST be calculated as a positive, geometric radial distance from the LRE boundary, independent of the actual terrain topology below the spacecraft.

### 3.1. Fundamental Constants
For the purpose of tactical separation, the LRE uses the Mean Earth/Polar Axis (ME) system with the following baseline parameters:
* **Equatorial Radius (R_eq):** 1737.4 km
* **Polar Radius (R_pol):** 1736.0 km
* **Reference System:** Selenocentric coordinates (origin at the center of lunar mass).

## 4. Altitude Definitions

### 4.1. Lunar Flight Levels (LFL)
The primary unit for vertical separation is the Lunar Flight Level (LFL). It is defined as a fixed geometric offset from the LRE. 
* **Rule:** A spacecraft reporting "LFL 50" is flying exactly 50 km geometrically above the LRE surface.
* **Usage:** Mandatory for all suborbital transit and orbital phases.

### 4.2. Terminal Altimetry (AGL)
Above Ground Level (AGL) is the real-time distance between the spacecraft and the physical lunar crust.
* **Rule:** AGL data is collected via active sensors (radar, LiDAR, or optical flow).
* **Usage:** Strictly restricted to Terminal Maneuvering Areas (TMA) - specifically descent, landing, hover, and immediate ascent phases. It MUST NOT be used for en-route traffic deconfliction.