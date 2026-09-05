#!/usr/bin/env python3
"""Offline analysis of recorded CSI sessions.

Replicates the browser viewer's motion-detection pipeline exactly (see
docs/ARCHITECTURE.md section 4 and tools/csi_3d_viewer.html runMotion):
gain-normalized shape deviation -> AGC-transient rejection -> 1.5 s rolling
std -> p95 tail level -> p90x1.5 calibration threshold -> 1 s / 3 s hysteresis.
"""
import argparse
import json
import sys

MVAR_MS = 1500
MCAL_MS = 5000
M_THR_RATIO = 1.5
M_ON_MS = 1000.0
M_OFF_MS = 3000.0
M_LEVEL_Q = 0.95
M_TRANSIENT_DB = 2.0
RING_CAP = 12
MHIST_CAP = 4000
MVARHIST_CAP = 600
BASELINE_WIN = 30


def load_frames(path):
    frames = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            frames.append((float(d["t"]), d["amp"], d.get("rssi")))
    return frames


def quantile(arr, q, min_n=8):
    if len(arr) < min_n:
        return None
    srt = sorted(arr)
    return srt[min(len(srt) - 1, int(len(srt) * q))]


def analyze(frames):
    nsub = len(frames[0][1])
    base_win = []
    ring = []
    mhist = []
    mvarhist = []
    mcal = []
    mcal0 = None
    thr = None
    state = "INACTIVE"
    t_up = 0.0
    t_down = 0.0
    levels = []
    states = []
    bad_flags = []

    for t, amp, rssi in frames:
        base_win.append(amp)
        if len(base_win) > BASELINE_WIN:
            base_win.pop(0)
        mags = [sum(f) / len(f) + 1e-6 for f in base_win]
        cur_mag = sum(amp) / len(amp) + 1e-6
        base = [0.0] * nsub
        for f, m in zip(base_win, mags):
            for s in range(nsub):
                base[s] += f[s] / m
        acc = 0.0
        for s in range(nsub):
            b = base[s] / len(base_win)
            acc += abs(amp[s] / cur_mag - b)
        dev = acc / nsub

        ring.append((t, rssi, dev))
        if len(ring) > RING_CAP:
            ring.pop(0)
        if len(ring) >= 4:
            ct, crssi, cdev = ring[-4]
            bad = False
            if crssi is not None:
                for j in range(max(1, len(ring) - 7), len(ring) - 1):
                    a, b = ring[j][1], ring[j - 1][1]
                    if a is not None and b is not None and abs(a - b) > M_TRANSIENT_DB:
                        bad = True
                        break
            bad_flags.append(bad)
            if not bad:
                mhist.append((ct, cdev))
                if len(mhist) > MHIST_CAP:
                    mhist.pop(0)

        cutoff = t - MVAR_MS
        i = len(mhist) - 1
        while i >= 0 and mhist[i][0] > cutoff:
            i -= 1
        sub = mhist[i + 1:]
        var_dev = None
        if len(sub) >= 8:
            mean = sum(v for _, v in sub) / len(sub)
            sse = sum((v - mean) ** 2 for _, v in sub)
            var_dev = (sse / len(sub)) ** 0.5
        if var_dev is not None:
            mvarhist.append(var_dev)
            if len(mvarhist) > MVARHIST_CAP:
                mvarhist.pop(0)

        level = quantile(mvarhist, M_LEVEL_Q)
        levels.append(level)

        if thr is None:
            if level is not None:
                mcal.append(level)
            if mcal0 is None:
                mcal0 = t
            if len(mcal) >= 40 and t - mcal0 >= MCAL_MS:
                thr = quantile(mcal, 0.9) * M_THR_RATIO
            states.append(state)
            continue

        if level is not None and level > thr:
            t_up = t
        else:
            t_down = t
        if state == "INACTIVE" and t - t_down >= M_ON_MS:
            state = "ACTIVE"
        if state == "ACTIVE" and t - t_up >= M_OFF_MS:
            state = "INACTIVE"
        states.append(state)

    return {
        "thr": thr,
        "levels": levels,
        "states": states,
        "bad": bad_flags,
        "nsub": nsub,
    }


def segment_stats(res, frames, labels):
    t_end = frames[-1][0]
    segs = []
    for lo, hi, name in labels:
        lo_ms, hi_ms = lo * 1000.0, hi * 1000.0
        dur = 0.0
        act = 0.0
        badc = 0
        tot = 0
        lvls = []
        for k, (t, _amp, _rssi) in enumerate(frames):
            if t < lo_ms or t >= hi_ms:
                continue
            dur += 1
            tot += 1
            if res["bad"][k] if k < len(res["bad"]) else False:
                badc += 1
            if res["states"][k] == "ACTIVE":
                act += 1
            if res["levels"][k] is not None:
                lvls.append(res["levels"][k])
        segs.append({
            "name": name,
            "start_s": lo,
            "end_s": hi,
            "frames": tot,
            "bad_pct": round(badc / tot * 100, 1) if tot else 0.0,
            "active_pct": round(act / tot * 100, 1) if tot else 0.0,
            "mean_level": round(sum(lvls) / len(lvls), 4) if lvls else None,
        })
    return segs


def parse_labels(s):
    out = []
    if not s:
        return out
    for part in s.split(","):
        rng, name = part.split(":", 1)
        lo, hi = rng.split("-")
        hi = float(hi) if hi.strip() else None
        out.append((float(lo), hi, name.strip()))
    return out


def main():
    ap = argparse.ArgumentParser(description="Offline CSI session analysis")
    ap.add_argument("session", help="session .jsonl ({t, amp[], rssi} per line)")
    ap.add_argument("--labels", default="",
                    help='"start-end:name,start-end:name" in seconds')
    ap.add_argument("--plot", help="write summary figure PNG here")
    ap.add_argument("--json", help="write machine-readable summary JSON here")
    args = ap.parse_args()

    frames = load_frames(args.session)
    if len(frames) < 100:
        sys.exit("need >=100 frames")
    t0 = frames[0][0]
    frames = [(t - t0, a, r) for t, a, r in frames]
    res = analyze(frames)

    dur_s = frames[-1][0] / 1000.0
    fps = len(frames) / dur_s if dur_s else 0
    bad_pct = sum(res["bad"]) / max(1, len(res["bad"])) * 100
    labels = parse_labels(args.labels)
    segs = segment_stats(res, frames, labels)

    print(f"session: {args.session}")
    print(f"frames: {len(frames)}  duration: {dur_s:.1f}s  fps: {fps:.0f}  "
          f"nsub: {res['nsub']}  bad frames: {bad_pct:.1f}%")
    print(f"threshold: {res['thr'] if res['thr'] is not None else 'NOT CALIBRATED'}")
    if segs:
        print(f"{'segment':<12}{'span':<12}{'frames':>8}{'bad%':>8}{'ACTIVE%':>9}{'level':>9}")
        for s in segs:
            lvl = f"{s['mean_level']:.3f}" if s["mean_level"] is not None else "--"
            print(f"{s['name']:<12}{f'{s['start_s']:.0f}-{s['end_s']:.0f}s':<12}"
                  f"{s['frames']:>8}{s['bad_pct']:>8}{s['active_pct']:>9}{lvl:>9}")

    if args.json:
        import statistics
        lv = [x for x in res["levels"] if x is not None]
        out = {
            "session": args.session,
            "frames": len(frames),
            "duration_s": round(dur_s, 2),
            "fps": round(fps, 1),
            "bad_pct": round(bad_pct, 2),
            "threshold": res["thr"],
            "level_mean": round(statistics.fmean(lv), 5) if lv else None,
            "level_p95": round(quantile(lv, 0.95, 1), 5) if lv else None,
            "segments": segs,
        }
        with open(args.json, "w") as fh:
            json.dump(out, fh, indent=2)
        print(f"wrote {args.json}")

    if args.plot:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            print("matplotlib unavailable; skipping plot", file=sys.stderr)
            return
        ts = [frames[k][0] / 1000.0 for k in range(len(frames))]
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True,
                                       gridspec_kw={"height_ratios": [3, 1]})
        ax1.plot(ts, res["levels"], lw=0.8, color="#58a6ff", label="level (p95 tail)")
        if res["thr"] is not None:
            ax1.axhline(res["thr"], color="#f85149", ls="--", lw=1, label=f"threshold {res['thr']:.3f}")
        runs = []
        start = None
        for k, st in enumerate(res["states"]):
            if st == "ACTIVE" and start is None:
                start = ts[k]
            elif st != "ACTIVE" and start is not None:
                runs.append((start, ts[k]))
                start = None
        if start is not None:
            runs.append((start, ts[-1]))
        for a, b in runs:
            ax1.axvspan(a, b, color="#f85149", alpha=0.15)
        ax1.set_ylabel("decision level")
        ax1.set_title("CSI motion analysis")
        ax1.legend(loc="upper right", fontsize=8)
        rssis = [r for _t, _a, r in frames]
        ax2.plot(ts, rssis, lw=0.6, color="#3fb950")
        bx = [ts[k] for k in range(min(len(ts), len(res["bad"]))) if res["bad"][k]]
        by = [rssis[k] for k in range(min(len(ts), len(res["bad"]))) if res["bad"][k]]
        ax2.plot(bx, by, "r.", ms=2, label="AGC-transient frames")
        ax2.set_ylabel("RSSI dBm")
        ax2.set_xlabel("time s")
        ax2.legend(loc="upper right", fontsize=8)
        fig.tight_layout()
        fig.savefig(args.plot, dpi=110)
        print(f"wrote {args.plot}")


if __name__ == "__main__":
    main()
