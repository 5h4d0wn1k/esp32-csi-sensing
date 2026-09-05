#!/usr/bin/env python3
"""sensorhub.py — WebSocket bridge for CSI (and future RF) sensors.

Streams raw sensor data from any connected source to browsers over WebSocket,
so the HTML viewer works in any browser (no Web Serial needed).

The blocking serial I/O runs in a dedicated thread; parsed frames are handed
to the asyncio loop, so the loop stays free to serve WebSocket clients.

Sources (add more here — this is the registry):
  serial-csi : reads CSI_DATA CSV lines from an ESP32 `csi_recv` serial port
               (e.g. /dev/ttyUSB0 at 921600 baud)

Client protocol (JSON, one object per line over the WS):
  {"src":"nodemcu","kind":"csi","mac":"<AP_MAC>","rssi":-51,"ch":6,"nsub":64,"amp":[...]}

Supported CSI line formats (auto-detected by presence of a MAC in field 2):
  csi_recv_router (ESP32, joins AP + pings it):  CSI_DATA,<len>,<mac>,<rssi>,<rate>,...,<ch>,...,"<data>"
  csi_recv (ESP32, ESP-NOW):                     CSI_DATA,<len>,<rssi>,<rate>,...,<ch>,...,"<data>"
Any even subcarrier count >= 32 is accepted (64 for LLTF router capture,
192 for the ESP-NOW HT40 link).

Usage:
  python sensorhub.py -p 8765 -s /dev/ttyUSB0:921600       # serve WS on 8765
  python sensorhub.py --detector --oled                    # + motion detect, OLED cmds
  (serve the tools dir separately with: python -m http.server 8000)

With --detector the hub also publishes (on state change + every 1 s):
  {"type":"motion","state":"ACTIVE"|"INACTIVE","level":x,"thr":y,"fps":z}
and accepts {"cmd":"recal"} from clients to reset the calibration baseline.
--oled additionally writes b"M1\\n"/b"M0\\n" on state change plus periodic
b"F<fps>\\n" / b"R<rssi>\\n" lines down the serial link (ESP32 OLED driver).
"""
import argparse
import asyncio
import glob
import json
import logging
import math
import re
import threading
import time

log = logging.getLogger("hub")

RE_CSI = re.compile(
    r'CSI_DATA,(-?\d+),([0-9a-f:]+),(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+),'
    r'(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+),'
    r'(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+),"(\[[^\]]*\])"')

# ---- host-side motion detector (exact port of csi_3d_viewer.html runMotion) ----
MVAR_MS, MCAL_MS, M_THR_RATIO = 1500, 5000, 1.5
M_ON, M_OFF, M_LEVEL_Q, M_TRANSIENT_DB = 1.0, 3.0, 0.95, 2.0


class MotionDetector:
    """Gain-normalized shape-deviation detector (port of the viewer's
    runMotion/rollingStd/quantile incl. RSSI-jump bad-frame window and
    tUp/tDown hysteresis)."""

    def __init__(self):
        self.state, self.t_up, self.t_down = "INACTIVE", 0.0, 0.0
        self.thr, self.cal, self.cal0 = None, [], 0.0
        self.var_hist, self.ring, self.hist, self.frames = [], [], [], []

    @staticmethod
    def _quantile(arr, q):
        if len(arr) < 8:
            return None
        srt = sorted(arr)
        return srt[min(len(srt) - 1, int(len(srt) * q))]

    @staticmethod
    def _rolling_std(hist, now, win_ms):
        cutoff = now - win_ms
        i = len(hist) - 1
        while i >= 0 and hist[i][0] > cutoff:
            i -= 1
        sub = hist[i + 1:]
        if len(sub) < 8:
            return None
        mean = sum(v for _, v in sub) / len(sub)
        return math.sqrt(sum((v - mean) ** 2 for _, v in sub) / len(sub))

    def recalibrate(self):
        self.state, self.t_up, self.t_down = "INACTIVE", 0.0, 0.0
        self.thr, self.cal, self.cal0 = None, [], 0.0
        self.var_hist, self.ring = [], []

    def update(self, amp, rssi, now):
        """Feed one frame; now is a ms timestamp. Returns (level, thr)."""
        self.frames.append(amp)
        if len(self.frames) > 150:
            self.frames.pop(0)
        if len(self.frames) < 2:
            return None, None
        win = self.frames[-min(30, len(self.frames)):]
        mag = lambda f: sum(f) / len(f) + 1e-6
        win_mag = [mag(f) for f in win]
        cur_mag = mag(amp)
        nsub = len(amp)
        base = [0.0] * nsub
        for k, f in enumerate(win):
            inv = 1.0 / win_mag[k]
            for s in range(nsub):
                base[s] += f[s] * inv
        acc = 0.0
        for s in range(nsub):
            base[s] /= len(win)
            acc += abs(amp[s] / cur_mag - base[s])
        dev = acc / nsub
        # AGC transient rejection: an RSSI jump > M_TRANSIENT_DB between any two
        # consecutive frames around the candidate invalidates it; each frame is
        # only committed once jumps at [idx-3, idx+2] are known.
        self.ring.append([now, rssi, dev])
        if len(self.ring) > 12:
            self.ring.pop(0)
        if len(self.ring) >= 4:
            c = self.ring[-4]
            bad = False
            if c[1] is not None:
                for j in range(max(1, len(self.ring) - 7), len(self.ring) - 1):
                    a, b = self.ring[j][1], self.ring[j - 1][1]
                    if a is not None and b is not None and \
                            abs(a - b) > M_TRANSIENT_DB:
                        bad = True
                        break
            if not bad:
                self.hist.append((c[0], c[2]))
                if len(self.hist) > 4000:
                    self.hist.pop(0)
        var_dev = self._rolling_std(self.hist, now, MVAR_MS)
        if var_dev is not None:
            self.var_hist.append(var_dev)
            if len(self.var_hist) > 600:
                self.var_hist.pop(0)
        level = self._quantile(self.var_hist, M_LEVEL_Q)
        if self.thr is None:
            if level is not None:
                self.cal.append(level)
            if self.cal0 == 0.0:
                self.cal0 = now
            if len(self.cal) >= 40 and now - self.cal0 >= MCAL_MS:
                self.thr = self._quantile(self.cal, 0.9) * M_THR_RATIO
            return level, self.thr
        if level is not None and level > self.thr:
            self.t_up = now
        else:
            self.t_down = now
        if self.state == "INACTIVE" and now - self.t_down >= M_ON * 1000:
            self.state = "ACTIVE"
        if self.state == "ACTIVE" and now - self.t_up >= M_OFF * 1000:
            self.state = "INACTIVE"
        return level, self.thr


class SerialCsiSource:
    name = "nodemcu"

    def __init__(self, dev, baud):
        self.dev, self.baud = dev, baud
        self.ser = None
        self.q = None
        self._loop = None

    def connect(self):
        import serial
        try:
            self.ser = serial.Serial(self.dev, self.baud, timeout=1)
            log.info("opened %s @ %d", self.dev, self.baud)
            return True
        except Exception as e:
            log.warning("cannot open %s: %s", self.dev, e)
            return False

    def write_line(self, data):
        """Best-effort command write back down the serial link (OLED etc.)."""
        if self.ser is None:
            return
        try:
            self.ser.write(data)
            self.ser.flush()
        except Exception as e:
            log.warning("serial write %r failed: %s", data, e)

    def _parse(self, line):
        line = line.replace(b"\x00", b"")
        m = RE_CSI.match(line.decode("utf-8", "replace"))
        if not m:
            return None
        g = m.groups()
        vals = [int(x) for x in re.findall(r"-?\d+", g[23])]
        if len(vals) < 2:
            return None
        has_mac = ":" in g[1]
        if has_mac:                       # csi_recv_router: CSI_DATA,<id>,<mac>,<rssi>,...<ch>,...
            mac, rssi, ch = g[1], int(g[2]), int(g[15])
        else:                             # legacy csi_recv: CSI_DATA,<id>,<rssi>,<rate>,...<ch>,...
            mac, rssi, ch = None, int(g[2]), int(g[15])
        n = len(vals) // 2 * 2
        if n // 2 < 32:  # drop truncated glitch frames, keep 64/128/192-subcarrier frames
            return None
        amp = []
        ph = []
        for i in range(0, n, 2):
            im, rl = vals[i], vals[i + 1]
            amp.append(int((im * im + rl * rl) ** 0.5))
            ph.append(int(math.degrees(math.atan2(rl, im))))
        return {"src": self.name, "kind": "csi",
                "mac": mac, "rssi": rssi, "ch": ch,
                "nsub": len(amp), "amp": amp, "ph": ph}

    def _reader(self):
        """Blocking serial read loop, runs in a dedicated thread."""
        buf = b""
        while True:
            try:
                data = self.ser.read(4096)
                if not data:
                    continue
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    item = self._parse(line)
                    if item is not None and self._loop and self.q is not None:
                        try:
                            self._loop.call_soon_threadsafe(self._safe_put, item)
                        except Exception:
                            pass
            except Exception as e:
                log.exception("serial error (reconnecting): %s", e)
                try:
                    self.ser.close()
                except Exception:
                    pass
                while not self.connect():
                    time.sleep(2)
                buf = b""

    def _safe_put(self, item):
        try:
            self.q.put_nowait(item)
        except asyncio.QueueFull:
            pass

    async def stream(self, broadcast):
        self.q = asyncio.Queue(maxsize=4096)
        self._loop = asyncio.get_running_loop()
        threading.Thread(target=self._reader, name=f"ser-{self.name}",
                         daemon=True).start()
        while True:
            item = await self.q.get()
            await broadcast(item)


def detect_serial():
    """Auto-find an ESP32 on /dev/ttyUSB* / /dev/ttyACM* (best effort)."""
    for pat in ("/dev/ttyUSB*", "/dev/ttyACM*"):
        for d in glob.glob(pat):
            yield d, 921600


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-p", "--ws-port", type=int, default=8765)
    ap.add_argument("-s", "--serial", action="append", default=[],
                    help="dev:baud pairs (repeatable); default: autodetect")
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--detector", action="store_true",
                    help="host-side motion detection; publishes motion events on the WS")
    ap.add_argument("--oled", action="store_true",
                    help="write M0/M1/F/R command lines to serial (implies --detector)")
    args = ap.parse_args()
    if args.oled:
        args.detector = True
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    pairs = [tuple(s.split(":")) if ":" in s else (s, 921600) for s in args.serial]
    if not pairs:
        pairs = list(detect_serial())
        log.info("autodetect serial candidates: %s", pairs)

    sources = []
    for dev, baud in pairs:
        src = SerialCsiSource(dev, int(baud))
        if src.connect():
            sources.append(src)

    clients = set()

    async def broadcast(msg):
        payload = json.dumps(msg)  # text frame — browsers expect string in ev.data
        if not clients:
            await asyncio.sleep(0)
            return
        for ws in list(clients):
            try:
                await ws.send(payload)
            except Exception:
                clients.discard(ws)

    async def handler(ws):
        clients.add(ws)
        log.info("client connected (%d total)", len(clients))
        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except Exception:
                    continue
                if isinstance(msg, dict) and msg.get("cmd") == "recal":
                    if det is not None:
                        det.recalibrate()
                        latest["thr"] = latest["level"] = None
                        latest["state"] = det.state
                        log.info("motion recalibration requested over WS")
        finally:
            clients.discard(ws)
            log.info("client left (%d total)", len(clients))

    det = MotionDetector() if args.detector else None
    det_nsub = None                    # lock onto first frame's subcarrier count
    latest = {"rssi": None, "level": None, "thr": None,
              "state": "INACTIVE", "fps": 0}
    fps_win = [0, None]                # frame count, window start (ms)
    oled_last = [0.0, 0.0]             # last F write, last R write (monotonic s)

    def serial_cmd(data):
        for src in sources:
            src.write_line(data)

    async def feed(item):
        nonlocal det_nsub
        amp = item.get("amp")
        if det is not None and amp:
            if det_nsub is None:
                det_nsub = len(amp)
            if len(amp) == det_nsub:   # mirror viewer: fixed N_SUB stream
                now = time.monotonic() * 1000.0
                if fps_win[1] is None:
                    fps_win[1] = now
                fps_win[0] += 1
                if now - fps_win[1] > 1000.0:
                    latest["fps"] = round(fps_win[0] * 1000.0 / (now - fps_win[1]))
                    fps_win[0], fps_win[1] = 0, now
                rssi = item.get("rssi")
                latest["rssi"] = rssi
                prev = det.state
                level, thr = det.update(amp, rssi, now)
                latest["level"], latest["thr"], latest["state"] = \
                    level, thr, det.state
                if thr is not None and det.state != prev:
                    await broadcast({"type": "motion", "state": det.state,
                                     "level": level, "thr": thr,
                                     "fps": latest["fps"]})
                    if args.oled:
                        serial_cmd(b"M1\n" if det.state == "ACTIVE" else b"M0\n")
                        oled_last[0] = oled_last[1] = time.monotonic()
        await broadcast(item)

    async def motion_reporter():
        last_hb = 0.0
        while True:
            await asyncio.sleep(0.25)
            now = time.monotonic()
            if now - last_hb >= 1.0:
                last_hb = now
                await broadcast({"type": "motion", "state": latest["state"],
                                 "level": latest["level"], "thr": latest["thr"],
                                 "fps": latest["fps"]})
            if args.oled:
                if now - oled_last[0] >= 5.0:
                    oled_last[0] = now
                    serial_cmd(b"F%d\n" % latest["fps"])
                if now - oled_last[1] >= 5.0:
                    oled_last[1] = now
                    if latest["rssi"] is not None:
                        serial_cmd(b"R%d\n" % latest["rssi"])

    async def serve_ws():
        async with websockets.serve(handler, "127.0.0.1", args.ws_port):
            log.info("WS on ws://127.0.0.1:%d", args.ws_port)
            await asyncio.Future()

    tasks = [asyncio.create_task(serve_ws())]
    if det is not None:
        tasks.append(asyncio.create_task(motion_reporter()))
    for src in sources:
        tasks.append(asyncio.create_task(src.stream(feed)))
        log.info("source '%s' streaming", src.name)
    await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    import websockets
    asyncio.run(main())
