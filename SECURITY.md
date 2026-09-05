# Security policy

Maintained by the **esp32-csi-sensing contributors** as part of the
wireless-security-toolkit umbrella.

## Supported versions

| Version               | Supported |
|-----------------------|-----------|
| `main` branch         | yes       |
| Tags / older commits  | no        |

Only the tip of `main` receives fixes; update your checkout before reporting.

## Reporting a vulnerability

Use **GitHub's private vulnerability reporting** (repository Security tab ->
"Report a vulnerability"). Do **not** open a public issue, discussion, or PR
for anything you believe is exploitable. Include: affected component, commit
hash, reproduction steps or PoC, observed vs expected behaviour, and your
severity assessment. Expect an acknowledgement within a few days and status
updates during triage.

## Scope

In scope:

- `tools/sensorhub.py` — WebSocket bridge (serial parsing, WS server)
- `tools/csi_3d_viewer.html` — browser viewer (WS client, replay, controls)
- `tools/csi_visualizer.py`, `tools/motion_detector.py` — offline analysis
- `firmware/` — `csi_send`, `csi_recv`, `csi_recv_router`,
  `csi_recv_router_oled` (modified ESP-IDF apps)
- CI/build scripts under `.github/` and `scripts/`

Out of scope: bugs in upstream `esp-csi`/ESP-IDF (report upstream; we track
fixes), issues requiring physical access to reflash a board, and generic
RF-side Wi-Fi/ESP-NOW attacks (see `docs/CAPABILITIES.md` §4.9).

## Disclaimer

This project is a **research tool**, not a certified security product. It has
not been independently audited or evaluated against any security standard, and
its sensing output is probabilistic with documented limits
(`docs/CAPABILITIES.md` §5). Do not rely on it to protect life, property, or
production systems.

## Coordinated disclosure

We follow a **90-day disclosure** policy: reports are acknowledged, fixed, and
disclosed within 90 days of submission wherever possible. Reporters are
credited unless they ask to remain anonymous.
