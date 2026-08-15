#!/usr/bin/env python3
"""Live CSI visualizer for esp-csi get-started firmware.

Reads CSI_DATA lines from the receiver's serial port and renders the
per-subcarrier amplitude as a scrolling heatmap + RSSI strip.

Usage:
  python csi_visualizer.py -p /dev/ttyUSB0 -b 921600          # live capture
  python csi_visualizer.py --csv capture.csv -o heatmap.png   # render saved capture

CSV line format (classic ESP32):
  type,id,mac,rssi,rate,sig_mode,mcs,bandwidth,smoothing,not_sounding,
  aggregation,stbc,fec_coding,sgi,noise_floor,ampdu_cnt,channel,secondary_channel,
  local_timestamp,ant,sig_len,rx_state,len,first_word,data
  data = [Im0,Re0,Im1,Re1,...]  (len field reports the array length)
"""
import argparse
import re
import time
import serial
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HEADER = ("type,id,mac,rssi,rate,sig_mode,mcs,bandwidth,smoothing,not_sounding,"
          "aggregation,stbc,fec_coding,sgi,noise_floor,ampdu_cnt,channel,"
          "secondary_channel,local_timestamp,ant,sig_len,rx_state,len,first_word,data")

# 23 fields before the quoted data array
ROW_RE = re.compile(
    r'CSI_DATA,(\d+),([0-9a-f:]+),(-?\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),'
    r'(\d+),(\d+),(\d+),(-?\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),'
    r'"(\[[^\]]*\])"')


def fields(line):
    line = line.replace("\x00", "")
    m = ROW_RE.match(line)
    if not m:
        return None
    g = m.groups()
    return {
        "id": int(g[0]), "mac": g[1], "rssi": int(g[2]), "rate": int(g[3]),
        "noise": int(g[13]), "channel": int(g[15]), "ts": int(g[17]),
        "len": int(g[21]),
        "data": np.array([int(x) for x in re.findall(r"-?\d+", g[23])]),
    }


def parse_csv(path):
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line.startswith("CSI_DATA"):
                continue
            r = fields(line)
            if r is not None:
                rows.append(r)
    return rows


def amp_of(vals):
    """[(im,re)] pairs -> amplitude per subcarrier."""
    n = len(vals) // 2 * 2
    p = vals[:n].reshape(-1, 2)
    return np.hypot(p[:, 0], p[:, 1])


def render(rows, out="heatmap.png"):
    from collections import Counter
    target = Counter(len(r["data"]) for r in rows).most_common(1)[0][0]
    rows = [r for r in rows if len(r["data"]) == target]
    amps = np.stack([amp_of(r["data"]) for r in rows])
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), height_ratios=[3, 1])
    ax1.imshow(amps.T, aspect="auto", origin="lower", cmap="viridis",
               extent=[0, len(rows), -0.5, amps.shape[1] - 0.5])
    ax1.set_ylabel("subcarrier index")
    ax1.set_title(f"CSI amplitude heatmap — {len(rows)} frames, ch {rows[0]['channel']}, "
                  f"rate {rows[0]['rate']}Mbps, {amps.shape[1]} subcarriers")
    rssi = np.array([r["rssi"] for r in rows])
    ax2.plot(np.arange(len(rssi)), rssi, lw=1)
    ax2.set_ylabel("RSSI dBm")
    ax2.set_xlabel("frame")
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    print(f"saved {out}: {amps.shape[1]} subcarriers x {len(rows)} frames")


def live(port, baud, seconds, out):
    ser = serial.Serial(port, baud, timeout=1)
    start = time.time()
    rows = []
    while time.time() - start < seconds:
        line = ser.readline()
        if b"CSI_DATA" not in line:
            continue
        r = fields(line.decode("utf-8", "replace").strip())
        if r is not None:
            rows.append(r)
    print(f"captured {len(rows)} frames in {seconds}s ({len(rows)/seconds:.1f}/s)")
    if out and rows:
        render(rows, out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-p", "--port", default="/dev/ttyUSB0")
    ap.add_argument("-b", "--baud", type=int, default=921600)
    ap.add_argument("-t", "--seconds", type=float, default=5.0)
    ap.add_argument("-o", "--out")
    ap.add_argument("--csv")
    args = ap.parse_args()
    if args.csv:
        render(parse_csv(args.csv), args.out or "heatmap.png")
    else:
        live(args.port, args.baud, args.seconds, args.out)
