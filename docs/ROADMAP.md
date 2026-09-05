# Roadmap

Priorities for the esp32-csi-sensing sensing stack (hub, viewer, offline
tools, firmware). Ordering follows expected value per unit of work and stays
consistent with the future-work list in `docs/CAPABILITIES.md` §8.

## How to read this

- **Impact** — value to the project's core claims (sensing that works and is
  honestly characterized).
- **Effort** — rough engineering cost: low (days), med (weeks), high (longer).
- **Risk** — chance the item fails or underdelivers technically.
- **Notes** — dependencies, physics limits, and pointers into
  `docs/CAPABILITIES.md` where an honest-limits caveat applies.

## Now — current focus

| Item | Impact | Effort | Risk | Notes |
|------|--------|--------|------|-------|
| Validate breath estimator on real still-person recordings | high | med | high | The 0.15–0.5 Hz band is the right next experiment (`CAPABILITIES.md` §4.4) but our metric is amplitude-deviation variance, not a spectral estimator, and AGC gain wobble pollutes exactly that band. Failure is a possible outcome; validate on recordings before claiming anything. |
| Labeled dataset collection campaign (viewer Record button) | high | low | low | Timestamped ground-truth annotation during capture turns anecdotes into datasets; prerequisite for every ML item below (`CAPABILITIES.md` §8.2). Add a Record/label control to `csi_3d_viewer.html`, store labeled sessions under `data/captures/`. |
| Two-receiver fusion demo | med | med | med | The hub is already a source registry with MAC-tagged frames; two receivers enable a segment-tripwire demo and drift-resistant baselines (fusion averages single-link ambient drift). No fusion logic exists yet (`CAPABILITIES.md` §8.3). |

Exit criteria for this phase: a published go/no-go on breathing, at least one
labeled session set per scenario class, and a two-node capture with fused
decision output in the viewer or hub logs.

## Next — after the current items land

| Item | Impact | Effort | Risk | Notes |
|------|--------|--------|------|-------|
| Edge inference port to ESP32-S3 | high | high | med | Move the detector (and eventually the breath estimator) onto an S3 with vector instructions so no host PC is needed. Must reproduce AGC-transient rejection and the p95-tail decision exactly; serial bandwidth stops being a constraint. |
| MQTT / Home Assistant bridge | med | low | low | Publish motion/presence events from `sensorhub.py` over MQTT topics; makes the alarm primitives of `CAPABILITIES.md` §4.1/§4.7 usable in existing home-automation stacks. Keep payloads event-only (data minimization, §7). |
| Direction finding with spaced receivers | med | high | high | Multiple spaced receivers plus fusion could give crude bearing/volumetric localization. Physics-limited: 20 MHz gives no ranging; needs the multi-receiver work first and honest expectations (`CAPABILITIES.md` §5: no trajectories today). |
| ML gesture classification | med | med | high | Field-proven in the literature but blocked on labeled data volume from the Now campaign (`CAPABILITIES.md` §8.4). Start with few gesture classes on direct-link captures at ≥5 m separation. |

Sequencing note: direction finding and ML gestures both consume outputs of the
Now phase (fusion demo, labeled datasets); do not start them before those land.

## Later — exploratory / opportunistic

| Item | Impact | Effort | Risk | Notes |
|------|--------|--------|------|-------|
| 802.11bf alignment | med | high | med | Standard ratified: **IEEE Std 802.11bf-2025** (published 2025-09-26, `CAPABILITIES.md` §6). Remaining bet is commodity-AP adoption: when consumer firmware exposes sensing sessions, this stack's hub/detector layer should map onto it. Watch router vendor support, not the standard itself. |
| `wardrive.py` GPS scanner | low | med | low | Passive-RF-awareness layer for the umbrella toolkit: log CSI-visible emitters and ambient-floor statistics alongside conventional AP discovery (`CAPABILITIES.md` §8.5). |
| Android companion app | low | med | med | The viewer already runs in any mobile browser without Web Serial (`docs/VISUALIZATION.md`); a native app would add background capture/notification only. Low priority until events/alerts exist. |
| Alarm-system integration | high | med | med | Timestamped event logs, armed/disarmed windows, alert pushes, panel integration (`CAPABILITIES.md` §4.1). Depends on the MQTT bridge; pet immunity is untested and a known hard problem — do not promise reliability. |

Later items are revisited whenever upstream standards, hardware availability,
or the umbrella toolkit create a concrete pull; none has a committed date.

## Standing constraints

Anything added here inherits the honest envelope of `docs/CAPABILITIES.md`
§5: no person identification, no trajectory tracking, no multi-wall coverage,
no reliable people counting, and calibration re-runs after any environment
change. Roadmap items that would cross those lines must say so explicitly and
cite the limits they are pushing against.
