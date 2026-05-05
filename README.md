# 🔬 Incubot

**Incubot** is a robotic microscopy device built from a deconstructed 3D printer frame, designed to autonomously image cells in a standard 96-well plate. It uses a Raspberry Pi 5 as the main controller, a Pi Camera Module for imaging, an Arduino for motion control via G-code, and a PyQt-based graphical interface for operation.

This is an ongoing research/engineering project, designed to be picked up and extended by future students.

> **GitHub:** [https://github.com/DavidDaCoder12/Incubot](https://github.com/DavidDaCoder12/Incubot)

---

## Table of Contents

- [Project Overview & Goals](#project-overview--goals)
- [Hardware Components](#hardware-components)
- [Software & Tech Stack](#software--tech-stack)
- [Repository Structure](#repository-structure)
- [How It Works](#how-it-works)
- [Setup & Installation](#setup--installation)
- [Running the Application](#running-the-application)
- [Known Issues & Current Limitations](#known-issues--current-limitations)
- [Future Work](#future-work)
- [Contributing](#contributing)

---

## Project Overview & Goals

The goal of Incubot is to automate microscopy of biological cells grown in a standard 96-well plate. Rather than manually positioning a microscope over each well, Incubot uses a repurposed 3D printer motion system to navigate the XY plane and a motorized Z-axis for focusing.

**What currently works:**
- Navigate to any selected well in a 96-well plate via a graphical well-grid interface
- Coarse and fine Z-axis movement for focusing
- Live camera preview
- Image capture and saving
- LED illumination control
- Preset saving and loading for well configurations
- Z-axis and tilt calibration routines

**End goal (not yet complete):**
- Fully automated time-lapse imaging — visit a predefined set of wells at regular intervals, auto-focus, and save images without human intervention

---

## Hardware Components

| Component | Details |
|---|---|
| Motion System | Deconstructed FDM 3D printer (XYZ axes) |
| Motion Controller | Arduino (G-code over serial) |
| Single Board Computer | Raspberry Pi 5 |
| Camera | Raspberry Pi Camera Module |
| Illumination | LED (controlled via `led_control.py`) |
| Sample Format | Standard 96-well plate |

> **Note for future students:** The 3D printer's extruder and heated bed have been removed. The print head mount has been replaced with the camera and lens assembly. The Z-axis is used exclusively for focusing, not for printing.

---

## Software & Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| GUI Framework | PyQt5 (Qt Designer `.ui` files + generated Python) |
| Motion Commands | G-code sent over serial |
| Serial Communication | `pySerial` |
| Image Capture & Processing | `OpenCV` (`cv2`) |
| Numerical Operations | `NumPy` / `SciPy` |
| Packaging | PyInstaller (`main.spec`) |
| SBC OS | Raspberry Pi OS (64-bit) |

---

## Repository Structure

```
Incubot/
├── main.py                   # Entry point — launches the application
├── main_window.py            # Main GUI window logic
├── qt_Incubot.ui             # Qt Designer UI file for main window
├── ui_mainwindow.py          # Auto-generated Python from qt_Incubot.ui
├── qt_update.py              # Handles live UI updates
│
├── camera_actions.py         # Image capture logic
├── camera_preview.py         # Live camera preview stream
│
├── movement_control.py       # G-code motion commands (XY + Z)
├── led_control.py            # LED illumination control
│
├── imaging_script.py         # Core imaging logic
├── imaging_worker.py         # Background thread for imaging operations
│
├── experiment_dialog.py      # Experiment setup dialog logic
├── ui_experiment_dialog.py   # Auto-generated Python from experiment dialog UI
├── ui_experiment_dialog.ui   # Qt Designer UI file for experiment dialog
│
├── tilt_calibration.py       # Tilt calibration routine
├── z_calibration.npy         # Stored Z-axis calibration data (NumPy array)
│
├── parameters.py             # System parameters and configuration
├── parameters.log            # Log of parameter changes
│
├── presets.py                # Preset management logic
├── presets/                  # Saved well-selection presets
├── images/                   # Captured images output directory
│
├── well_grid_widget.py       # Interactive 96-well plate grid widget
├── update_save.py            # Save/load state logic
│
├── main.spec                 # PyInstaller build spec
├── pyvenv.cfg                # Virtual environment config
├── lib/python3.11/           # Vendored Python packages
├── build/ dist/ bin/         # Build artifacts (do not edit)
└── __pycache__/              # Python cache (do not edit)
```

---

## How It Works

### 1. GUI & Well Selection
The application launches via `main.py`, opening a PyQt5 main window (`main_window.py`, `qt_Incubot.ui`). The central widget is an interactive 96-well plate grid (`well_grid_widget.py`) where the user can click wells to select imaging targets. Well configurations can be saved and reloaded as presets via `presets.py`.

### 2. Motion Control
When a well is selected, `movement_control.py` calculates the corresponding XY motor coordinates based on the physical layout of the 96-well plate (9 mm well spacing, A1–H12 layout) and sends the appropriate G-code command to the Arduino over serial. The Arduino translates these into stepper motor movements.

### 3. Z-Axis Focusing
The Z-axis is used exclusively for focusing. There are two movement modes:
- **Coarse** — large Z steps to get into the approximate focal plane
- **Fine** — small Z steps for precise focus adjustment

Z calibration data is stored in `z_calibration.npy` (a NumPy array) and is loaded at startup. A tilt calibration routine (`tilt_calibration.py`) compensates for any physical tilt in the well plate mount.

### 4. Illumination
`led_control.py` manages the LED illumination. The LED can be toggled and adjusted to suit imaging conditions.

### 5. Image Capture
Once positioned and focused, `camera_actions.py` captures a frame from the Pi Camera via OpenCV and saves it to the `images/` directory. A live preview is provided by `camera_preview.py` so the user can visually confirm focus before capturing.

### 6. Experiment Setup & Imaging Worker
The experiment dialog (`experiment_dialog.py`) allows the user to define imaging parameters — which wells to visit, imaging intervals, and so on. `imaging_worker.py` runs the imaging loop in a background thread to keep the GUI responsive. The interval-based automation is a work in progress — see [Known Issues](#known-issues--current-limitations).

---

## Setup & Installation

### Prerequisites
- Raspberry Pi 5 running Raspberry Pi OS (64-bit)
- Arduino flashed with a G-code-compatible firmware (e.g. Marlin)
- Raspberry Pi Camera Module physically connected
- Python 3.11

### 1. Clone the Repository
```bash
git clone https://github.com/DavidDaCoder12/Incubot.git
cd Incubot
```

### 2. Set Up a Virtual Environment
The repo includes a `pyvenv.cfg` and vendored packages under `lib/python3.11/`. If running fresh, set up a virtual environment:
```bash
python3.11 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install opencv-python numpy scipy pyserial PyQt5
```

> If packages are already present under `lib/python3.11/site-packages`, you may be able to use them directly by ensuring that directory is on your `PYTHONPATH`. When in doubt, install fresh into a virtual environment.

### 4. Enable the Camera
```bash
sudo raspi-config
```
Navigate to **Interface Options → Camera** and enable it. Reboot when prompted.

### 5. Connect the Arduino
Plug the Arduino into the Raspberry Pi via USB. Find the serial port:
```bash
ls /dev/ttyUSB* /dev/ttyACM*
```
Update the port in `parameters.py` to match (e.g. `/dev/ttyUSB0` or `/dev/ttyACM0`).

### 6. Physical Setup
- Mount the 96-well plate in the designated position on the printer bed
- Ensure the camera is securely fixed to the Z-carriage
- Home all axes before any motion (`G28` command)

---

## Running the Application

```bash
python main.py
```

This opens the main PyQt5 window. From there:

1. **Select wells** on the grid widget
2. **Adjust Z-axis** using coarse/fine controls until the cells are in focus
3. **Toggle the LED** for illumination as needed
4. **Capture** an image — it will be saved to the `images/` folder
5. **Save a preset** if you want to return to the same well configuration later
6. **Set up an experiment** via the Experiment dialog (interval imaging — partially implemented)

### Building a Standalone Executable (Optional)
A PyInstaller spec file is included if you want to distribute a standalone app:
```bash
pip install pyinstaller
pyinstaller main.spec
```
The output will appear in the `dist/` folder.

---

## Known Issues & Current Limitations

### 🔴 Z-Axis Focus Calibration
The most significant ongoing challenge. The Z-axis lacks reliable, repeatable auto-focus. Key problems:
- The focal plane shifts between wells due to physical variation in plate height across the well-plate surface
- A tilt calibration routine exists (`tilt_calibration.py`) and calibration data is stored in `z_calibration.npy`, but the calibration is not yet robust enough for fully automated use
- Manual focus adjustment is currently required before each capture

### 🟡 Automated Interval Imaging Incomplete
The experiment dialog and imaging worker exist but the full automated time-lapse loop (visit well → auto-focus → capture → wait → repeat) is not complete. The scaffolding is in place — this is a primary area for future work.

### 🟡 Serial Connection Stability
Occasional serial disconnects from the Arduino can occur during long sessions. Reconnection handling may need to be made more robust in `movement_control.py`.

### 🟡 Build Artifacts in Repo
The `__pycache__/`, `build/`, `dist/`, `bin/`, and `lib/` directories are committed to the repository and should ideally be excluded via a `.gitignore`. Future students should not need to modify anything in these folders.

---

## Future Work

Suggested areas for future students to focus on:

- **Auto-focus algorithm** — Implement reliable software auto-focus using focus scoring metrics (Laplacian variance, Brenner gradient, or Tenengrad). The Z calibration data in `z_calibration.npy` is a useful starting point.
- **Complete the interval imaging loop** — `imaging_worker.py` and `experiment_dialog.py` already provide scaffolding. The main task is connecting experiment parameters to a reliable timed loop with auto-focus at each well stop.
- **Z & tilt calibration robustness** — Improve `tilt_calibration.py` so the per-well Z offset is accurate enough to rely on for automated runs without manual adjustment.
- **Add a `.gitignore`** — Exclude `__pycache__/`, `build/`, `dist/`, `bin/`, `lib/`, `*.pyc`, and `*.log` from version control to keep the repo clean.
- **Image organization** — Currently images go into a flat `images/` folder. Consider organizing by experiment name, date, and well ID.
- **Parameter configuration UI** — Expose the serial port and key motion parameters in the GUI rather than requiring direct edits to `parameters.py`.

---

## Contributing

This project is designed to be picked up and extended by future students. If you're taking it on:

1. **Read this README fully** before touching any hardware — especially the homing and physical setup steps
2. **Check the Issues tab** on GitHub for outstanding bugs and ideas
3. **Make a new branch** for your work — don't commit directly to `main`
4. **Don't modify build artifacts** — `build/`, `dist/`, `bin/`, and `__pycache__/` are generated files
5. **Document hardware changes** — if you adjust the plate mount or Z-carriage, note the new coordinate offsets in the code and in this README
6. **Leave notes** — open GitHub Issues or add comments in the code so the next person has context

---

*Original author: David — GitHub: [@DavidDaCoder12](https://github.com/DavidDaCoder12)*
