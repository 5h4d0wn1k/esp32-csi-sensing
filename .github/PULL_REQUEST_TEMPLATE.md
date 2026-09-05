# Pull Request

## Description

<!-- What does this PR change and why? Link related issues. -->

## Hardware tested on

- Board (e.g. ESP32-DevKitC / ESP32-S3):
- Firmware variant:
- Host OS:

## How to verify

1. Flash the firmware variant above to the board.
2. Run `python tools/sensorhub.py` on the host and confirm a CSI stream connects.
3. Viewer smoke test: open `tools/csi_3d_viewer.html` in a browser, connect to the hub, and confirm points render / update without console errors.
4. If applicable: `python tools/analyze_session.py examples/sample_session/session.jsonl` exits 0.

## Checklist

- [ ] No personal data (SSID, MACs, paths, photos) — see docs/PRIVACY.md
- [ ] `scripts/check_viewer_js.sh` passes
- [ ] `analyze_session.py` smoke passes
- [ ] Docs updated
