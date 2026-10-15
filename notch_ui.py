"""
Floating Screen-Edge Notch Widget (Tkinter).

Features:
- Adaptive orientation: Horizontal (snap Top/Bottom) or Vertical (snap Left/Right).
- Screen-edge & corner snapping: Automatically docks to screen edges/corners and
  prevents the notch from ever getting lost outside monitor borders.
- Full multi-monitor support with Win32 work area detection (excludes taskbar).
- Dual circle indicators: 5-Hour Limit and Weekly Limit side-by-side or stacked.
- Adaptive hover detail card that positions intelligently relative to any edge.
"""

import tkinter as tk
from tkinter import font as tkfont
from typing import Dict, Any, Optional, Callable, Tuple
import ctypes
from ctypes import wintypes


def get_monitor_work_area(x: int, y: int) -> Tuple[int, int, int, int]:
    """
    Returns (left, top, right, bottom) of the monitor's work area (excluding taskbar)
    for the screen containing point (x, y). Works across any multi-monitor layout.
    """
    try:
        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", wintypes.DWORD),
            ]

        user32 = ctypes.windll.user32
        pt = wintypes.POINT(int(x), int(y))
        h_mon = user32.MonitorFromPoint(pt, 2)  # MONITOR_DEFAULTTONEAREST = 2
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if user32.GetMonitorInfoW(h_mon, ctypes.byref(mi)):
            return mi.rcWork.left, mi.rcWork.top, mi.rcWork.right, mi.rcWork.bottom
    except Exception:
        pass
    return 0, 0, 1920, 1040


class HoverCard(tk.Toplevel):
    """Flyout card that appears beneath/beside the notch on hover with full quota details."""

    def __init__(self, master):
        super().__init__(master)
        self.overrideredirect(True)
        self.wm_attributes("-topmost", True)
        self.configure(bg="#181a20")
        self.withdraw()  # Initially hidden

        # Border frame for subtle shadow/stroke effect
        self.border_frame = tk.Frame(self, bg="#2d3139", padx=1, pady=1)
        self.border_frame.pack(fill=tk.BOTH, expand=True)

        self.inner_frame = tk.Frame(self.border_frame, bg="#12141a", padx=14, pady=12)
        self.inner_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        self.header_frame = tk.Frame(self.inner_frame, bg="#12141a")
        self.header_frame.pack(fill=tk.X, pady=(0, 8))

        self.title_lbl = tk.Label(
            self.header_frame,
            text="ANTIGRAVITY USAGE",
            font=("Segoe UI", 8, "bold"),
            fg="#94a3b8",
            bg="#12141a",
        )
        self.title_lbl.pack(side=tk.LEFT)

        self.status_badge = tk.Label(
            self.header_frame,
            text="LIVE",
            font=("Segoe UI", 7, "bold"),
            fg="#34d399",
            bg="#064e3b",
            padx=5,
            pady=1,
        )
        self.status_badge.pack(side=tk.RIGHT)

        # Content container
        self.content_frame = tk.Frame(self.inner_frame, bg="#12141a")
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        # Footer
        self.footer_lbl = tk.Label(
            self.inner_frame,
            text="Right-click notch for menu  ·  Drag to snap",
            font=("Segoe UI", 7),
            fg="#64748b",
            bg="#12141a",
            pady=4,
        )
        self.footer_lbl.pack(fill=tk.X, pady=(8, 0))

    def update_data(self, data: Dict[str, Any]):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        status = data.get("status", "disconnected")
        if status == "connected":
            self.status_badge.config(text="● LIVE", fg="#34d399", bg="#064e3b")
        elif status == "stale":
            self.status_badge.config(text="● CACHED", fg="#fbbf24", bg="#451a03")
        else:
            self.status_badge.config(text="● OFFLINE", fg="#f87171", bg="#450a0a")

        groups = data.get("groups", [])
        if not groups:
            no_data = tk.Label(
                self.content_frame,
                text="Waiting for Antigravity language server...",
                font=("Segoe UI", 9, "italic"),
                fg="#94a3b8",
                bg="#12141a",
                pady=10,
            )
            no_data.pack()
            return

        for idx, g in enumerate(groups):
            group_name = g.get("displayName", "Models")
            if idx > 0:
                sep = tk.Frame(self.content_frame, height=1, bg="#1e222b")
                sep.pack(fill=tk.X, pady=6)

            g_lbl = tk.Label(
                self.content_frame,
                text=group_name,
                font=("Segoe UI", 9, "bold"),
                fg="#f1f5f9",
                bg="#12141a",
                anchor="w",
            )
            g_lbl.pack(fill=tk.X, pady=(2, 4))

            for b in g.get("buckets", []):
                window_name = "5-Hour Limit" if b.get("window") == "5h" else "Weekly Limit"
                rem_pct = b.get("remainingPct", 100.0)
                countdown = b.get("countdown", "")

                row = tk.Frame(self.content_frame, bg="#12141a")
                row.pack(fill=tk.X, pady=2)

                lbl_left = tk.Label(
                    row,
                    text=window_name,
                    font=("Segoe UI", 8),
                    fg="#cbd5e1",
                    bg="#12141a",
                )
                lbl_left.pack(side=tk.LEFT)

                if rem_pct > 40:
                    val_color = "#34d399"  # Green
                elif rem_pct > 15:
                    val_color = "#fbbf24"  # Amber
                else:
                    val_color = "#f87171"  # Red

                pct_txt = f"{rem_pct}% left"
                if countdown and countdown != "unknown":
                    pct_txt += f"  ({countdown})"

                lbl_right = tk.Label(
                    row,
                    text=pct_txt,
                    font=("Segoe UI", 8, "bold"),
                    fg=val_color,
                    bg="#12141a",
                )
                lbl_right.pack(side=tk.RIGHT)

                # Progress bar
                bar_bg = tk.Canvas(
                    self.content_frame,
                    height=4,
                    bg="#222734",
                    highlightthickness=0,
                )
                bar_bg.pack(fill=tk.X, pady=(1, 4))
                self.update_idletasks()
                bar_width = 250
                fill_w = max(0, min(bar_width, int(bar_width * (rem_pct / 100.0))))
                bar_bg.create_rectangle(0, 0, fill_w, 4, fill=val_color, width=0)


class CodenotchWindow:
    """The main adaptive notch widget with edge snapping."""

    def __init__(self, root: tk.Tk, on_refresh_requested: Optional[Callable] = None):
        self.root = root
        self.on_refresh_requested = on_refresh_requested
        self.data: Dict[str, Any] = {"status": "starting", "groups": []}

        # Orientation state: "horizontal" or "vertical"
        self.orientation = "horizontal"
        self.dock_edge = "top"  # "top", "bottom", "left", "right", or "floating"

        # Dimensions
        self.h_width, self.h_height = 475, 36
        self.v_width, self.v_height = 54, 330

        self.pill_width = self.h_width
        self.pill_height = self.h_height

        # Window styling
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        self.root.configure(bg="#000000")

        # Fonts
        self.f_brand = tkfont.Font(family="Segoe UI", size=8, weight="bold")
        self.f_num = tkfont.Font(family="Segoe UI", size=8, weight="bold")
        self.f_tag = tkfont.Font(family="Segoe UI", size=7, weight="bold")
        self.f_cd = tkfont.Font(family="Segoe UI", size=7)

        # Vertical mode fonts
        self.f_v_brand = tkfont.Font(family="Segoe UI", size=7, weight="bold")
        self.f_v_num = tkfont.Font(family="Segoe UI", size=7, weight="bold")
        self.f_v_tag = tkfont.Font(family="Segoe UI", size=6)

        # Initial position: top-center of primary screen
        mon_left, mon_top, mon_right, _ = get_monitor_work_area(100, 100)
        start_x = mon_left + ((mon_right - mon_left) - self.pill_width) // 2
        start_y = mon_top + 6
        self.root.geometry(f"{self.pill_width}x{self.pill_height}+{start_x}+{start_y}")

        # Drag tracking
        self._drag_data = {"x": 0, "y": 0}

        # Main canvas
        self.canvas = tk.Canvas(
            self.root,
            width=self.pill_width,
            height=self.pill_height,
            bg="#000000",
            highlightthickness=0,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Hover Card
        self.hover_card = HoverCard(self.root)
        self._hover_cancel_id: Optional[str] = None

        # Bind mouse events
        self.canvas.bind("<Button-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_drag_release)
        self.canvas.bind("<Button-3>", self._show_context_menu)
        self.canvas.bind("<Enter>", self._on_mouse_enter)
        self.canvas.bind("<Leave>", self._on_mouse_leave)

        # Context menu with quick-snap options
        self.menu = tk.Menu(self.root, tearoff=0, bg="#1a1c23", fg="#e2e8f0", activebackground="#2d3748")
        self.menu.add_command(label="🔄  Refresh Quota Now", command=self._trigger_refresh)
        self.menu.add_separator()
        self.menu.add_command(label="⬆️  Snap Top Center", command=lambda: self.snap_to("top_center"))
        self.menu.add_command(label="⬅️  Snap Left Edge", command=lambda: self.snap_to("left"))
        self.menu.add_command(label="➡️  Snap Right Edge", command=lambda: self.snap_to("right"))
        self.menu.add_command(label="⬇️  Snap Bottom Center", command=lambda: self.snap_to("bottom_center"))
        self.menu.add_separator()
        self.menu.add_command(label="❌  Close Notch", command=self.root.destroy)

        self._render_notch()

    def _on_drag_start(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _on_drag_motion(self, event):
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        new_x = self.root.winfo_x() + dx
        new_y = self.root.winfo_y() + dy

        # Keep partially visible during drag
        self.root.geometry(f"+{new_x}+{new_y}")
        self._update_hover_position()

    def _on_drag_release(self, _event):
        """Calculates snapping to closest edge or corner and adapts orientation."""
        cur_x = self.root.winfo_x()
        cur_y = self.root.winfo_y()

        # Find which monitor the center of the window is currently inside
        center_x = cur_x + self.pill_width // 2
        center_y = cur_y + self.pill_height // 2
        mon_left, mon_top, mon_right, mon_bottom = get_monitor_work_area(center_x, center_y)
        mon_w = mon_right - mon_left
        mon_h = mon_bottom - mon_top

        # Distances to the 4 edges of this monitor
        dist_left = abs(cur_x - mon_left)
        dist_right = abs(mon_right - (cur_x + self.pill_width))
        dist_top = abs(cur_y - mon_top)
        dist_bottom = abs(mon_bottom - (cur_y + self.pill_height))

        min_horizontal_edge = min(dist_left, dist_right)
        min_vertical_edge = min(dist_top, dist_bottom)

        SNAP_THRESHOLD = 70  # Pixels sensitivity for snapping

        # Decide whether to snap to Left/Right (Vertical) or Top/Bottom (Horizontal)
        if min_horizontal_edge < SNAP_THRESHOLD and min_horizontal_edge < min_vertical_edge:
            # Snap to vertical edge (Left or Right)
            self._apply_orientation("vertical")
            if dist_left <= dist_right:
                self.dock_edge = "left"
                snap_x = mon_left + 4
            else:
                self.dock_edge = "right"
                snap_x = mon_right - self.pill_width - 4

            # Corner snapping along the vertical edge:
            if abs(cur_y - mon_top) < SNAP_THRESHOLD:
                snap_y = mon_top + 6  # Top corner
            elif abs(mon_bottom - (cur_y + self.pill_height)) < SNAP_THRESHOLD:
                snap_y = mon_bottom - self.pill_height - 6  # Bottom corner
            else:
                # Clamp within monitor work area
                snap_y = max(mon_top + 4, min(mon_bottom - self.pill_height - 4, cur_y))

        elif min_vertical_edge < SNAP_THRESHOLD:
            # Snap to horizontal edge (Top or Bottom)
            self._apply_orientation("horizontal")
            if dist_top <= dist_bottom:
                self.dock_edge = "top"
                snap_y = mon_top + 6
            else:
                self.dock_edge = "bottom"
                snap_y = mon_bottom - self.pill_height - 6

            # Corner & Center snapping along the horizontal edge:
            if abs(cur_x - mon_left) < SNAP_THRESHOLD:
                snap_x = mon_left + 6  # Left corner
            elif abs(mon_right - (cur_x + self.pill_width)) < SNAP_THRESHOLD:
                snap_x = mon_right - self.pill_width - 6  # Right corner
            elif abs(cur_x - (mon_left + (mon_w - self.pill_width) // 2)) < SNAP_THRESHOLD * 1.5:
                snap_x = mon_left + (mon_w - self.pill_width) // 2  # Center snap
            else:
                snap_x = max(mon_left + 4, min(mon_right - self.pill_width - 4, cur_x))

        else:
            # Floating freely (remain in current orientation or default horizontal)
            # Ensure window never gets hidden outside monitor bounds!
            self.dock_edge = "floating"
            snap_x = max(mon_left + 6, min(mon_right - self.pill_width - 6, cur_x))
            snap_y = max(mon_top + 6, min(mon_bottom - self.pill_height - 6, cur_y))

        # Position and render
        self.root.geometry(f"+{snap_x}+{snap_y}")
        self._update_hover_position()
        self._render_notch()

    def _apply_orientation(self, target: str):
        """Switches between horizontal and vertical dimensions and reconfigures canvas."""
        if self.orientation == target:
            return
        self.orientation = target
        if target == "vertical":
            self.pill_width = self.v_width
            self.pill_height = self.v_height
        else:
            self.pill_width = self.h_width
            self.pill_height = self.h_height

        self.root.geometry(f"{self.pill_width}x{self.pill_height}")
        self.canvas.config(width=self.pill_width, height=self.pill_height)

    def snap_to(self, preset: str):
        """Preset snapping helper for context menu."""
        cur_x = self.root.winfo_x()
        cur_y = self.root.winfo_y()
        mon_left, mon_top, mon_right, mon_bottom = get_monitor_work_area(cur_x, cur_y)
        mon_w = mon_right - mon_left
        mon_h = mon_bottom - mon_top

        if preset == "left":
            self._apply_orientation("vertical")
            self.dock_edge = "left"
            snap_x = mon_left + 4
            snap_y = mon_top + (mon_h - self.pill_height) // 2
        elif preset == "right":
            self._apply_orientation("vertical")
            self.dock_edge = "right"
            snap_x = mon_right - self.pill_width - 4
            snap_y = mon_top + (mon_h - self.pill_height) // 2
        elif preset == "bottom_center":
            self._apply_orientation("horizontal")
            self.dock_edge = "bottom"
            snap_x = mon_left + (mon_w - self.pill_width) // 2
            snap_y = mon_bottom - self.pill_height - 6
        else:  # top_center
            self._apply_orientation("horizontal")
            self.dock_edge = "top"
            snap_x = mon_left + (mon_w - self.pill_width) // 2
            snap_y = mon_top + 6

        self.root.geometry(f"{self.pill_width}x{self.pill_height}+{snap_x}+{snap_y}")
        self._update_hover_position()
        self._render_notch()

    def _show_context_menu(self, event):
        self._hide_hover_card_immediate()
        self.menu.post(event.x_root, event.y_root)

    def _trigger_refresh(self):
        if self.on_refresh_requested:
            self.on_refresh_requested()

    def _on_mouse_enter(self, _event):
        if self._hover_cancel_id:
            self.root.after_cancel(self._hover_cancel_id)
            self._hover_cancel_id = None
        self._hover_cancel_id = self.root.after(180, self._show_hover_card)

    def _on_mouse_leave(self, _event):
        if self._hover_cancel_id:
            self.root.after_cancel(self._hover_cancel_id)
            self._hover_cancel_id = None
        self._hover_cancel_id = self.root.after(220, self._hide_hover_card_immediate)

    def _show_hover_card(self):
        self._update_hover_position()
        self.hover_card.update_data(self.data)
        self.hover_card.deiconify()

    def _hide_hover_card_immediate(self):
        self.hover_card.withdraw()

    def _update_hover_position(self):
        notch_x = self.root.winfo_x()
        notch_y = self.root.winfo_y()
        notch_w = self.pill_width
        notch_h = self.pill_height

        card_w = 280
        card_h = 220

        # Query work area of whichever monitor the notch is on
        mon_left, mon_top, mon_right, mon_bottom = get_monitor_work_area(notch_x, notch_y)

        if self.orientation == "vertical":
            # In vertical mode, position card to the side of the notch
            if self.dock_edge == "right":
                card_x = notch_x - card_w - 8
            else:
                card_x = notch_x + notch_w + 8
            # Align top with notch, clamped within screen
            card_y = max(mon_top + 4, min(mon_bottom - card_h - 4, notch_y))
        else:
            # In horizontal mode, center card beneath or above notch
            card_x = notch_x + (notch_w - card_w) // 2
            card_x = max(mon_left + 4, min(mon_right - card_w - 4, card_x))

            if self.dock_edge == "bottom":
                card_y = notch_y - card_h - 8  # Open above
            else:
                card_y = notch_y + notch_h + 8  # Open below

        self.hover_card.geometry(f"{card_w}x{card_h}+{card_x}+{card_y}")

    def update_data(self, data: Dict[str, Any]):
        """Called whenever fresh quota data arrives."""
        self.data = data
        self._render_notch()
        if self.hover_card.winfo_ismapped():
            self.hover_card.update_data(data)

    def _draw_rounded_pill(self, x1, y1, x2, y2, r, fill, outline):
        """Draws a smooth rounded pill rectangle on canvas."""
        points = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1,
        ]
        return self.canvas.create_polygon(points, smooth=True, fill=fill, outline=outline, width=1)

    def _draw_progress_ring(self, cx, cy, radius, percent, color, bg_color="#222634", width=2.5):
        """Draws a circular percentage meter on the canvas."""
        bbox = (cx - radius, cy - radius, cx + radius, cy + radius)
        self.canvas.create_oval(bbox, outline=bg_color, width=width)

        if percent > 0:
            extent = -int((percent / 100.0) * 359)
            if extent != 0:
                self.canvas.create_arc(
                    bbox,
                    start=90,
                    extent=extent,
                    style=tk.ARC,
                    outline=color,
                    width=width,
                )

    def _extract_buckets(self):
        """Helper to extract 5h and weekly buckets for Gemini and Claude."""
        gem_5h, gem_wk = None, None
        tp_5h, tp_wk = None, None

        for g in self.data.get("groups", []):
            name = g.get("displayName", "").lower()
            if "gemini" in name:
                for b in g.get("buckets", []):
                    if b.get("window") == "5h":
                        gem_5h = b
                    elif b.get("window") == "weekly":
                        gem_wk = b
            elif "claude" in name or "gpt" in name or "3p" in name:
                for b in g.get("buckets", []):
                    if b.get("window") == "5h":
                        tp_5h = b
                    elif b.get("window") == "weekly":
                        tp_wk = b
        return gem_5h, gem_wk, tp_5h, tp_wk

    def _render_notch(self):
        self.canvas.delete("all")

        # Pill background
        self._draw_rounded_pill(
            2, 2, self.pill_width - 2, self.pill_height - 2,
            r=16,
            fill="#0f1117",
            outline="#232733",
        )

        status = self.data.get("status", "disconnected")
        groups = self.data.get("groups", [])

        if self.orientation == "vertical":
            self._render_vertical(status, groups)
        else:
            self._render_horizontal(status, groups)

    def _render_horizontal(self, status: str, groups: list):
        cy = 18

        # Status Dot (far left)
        dot_color = "#34d399" if status == "connected" else ("#fbbf24" if status == "stale" else "#f87171")
        self.canvas.create_oval(13, 14, 21, 22, fill=dot_color, outline="")

        if not groups:
            msg = "Antigravity connecting..." if status != "disconnected" else "Antigravity offline"
            self.canvas.create_text(
                self.pill_width // 2, cy,
                text=msg,
                font=("Segoe UI", 9),
                fill="#94a3b8",
            )
            return

        gem_5h, gem_wk, tp_5h, tp_wk = self._extract_buckets()
        cur_x = 28

        # --- Gemini Section ---
        self.canvas.create_text(cur_x, cy, anchor="w", text="Gemini", font=self.f_brand, fill="#e2e8f0")
        cur_x += self.f_brand.measure("Gemini") + 8

        # 5-Hour Circle Indicator
        g_5h_pct = gem_5h.get("remainingPct", 100.0) if gem_5h else 100.0
        g_5h_cd = gem_5h.get("countdown", "") if gem_5h else ""
        cur_x = self._draw_h_metric_cell(cur_x, cy, g_5h_pct, "5h", g_5h_cd, primary_color="#38bdf8")

        cur_x += 6

        # Weekly Circle Indicator
        g_wk_pct = gem_wk.get("remainingPct", 100.0) if gem_wk else 100.0
        cur_x = self._draw_h_metric_cell(cur_x, cy, g_wk_pct, "Wk", "", primary_color="#34d399")

        cur_x += 10

        # --- Divider ---
        self.canvas.create_line(cur_x, 10, cur_x, 26, fill="#232733")
        cur_x += 10

        # --- Claude Section ---
        self.canvas.create_text(cur_x, cy, anchor="w", text="Claude", font=self.f_brand, fill="#e2e8f0")
        cur_x += self.f_brand.measure("Claude") + 8

        # 5-Hour Circle Indicator
        c_5h_pct = tp_5h.get("remainingPct", 100.0) if tp_5h else 100.0
        c_5h_cd = tp_5h.get("countdown", "") if tp_5h else ""
        cur_x = self._draw_h_metric_cell(cur_x, cy, c_5h_pct, "5h", c_5h_cd, primary_color="#a855f7")

        cur_x += 6

        # Weekly Circle Indicator
        c_wk_pct = tp_wk.get("remainingPct", 100.0) if tp_wk else 100.0
        self._draw_h_metric_cell(cur_x, cy, c_wk_pct, "Wk", "", primary_color="#34d399")

    def _draw_h_metric_cell(self, cur_x, cy, pct, tag, countdown, primary_color):
        ring_radius = 7.5
        cx = cur_x + ring_radius + 1

        if pct <= 15:
            ring_color = "#ef4444"
        elif pct <= 40:
            ring_color = "#fbbf24"
        else:
            ring_color = primary_color

        self._draw_progress_ring(cx, cy, radius=ring_radius, percent=pct, color=ring_color, width=2.5)
        cur_x = cx + ring_radius + 4

        num_str = f"{int(pct)}%"
        self.canvas.create_text(cur_x, cy, anchor="w", text=num_str, font=self.f_num, fill="#f1f5f9")
        cur_x += self.f_num.measure(num_str)

        tag_str = f" {tag}"
        self.canvas.create_text(cur_x, cy - 1, anchor="w", text=tag_str, font=self.f_tag, fill="#94a3b8")
        cur_x += self.f_tag.measure(tag_str)

        if countdown and countdown != "unknown" and pct < 99.5:
            cd_str = f" ({countdown})"
            self.canvas.create_text(cur_x, cy, anchor="w", text=cd_str, font=self.f_cd, fill="#64748b")
            cur_x += self.f_cd.measure(cd_str)

        return cur_x

    def _render_vertical(self, status: str, groups: list):
        """Draws compact vertical dock pill when snapped to Left or Right edge."""
        cx = self.pill_width // 2

        # Status Dot (top center)
        dot_color = "#34d399" if status == "connected" else ("#fbbf24" if status == "stale" else "#f87171")
        self.canvas.create_oval(cx - 4, 12, cx + 4, 20, fill=dot_color, outline="")

        if not groups:
            self.canvas.create_text(cx, 160, text="...", font=("Segoe UI", 10), fill="#94a3b8")
            return

        gem_5h, gem_wk, tp_5h, tp_wk = self._extract_buckets()

        # --- Gemini Section ---
        # Label
        self.canvas.create_text(cx, 34, text="GEMINI", font=self.f_v_brand, fill="#38bdf8")

        # 5h Ring
        g_5h_pct = gem_5h.get("remainingPct", 100.0) if gem_5h else 100.0
        g_5h_cd = gem_5h.get("countdown", "") if gem_5h else ""
        g_5h_color = "#ef4444" if g_5h_pct <= 15 else ("#fbbf24" if g_5h_pct <= 40 else "#38bdf8")
        self._draw_progress_ring(cx, 58, radius=8.5, percent=g_5h_pct, color=g_5h_color, width=2.5)
        self.canvas.create_text(cx, 76, text=f"{int(g_5h_pct)}% 5h", font=self.f_v_num, fill="#f1f5f9")

        # Wk Ring
        g_wk_pct = gem_wk.get("remainingPct", 100.0) if gem_wk else 100.0
        g_wk_color = "#ef4444" if g_wk_pct <= 15 else ("#fbbf24" if g_wk_pct <= 40 else "#34d399")
        self._draw_progress_ring(cx, 102, radius=8.5, percent=g_wk_pct, color=g_wk_color, width=2.5)
        self.canvas.create_text(cx, 120, text=f"{int(g_wk_pct)}% Wk", font=self.f_v_num, fill="#f1f5f9")

        # Divider line
        self.canvas.create_line(10, 142, self.pill_width - 10, 142, fill="#232733")

        # --- Claude Section ---
        # Label
        self.canvas.create_text(cx, 160, text="CLAUDE", font=self.f_v_brand, fill="#a855f7")

        # 5h Ring
        c_5h_pct = tp_5h.get("remainingPct", 100.0) if tp_5h else 100.0
        c_5h_color = "#ef4444" if c_5h_pct <= 15 else ("#fbbf24" if c_5h_pct <= 40 else "#a855f7")
        self._draw_progress_ring(cx, 184, radius=8.5, percent=c_5h_pct, color=c_5h_color, width=2.5)
        self.canvas.create_text(cx, 202, text=f"{int(c_5h_pct)}% 5h", font=self.f_v_num, fill="#f1f5f9")

        # Wk Ring
        c_wk_pct = tp_wk.get("remainingPct", 100.0) if tp_wk else 100.0
        c_wk_color = "#ef4444" if c_wk_pct <= 15 else ("#fbbf24" if c_wk_pct <= 40 else "#34d399")
        self._draw_progress_ring(cx, 228, radius=8.5, percent=c_wk_pct, color=c_wk_color, width=2.5)
        self.canvas.create_text(cx, 246, text=f"{int(c_wk_pct)}% Wk", font=self.f_v_num, fill="#f1f5f9")

        # Reset countdown badge if active
        if g_5h_cd and g_5h_cd != "unknown" and g_5h_pct < 99.5:
            self.canvas.create_text(cx, 276, text=g_5h_cd, font=self.f_v_tag, fill="#64748b")
