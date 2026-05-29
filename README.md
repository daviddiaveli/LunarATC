# 🌑 LunarATC — The Operating System for Lunar Airspace

A next-generation Air Traffic Control framework defining orbital and suborbital separation standards for lunar operations.

---

### 🌍 Proč Měsíc potřebuje nový systém? (Srozumitelně pro každého)

V pozemském letectví se piloti a dispečeři orientují podle tlaku vzduchu. Když letadlo stoupá, tlak klesá, a přístroje díky tomu přesně vědí, v jakém výškovém patře se stroj nachází. Všichni sdílejí stejná pravidla, což zabraňuje kolizím.

**Na Měsíci ale žádný vzduch není. A chybí tam i hladina moře, od které by se dalo měřit „X metrů nad mořem“.**

Měsíční povrch je navíc extrémně rozeklaný, plný hlubokých kráterů a vysokých pohoří. Kdyby měsíční moduly určovaly svou výšku jen pomocí přístrojů namířených dolů na zem, jejich výška by na obrazovkách divoce skákala nahoru a dolů podle toho, nad čím zrovna letí – i kdyby letěly v naprosto dokonalé přímce.

**Řešení LunarATC:**
Tento protokol ruší závislost na atmosféře i povrchu. Zavádí matematicky definovanou, dokonale hladkou virtuální sféru (Měsíční referenční elipsoid), která slouží jako „absolutní nula“. Všechny stroje v našem systému určují svou polohu a výšku čistě geometricky vůči tomuto virtuálnímu středu. Výsledkem je stabilní, bezpečný a předvídatelný systém letových hladin ve vakuu.

---

### ⚙️ Core Technical Vision & RFC Architecture

LunarATC shifts the paradigm of traffic deconfliction from aerodynamic tracking to pure astrodynamics. It is built to handle the chaotic commercial and scientific lunar traffic of the upcoming decades.

#### 🏛️ Structural Blueprint
The framework is strictly decoupled into protocol specifications and execution layers:

* **`/rfc` (Request for Comments):** Formal engineering standards. This is where the core physics, data packet structures, and compliance rules are defined.
* **`/core` (The Deconfliction Engine):** High-integrity Python implementation responsible for 4D trajectory prediction, separation monitoring, and automated clearance generation.
* **`/simulation` (Traffic Generator):** A stochastic environment generating simultaneous lunar ascents, orbital insertions, and suborbital hops to stress-test the protocol.

#### 🛰️ Roadmap & Next Steps
1. **RFC-001: Reference Frame & Geometric Altimetry** — Establishing the mathematical baseline for vertical separation without atmospheric pressure.
2. **RFC-002: Lunar-ADS-B State Vector Protocol** — Defining the data packet format for autonomous broadcast telemetry in vacuum (including delta-V vectors).
3. **RFC-003: Tactical Separation Minimums** — Calculating safety buffers for high-velocity crossing trajectories under 1/6th of Earth's gravity.