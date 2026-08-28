"""Standalone serial driver for the Dorna pipette.

Serial protocol (38400 baud, 8N1, ASCII):

    Command                       Reply
    -------------------------     ---------------------------------------------
    {addr}>?                      {addr}<0 idle, {addr}<1 busy, {addr}<2 accepted
    {addr}>It{speed},100,1        home only (keeps tip)
    {addr}>It{speed},100,0        home + eject tip
    {addr}>Ia{steps},{speed},10   aspirate
    {addr}>Da{steps},0,{speed},{stop_speed}   dispense (high stop speed = blowout)
    {addr}>Rr3                    tip presence: {addr}<2:1 tip on, {addr}<2:0 no tip

Commands are terminated with '\\r'. Replies are terminated with '\\r' ONLY
(no '\\n'), so reads must use read_until(b'\\r') — readline() blocks until
the serial timeout on every call.

Error replies: {addr}<10 = parameter out of range, {addr}<14 = invalid register.
"""

import time
from typing import Optional

import serial


class DornaPipette:
    """Driver for one Dorna pipette on a serial port.

    Args:
        port: serial port, e.g. '/dev/ttyUSB0' or 'COM3'. On Linux, prefer
            a stable /dev/serial/by-id/... path — USB adapters can
            re-enumerate between sessions.
        addr: device address (fresh units are usually 1).
        steps_per_ul: plunger calibration — depends on the barrel size,
            e.g. a 1 mL barrel with a 5000-step full stroke = 5 steps/µL.
            Verify with a gravimetric check before precision work.
    """

    def __init__(
        self,
        port: str,
        addr: int = 1,
        baud: int = 38400,
        steps_per_ul: float = 5.0,
    ):
        self.port = port
        self.addr = addr
        self.baud = baud
        self.steps_per_ul = steps_per_ul
        self.ser: Optional[serial.Serial] = None

    # ==================================================
    # Connection lifecycle
    # ==================================================

    def is_connected(self) -> bool:
        return self.ser is not None and self.ser.is_open

    def connect(self, initialize: bool = False) -> bool:
        """Open the port and handshake.

        Set initialize=True to also home the plunger once connected.
        """
        if self.is_connected():
            return True

        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=2)
        except serial.SerialException:
            self.ser = None
            return False

        if not self._handshake():
            self.close()
            return False

        if initialize:
            return self.initialize()
        return True

    def close(self) -> None:
        if self.ser:
            try:
                self.ser.close()
            finally:
                self.ser = None

    def __enter__(self) -> "DornaPipette":
        if not self.connect():
            raise ConnectionError(
                f"Could not connect to pipette "
                f"(port={self.port!r}, addr={self.addr})"
            )
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _handshake(self) -> bool:
        return self._send("?").startswith(f"{self.addr}<")

    # ==================================================
    # Low-level I/O
    # ==================================================

    def send(self, cmd: str, verbose: bool = False) -> str:
        """Send a raw command (the part AFTER '{addr}>', e.g. '?' or 'Rr3')
        and return the raw reply. Useful for poking at the protocol.
        """
        return self._send(cmd, verbose=verbose)

    def _send(self, cmd: str, verbose: bool = False) -> str:
        if not self.is_connected():
            return ""
        try:
            full = f"{self.addr}>{cmd}\r"
            self.ser.reset_input_buffer()
            self.ser.write(full.encode("ascii"))
            # Replies end with '\r' only (no '\n') — readline() would
            # block for the full serial timeout on every call.
            resp = (
                self.ser.read_until(b"\r").decode("ascii", errors="ignore").strip()
            )
            if verbose:
                print(f">> {full.strip()!r}   << {resp!r}")
            return resp
        except serial.SerialException:
            self.close()
            return ""

    def _wait_until_idle(self, timeout: float = 15.0) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            if self._send("?").startswith(f"{self.addr}<0"):
                return True
            time.sleep(0.2)
        return False

    # ==================================================
    # Public device API
    # ==================================================

    def status(self) -> str:
        """Raw status reply: '{addr}<0' idle, '{addr}<1' busy/moving."""
        return self._send("?")

    def is_idle(self) -> bool:
        return self.status().startswith(f"{self.addr}<0")

    def has_tip(self) -> Optional[bool]:
        """Tip-presence register read.

        Returns True/False only from a VALID response; None when the
        pump gave no / unparseable response. A silent False on a dead
        serial line would be indistinguishable from a real "no tip" —
        None lets callers say "pipette unavailable" instead of lying.
        """
        # Reply is "{addr}<...:{value}" — the value after the last colon
        # is tip presence (1 = tip on, 0 = no tip), e.g. "1<2:0"/"1<2:1".
        resp = self._send("Rr3")
        if not resp.startswith(f"{self.addr}<") or ":" not in resp:
            return None
        value = resp.rsplit(":", 1)[-1]
        if value not in ("0", "1"):
            return None
        return value == "1"

    def initialize(self, speed: int = 16000) -> bool:
        """Home the plunger (mode 1 = home only, keeps tip).

        Run once after power-up, before any aspirate/dispense.
        """
        res = self._send(f"It{speed},100,1")
        return f"{self.addr}<2" in res and self._wait_until_idle()

    def eject_tip(self, speed: int = 64000) -> bool:
        """Home + eject tip (mode 0)."""
        res = self._send(f"It{speed},100,0")
        return f"{self.addr}<2" in res and self._wait_until_idle()

    def aspirate(self, volume_ul: float, speed: int = 200) -> bool:
        steps = int(volume_ul * self.steps_per_ul)
        res = self._send(f"Ia{steps},{speed},10")
        return f"{self.addr}<2" in res and self._wait_until_idle()

    def dispense(
        self,
        volume_ul: float,
        speed: int = 500,
        blowout: bool = False,
    ) -> bool:
        """Dispense. blowout=True uses a high stop speed to push out
        residual liquid — use it on the final dispense of a transfer.
        """
        steps = int(volume_ul * self.steps_per_ul)
        stop_spd = 500 if blowout else 10
        res = self._send(f"Da{steps},0,{speed},{stop_spd}")
        return f"{self.addr}<2" in res and self._wait_until_idle()
