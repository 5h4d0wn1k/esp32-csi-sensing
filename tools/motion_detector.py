#!/usr/bin/env python3
"""Host-side presence/motion detection from the csi_recv serial stream.

Uses the classic ESP32 CSI amplitude pattern: when nothing moves in the room,
the subcarrier amplitudes stay near-stable; a moving person (or hand) changes
the multipath, so the frame-to-baseline deviation spikes.

Usage:
  python motion_detector.py -p /dev/ttyUSB0 -b 921600 -t 30          # live 30s
  python motion_detector.py --csv capture.csv                        # replay capture
"""
import argparse
import sys
import time
import serial
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from csi_visualizer import parse_csv, amp_of, clean_rows

WINDOW = 30        # frames for the sliding baseline
ACTIVE_T = 3.0     # deviation threshold (mean |frame - baseline|) -> motion
DEBOUNCE = 2       # consecutive frames required to switch state


def decide(frames, t_end=None, threshold=None):
    """Yield (frame_idx, metric, state). Auto-calibrates threshold from the
    first WINDOW frames (static baseline) unless one is given."""
    devs, states, times = [], [], []
    state, hold = "INACTIVE", 0
    t0 = time.time()
    amp_rows = [amp_of(f["data"]) for f in frames]
    if threshold is None and len(amp_rows) > WINDOW:
        first = np.mean(np.abs(np.diff(np.stack(amp_rows[:WINDOW]), axis=0)), axis=1)
        threshold = float(np.median(first) + 3 * np.std(first))
    thr = threshold if threshold is not None else ACTIVE_T
    for i, a in enumerate(amp_rows):
        if t_end is not None and time.time() - t0 > t_end:
            break
        base = np.mean(np.stack(amp_rows[max(0, i - WINDOW):i]), axis=0) if i else a
        dev = float(np.mean(np.abs(a - base)))
        devs.append(dev)
        want = "ACTIVE" if dev > thr else "INACTIVE"
        if want != state:
            hold += 1
            if hold >= DEBOUNCE:
                state, hold = want, 0
        else:
            hold = 0
        states.append(state)
        times.append(frames[i]["ts"] / 1e6 if frames[i]["ts"] else i)
    return devs, states, times, thr


def live(port, baud, seconds):
    from csi_visualizer import fields
    ser = serial.Serial(port, baud, timeout=1)
    t0 = time.time()
    frames = []
    while time.time() - t0 < seconds:
        line = ser.readline()
        if b"CSI_DATA" not in line:
            continue
        r = fields(line.decode("utf-8", "replace").strip())
        if r is not None:
            frames.append(r)
            if len(frames) % 25 == 0:
                print(f"\r  {len(frames)} frames...", end="", flush=True)
    print()
    return frames


def report(devs, states, thr=None):
    n = len(devs)
    active = sum(1 for s in states if s == "ACTIVE")
    t = f" | threshold: {thr:.2f}" if thr is not None else ""
    print(f"frames: {n} | active: {active} ({100 * active / max(n,1):.0f}%)"
          f"{t} | metric min/med/max: {min(devs):.2f}/{np.median(devs):.2f}/{max(devs):.2f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-p", "--port", default="/dev/ttyUSB0")
    ap.add_argument("-b", "--baud", type=int, default=921600)
    ap.add_argument("-t", "--seconds", type=float, default=15)
    ap.add_argument("--csv")
    ap.add_argument("-o", "--out", default=None, help="PNG chart")
    args = ap.parse_args()

    if args.csv:
        rows, _ = clean_rows(parse_csv(args.csv))
    else:
        rows, _ = clean_rows(live(args.port, args.baud, args.seconds))
    if not rows:
        print("no CSI frames captured"); sys.exit(1)

    devs, states, times, thr = decide(rows, t_end=args.seconds if not args.csv else None)
    report(devs, states, thr)

    if args.out:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
        ax1.plot(times, devs, lw=1)
        ax1.axhline(thr, color="r", ls="--", lw=1)
        ax1.set_ylabel("deviation"); ax1.set_title(f"motion metric vs ACTIVE threshold ({thr:.2f})")
        ax2.plot(times, [1 if s == "ACTIVE" else 0 for s in states], drawstyle="steps-post")
        ax2.set_ylabel("ACTIVE"); ax2.set_xlabel("t (s)")
        fig.tight_layout(); fig.savefig(args.out, dpi=110)
        print(f"saved {args.out}")
