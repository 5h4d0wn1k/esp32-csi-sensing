# Sample session

An anonymized 60-second recording of real CSI frames from the router-
illuminated setup (64-subcarrier LLTF, ~94 fps, quiet room, no people
present). Use it to test the toolchain without hardware.

## Format

One JSON object per line:

```json
{"t": 1234, "amp": [0.123, ...], "rssi": -46}
```

| Field | Meaning |
|-------|---------|
| `t` | milliseconds since first frame |
| `amp` | 64 subcarrier amplitudes (LLTF, HT20) |
| `rssi` | frame RSSI in dBm |

No MAC addresses, SSIDs, or any other identifying data. Note that a fixed
room's amplitude pattern acts as a layout fingerprint; see docs/PRIVACY.md.

## Analyze it

```bash
python tools/analyze_session.py examples/sample_session/session.jsonl \
    --plot /tmp/session.png --json /tmp/session.json
```

Expected result on this file: threshold self-calibrates around ~0.25 (this
geometry has a higher floor than tighter setups - calibration adapts),
0% ACTIVE time, ~2% AGC-transient frames.

## Record your own

Use the viewer's Record button (exports the same JSONL format), then label
segments by hand and pass `--labels "10-20:walk,30-40:static"` to compare
detection accuracy per segment.
