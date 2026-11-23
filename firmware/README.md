# Firmware

Microcontroller code for the radar hardware. Planned:

- **Controller board** – drives the gantry steppers, sets the RF switch matrix (SP8T select lines),
  reads limit switches / temperature, and talks to the backend over UART/USB.
  Candidate MCUs: MSPM0G3507 (used in the MECH 421 labs) or STM32G4 (NUCLEO-G474RE).
- **Custom RF board (later)** – synthesizer + I/Q demodulator read by an STM32G4 (dual simultaneous ADCs),
  replacing the VNA.

Put each target in its own subfolder (e.g. `firmware/controller-mspm0/`, `firmware/rf-stm32g4/`).
The backend will get a driver for the controller's serial protocol next to `software/backend/app/vna/`.
