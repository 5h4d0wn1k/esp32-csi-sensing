# Architecture

End-to-end dataflow of the CSI sensing stack: what runs where, the exact wire
formats between stages, and the motion-detection pipeline shared by the hub
(`tools/sensorhub.py`) and the viewer (`tools/csi_3d_viewer.html`, v5.5).
Numbers are measured on the lab desk; see `docs/PLACEMENT.md` for physics
limits and `firmware/README.md` for build/flash details. Design rule:
**dumb sensor board, smart host** — the NodeMCU only streams raw CSI, all
analysis happens host-side, so the analysis evolves without reflashing.

## 1. System overview

```
        optional near-field illuminator              primary whole-room illuminator
   +-----------------------------+            +------------------------------------+
   | ESP32-C6  csi_send          |            | Router AP: a consumer Wi-Fi AP        |
   | ESP-NOW beacons @100/s, ch6 |            | SSID <YOUR_SSID>, ch6           |
   | HT40, 192 subcarriers       |            +------------------+-----------------+
   +--------------+--------------+                               | RF 802.11n (LLTF CSI)
                  | RF                                           v
                  |        +------------------------------------------------------+
                  +------->| Receiver: NodeMCU ESP32, fw csi_recv_router          |
                           | joins the AP + self-pings it @100 Hz                 |
                           | 74-100 CSI frames/s, 64 subcarriers, RSSI ~ -56 dBm  |
                           +---------------------------+--------------------------+
                                                       | UART0, 921600 baud
                                                       | CSI_DATA,... CSV lines
                                                       v
                           +------------------------------------------------------+
                           | Host: tools/sensorhub.py                             |
                           | serial thread -> regex parse -> MotionDetector       |
                           | serves ws://127.0.0.1:8765                           |
                           +---+-------------------------------+------------------+
                               | WebSocket, JSON text frames    | serial write-back
                               | CSI frames + motion events     | (with --oled)
                               v                                v
                   +-----------------------+      +------------------------------+
                   | Browser viewer        |      | SSD1306 OLED status display  |
                   | csi_3d_viewer.html    |      | fw csi_recv_router_oled      |
                   | three.js surface      |      | (optional flashed variant)   |
                   +-----------------------+      +------------------------------+

   Planned (dotted) paths:
   sensorhub ..... M0/M1/F/R/B lines ......> SSD1306 OLED   (B = breath rate, fw ready)
   sensorhub ..... raw frame/event JSON ...> recorder JSONL > analyze_session.py
   sensorhub ..... 2nd -s dev:baud ........> second receiver (source registry)
```

Link roles (measured, see `docs/PLACEMENT.md`): router->receiver works at
room scale (-50..-60 dBm); the ESP-NOW C6 link senses bodies only at >= 5 m
(-60..-70 dBm) and is dead at 1-2 m (-35..-47 dBm, direct path dominates).

The ESP32 CSI engine fires only for frames addressed to the receiver's own
MAC, so promiscuous all-MAC capture cannot see router->client unicast; the
receiver must join the AP and self-ping it (`csi_recv_router`). The all-MAC
variant `csi_recv` exists for the ESP-NOW sender and any other transmitter
on ch6.

## 2. UART frame format

The receiver prints one CSV line per CSI frame at 921600 baud. First boot
prints a header line; every subsequent line starts with the `CSI_DATA`
keyword.

### 2.1 Flashed long-form variant (classic ESP32, primary)

Header: `type,id,mac,rssi,rate,sig_mode,mcs,bandwidth,smoothing,not_sounding,
aggregation,stbc,fec_coding,sgi,noise_floor,ampdu_cnt,channel,
secondary_channel,local_timestamp,ant,sig_len,rx_state,len,first_word,data`

24 columns after the keyword: **22 numeric fields + source MAC + quoted IQ
array**. Field positions are 1-based after `CSI_DATA`:

| # | Field | Meaning | Used by hub |
|---|-------|---------|-------------|
| 1 | `id` | frame sequence counter | no |
| 2 | `mac` | transmitting BSSID (`MACSTR`) | yes -> `mac` |
| 3 | `rssi` | per-frame RSSI, dBm | yes -> `rssi` |
| 4 | `rate` | PHY rate | no |
| 5 | `sig_mode` | 0 = legacy, 1 = HT | no |
| 6 | `mcs` | MCS index | no |
| 7 | `bandwidth` | 0 = 20 MHz, 1 = 40 MHz | no |
| 8-13 | `smoothing..sgi` | rx_ctrl flags | no |
| 14 | `noise_floor` | dBm | no |
| 15 | `ampdu_cnt` | A-MPDU subframe count | no |
| 16 | `channel` | primary channel (6 here) | yes -> `ch` |
| 17 | `secondary_channel` | 0/1/2 | no |
| 18 | `local_timestamp` | TSF, us | no |
| 19 | `ant` | antenna index | no |
| 20 | `sig_len` | received frame length | no |
| 21 | `rx_state` | populated with `sig_mode` (upstream carry-over) | no |
| 22 | `len` | IQ byte count = 2 x nsub (128 -> 64 sc LLTF, 384 -> 192 sc HT40) | implicit (array length) |
| 23 | `first_word` | first-word-invalid flag | no |
| 24 | `data` | quoted `[im,re,im,re,...]` int8 pairs | yes -> `amp`,`ph` |

The hub regex (`RE_CSI`, sensorhub.py:46) captures exactly these 24 groups;
it reads `mac`=group 2, `rssi`=group 3, `channel`=group 16, `data`=group 24.
`csi_recv_router` filters on BSSID in firmware (`memcmp(info->mac, ctx, 6)`),
so every line carries the AP's MAC.

### 2.2 Alternate variants

- **Short 14-column variant** (C5/C6/C61 builds, also present in
  `firmware/csi_recv/main/app_main.c`): `seq,mac,rssi,rate,noise_floor,
  fft_gain,agc_gain,channel,local_timestamp,sig_len,rx_format,len,
  first_word,data`. Replaces the rate-control block with explicit
  `fft_gain`/`agc_gain` columns. The current hub regex does NOT match it
  (expects 24 groups), so such lines are silently dropped; supporting it
  means adding a second pattern and remapping indices.
- **MAC-less legacy ESP-NOW layout**: upstream omits the MAC when built
  without router mode. The hub auto-detects this structurally — a colon in
  field 2 means MAC is present; otherwise `mac=None` and the same absolute
  group indices are kept (sensorhub.py:196-199).

Any even subcarrier count >= 32 is accepted downstream (64 for the router
LLTF capture, 192 for the ESP-NOW HT40 link).

## 3. Hub internals (`tools/sensorhub.py`)

### 3.1 Threading model

- One blocking reader thread per serial source (`SerialCsiSource._reader`,
  daemon): 4096-byte reads with a 1 s timeout, split on `\n`.
- Parsed frames cross into the asyncio loop via
  `loop.call_soon_threadsafe(q.put_nowait)`; the queue is bounded at 4096 and
  **drops on overflow** rather than backpressuring the serial thread.
- Sources come from repeatable `-s dev:baud` args (default: autodetect
  `/dev/ttyUSB*` / `/dev/ttyACM*` at 921600). Every source feeds the same
  `feed()` coroutine; every client sees every source's frames.

### 3.2 Parsing

Per line: strip NUL bytes, UTF-8/replace decode, anchored regex match,
extract all integers from the quoted array, truncate to an even count, drop
frames with < 32 subcarriers (glitch frames). Each pair becomes
`amp[k] = int(hypot(im, re))`, `ph[k] = int(degrees(atan2(re, im)))`.

### 3.3 WebSocket protocol (ws://127.0.0.1:8765)

Server -> client, JSON text frames, one object per message:

```json
{"src":"nodemcu","kind":"csi","mac":"<AP_MAC>","rssi":-56,
 "ch":6,"nsub":64,"amp":[...64 ints...],"ph":[...64 ints...]}
```

With `--detector` the hub additionally publishes motion objects **on every
state change plus a 1 s heartbeat** (0.25 s scheduler tick):

```json
{"type":"motion","state":"ACTIVE","level":0.031,"thr":0.0204,"fps":87}
```

`level`/`thr` may be `null` while calibrating. The only client -> server
command is `{"cmd":"recal"}`: it resets the detector to INACTIVE, clears the
calibration baseline/threshold, and re-enters the 5 s calibration window.

### 3.4 Detector gating and fps

The detector locks onto the first frame's subcarrier count (`det_nsub`);
only matching frames feed `MotionDetector` and the published `fps` (1 s
sliding window). Mismatched-length frames are still broadcast but bypass
detection — mixing 64- and 192-subcarrier sources cannot corrupt the metric.

### 3.5 OLED serial feedback (`--oled`, implies `--detector`)

Newline-terminated ASCII written back down the same serial link
(`write_line`, best-effort):

| Line | When | Meaning |
|------|------|---------|
| `M1` / `M0` | on every state change | motion ACTIVE / CLEAR (display inverts 200 ms) |
| `F<fps>` | every 5 s | measured frame rate |
| `R<rssi>` | every 5 s (if rssi known) | link RSSI, dBm |
| `B<bpm>` | reserved | breath rate — parsed by `csi_recv_router_oled` (shows `--` when silent > 10 s) but not yet emitted by the hub |

On the firmware side a 100 ms FreeRTOS task parses UART0 RX non-blockingly
and drops garbage lines; the SSD1306 runs on I2C @ 400 kHz (GPIO21/22,
addr 0x3C). An M-transition write also resets both 5 s F/R timers so the
display refreshes immediately after a flip.

### 3.6 Serial-bounce resilience

Any exception in the reader thread (USB unplug, spurious close) is logged,
the port is closed, and the thread loops on `connect()` every 2 s until the
device reappears; the partial line buffer is discarded. Frames during the
outage are simply lost — there is no replay. Dead WebSocket clients are
discarded lazily on failed `send()`.

## 4. Motion-detection pipeline

Host-side detector, an exact port of the viewer's `runMotion`
(csi_3d_viewer.html:267) into `MotionDetector` (sensorhub.py:56). Metric:
gain-normalized amplitude-shape deviation, decided on the tail of its
rolling variance.

### 4.1 Stages

1. **Ingest** — keep the last 150 frames; need >= 2; take a baseline window
   of the last min(30, N) frames.
2. **Shape deviation** — normalize every frame by its own mean magnitude
   (`mag + 1e-6`), average the window into a per-subcarrier baseline, then
   `dev = mean_s |amp[s]/curMag - base[s]|`. Per-frame normalization cancels
   AGC gain magnitude steps; only *shape* change survives.
3. **AGC transient rejection** — push `(now, rssi, dev)` into a 12-entry
   ring; the candidate is the entry 4 back (a 3-frame commit delay: a jump
   is only "final" once jumps at `[idx-3, idx+2]` are known). If any
   adjacent RSSI pair around the candidate differs by more than
   `M_TRANSIENT_DB`, the candidate is discarded; otherwise it enters the
   good-sample history (capped 4000).
4. **Rolling variance** — population standard deviation of `dev` over the
   last `MVAR_MS` of good samples (>= 8 required); pushed into a 600-entry
   level history (~6 s at router frame rates).
5. **Level** — `level = quantile(var_hist, M_LEVEL_Q)` (>= 8 entries
   required). Sporadic body signal lives in the tail; a stable static floor
   stays far below it.
6. **Calibration** — while `thr is None`, collect levels; after >= 40
   samples AND >= `MCAL_MS` elapsed, `thr = quantile(cal, 0.9) *
   M_THR_RATIO`. Requires a quiet room (see `docs/PLACEMENT.md`).
7. **Hysteresis** — time-based latch on the level (below).

### 4.2 Constants

| Constant | Value | Meaning |
|----------|-------|---------|
| `MVAR_MS` | 1500 ms | rolling-variance window of the deviation |
| `MCAL_MS` | 5000 ms | minimum calibration duration |
| `M_THR_RATIO` | 1.5 | `thr = p90(cal level) x 1.5` (raise to 2 in a noisy room) |
| `M_ON` | 1.0 s | continuous time above threshold to latch ACTIVE |
| `M_OFF` | 3.0 s | continuous time below threshold to drop INACTIVE |
| `M_LEVEL_Q` | 0.95 | decision level = p95 of the variance history |
| `M_TRANSIENT_DB` | 2.0 dB | adjacent-frame RSSI jump treated as an AGC step |
| ring | 12 entries | transient-evaluation window, 3-frame commit delay |
| min good samples | 8 | floor for `quantile()` and `_rolling_std()` |
| level-history cap | 600 | ~6 s of variance values at ~100 fps |
| other caps | 150 / 30 / 4000 / 40 | frame ring / baseline window / good-sample history / calibration samples |

### 4.3 State machine

```
on frame(amp, rssi):
    dev  = shape_deviation(amp, last 30 frames)         # stage 2
    ring.push(now, rssi, dev); trim to 12
    cand = ring[-4]                                     # 3-frame commit delay
    if no adjacent |rssi jump| > 2.0 dB in ring[-7:-1]:
        hist.push(cand.dev)                             # clean sample only
    var  = stddev(hist, last 1500 ms)                   # needs >= 8 samples
    var_hist.push(var); trim to 600
    level = quantile(var_hist, 0.95)                    # needs >= 8 samples

    if thr is None:                                     # calibrating
        cal.push(level)
        if len(cal) >= 40 and now - t0 >= 5000 ms:
            thr = quantile(cal, 0.90) * 1.5
        return

    if level > thr: t_above = now   else: t_below = now
    if state == INACTIVE and now - t_below >= 1000 ms: state = ACTIVE
    if state == ACTIVE   and now - t_above  >= 3000 ms: state = INACTIVE
```

(`t_above`/`t_below` are the timestamps of the last above/below-threshold
observation; the latch conditions are "continuously above for M_ON" /
"continuously below for M_OFF".)

### 4.4 Why AGC transients are rejected

The receiver's AGC gain steps produce > 2 dB per-frame RSSI jumps whose CSI
ripple correlates strongly with the shape metric — measured
**corr(dev, rssi) = 0.87** — making a gain step indistinguishable from body
motion at the dev stage. Mean-normalization removes the gain *magnitude* but
not the induced shape ripple, so the only robust defense is temporal: flag
jump-contaminated frames via the delayed-commit ring and exclude them from
the variance history entirely.

### 4.5 Measured performance and latency

Validated end-to-end on the router link (v5.5 module code, noisy capture,
threshold 0.0204):

| Scenario | Result |
|----------|--------|
| Static room | 0% false ACTIVE |
| Hand wave | 92% detected |
| Walking | 99-100% detected |
| Standing in beam | 83% |

Latency budget to ACTIVE: ~0.3-0.4 s shape-window warm-up (30 frames at
74-100 fps) + ~1.5 s variance window fill + 1.0 s `M_ON` hysteresis (UART/WS
transport < 10 ms) — **~2.5 s total**. Deactivation takes `M_OFF` = 3.0 s.

## 5. Rendering (`tools/csi_3d_viewer.html`)

- **Surface mesh** — one indexed `BufferGeometry` grid of
  `MAX_FRAMES=150` time columns x `N_SUB` subcarrier rows. Axes: **X = time**
  (newest frame at x=0), **Z = subcarrier index** (centered), **Y =
  amplitude**, vertex-colored with a viridis gradient normalized to the
  global amplitude max of the visible window. Wireframe toggle shares the
  same geometry.
- **Dominant-source selection** — per-MAC frame counts accumulate for 2 s,
  then the most frequent MAC becomes `activeMac`; frames from other
  transmitters are dropped before display and detection. This lets the
  all-MAC receiver sit on a shared channel and track one stable link.
- **Adaptive subcarriers** — the first frame's `nsub` sizes the mesh
  (`applyNSub`); 64 (router LLTF) and 192 (ESP-NOW HT40) are the expected
  values. A size switch rebuilds the geometry and resets the entire motion
  state (calibration included). Frames whose length mismatches `N_SUB` are
  skipped.
- **FPS budget** — `requestAnimationFrame` drives OrbitControls + render at
  display rate; the expensive CPU rebuild (positions, colors, normals:
  O(MAX_FRAMES x N_SUB), ~57k triangles at 192 subcarriers) is throttled to
  one rebuild per 50 ms (20 Hz). Sparklines (RSSI, motion metric +
  threshold) redraw per frame on 2D canvases.

## 6. Extension points

- **Multi-receiver** — the hub is already a source registry: add `-s
  dev:baud` per extra board; each gets its own reader thread and queue, and
  all clients see all sources tagged by `src`/`mac`. Remaining work is
  viewer-side: per-source meshes/detectors (today one `N_SUB`, one
  `activeMac`).
- **Recorder -> analyze_session.py** (planned) — a passthrough consumer can
  persist raw frame objects and `motion` events as JSONL (one JSON object
  per line, superset of the WS protocol): lossless replays for the viewer's
  file-load path plus offline batch analysis (threshold sweeps, comparison
  against `tools/motion_detector.py`).
- **OLED protocol** — the firmware parser already accepts `B<bpm>`; wiring a
  respiration estimator into the hub's `motion_reporter` tick is additive.
  New status lines must stay newline-terminated ASCII with digits-only
  payloads, at >= 5 s cadence (non-blocking 100 ms parse task).
