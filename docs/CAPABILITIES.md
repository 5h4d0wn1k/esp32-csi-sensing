# Capabilities assessment (honest, v1.0)

This document takes stock of what Wi-Fi CSI (Channel State Information) sensing
can realistically achieve in cybersecurity and surveillance contexts. It keeps
three layers strictly separated: **what this build demonstrably does today**
(measured, see `PLACEMENT.md`), **what the research field has shown** (published,
peer-reviewed), and **what is speculation or roadmap**. Companions: `README.md`
(build), `PLACEMENT.md` (physics/placement), `VISUALIZATION.md` (tooling).

## 1. Executive summary

The system is a two-board ESP32 CSI pipeline: a receiver (NodeMCU) captures
~74–100 CSI frames/s at 64 subcarriers (HT20 LLTF) from a consumer Wi-Fi AP
illuminating the whole room, plus an optional ESP32-C6 sender for ESP-NOW
beacons. A host-side detector computes gain-normalized amplitude deviation per
subcarrier, rejects receiver AGC transients, and decides motion on the p95 tail
of a rolling variance against a quiet-room calibration threshold. Demonstrably,
today:

- **Room-scale motion detection** through a commodity router as illuminator,
  at several meters, no camera, no microphone, no transmitter cooperation
  beyond it being on-channel: walking detected 99–100%, hand-wave 92%, static
  room 0% false ACTIVE, stand-in-beam 83% (presence).
- **Multi-transmitter awareness**: every frame is tagged with its source MAC,
  so the receiver senses the router, the ESP-NOW sender, and any other emitter
  on the channel simultaneously.
- **Robustness engineering that survives real hardware**: AGC gain steps
  (which correlate 0.87 with the naive motion metric) are rejected by
  RSSI-jump flagging; ambient drift is mitigated by a Recalibrate control.

What it does not do: identify people, track trajectories, see through multiple
walls, survive channel changes without recalibration, or replace a camera
(Section 5 enumerates the envelope honestly).

Why this matters for security: the same physics means **any 2.4 GHz transmitter
already illuminating a space is a potential motion-sensing opportunity** — for
defenders building covert-presence alarms for air-gapped rooms, and for attackers
who want occupancy intelligence without deploying anything that looks like a
sensor.

## 2. How it works in one page

Physics to decision, in five steps; full detail and hard numbers live in
`PLACEMENT.md`.

1. **Illumination.** A transmitter on the channel (here: the AP,
   ch6, RSSI ≈ −56 dBm at the receiver) floods the room with multipath; the
   receiver measures the combined channel once per frame.
2. **Perturbation.** A human body occludes part of the propagation paths and
   re-radiates. The measurable condition is that the body blocks a meaningful
   fraction of the **first Fresnel zone** of some link. This single geometric
   fact explains every placement result we have: a 1–2 m desk link fails
   (direct path dominates; per-subcarrier mean dev 0.083 walk vs 0.086 static —
   zero separation), a ≥5 m corridor link works, and a router lighting the whole
   room works at several meters.

3. **Measurement.** Each frame carries per-subcarrier amplitude and phase plus
   RSSI; we use gain-normalized amplitude deviation per subcarrier (phase on
   the ESP32 is contaminated by CFO/SFO and currently unused).

4. **Cleaning.** The receiver's AGC gain steps produce >2 dB per-frame RSSI
   jumps that look exactly like body motion in the shape metric
   (corr(dev, rssi) ≈ 0.87). Flagged frames (>2 dB jump, judged with a 3-frame
   commit delay) are excluded from the variance history entirely; without this
   step the detector is unusable on real hardware.

5. **Decision.** A 1.5 s rolling standard deviation (min 8 good frames) forms
   the instantaneous level; the decision level is the **p95 tail over the last
   ~6 s** — sporadic body signal lives in the tail, a stable static floor stays
   far below. Threshold = p90 of a 5 s quiet-room calibration × 1.5. Hysteresis:
   ACTIVE after 1.0 s above, INACTIVE after 3.0 s below. Measured operating point:
   threshold 0.0204, static floor ~0.01, motion 0.03–0.09.

Step 2 bounds everything in this document: **sensing happens where bodies
intersect Fresnel zones**, not where software wishes it did.

## 3. Demonstrated capabilities of this build

| Capability | Status | Measured performance |
|---|---|---|
| Room-scale motion detection (router illumination) | Working, validated | Walking 99–100%, hand-wave 92%, static 0% false ACTIVE |
| Presence detection (standing still in beam) | Working, validated | 83% stand-in-beam; legitimately reads ACTIVE — presence, not just motion |
| Direct two-node ESP-NOW sensing @ 1–2 m | Does not work | Mean dev 0.083 (walk) vs 0.086 (static) — zero separation; direct path dominates |
| Direct two-node ESP-NOW sensing ≥5 m (corridor/doorway) | Working | Body occupies real fraction of path; −60…−70 dBm link |
| Multi-transmitter CSI tagging | Working | Per-frame source-MAC tag; router + ESP-NOW sender sensed concurrently |
| AGC-transient rejection | Working, v5.5 | >2 dB RSSI-jump flagging, 3-frame commit delay; fixes corr(dev, rssi) ≈ 0.87 artifact |
| Quiet-room auto-calibration + Recalibrate | Working | 5 s calibration; threshold = cal p90 × 1.5; manual re-baseline on ambient drift |
| Live 3D viewer + offline replay | Working | Browser viewer over WebSocket bridge; CSV replay for captures |
| Frame throughput | Measured | ~74–100 frames/s router mode, ~69/s ESP-NOW @ ch6 |

Not demonstrated (and not claimed): everything in Section 5.

## 4. Application domains

For each domain: what the field has shown, what this build could do with modest engineering, and an honest maturity rating.

### 4.1 Physical security and intrusion detection

**Field.** Device-free intrusion detection is the oldest result in this area:
Youssef et al. framed it in 2007, radio tomographic imaging (Wilson & Patwari,
2010) turned mesh networks into fence-line motion sensors, and commercial
products now sell Wi-Fi motion detection for homes. Binary indoor
motion/presence is solved technology.

**This build.** The core alarm primitive already works: motion in an illuminated
room latches ACTIVE within ~1 s and clears ~3 s after stillness. Straightforward
host-side extensions: timestamped event logs, alert pushes, armed/disarmed
windows, alarm-panel integration; the sensor node is a $10 board with no lens
to cover and no obvious sensor signature. CSI events also carry timestamps and
rough signal character (variance magnitude, duration), so they **verify other
alarms**: a glass-break audio trigger with no CSI motion smells like a false
alarm; CSI motion with no camera coverage tells you where to look.

**Limits.** Needs quiet-room calibration; ambient drift raises the floor
mid-session (Recalibrate mitigates; automating that is roadmap); single receiver
gives no location, only "something moved"; pet immunity is **untested here** and a known hard problem in the field.

**Maturity:** high for binary motion; low for anything finer.

### 4.2 Covert surveillance and espionage

**Field.** Through-wall RF motion sensing is decades old (radar) and
well-established with Wi-Fi-class hardware in the lab (Wi-Vi, WiTrack). The
espionage-relevant facts are structural, not exotic: the sensing device looks
like a plain IoT gadget (no lens, no microphone, no thermal signature; its
antenna is indistinguishable from any smart plug's); it needs no victim
cooperation or pairing — it rides whatever 2.4 GHz traffic already exists or
brings its own beaconing transmitter; and through-wall sensing works when
illuminator and receiver bracket the space of interest.

**Realistic limits, stated plainly.**

- **Walls attenuate 2.4 GHz.** Each interior drywall/plaster wall costs real
  dB; concrete, brick, metalized insulation cost much more. Practical
  through-wall range is *adjacent room with a strong illuminator*, not
  building-wide — anyone claiming whole-building coverage from one node is
  selling something.
- **Same-channel requirement.** The receiver senses only transmitters whose
  frames reach it on its channel: use the target's own AP (ideal — nothing new
  to detect) or deploy an illuminator, which reintroduces a detectable emitter
  (see 4.9).
- **Calibration fragility is operational brittleness.** The detector needs a
  quiet-room baseline and degrades when the environment shifts; a covert
  deployment surviving days without recalibration is nontrivial.
- **No imagery, no identity.** Output is "something moved in the beam".
  Intelligence value comes from *timing* (when is the room empty), not pictures.

**This build.** Demonstrates the core primitive (room-scale motion via an
existing AP). A red-team deployment would add persistent logging, alerting on
occupancy during scheduled-empty windows, and remote retrieval — none exists yet.

**Maturity:** motion/presence — demonstrated; anything richer — lab-grade.
### 4.3 Presence and occupancy analytics

**Field.** Occupancy-driven HVAC, meeting-room booking truth, retail footfall,
hot-desk analytics: large commercial pull, and a main reason 802.11bf exists
(Section 6). Chipset vendors and startups have shipped or demoed exactly this.

**This build.** Single-room binary occupancy plus a motion-intensity signal is
achievable today by logging detector output. Footfall *counting* through a
doorway is plausibly reachable (doorway geometry concentrates the Fresnel-zone
crossing) but is **not implemented** and would need direction logic.

**Privacy implications — worth spelling out.**

- Device-free sensing observes people who never opted in and usually cannot
  know it is happening: no badge swipe, no app, no consent dialog.
- No images are recorded, but sustained occupancy traces are behavioral data:
  schedules, habits, absence patterns — arguably personal data under GDPR-style
  regimes once linked to individuals or used to profile them.
- Aggregation across rooms/time reconstructs lives: a building-wide occupancy
  grid sampled continuously is a surveillance system even with zero cameras.

**Maturity:** presence — high; counts/analytics — medium; governance — lagging
everywhere.

### 4.4 Health and safety monitoring

**Field.** The strongest published results and clearest social value:

- **Fall detection**: contactless fall detection with commodity Wi-Fi is
  well-published (e.g., RT-Fall, IEEE TMC 2017) and is the flagship elder-care
  use case — bathrooms and bedrooms where cameras are unacceptable.
- **Breathing/vitals while still**: WiTrack (CHI 2015) demonstrated breathing
  and heart-rate extraction through walls with RF; commercial RF sleep trackers
  exist — Google Nest Hub's Soli radar does contactless sleep/breathing sensing
  (60 GHz radar, not Wi-Fi, but proof of consumer demand), and Origin Wireless
  sells Wi-Fi-based sleep analytics. Sleep staging: research-grade; early
  commercial via radar.

**This build.** Breathing-rate estimation while a person sits still in the beam
is the roadmap item (0.15–0.5 Hz band). Plausibility: chest displacement of
millimeters to centimeters modulates subcarrier phase/amplitude at breathing
frequency, and 74–100 frames/s comfortably oversamples 0.15–0.5 Hz. Honest
caveats: our metric is amplitude *deviation variance*, not a narrowband spectral
estimator; breathing extraction likely wants a phase-coherent or bandpass
metric, and the AGC artifacts we reject are exactly the slow gain wobble that
pollutes a 0.2 Hz band. Right next experiment; might fail.

**Maturity:** falls — medium (research mature, early commercial); breathing —
lab-grade to early-commercial via radar; this build — not yet attempted.

### 4.5 Search and rescue

**Field.** Detecting survivors under rubble via respiration is an established
through-wall-radar application; dedicated UWB life-detector radars are deployed
by professional SAR teams. The Wi-Fi lineage (Wi-Vi, WiTrack) cites this
motivation explicitly.

**Reality check for Wi-Fi CSI.** Range resolution scales with bandwidth. Our
20 MHz HT20 channel gives time resolution on the order of tens of nanoseconds —
tens of meters of range bin, useless for localizing a chest under rubble; radar
systems use hundreds of MHz to GHz. Wi-Fi CSI contributions here are indirect:
cheap dense motion sensors for staging areas, or techniques that migrate into
purpose-built radar. **This build contributes nothing here** — a single 20 MHz
link cannot penetrate rubble meaningfully and cannot range.

**Maturity:** dedicated UWB radar — deployed; Wi-Fi CSI — research only.

### 4.6 Border and perimeter monitoring

**Field.** Radio tomographic imaging (Wilson & Patwari, 2010) is canonical: a
mesh of cheap nodes along a fence line detects and roughly locates anyone
crossing the sensed volume, no cameras, no per-node intelligence. Long thin
deployments suit the physics — every crossing cuts many links.

**This build.** A chain of receivers spaced ≥5 m (our measured minimum for
direct-link sensing) along a perimeter, each watching shared illuminators,
would form segment tripwires. Requires the multi-receiver fusion roadmap item
(Section 8); the hub architecture (source registry, MAC-tagged frames)
anticipates it but implements no fusion.

**Unsolved here.** Outdoor noise (wind-blown foliage, rain, animals) raises the
variance floor exactly like ambient indoor drift, and we have zero outdoor
measurements; keeping a stable baseline outdoors is genuine research-grade
statistics.

**Maturity:** research/demonstration; commercial RTI-adjacent systems exist in
niches.

### 4.7 Cybersecurity — defensive applications

- **RF environment awareness.** The receiver already tags every frame's source
  MAC, doubling as a passive inventory of emitters on the channel; a persistent
  floor shift hints something new is transmitting. (Rogue-AP detection itself
  belongs to a proper WIDS.)
- **Tamper/decoy detection for air-gapped rooms.** The motivating scenario for
  this repo: a sensor disguised as an ordinary IoT gadget watches a server room
  or SCIF that should be empty. Motion during protected hours — before anyone
  touches the safe, console, or cabling — alerts and correlates cleanly with
  access-control logs; badge logs showing nobody entered while CSI saw motion
  is either a sensor fault or a problem worth investigating.
- **Insider-threat tripwires.** After-hours motion in restricted zones, motion
  in spaces a role never requires entering, dwell near sensitive assets — all
  timestamped-event logic atop the existing detector.
- **Physical-access evidence correlated with logs.** Exfiltration
  investigations hinge on "was anyone physically at this machine?" A CSI motion
  timeline is independent evidence that survives host compromise — an attacker
  who wipes audit logs cannot wipe the RF record.

Buildable from this codebase with modest work: persistent logging, alert rules, retention. The detector itself is done.

### 4.8 Cybersecurity — offensive / red-team applications

- **Pre-entry presence detection.** Know whether a target room is occupied
  before physical intrusion, from an adjacent space, using the target's own AP
  as illuminator — this build demonstrates the primitive; packaging (persistent
  node, remote readout) is straightforward engineering.
- **Occupancy pattern mapping.** A week-long deployment yields patrol schedules,
  cleaner visits, empty-window histograms — high-value operational intelligence
  for planning physical operations. Timing intelligence is exactly what a binary
  motion sensor produces well.
- **Keystroke and acoustic side channels.** Published research shows
  fine-grained CSI can leak typed input and aspects of speech: WiKey (MobiCom
  2015) infers keystrokes; WindTalker (AsiaCCS 2016) attacks PIN entry;
  WiHear-era work (MobiCom 2014) reconstructed speech characteristics.
  **These are lab-grade results**: near-line-of-sight distances, training data
  from the victim's own keyboard, controlled conditions — they do not transfer
  to field use against an unaware target, and this build implements none of
  them. The honest answer to red teams: "demonstrated in papers, not practical
  here."
- **What this build actually offers an operator** is the boring version: occupied/empty, with timestamps, from hardware that looks like a smart plug.

### 4.9 Counter-surveillance: detecting and defeating RF motion sensing

Defense is genuinely easy against this class of system because calibration is
fragile by design. Everything below is legal almost everywhere; jamming is not
(last bullet).

**Forensic indicators of a CSI sensor on your network/channel:**

- A client that stays associated but generates suspiciously regular unicast
  traffic — our self-ping scheme produces a steady ~74–100 frames/s cadence
  that stands out in any controller export.
- Unknown ESP32-class OUIs among associated clients or observed MACs.
- ESP-NOW beacons on your channel (raw 802.11 vendor frames, no association);
  in captures, constant frame rate and fixed sizes to a single client.

**Defeat mechanisms (all legal):**

- **Move/reposition the AP.** Propagation geometry defines the Fresnel zones;
  relocating the illuminator invalidates the calibration baseline and can move
  the sensed volume entirely.
- **Channel hopping.** Scheduled AP channel changes force reassociation and
  recalibration; a covert receiver tuned to one channel loses coverage each hop.
- **MAC randomization hygiene** on your own devices starves promiscuous-mode
  receivers of stable per-source baselines (less relevant against our
  associated-client mode, relevant against sniffer variants).
- **RF shielding.** Faraday paint/mesh, metal racks, existing metal mass
  attenuate the illuminator toward unusability; shielding one room costs less
  than the sensor it defeats.- **Ambient noise as camouflage.** Ironically, a busy room defeats the
  detector: ambient instability raises the variance floor (~0.05 measured) and
  masks body signal; crowd motion partially self-masks.
- **Jamming: don't.** Deliberate interference is illegal in most jurisdictions
  regardless of intent, and unnecessary — everything above works better.

General lesson: statistical-baseline sensors trade sensitivity for calibration stability — any defender who knows a CSI sensor *might* exist can make its life miserable with routine, legitimate network changes.

## 5. Honest capability envelope of THIS build

What it will not do, with reasons:

- **Identify people.** Output is one scalar statistic per instant. Gait-based
  person ID exists in the literature but needs ML over rich features and
  labeled data; nothing here supports it.
- **Track trajectories.** One receiver, one link, no ranging (20 MHz gives no
  usable time resolution). Localization needs many links (RTI arrays) or
  multiple coordinated receivers.
- **See through multiple walls.** Attenuation plus multipath washout; adjacent
  room with a strong illuminator is the realistic ceiling.
- **Work across channels or after topology changes.** Calibration binds to
  channel, geometry, furniture — change any and you recalibrate. Inherent to
  baseline-statistical detectors.
- **Count people reliably.** One body vs three barely differ in a scalar
  variance tail; crowd motion partially masks itself (floor rises).
- **Replace cameras.** No visual evidence, no identity, no forensics-grade
  record. It answers "did something move", never "who" or "what".
- **Run unattended indefinitely.** Ambient drift raises the floor mid-session;
  Recalibrate is currently a human pressing a button.
- **Pet/small-body immunity.** Untested; assume false positives from anything
  Fresnel-zone-sized until measured otherwise.

## 6. Wi-Fi sensing standards and ecosystem

**Standards.** IEEE Task Group **802.11bf (WLAN Sensing)**, formed 2020,
standardizes sensing session setup and measurement exchange so Wi-Fi
infrastructure can sense interoperably. **Ratified: published as IEEE Std
802.11bf-2025 on 2025-09-26** (verified; free via the IEEE GET program).
Commodity AP/router support remains the lagging step — consumer firmware
does not yet expose sensing sessions, which is why raw-CSI stacks like this
one still matter. The Wi-Fi Alliance has run corresponding
Wi-Fi Sensing marketing/certification efforts. Direction of travel: sensing
becomes a mainstream Wi-Fi *feature*, sharpening every privacy question in
Section 7.

**Industry.** Chipset vendors (Qualcomm, Intel, Broadcom) have publicized
Wi-Fi sensing demos and contribute to 11bf; Qualcomm partnered with Cognitive
Systems ("WiFi Motion" ships through router OEMs); Intel has shown laptop
presence-detection use cases — commercial announcements, not peer-reviewed
results, so weight accordingly.

**Academic lineage (selected):**

| Year | System / result | Contribution |
|---|---|---|
| 2007 | Device-free passive detection (Youssef et al.) | Framed sensing *without* wearables; RSSI-based |
| 2010 | Radio tomographic imaging (Wilson & Patwari) | Mesh-network device-free tracking; perimeter use case |
| 2013 | Wi-Vi (Adib & Katabi) | Through-wall motion with Wi-Fi-class hardware |
| 2013 | WiSee (Pu et al.) | Doppler-based whole-home gesture recognition |
| 2014 | WiTrack (Adib et al.) | 3D body tracking via radio reflections |
| 2015 | WiTrack2.0 vitals (Adib et al.) | Contactless breathing/heart rate through walls |
| 2015 | RF-Capture (Adib et al.) | Coarse silhouette capture behind walls |
| 2015 | WiKey (Ali et al.) | Keystroke inference from CSI (lab conditions) |
| 2015 | WiGest (Abdelnasser et al.) | Gesture recognition from RSSI alone |
| 2017 | RT-Fall (Wang et al.) | Contactless fall detection, commodity Wi-Fi |
| 2019 | CSUR survey (Ma, Zhou, Wang) | Canonical taxonomy of CSI sensing |
| 2020– | 802.11bf, ESP32 CSI tooling | Standardization + commodity instrumentation |

**Tooling this repo builds on.** Steven Hernandez's **ESP32-CSI-Tool**
(GitHub, 2019+) established the firmware-capture workflow (associated paper:
Hernandez & Bulut, MSWiM 2020 — believed correct, verify citation); Espressif's
official **esp-csi** repository provides the maintained examples
(`get-started/csi_send`, `csi_recv`, `esp-radar`) this repo's firmware derives from.

## 7. Legal and ethical considerations

Jurisdiction-dependent throughout; orientation, not legal advice.

- **Radio law comes first.** Transmitting on 2.4 GHz ISM is license-exempt;
  deliberate interference (jamming) is prohibited nearly everywhere. Passive
  reception of neighbors' CSI-bearing frames is generally lawful *reception*;
  the binding constraints come from privacy law, not spectrum law.
- **Consent and expectation of privacy.** Device-free sensing observes people
  who never interacted with it. Homes, hotel rooms, rented spaces carry the
  highest expectation of privacy; workplaces lower, though many jurisdictions
  require notice before employee monitoring. Deploying in a space you do not
  control is unethical and often unlawful, however innocuous the hardware looks.
- **Wiretapping analogies and their limits.** CSI intercepts no "content" in
  the communications-law sense, so classic wiretap statutes may not apply — but
  continuous behavioral observation (occupancy, schedules, absence) can fall
  under general privacy/data-protection regimes; GDPR treats linked behavioral
  traces as personal data. No camera does not mean no regulated data.
- **Data minimization.** For defensive deployments: collect motion events, not
  raw CSI archives; define retention; signpost honestly. Raw CSI is re-analyzable
  by future algorithms — treat archives as sensitive.
- **Responsible publication.** Detection and defeat belong together; Section
  4.9 exists so this document arms both sides symmetrically. Publishing
  methodology and countermeasures alongside capability claims is the norm this
  repo tries to meet; turnkey covert-surveillance packaging is out of scope.

## 8. Future roadmap tie-in

Ordered by expected value per unit of work, consistent with the repo roadmap:

1. **Breathing-rate estimation** (0.15–0.5 Hz band, subject seated in beam).
   The right next experiment: needs a spectral metric rather than variance
   tails, plus careful handling of the AGC artifacts we already flag — and
   failure is a possible outcome.2. **Labeled session recorder.** Timestamped ground-truth annotation during
   capture turns anecdotes into datasets; prerequisite for everything below.
3. **Multi-receiver fusion.** The hub is already a source registry with
   MAC-tagged frames. Two-plus receivers enable segment tripwires (perimeter),
   crude volumetric localization, and drift-resistant baselines (fusion across
   links averages single-link ambient drift).
4. **ML classification.** With labeled data: gesture classes, person count,
   eventually gait-based identification — all field-proven, all requiring data
   volume this repo does not yet have.
5. **Wardriving integration.** Log CSI-visible emitters and ambient-floor
   statistics alongside conventional AP discovery — a passive-RF-awareness
   layer for the umbrella toolkit.

## 9. References

Only references the author is confident exist are listed without comment; uncertain items are marked.

1. M. Youssef, M. Mah, A. Agrawala, "Challenges: Device-free Passive Localization for Wireless Environments," ACM MobiSys, 2007.
2. J. Wilson, N. Patwari, "See-Through Walls: Motion Tracking Using Variance-Based Radio Tomography Networks," IEEE Trans. Mobile Computing, 2010.
3. F. Adib, D. Katabi, "See Through Walls with Wi-Fi! (Wi-Vi)," ACM SIGCOMM, 2013.
4. Q. Pu, S. Gupta, S. Gollakota, S. Patel, "WiSee: Wi-Fi Enabled Gesture Recognition via Wireless Signals," ACM MobiCom, 2013.
5. F. Adib, Z. Kabelac, D. Katabi, A. C. Miller, "3D Tracking via Body Radio Reflections (WiTrack)," USENIX NSDI, 2014.
6. F. Adib, C.-Y. Hsu, H. Mao, Z. Kabelac, D. Katabi, "Smart Homes That Monitor Breathing and Heart Rate (WiTrack2.0)," ACM CHI, 2015.
7. F. Adib, H. Mao, Z. Kabelac, D. Katabi, R. C. Miller, "RF-Capture," ACM SIGCOMM, 2015.
8. K. Ali, A. X. Liu, W. Wang, M. Shahzad, "Keystroke Recognition Using WiFi Signals (WiKey)," ACM MobiCom, 2015.
9. H. Abdelnasser, M. Youssef, K. A. Harras, "WiGest: A Ubiquitous Gesture Recognition Technique," ACM MobiSys, 2015.
10. H. Wang, D. Zhang, et al., "RT-Fall: A Real-Time and Contactless Fall Detection System with Commodity WiFi Devices," IEEE Trans. Mobile Computing, 2017.
11. Y. Ma, G. Zhou, S. Wang, "WiFi Sensing with Channel State Information: A Survey," ACM Computing Surveys, vol. 52, no. 3, 2019.
12. S. M. Hernandez, E. Bulut, "Wi-ESP: A Real-Time Passive CSI Sensing Tool for ESP32," ACM MSWiM, 2020. *(citation details believed correct — verify)* Primary artifact: https://github.com/stevenmhernandez/ESP32-CSI-Tool
13. Espressif, "esp-csi" (official CSI examples/firmware), https://github.com/espressif/esp-csi
14. IEEE, "IEEE Std 802.11bf-2025 — Enhancements for Wireless LAN Sensing" (ratified; published 2025-09-26).
15. Wi-Fi Alliance, Wi-Fi Sensing program materials (industry, ongoing).
16. Mengyuan Li et al., "WindTalker: Fine-Grained Attack on User Passwords via WiFi Signals," ACM AsiaCCS, 2016. *(author list abbreviated — verify before formal citation)*
17. WiHear — speech/lip reconstruction from Wi-Fi physical-layer signals, ACM MobiCom, ~2014. *(recalled from memory — verify authors/metadata)*
18. Commercial systems cited in text (industry sources, not peer-reviewed): Cognitive Systems "WiFi Motion"; Origin Wireless home sensing/sleep analytics; Google Nest Hub Soli radar sleep sensing (60 GHz radar, not Wi-Fi — included as market evidence).
