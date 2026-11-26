import customtkinter as ctk
import threading
import os
from tkinter import filedialog
from engine.extractor import VideoExtractor

class AddDownloadDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_confirm):
        super().__init__(parent)
        self.title("Add Download")
        self.geometry("520x580")
        self.resizable(False, False)
        self.on_confirm = on_confirm
        self.video_info = None
        self.formats = []
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)

        # Title
        ctk.CTkLabel(
            self,
            text="Add Download",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#89b4fa"
        ).grid(row=0, column=0, padx=20, pady=(16, 4), sticky="w")

        # URL entry
        ctk.CTkLabel(
            self, text="URL",
            font=ctk.CTkFont(size=12),
            text_color="#6c7086"
        ).grid(row=1, column=0, padx=20, pady=(8, 2), sticky="w")

        self.url_entry = ctk.CTkEntry(
            self,
            placeholder_text="Paste URL here...",
            height=38,
            corner_radius=8,
            border_color="#45475a",
            fg_color="#1e1e2e"
        )
        self.url_entry.grid(row=2, column=0, padx=20, sticky="ew")

        # Detect button
        self.detect_btn = ctk.CTkButton(
            self,
            text="🔍  Detect / Fetch Info",
            height=36,
            corner_radius=8,
            fg_color="#313244",
            hover_color="#45475a",
            command=self._on_detect
        )
        self.detect_btn.grid(row=3, column=0, padx=20, pady=8, sticky="ew")

        # Status
        self.status_label = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(size=11),
            text_color="#6c7086"
        )
        self.status_label.grid(row=4, column=0, padx=20, sticky="w")

        # Video info frame
        self.info_frame = ctk.CTkFrame(
            self,
            fg_color="#1e1e2e",
            corner_radius=8,
            border_width=1,
            border_color="#313244"
        )
        self.info_frame.grid(row=5, column=0, padx=20, pady=8, sticky="ew")
        self.info_frame.grid_columnconfigure(0, weight=1)
        self.info_frame.grid_remove()

        self.title_label = ctk.CTkLabel(
            self.info_frame,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#cdd6f4",
            wraplength=420,
            anchor="w"
        )
        self.title_label.grid(row=0, column=0, padx=12, pady=(10, 2), sticky="w")

        self.meta_label = ctk.CTkLabel(
            self.info_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#6c7086",
            anchor="w"
        )
        self.meta_label.grid(row=1, column=0, padx=12, pady=(0, 4), sticky="w")

        # Format dropdown
        ctk.CTkLabel(
            self.info_frame,
            text="Quality",
            font=ctk.CTkFont(size=11),
            text_color="#6c7086"
        ).grid(row=2, column=0, padx=12, sticky="w")

        self.format_var = ctk.StringVar(value="Best Quality (Auto)")
        self.format_dropdown = ctk.CTkOptionMenu(
            self.info_frame,
            variable=self.format_var,
            values=["Best Quality (Auto)"],
            fg_color="#313244",
            button_color="#45475a",
            button_hover_color="#585b70"
        )
        self.format_dropdown.grid(row=3, column=0, padx=12,
                                   pady=(2, 8), sticky="ew")

        # Audio only
        self.audio_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            self.info_frame,
            text="Audio Only (MP3)",
            variable=self.audio_var,
            checkbox_width=18,
            checkbox_height=18
        ).grid(row=4, column=0, padx=12, pady=(0, 10), sticky="w")

        # Save path
        ctk.CTkLabel(
            self, text="Save Location",
            font=ctk.CTkFont(size=12),
            text_color="#6c7086"
        ).grid(row=6, column=0, padx=20, pady=(4, 2), sticky="w")

        path_frame = ctk.CTkFrame(self, fg_color="transparent")
        path_frame.grid(row=7, column=0, padx=20, sticky="ew")
        path_frame.grid_columnconfigure(0, weight=1)

        default_dir = os.path.join(os.path.expanduser("~"),
                                    "Downloads", "PixelDownloader")
        self.path_entry = ctk.CTkEntry(
            path_frame,
            height=36,
            corner_radius=8,
            border_color="#45475a",
            fg_color="#1e1e2e"
        )
        self.path_entry.insert(0, default_dir)
        self.path_entry.grid(row=0, column=0, sticky="ew")

        ctk.CTkButton(
            path_frame,
            text="Browse",
            width=70,
            height=36,
            corner_radius=8,
            fg_color="#313244",
            hover_color="#45475a",
            command=self._browse_folder
        ).grid(row=0, column=1, padx=(6, 0))

        # Download button
        self.download_btn = ctk.CTkButton(
            self,
            text="⬇  Start Download",
            height=42,
            corner_radius=8,
            fg_color="#89b4fa",
            hover_color="#7aa2f7",
            text_color="#1a1a2e",
            font=ctk.CTkFont(size=14, weight="bold"),
            state="disabled",
            command=self._on_download
        )
        self.download_btn.grid(row=8, column=0, padx=20,
                                pady=(12, 16), sticky="ew")

    def _on_detect(self):
        url = self.url_entry.get().strip()
        if not url:
            self.status_label.configure(text="Please enter a URL first.")
            return

        self.detect_btn.configure(state="disabled", text="Fetching...")
        self.status_label.configure(text="Fetching video info...")

        def fetch():
            try:
                ext = VideoExtractor()
                info = ext.get_info(url)
                self.after(0, self._on_fetched, info)
            except Exception as e:
                self.after(0, self._on_fetch_failed, str(e))

        threading.Thread(target=fetch, daemon=True).start()

    def _on_fetched(self, info):
        self.detect_btn.configure(state="normal",
                                   text="🔍  Detect / Fetch Info")
        self.video_info = info
        self.formats = info.get("formats", [])

        self.title_label.configure(text=info.get("title", "Unknown"))
        dur = info.get("duration", 0)
        mins, secs = divmod(int(dur), 60)
        self.meta_label.configure(
            text=f"By {info.get('uploader','Unknown')} • {mins}:{secs:02d}"
        )

        options = ["Best Quality (Auto)"] + [
            f"{f['label']} — {f['ext'].upper()}" +
            (f" ({f['filesize']/1024/1024:.1f} MB)" if f.get("filesize") else "")
            for f in self.formats
        ]
        self.format_dropdown.configure(values=options)
        self.format_var.set("Best Quality (Auto)")

        self.info_frame.grid()
        self.download_btn.configure(state="normal")
        self.status_label.configure(text="✓ Info fetched. Choose quality and download.")

    def _on_fetch_failed(self, error):
        self.detect_btn.configure(state="normal",
                                   text="🔍  Detect / Fetch Info")
        self.video_info = None
        self.info_frame.grid_remove()
        self.download_btn.configure(state="normal")
        self.status_label.configure(
            text="Direct file download (not a video stream)."
        )

    def _browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, folder)

    def _on_download(self):
        url = self.url_entry.get().strip()
        if not url:
            return

        is_video = self.video_info is not None
        audio_only = self.audio_var.get() if is_video else False
        format_id = None

        if is_video and self.formats:
            selected = self.format_var.get()
            if selected != "Best Quality (Auto)":
                idx = self.format_dropdown.cget("values").index(selected) - 1
                if 0 <= idx < len(self.formats):
                    format_id = self.formats[idx]["format_id"]

        filename = None
        if not is_video:
            filename = url.split("/")[-1].split("?")[0] or "download"

        self.on_confirm(url, filename, is_video, audio_only, format_id)
        self.destroy()
