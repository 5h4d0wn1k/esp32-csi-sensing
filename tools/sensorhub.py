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
  {"src":"nodemcu","kind":"csi","mac":"00:17:7c:74:1d:35","rssi":-51,"ch":6,"nsub":64,"amp":[...]}

Supported CSI line formats (auto-detected by presence of a MAC in field 2):
  csi_recv_router (ESP32, joins AP + pings it):  CSI_DATA,<len>,<mac>,<rssi>,<rate>,...,<ch>,...,"<data>"
  csi_recv (ESP32, ESP-NOW):                     CSI_DATA,<len>,<rssi>,<rate>,...,<ch>,...,"<data>"
Any even subcarrier count >= 32 is accepted (64 for LLTF router capture,
192 for the ESP-NOW HT40 link).

Usage:
  python sensorhub.py -p 8765 -s /dev/ttyUSB0:921600       # serve WS on 8765
  (serve the tools dir separately with: python -m http.server 8000)
"""
import argparse
import asyncio
import glob
import json
import logging
import math
import re
import threading

log = logging.getLogger("hub")

RE_CSI = re.compile(
    r'CSI_DATA,(-?\d+),([0-9a-f:]+),(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+),'
    r'(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+),'
    r'(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+),"(\[[^\]]*\])"')


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
        import time
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
    args = ap.parse_args()
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
            await ws.wait_closed()
        finally:
            clients.discard(ws)
            log.info("client left (%d total)", len(clients))

    async def serve_ws():
        async with websockets.serve(handler, "127.0.0.1", args.ws_port):
            log.info("WS on ws://127.0.0.1:%d", args.ws_port)
            await asyncio.Future()

    tasks = [asyncio.create_task(serve_ws())]
    for src in sources:
        tasks.append(asyncio.create_task(src.stream(broadcast)))
        log.info("source '%s' streaming", src.name)
    await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    import time
    import websockets
    asyncio.run(main())
