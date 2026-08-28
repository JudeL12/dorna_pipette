# dorna_pipette

Standalone driver and bench-test notebook for the **Dorna pipette** over serial.
No robot or workspace software required — just the pipette, its RS-232/USB
adapter, and Python.

## Install

```bash
git clone https://github.com/JudeL12/dorna_pipette.git
cd dorna_pipette
pip install -e .          # installs the package + pyserial
```

For the test notebook, also install Jupyter:

```bash
pip install -e ".[notebook]"
jupyter notebook notebooks/pipette_test.ipynb
```

> **Linux note:** your user needs serial-port access:
> `sudo usermod -a -G dialout $USER` (then log out/in).

## Quick start

```python
from dorna_pipette import DornaPipette

# port: '/dev/ttyUSB0' on Linux, 'COM3' on Windows. addr: usually 1.
pip = DornaPipette("/dev/ttyUSB0", addr=1, steps_per_ul=5.0)
pip.connect()

pip.initialize()               # home the plunger (once after power-up)
pip.has_tip()                  # True / False / None (no response)
pip.aspirate(50)               # µL
pip.dispense(50, blowout=True) # blowout pushes out residual liquid
pip.eject_tip()
pip.close()
```

Or as a context manager — see [examples/basic_usage.py](examples/basic_usage.py).

## Calibration

`steps_per_ul` depends on the barrel size:

| Barrel | Full stroke | steps/µL |
|---|---|---|
| 1 mL | 5000 steps | **5** (1 step = 0.2 µL) |

Over-range aspirate commands are rejected with `{addr}<10` and no motion.
The notebook includes a **gravimetric calibration cell** (dispense a known step
count into a tared vessel on a scale) — run it before precision work.

## Protocol reference

ASCII over serial, **38400 baud, 8N1**. Commands end with `\r`. Replies end with
`\r` only (no `\n`) — read with `read_until(b'\r')`, never `readline()`.

| Action | Command | Reply |
|---|---|---|
| Query status | `{addr}>?` | `{addr}<0` idle, `{addr}<1` busy/moving |
| Initialize (home only) | `{addr}>It{speed},100,1` | `{addr}<2` = accepted |
| Home + eject tip | `{addr}>It{speed},100,0` | `{addr}<2` = accepted |
| Aspirate | `{addr}>Ia{steps},{speed},10` | `{addr}<2` = accepted |
| Dispense | `{addr}>Da{steps},0,{speed},{stop_speed}` | `{addr}<2` = accepted; high stop speed = blowout |
| Tip presence | `{addr}>Rr3` | `{addr}<2:1` = tip on, `{addr}<2:0` = no tip |

Error replies: `{addr}<10` = parameter out of range, `{addr}<14` = invalid register.

## Troubleshooting

- **Connect fails** — check power and cable; confirm the adapter shows up
  (`ls /dev/ttyUSB*` on Linux, Device Manager on Windows); check dialout group membership.
- **No answer at address 1** — units previously daisy-chained over RS-485 keep their
  assigned address. Try other values for `addr` (0–15).
- **Port changes between sessions** — USB adapters can re-enumerate (`ttyUSB0` → `ttyUSB1`).
  On Linux, use the stable `/dev/serial/by-id/...` path instead.
- **Every read is slow or empty** — you're using `readline()` somewhere. Replies have no
  `\n`; the driver already handles this correctly.

## Repo layout

- [dorna_pipette/pipette.py](dorna_pipette/pipette.py) — the driver (`DornaPipette`)
- [notebooks/pipette_test.ipynb](notebooks/pipette_test.ipynb) — interactive bench test: connect → home → tip check → aspirate/dispense → eject → calibration → soak test → raw console
- [examples/basic_usage.py](examples/basic_usage.py) — minimal script
