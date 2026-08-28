# dorna_pipette

This is a dorna_pipette guide. You need the pipette, a 24 VDC supply, an RS-232
adapter, and Python.

---

## 1. What you need

| Item | Notes |
|---|---|
| Dorna pipette | |
| 24 VDC power supply | Sized for the pipette's peak plunger current — draw spikes during homing and tip eject. Check the pipette datasheet for the rating. |
| RS-232 serial adapter | USB-to-RS-232 is the usual choice. |
| Python 3.8+ | |

---

## 2. Wiring

The pipette cable carries four conductors. Two are power, two are serial data.

Both grounds return to the **power supply**. The pipette's V- and the adapter's
signal ground land on the supply's V- terminals — most supplies have several, and
they are all the same node internally, so any two will do. The RS-232 signal ground
has to sit at the same reference as the pipette's V- return; if it doesn't, the
pipette powers up normally but never replies.

![dorna_pipette wiring diagram](docs/wiring.svg)

### Connection list

```
  Pipette RED    (+24 VDC) ───────► Supply   V+
  Pipette BLACK  (GND)     ───────► Supply   V-
  Pipette GREEN  (RX)      ───────► Adapter  TX
  Pipette BLUE   (TX)      ───────► Adapter  RX

  Adapter GND              ───────► Supply   V-   (second V- terminal)
```

### Serial port settings

```
  38400 baud, 8 data bits, no parity, 1 stop bit (8N1)
  No hardware or software flow control
```

The driver sets this for you. The values are listed here for anyone testing the link
with a terminal program first.

---

## 3. Install

```bash
git clone https://github.com/JudeL12/dorna_pipette.git
cd dorna_pipette
pip install -e .
```

That installs the package and `pyserial`. For the bench-test notebook:

```bash
pip install -e ".[notebook]"
jupyter notebook notebooks/pipette_test.ipynb
```

---

## 4. Quick start

```python
from dorna_pipette import DornaPipette

# port: '/dev/ttyUSB0' on Linux, 'COM3' on Windows. addr: usually 1.
pip = DornaPipette("/dev/ttyUSB0", addr=1, steps_per_ul=5.0)
pip.connect()

pip.initialize()                # home the plunger — once per power-up
pip.has_tip()                   # True / False / None (None = no valid reply)
pip.aspirate(50)                # µL
pip.dispense(50, blowout=True)  # blowout clears residual liquid
pip.eject_tip()
pip.close()
```

Order of operations on a cold start: power up → `connect()` → `initialize()` → press a
tip on → aspirate / dispense → `eject_tip()`. Homing before any plunger move is required;
aspirate commands sent to an un-homed pipette will not behave predictably.

### API

| Method | Does |
|---|---|
| `connect(initialize=False)` | Open the port and handshake. Returns `False` on failure rather than raising. |
| `close()` | Close the port. |
| `status()` | Raw status string. |
| `is_idle()` | `True` when the plunger is not moving. |
| `has_tip()` | `True` / `False` / `None`. `None` means no valid reply — treat as "pipette unavailable", not "no tip". |
| `initialize(speed=16000)` | Home the plunger, keep the tip. |
| `eject_tip(speed=64000)` | Home and eject the tip. |
| `aspirate(volume_ul, speed=200)` | |
| `dispense(volume_ul, speed=500, blowout=False)` | |
| `send(cmd, verbose=False)` | Raw command, address prefix added for you. |

All motion methods block until the pipette reports idle and return `True` on success.

---

## 5. Protocol reference

ASCII over serial. Commands are terminated with `\r`. Replies are terminated with
`\r` **only** — there is no `\n`. Read with `read_until(b'\r')`; `readline()` will
block for the full serial timeout on every call.

| Action | Command | Reply |
|---|---|---|
| Query status | `{addr}>?` | `{addr}<0` idle, `{addr}<1` busy/moving |
| Initialize (home only) | `{addr}>It{speed},100,1` | `{addr}<2` accepted |
| Home + eject tip | `{addr}>It{speed},100,0` | `{addr}<2` accepted |
| Aspirate | `{addr}>Ia{steps},{speed},10` | `{addr}<2` accepted |
| Dispense | `{addr}>Da{steps},0,{speed},{stop_speed}` | `{addr}<2` accepted; high stop speed = blowout |
| Tip presence | `{addr}>Rr3` | `{addr}<2:1` tip on, `{addr}<2:0` no tip |

Errors: `{addr}<10` = parameter out of range. `{addr}<14` = invalid register.

---

## 6. Repo layout

- [dorna_pipette/pipette.py](dorna_pipette/pipette.py) — the driver (`DornaPipette`)
- [notebooks/pipette_test.ipynb](notebooks/pipette_test.ipynb) — interactive bench test:
  connect → home → tip check → aspirate/dispense → eject → soak test →
  raw command console
- [examples/basic_usage.py](examples/basic_usage.py) — minimal script
- [docs/wiring.svg](docs/wiring.svg) — wiring diagram
