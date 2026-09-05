# Privacy Policy & Publication Guide

Status: pre-publication audit for open-sourcing this repository.
Scope: end-user data handling, contributor rules, launch checklist, and the
findings of a full working-tree + git-history privacy audit (2026-08-21).

---

## 1. Data collected by this tool (end users)

**Everything stays on your hardware. There is no telemetry and no network egress.**

The data path is strictly local:

```
ESP32 receiver --USB serial--> host hub (sensorhub.py) --ws://127.0.0.1--> browser viewer
```

- The WebSocket bridge binds to `127.0.0.1` only (`tools/sensorhub.py`). Frames
  never leave the machine running the hub.
- The browser viewer fetches its JS libraries from local disk (`tools/lib/`,
  no CDN) and talks only to localhost. No analytics, no fonts, no external
  requests.
- The Python tools (`csi_visualizer.py`, `motion_detector.py`) read serial or
  local CSV files and write local PNG/CSV output. Nothing is uploaded.

**What a recorded session contains:** timestamps, per-subcarrier amplitude
(and raw phase), RSSI, channel, frame ID, and the source MAC of the
transmitter being sensed. That is all.

**Why this is non-identifying — and why you should still be careful:**

- No images, audio, text, or identity information is captured. The tool cannot
  answer "who", only "something moved".
- However, CSI/RSSI traces are *environmental fingerprints*. A long recording
  from a fixed room encodes that room's static multipath geometry (furniture,
  wall layout). In principle, captures from a known space can be matched to
  that space. Treat long recordings of your own home like you would treat a
  floor-plan scan.
- Practical guidance before sharing a capture publicly:
  - Prefer short synthetic/demo captures over long recordings of your home.
  - Scrub or rename files that encode location or date-of-capture meaning.
  - Remember the source-MAC column: replace real hardware MACs with dummy
    values (e.g. `1a:00:00:00:00:00`) before publishing captures.

## 2. Contributor privacy rules

Never commit any of the following to this repository:

| Never commit | Instead |
|---|---|
| Your Wi-Fi SSID or password (Airtel/Jio/home network names, `CONFIG_ESP_WIFI_PASSWORD` values) | `<YOUR_SSID>` placeholders; keep real values in `sdkconfig` (gitignored) |
| Photos/videos of your home, desk, or gear with identifying details (street view, labels, ISP equipment) | Neutral bench photos or diagrams |
| MAC addresses of your personal routers/devices | Dummy locally-administered MACs (`1a:xx:xx...` or `<RX_MAC>`) |
| Absolute home paths (`/home/<user>/...`) | `~/...` relative paths |
| Personal email addresses in configs, logs, or docs | Project contact via GitHub, noreply address only |
| Real names in code comments, commit trailers, or sample data | Pseudonymous handle only |

**Pre-commit scan (run before every push):**

```bash
# quick keyword sweep (should return nothing)
git grep -n -i -E "airtel|xstream|jiofi|digisol|DHR-[0-9]+|cynik|/home/[a-z]|password=|passwd|secret" -- . ':!tools/lib'

# real MAC sweep (allow-list the Espressif example MAC 1a:00:00:00:00:00)
git grep -n -E "([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}" -- . ':!tools/lib' | grep -v "1a:00:00:00:00:00"

# full-history secret scan (install: pip install gitleaks || brew install gitleaks)
gitleaks detect --source . --redact
# or: trufflehog filesystem --directory=. --only-verified
```

Consider adding a `.gitleaks.toml` allowlist for `tools/lib/` (vendored
Three.js) and enabling the gitleaks GitHub Action once public.

## 3. Launch checklist (going public)

The current git history **cannot be published as-is**: the strings
`Airtel_Xstream`, `Digisol DHR-3400`, and the AP MAC `00:17:7c:74:1d:35`
appear in blobs across at least 10 commits (from `c442a66` through `HEAD`),
in `README.md`, `docs/PLACEMENT.md`, `docs/VISUALIZATION.md`,
`firmware/README.md`, and `tools/sensorhub.py`. Rewriting 10+ commits with
`filter-repo` is error-prone; a fresh history is cleaner and loses nothing
(the project is young).

- [ ] Apply the replacements in Appendix 4 to the working tree (maintainer applies centrally).
- [ ] Set author identity to noreply **before** the clean commit:
      `git config user.name "5h4d0wn1k"` and
      `git config user.email "5h4d0wn1k@users.noreply.github.com"`
      (current history already uses the noreply address — keep it that way).
- [ ] Create a fresh single-commit history:
      ```bash
      git checkout --orphan public-v1
      git add -A && git commit -m "esp32-csi-sensing v1.0.0: ESP32 Wi-Fi CSI capture, 3D visualization, motion detection"
      git branch -M main public-v1   # replaces old main
      ```
      (or push the orphan branch to a brand-new repo; either way the old
      objects must not be pushed).
- [ ] Verify the final tree AND the new history:
      ```bash
      gitleaks detect --source . --redact
      git grep -n -i -E "airtel|xstream|digisol|00:17:7c" $(git rev-list --all)
      ```
- [ ] Add MIT `LICENSE` (planned) and reference it in `README.md`.
- [ ] Remove the stale status line "Repo is private; will be made public on request" (README.md:9).
- [ ] Decide on the umbrella-toolkit link (README.md:8): keeping
      `github.com/5h4d0wn1k/...` publishes the pseudonym by design — confirm
      that is intended before going public.
- [ ] Repo description suggestion:
      *"Wi-Fi CSI (channel state information) sensing with ESP32: raw capture, live 3D visualization, room-scale motion/presence detection — no camera, no telemetry."*
- [ ] Topics: `wifi-sensing` `csi` `esp32` `esp32-csi` `surveillance`
      `physical-security` `security-research` `rf-sensing` `motion-detection`
      `privacy`.
- [ ] Release flow: tag `v1.0.0` on the clean initial commit; attach the sample
      capture CSV and rendered PNGs as release assets; enable GitHub Discussions
      for Q&A and keep Issues enabled for bugs (or Issues off + Discussions
      only while the project is single-maintainer).
- [ ] After publication: delete/rename the old local branch so stale objects
      are never pushed accidentally; consider `git gc --aggressive` locally.

## 4. Findings appendix (audit 2026-08-21)

Replacements below are applied centrally by the maintainer; nothing was edited
during the audit. Non-findings verified clean: sample CSV uses only the
Espressif example MAC `1a:00:00:00:00:00`; PNGs carry no EXIF/GPS (Matplotlib
software tag only); all `127.0.0.1` references are localhost-only; `/dev/tty*`
paths are generic; firmware `.c` files are unmodified upstream Espressif code;
no emails, phone numbers, or real names anywhere; commit messages contain no
sensitive strings.

| # | Location | Snippet | Required replacement |
|---|---|---|---|
| 1 | `README.md:13` | `Digisol DHR-3400 (Airtel_Xstream, ch6)` | `any consumer AP (<YOUR_SSID>, ch6)` |
| 2 | `README.md:9` | `Repo is **private**; will be made public on request.` | delete line (stale pre-publication status) |
| 3 | `README.md:8` | `https://github.com/5h4d0wn1k/wireless-security-toolkit` | keep only if publishing the pseudonym is intended; else remove link |
| 4 | `docs/PLACEMENT.md:24` | `joins the AP (Airtel_Xstream, ch6)` | `joins the AP (<YOUR_SSID>, ch6)` |
| 5 | `docs/VISUALIZATION.md:56` | `joins **Airtel_Xstream** (open network, ch6)` | `joins **<YOUR_SSID>** (open network, ch6)` |
| 6 | `docs/VISUALIZATION.md:58` | `sensing the Digisol AP \`00:17:7c:74:1d:35\`` | `sensing the AP \`<RX_MAC>\`` |
| 7 | `tools/sensorhub.py:15` | `"mac":"00:17:7c:74:1d:35"` (docstring example) | `"mac":"<RX_MAC>"` or `1a:00:00:00:00:00` |
| 8 | `firmware/README.md:9` | `` `CONFIG_ESP_WIFI_SSID` = Airtel_Xstream, `CONFIG_ESP_WIFI_PASSWORD` set `` | `` `CONFIG_ESP_WIFI_SSID` = <YOUR_SSID>, credentials set via sdkconfig (never committed) `` |
| 9 | `docs/CAPABILITIES.md:46` *(untracked — will enter history when committed)* | `here: the Digisol router, ch6` | `here: the consumer AP, ch6` |

**History exposure:** items 1, 4–8 exist in committed blobs across ≥10 commits
(`c442a66`…`53e970e`); author/committer metadata is
`5h4d0wn1k <89957987+5h4d0wn1k@users.noreply.github.com>` (already noreply —
safe). This is why Section 3 mandates a fresh orphan-history publication.
