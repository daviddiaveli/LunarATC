# RFC-004: Terminal Area Management and Automated Descent Profiles

**Status:** Draft  
**Author:** David Pěkník  
**Date:** May 2026  
**Category:** Operational Specification  

## 1. Abstract
This RFC extends the Lunar Air Traffic Control (L-ATC) protocol to cover the Terminal Maneuvering Area (TMA). It defines the transition from orbital Flight Levels (LFL) to surface-relative landing phases and establishes rules for automated descent corridors.

## 2. Terminal Maneuvering Area (TMA)
The TMA is defined as a hemispherical volume of 50 km radius centered on a registered Lunar Surface Port (e.g., Artemis Base).

### 2.1. Jurisdiction Transition
*   **Inbound:** Spacecraft entering the 50 km radius MUST switch from Selenocentric En-route separation to TMA Tactical control.
*   **Outbound:** Spacecraft exiting the TMA MUST broadcast a state vector confirming stable orbit insertion before resuming LFL separation.

## 3. Automated Descent Corridors (ADC)
To prevent collisions during the high-risk landing phase, L-ATC mandates the use of ADCs.

*   **Vertical Profile:** Descents MUST follow a pre-calculated ballistic trajectory or a powered descent profile approved by the L-ATC engine.
*   **Deconfliction:** Only ONE spacecraft is permitted to occupy an ADC at any given time.
*   **Priority:** Manned missions (HMD) have absolute priority over cargo (CRG) and probes (PRB).

## 4. Emergency Abort Procedures
If a separation loss is predicted during descent:
1.  **Engine Override:** The L-ATC engine issues a "MANDATORY ASCENT" command.
2.  **Vector:** The spacecraft MUST immediately execute a prograde burn to reach a safe parking orbit (LFL 50 minimum).
3.  **Telemetry:** ADS-B packets MUST be set to "EMERGENCY" status, increasing broadcast frequency to 5 Hz.
