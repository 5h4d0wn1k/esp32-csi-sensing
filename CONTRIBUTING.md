# Contributing to esp32-csi-sensing

Thanks for your interest in improving this project! This repo covers ESP32
Wi-Fi CSI capture firmware, a Python bridge/analysis toolchain, and a browser
3D viewer. Please read this guide and `docs/PRIVACY.md` before opening a PR.

## Development setup

- **ESP-IDF v5.5** — required to build the firmware under `firmware/`
  (targets: ESP32-C6 for the sender, classic ESP32 for receivers).
- **Python 3** (with a virtualenv):
  ```bash
  python -m venv .venv && source .venv/bin/activate
  pip install numpy matplotlib websockets
  ```
- **Node.js >= 18** — used by the viewer JS syntax check (`scripts/check_viewer_js.sh`).
- Linux is assumed for flashing (`/dev/ttyUSB0`, `/dev/ttyACM0`) and serial bridging.

## Repository layout

| Path         | Contents                                                        |
|--------------|-----------------------------------------------------------------|
| `tools/`     | Python bridge & offline analysis, plus the HTML/JS 3D viewer    |
| `firmware/`  | Modified `app_main.c` sources for the ESP-IDF example projects  |
| `docs/`      | Architecture, build notes, placement guide, privacy policy      |
| `scripts/`   | CI/dev helper scripts (e.g. `check_viewer_js.sh`)               |
| `examples/`  | Sample sessions and data for trying the tools end-to-end        |
| `.github/`   | PR template and GitHub Actions workflows                        |

## Pull request flow

1. Fork (or branch) and keep each PR focused on one change.
2. Open a draft early if you want feedback; use the PR template in `.github/`.
3. Describe **what** changed and **why**, including hardware tested where relevant.
4. Run the verification checklist below and note the results in the PR.
5. Update `docs/` if you change behavior, thresholds, or the build process.
6. A maintainer will review; squash-merge keeps history tidy.

## Style rules

- Match the conventions of the file you are editing (naming, structure,
  argument handling) rather than importing a new style.
- Keep comments minimal — explain *why* only where it is non-obvious.
- No new dependencies without discussion; prefer the standard library or
  what is already listed above.

## Verification checklist

Run these before every PR:

```bash
bash scripts/check_viewer_js.sh
python -m py_compile tools/*.py
python tools/analyze_session.py examples/sample_session/session.jsonl
```

All three must pass cleanly. If you touched firmware, also build it with
ESP-IDF v5.5 before submitting.

## Hardware-testing disclosure

If your change affects capture, parsing, or detection behavior, state in the
PR which hardware you validated on (board type, firmware variant, router vs
ESP-NOW mode) and how it was tested. Untested hardware-affecting changes may
be held back until someone reproduces your results.

## Privacy — hard rule

**NEVER commit personal data**: SSIDs, passwords, MAC addresses of personal
gear, home photos, or absolute paths from your machine. This applies to
captures, logs, screenshots, config files, and commit messages alike. See
`docs/PRIVACY.md` for the full policy — sanitize everything before pushing.
