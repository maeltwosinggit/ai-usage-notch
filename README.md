# AI Usage Notch (Screen Edge Quota Monitor)

A lightweight, zero-installer floating screen-edge notch for Windows that pins your **AI assistant usage limits** (Antigravity, Claude, etc.) directly to your screen, inspired by [vinzdg/codenotch](https://github.com/vinzdg/codenotch).

* **100% Policy-Safe**: Runs directly through Python 3.11 with standard library `tkinter`. **No `.exe` installations**, no third-party packages, and zero administrator privileges required.
* **Dual Circle Indicators**: Displays both your active rolling **5-Hour Limit** (`5h` with reset countdown) and **Weekly Limit** (`Wk`) directly in the main view.
* **Adaptive Orientation**:
  * **Top / Bottom**: Sleek horizontal pill (`475 × 36 px`).
  * **Left / Right**: Compact vertical sidebar dock (`54 × 330 px`).
* **Screen & Corner Snapping**: Smoothly snaps to screen edges and corners across any multi-monitor setup and prevents the notch from being lost off-screen.
* **Intelligent Hover Card**: Hovering over the notch displays exact remaining percentages, countdowns to reset times, and status. Automatically opens away from the screen edge.

---

## Quick Start

### 1. Launch Silently (Recommended)
Double-click:
```
launch_notch.vbs
```
This runs the notch via `pythonw.exe` completely in the background without opening a black command prompt window.

### 2. Launch with Console (Debug / Testing)
Double-click `launch_notch.bat` or run:
```powershell
python main.py
```

---

## Controls & Usage

* **Drag to Snap**: Left-click and drag the notch. Dragging near any screen edge or corner automatically snaps it and adapts orientation.
* **Hover Details**: Move your mouse cursor over the notch to see the expanded flyout card showing exact percentage remaining and reset countdowns.
* **Right-Click Context Menu**:
  * **🔄 Refresh Quota Now**: Force an immediate update from Antigravity.
  * **⬆️ Snap Top Center**: Quick snap to the top center of your active screen.
  * **⬅️ Snap Left Edge**: Quick snap to the left edge in vertical dock mode.
  * **➡️ Snap Right Edge**: Quick snap to the right edge in vertical dock mode.
  * **⬇️ Snap Bottom Center**: Quick snap to the bottom center.
  * **❌ Close Notch**: Exits the application cleanly.

---

## Project Structure

```
codenotch-local/
├── main.py                 # Application entry point & background polling thread
├── notch_ui.py             # Tkinter floating adaptive notch & hover card UI
├── provider_antigravity.py # Local language server discovery & quota parser
├── launch_notch.vbs        # Silent double-click launcher (no terminal window)
├── launch_notch.bat        # Console launcher for testing
├── .gitignore              # Git ignore rules
└── README.md               # Documentation
```
