import customtkinter as ctk
from tkinter import filedialog
import os
import json

SETTINGS_PATH = os.path.join(os.path.expanduser("~"),
                              ".pixel-downloader", "settings.json")

DEFAULT_SETTINGS = {
    "download_dir": os.path.join(os.path.expanduser("~"),
                                  "Downloads", "PixelDownloader"),
    "max_concurrent": 3,
    "segments": 8,
    "notify_on_complete": True,
    "theme": "dark",
}

def load_settings():
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH) as f:
                return {**DEFAULT_SETTINGS, **json.load(f)}
        except:
            pass
    return DEFAULT_SETTINGS.copy()

def save_settings(s):
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w") as f:
        json.dump(s, f, indent=2)

class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_save=None):
        super().__init__(parent)
        self.title("Settings")
        self.geometry("460x500")
        self.resizable(False, False)
        self.on_save = on_save
        self.settings = load_settings()
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text="⚙  Settings",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#89b4fa"
        ).grid(row=0, column=0, padx=20, pady=(16, 12), sticky="w")

        # Download folder
        self._section("Download Folder", row=1)
        path_frame = ctk.CTkFrame(self, fg_color="transparent")
        path_frame.grid(row=2, column=0, padx=20, sticky="ew")
        path_frame.grid_columnconfigure(0, weight=1)

        self.path_entry = ctk.CTkEntry(
            path_frame, height=36, corner_radius=8,
            border_color="#45475a", fg_color="#1e1e2e"
        )
        self.path_entry.insert(0, self.settings["download_dir"])
        self.path_entry.grid(row=0, column=0, sticky="ew")

        ctk.CTkButton(
            path_frame, text="Browse", width=70, height=36,
            corner_radius=8, fg_color="#313244", hover_color="#45475a",
            command=self._browse
        ).grid(row=0, column=1, padx=(6, 0))

        # Max concurrent
        self._section("Max Concurrent Downloads", row=3)
        self.concurrent_var = ctk.IntVar(value=self.settings["max_concurrent"])
        concurrent_frame = ctk.CTkFrame(self, fg_color="transparent")
        concurrent_frame.grid(row=4, column=0, padx=20, sticky="w")

        ctk.CTkSlider(
            concurrent_frame,
            from_=1, to=10,
            variable=self.concurrent_var,
            width=200,
            command=lambda v: self.concurrent_label.configure(
                text=str(int(v))
            )
        ).pack(side="left")

        self.concurrent_label = ctk.CTkLabel(
            concurrent_frame,
            text=str(self.settings["max_concurrent"]),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#89b4fa",
            width=30
        )
        self.concurrent_label.pack(side="left", padx=8)

        # Segments
        self._section("Download Segments (chunks per file)", row=5)
        self.segments_var = ctk.IntVar(value=self.settings["segments"])
        seg_frame = ctk.CTkFrame(self, fg_color="transparent")
        seg_frame.grid(row=6, column=0, padx=20, sticky="w")

        ctk.CTkSlider(
            seg_frame,
            from_=1, to=32,
            variable=self.segments_var,
            width=200,
            command=lambda v: self.segments_label.configure(
                text=str(int(v))
            )
        ).pack(side="left")

        self.segments_label = ctk.CTkLabel(
            seg_frame,
            text=str(self.settings["segments"]),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#89b4fa",
            width=30
        )
        self.segments_label.pack(side="left", padx=8)

        # Theme
        self._section("Theme", row=7)
        self.theme_var = ctk.StringVar(value=self.settings["theme"].title())
        ctk.CTkOptionMenu(
            self,
            variable=self.theme_var,
            values=["Dark", "Light", "System"],
            fg_color="#313244",
            button_color="#45475a",
            button_hover_color="#585b70",
            command=lambda v: ctk.set_appearance_mode(v.lower())
        ).grid(row=8, column=0, padx=20, pady=(4, 0), sticky="w")

        # Notifications
        self._section("Notifications", row=9)
        self.notify_var = ctk.BooleanVar(value=self.settings["notify_on_complete"])
        ctk.CTkCheckBox(
            self,
            text="Notify when download completes",
            variable=self.notify_var,
            checkbox_width=18,
            checkbox_height=18
        ).grid(row=10, column=0, padx=20, pady=(4, 0), sticky="w")

        # Save button
        ctk.CTkButton(
            self,
            text="Save Settings",
            height=40,
            corner_radius=8,
            fg_color="#89b4fa",
            hover_color="#7aa2f7",
            text_color="#1a1a2e",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._save
        ).grid(row=11, column=0, padx=20, pady=20, sticky="ew")

    def _section(self, text, row):
        ctk.CTkLabel(
            self, text=text,
            font=ctk.CTkFont(size=12),
            text_color="#6c7086"
        ).grid(row=row, column=0, padx=20, pady=(12, 2), sticky="w")

    def _browse(self):
        folder = filedialog.askdirectory()
        if folder:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, folder)

    def _save(self):
        self.settings.update({
            "download_dir": self.path_entry.get(),
            "max_concurrent": int(self.concurrent_var.get()),
            "segments": int(self.segments_var.get()),
            "notify_on_complete": self.notify_var.get(),
            "theme": self.theme_var.get().lower(),
        })
        save_settings(self.settings)
        if self.on_save:
            self.on_save(self.settings)
        self.destroy()
