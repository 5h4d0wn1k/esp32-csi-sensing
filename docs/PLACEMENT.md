# Placement guide (measured)

Hard-learned numbers from the lab desk, so the demo works first try.

## The walk-between-the-nodes demo
Nodes are the ESP32-C6 sender (`csi_send`, on a power bank) and the NodeMCU
receiver (`csi_recv`, USB to the laptop).

| Sender→Receiver distance | RSSI     | Motion detect | Verdict |
|--------------------------|----------|---------------|---------|
| ~0.3–0.5 m (same desk)   | −24 dBm  | No            | Direct path saturates; body can't fit in the path |
| ~1.5 m                   | −40 dBm  | Yes (dev 20–63 vs thr ~12) | **Works** — walk between them |

Rules:
1. Put the two nodes **≥ 1.5 m apart** (a doorway or a corridor gap is ideal).
2. Walk *across* the line between the antennas, not near the endpoints.
3. Let the viewer auto-calibrate for ~1 s on an **empty** room before testing
   (the threshold is median+MAD of the first 30 frames).

## AGC / strong-signal lesson
At −24 dBm the receiver's AGC toggles between gain steps (frame magnitude
jumps ~21 ↔ 38), which swamps an absolute-amplitude detector. The viewer v5.2
motion metric normalizes each frame by its own mean magnitude before comparing
(shape-only, gain-invariant) — but physical separation is still required.

## Router as a whole-room illuminator
The Digisol (Airtel_Xstream, ch6) adds a strong second transmitter
(74 CSI/s @ −51 dBm when pinged), but:
- the ESP32's CSI only fires on **OFDM** frames — the router's 1 Mbps DSSS
  beacons produce no CSI;
- to light the room via the router, generate OFDM traffic (ping flood to
  `192.168.2.1` from a client on the same AP) or use the `csi_recv_router`
  example which joins the AP and self-pings;
- the all-MAC receiver also picks up neighbours on ch6 — the viewer shows the
  dominant source by MAC.

## Antennas
- Keep the NodeMCU's PCB antenna edge-on to the room (vertical), away from the
  laptop's metal and USB hub.
- The C6 is tiny — orient it so the chip's antenna points toward the receiver.

## Tuning
Motion sensitivity in `tools/csi_3d_viewer.html`:
- `MWIN` — baseline window in frames (30 = ~0.4 s at 74/s)
- threshold multiplier `3` in the median+MAD calibration (raise to 4–5 for a
  noisier room, lower to 2 for a quiet room)
- `MDEB` — consecutive frames to latch a state change (2)
