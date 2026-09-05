# Placement guide (measured, v5.5)

Hard-learned numbers from the lab desk. Two earlier claims in this file were
wrong and are now corrected: the "1.5 m ESP-NOW walk demo works" result was an
artifact (the receiver node was physically being moved), and per-frame deviation
was being corrupted by receiver AGC gain steps.

## The physics: when can a body be sensed?

The CSI shape-change from a body only registers when the body occludes a
meaningful fraction of the **propagation path** (roughly the first Fresnel zone).

| Link | Separation | RSSI | Body motion detect | Verdict |
|------|-----------|------|--------------------|---------|
| ESP-NOW sender↔receiver | ~1–2 m | −35…−47 dBm | **No** | Direct path dominates; a hand/walk perturbs CSI below the noise floor (per-subcarrier mean dev 0.083 vs 0.086 static vs walk — zero separation) |
| ESP-NOW sender↔receiver | ≥ 5 m (a corridor/doorway) | −60…−70 dBm | Yes | Body occupies a real fraction of the path; needs enough separation |
| Router (AP)↔receiver | room-scale | −50…−60 dBm | Yes (quiet room) | Whole room illuminated; static varDev ~0.01, motion 0.03–0.09 |

Rule: **the two-node desk demo does not work.** Use the router-illuminated
room-scale setup (`csi_recv_router`) or give the ESP-NOW nodes real separation.

## Router as a whole-room illuminator (primary demo)

- Receiver NodeMCU runs `csi_recv_router`: it joins the AP (<YOUR_SSID>, ch6)
  and self-pings the router, producing ~74–100 CSI frames/s at 64 subcarriers,
  RSSI ≈ −56 dBm.
- The all-MAC `csi_recv` promiscuous mode does **not** capture router→client
  unicast: the ESP32 CSI engine only fires for frames addressed to its own MAC.
- The metric is **variance-of-deviation over time**, and it only works when the
  room is **quiet**. Ambient radio instability (people near the link, ch6
  traffic) raises the floor to ~0.05 and masks motion. Detection needs:
  - a quiet room for the 5 s auto-calibration,
  - no-one near the receiver/AP,
  - Recalibrate after any big environment change.

## AGC transient rejection (v5.5)

The receiver's AGC gain steps produce >2 dB per-frame RSSI jumps that look
exactly like body motion in the shape metric (corr(dev, rssi) ≈ 0.87). The
viewer now:
- flags each frame with a 3-frame commit delay (a jump is only "final" once
  jumps at [idx−3, idx+2] are known),
- excludes flagged frames from the variance history entirely,
- decides on the **p95 tail of varDev over the last ~6 s** — sporadic body
  signal lives in the tail, a stable static floor stays far below.

Validated end-to-end (actual module code, Node harness, noisy capture):
threshold 0.0204; static 0% ACTIVE; hand-wave 92%; walking 100%; stand-in-beam 83%.

## Tuning (`tools/csi_3d_viewer.html`)

- `MVAR_MS` — variance window (1500 ms)
- `MCAL_MS` — calibration duration (5000 ms)
- `M_THR_RATIO` — threshold = p90(cal level) × 1.5 (raise to 2 for a noisier room)
- `M_ON` / `M_OFF` — hysteresis: ACTIVE after level above threshold 1.0 s,
  INACTIVE after 3.0 s of quiet
- `M_TRANSIENT_DB` — RSSI jump size treated as an AGC step (2.0 dB)

## Antennas

- NodeMCU PCB antenna edge-on to the room (vertical), away from laptop metal.
- C6: orient its chip antenna toward the receiver; keep it far from the receiver
  (the ESP-NOW link is only a motion sensor at ≥5 m).

## Calibration ritual

1. Make sure the room is empty and quiet (nobody moving, no walking nearby).
2. Open the viewer, wait ~5 s — it shows "calibrating static baseline...".
3. When the threshold appears, move/walk in the room. Watch `MOTION` latch
   ACTIVE after ~1 s of motion and drop after ~3 s of stillness.
4. Press **Recalibrate** whenever the ambient changes.
