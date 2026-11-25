import customtkinter as ctk
import os

def format_size(b):
    if b <= 0: return "0 B"
    for unit in ["B", "KB", "MB", "GB"]:
        if b < 1024: return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"

def format_speed(bps):
    return format_size(bps) + "/s"

STATUS_COLORS = {
    "completed":   "#a6e3a1",
    "downloading": "#89b4fa",
    "paused":      "#f9e2af",
    "failed":      "#f38ba8",
    "cancelled":   "#f38ba8",
    "queued":      "#6c7086",
}

FILE_ICONS = {
    ".mp4": "🎬", ".mkv": "🎬", ".webm": "🎬",
    ".mp3": "🎵", ".m4a": "🎵", ".wav": "🎵",
    ".zip": "📦", ".tar": "📦", ".gz": "📦",
    ".pdf": "📄", ".iso": "💿", ".exe": "⚙️",
}

class DownloadRow(ctk.CTkFrame):
    def __init__(self, master, download_data, on_pause,
                 on_resume, on_cancel, on_delete):
        super().__init__(
            master,
            corner_radius=10,
            fg_color=("#1e1e2e", "#1e1e2e"),
            border_width=1,
            border_color="#313244"
        )
        self.download_id = download_data["id"]
        self.status = download_data.get("status", "queued")
        self.save_path = download_data.get("save_path", "")
        self.url = download_data.get("url", "")
        self.on_pause = on_pause
        self.on_resume = on_resume
        self.on_cancel = on_cancel
        self.on_delete = on_delete
        self._last_downloaded = 0
        self._last_time = 0
        self._speed = 0

        self.filename_var = ctk.StringVar(value=download_data.get("filename", ""))
        self.grid_columnconfigure(0, weight=1)

        self._build_ui()
        self._restore_state(download_data)

    def _build_ui(self):
        # ── Top row ───────────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        top.grid_columnconfigure(1, weight=1)

        # File icon
        ext = os.path.splitext(self.filename_var.get())[-1].lower()
        icon = FILE_ICONS.get(ext, "📁")
        ctk.CTkLabel(
            top,
            text=icon,
            font=ctk.CTkFont(size=24),
            width=36
        ).grid(row=0, column=0, padx=(0, 10))

        # Filename + URL
        info = ctk.CTkFrame(top, fg_color="transparent")
        info.grid(row=0, column=1, sticky="ew")
        info.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            info,
            textvariable=self.filename_var,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#cdd6f4",
            anchor="w"
        ).grid(row=0, column=0, sticky="ew")

        ctk.CTkLabel(
            info,
            text=self.url[:70] + "..." if len(self.url) > 70 else self.url,
            font=ctk.CTkFont(size=10),
            text_color="#6c7086",
            anchor="w"
        ).grid(row=1, column=0, sticky="ew")

        # Status badge
        self.badge = ctk.CTkLabel(
            top,
            text=self.status.upper(),
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=STATUS_COLORS.get(self.status, "#6c7086"),
            width=100,
            anchor="e"
        )
        self.badge.grid(row=0, column=2, padx=(8, 0))

        # Action buttons
        btn_frame = ctk.CTkFrame(top, fg_color="transparent")
        btn_frame.grid(row=0, column=3, padx=(8, 0))

        self.pause_btn = ctk.CTkButton(
            btn_frame, text="⏸", width=30, height=28,
            corner_radius=6, fg_color="#313244",
            hover_color="#45475a",
            command=lambda: self.on_pause(self.download_id)
        )
        self.pause_btn.pack(side="left", padx=2)

        self.resume_btn = ctk.CTkButton(
            btn_frame, text="▶", width=30, height=28,
            corner_radius=6, fg_color="#313244",
            hover_color="#45475a",
            command=lambda: self.on_resume(self.download_id)
        )
        self.resume_btn.pack(side="left", padx=2)

        self.cancel_btn = ctk.CTkButton(
            btn_frame, text="✕", width=30, height=28,
            corner_radius=6, fg_color="#313244",
            hover_color="#45475a",
            command=lambda: self.on_cancel(self.download_id)
        )
        self.cancel_btn.pack(side="left", padx=2)

        self.delete_btn = ctk.CTkButton(
            btn_frame, text="🗑", width=30, height=28,
            corner_radius=6, fg_color="#4a1942",
            hover_color="#6b2155",
            command=lambda: self.on_delete(self.download_id)
        )
        self.delete_btn.pack(side="left", padx=2)

        # ── Progress bar ──────────────────────────────────────
        self.progress_bar = ctk.CTkProgressBar(
            self,
            height=6,
            corner_radius=3,
            progress_color="#89b4fa",
            fg_color="#313244"
        )
        self.progress_bar.grid(row=1, column=0, sticky="ew",
                                padx=12, pady=(0, 4))
        self.progress_bar.set(0)

        # ── Bottom row ────────────────────────────────────────
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=2, column=0, sticky="ew",
                    padx=12, pady=(0, 10))
        bottom.grid_columnconfigure(0, weight=1)

        self.size_label = ctk.CTkLabel(
            bottom,
            text="Waiting...",
            font=ctk.CTkFont(size=11),
            text_color="#6c7086",
            anchor="w"
        )
        self.size_label.grid(row=0, column=0, sticky="w")

        self.speed_label = ctk.CTkLabel(
            bottom,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#6c7086"
        )
        self.speed_label.grid(row=0, column=1, padx=8)

        self.percent_label = ctk.CTkLabel(
            bottom,
            text="0%",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#89b4fa"
        )
        self.percent_label.grid(row=0, column=2)

        self._update_buttons()

        # Right-click menu
        self.bind("<Button-3>", self._on_right_click)

    def _restore_state(self, data):
        status = data.get("status", "queued")
        downloaded = data.get("downloaded", 0)
        save_path = data.get("save_path", "")

        if status == "completed":
            self.progress_bar.set(1.0)
            self.percent_label.configure(text="100%")
            self.speed_label.configure(text="")
            real_size = downloaded
            if save_path and os.path.exists(save_path):
                real_size = os.path.getsize(save_path)
            self.size_label.configure(
                text=f"Done — {format_size(real_size)}" if real_size > 0 else "Completed"
            )
        elif status == "failed":
            self.size_label.configure(text="Failed — delete and retry")
        elif status == "queued":
            self.size_label.configure(text="Waiting to start...")

    def update_progress(self, downloaded, total, percent):
        import time
        now = time.time()
        elapsed = now - self._last_time
        if elapsed > 0.5:
            self._speed = (downloaded - self._last_downloaded) / elapsed if elapsed > 0 else 0
            self._last_downloaded = downloaded
            self._last_time = now

        self.progress_bar.set(min(percent / 100, 1.0))
        self.percent_label.configure(text=f"{percent:.1f}%")
        self.speed_label.configure(
            text=format_speed(self._speed) if self._speed > 0 else ""
        )
        if total > 0:
            self.size_label.configure(
                text=f"{format_size(downloaded)} of {format_size(total)}"
            )
        else:
            self.size_label.configure(text=format_size(downloaded))

        if percent >= 100:
            self.set_status("completed")

    def set_status(self, status):
        self.status = status
        self.badge.configure(
            text=status.upper(),
            text_color=STATUS_COLORS.get(status, "#6c7086")
        )
        self._update_buttons()
        if status == "completed":
            self.progress_bar.configure(progress_color="#a6e3a1")
            self.progress_bar.set(1.0)
            self.percent_label.configure(text="100%")
            self.speed_label.configure(text="")
            self.size_label.configure(text="Completed")
        elif status == "failed":
            self.progress_bar.configure(progress_color="#f38ba8")

    def _update_buttons(self):
        is_active = self.status == "downloading"
        is_paused = self.status == "paused"
        is_done = self.status in ("completed", "cancelled", "failed")

        self.pause_btn.configure(state="normal" if is_active else "disabled")
        self.resume_btn.configure(state="normal" if is_paused else "disabled")
        self.cancel_btn.configure(state="normal" if (is_active or is_paused) else "disabled")
        self.delete_btn.configure(state="normal" if is_done else "disabled")

    def _on_right_click(self, event):
        menu = ctk.CTkToplevel(self)
        menu.wm_overrideredirect(True)
        menu.geometry(f"+{event.x_root}+{event.y_root}")
        menu.configure(fg_color="#313244")

        buttons = [
            ("📂  Open File",   self._open_file),
            ("📁  Open Folder", self._open_folder),
            ("📋  Copy URL",    self._copy_url),
        ]
        for label, cmd in buttons:
            ctk.CTkButton(
                menu,
                text=label,
                anchor="w",
                fg_color="transparent",
                hover_color="#45475a",
                text_color="#cdd6f4",
                font=ctk.CTkFont(size=12),
                height=32,
                command=lambda c=cmd, m=menu: [m.destroy(), c()]
            ).pack(fill="x", padx=4, pady=2)

        menu.bind("<FocusOut>", lambda e: menu.destroy())
        menu.focus_set()

    def _open_file(self):
        import subprocess
        if self.save_path and os.path.exists(self.save_path):
            os.startfile(self.save_path) if os.name == "nt" else \
                subprocess.Popen(["xdg-open", self.save_path])

    def _open_folder(self):
        import subprocess
        folder = os.path.dirname(self.save_path)
        if folder and os.path.exists(folder):
            os.startfile(folder) if os.name == "nt" else \
                subprocess.Popen(["xdg-open", folder])

    def _copy_url(self):
        self.clipboard_clear()
        self.clipboard_append(self.url)
