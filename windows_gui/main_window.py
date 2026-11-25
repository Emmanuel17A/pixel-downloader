import customtkinter as ctk
from tkinter import messagebox
import threading
import asyncio
from engine.queue import DownloadQueue
from engine.database import get_all_downloads, delete_download
from windows_gui.download_row import DownloadRow
from windows_gui.add_dialog import AddDownloadDialog
from windows_gui.settings_dialog import SettingsDialog

# Theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Pixel Downloader")
        self.geometry("900x620")
        self.minsize(700, 500)
        self.iconname("Pixel Downloader")

        # Download queue
        self.queue = DownloadQueue(
            max_concurrent=3,
            progress_callback=self._on_progress
        )
        self.download_rows = {}

        # Async loop in background thread
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

        self._build_ui()
        self._load_existing_downloads()

        # Poll for UI updates
        self._poll_updates()

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.queue.start())

    def _build_ui(self):
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ── Header ────────────────────────────────────────────
        header = ctk.CTkFrame(self, height=60, corner_radius=0,
                              fg_color=("#1a1a2e", "#1a1a2e"))
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        header.grid_propagate(False)

        # Logo + title
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.grid(row=0, column=0, padx=16, pady=8, sticky="w")

        ctk.CTkLabel(
            title_frame,
            text="⬇  Pixel Downloader",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#89b4fa"
        ).pack(side="left")

        ctk.CTkLabel(
            title_frame,
            text="  by Pixel & Galaxy Lab",
            font=ctk.CTkFont(size=11),
            text_color="#6c7086"
        ).pack(side="left", padx=(4, 0))

        # Header buttons
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.grid(row=0, column=2, padx=16, pady=8, sticky="e")

        ctk.CTkButton(
            btn_frame,
            text="+ Add Download",
            width=140,
            height=34,
            corner_radius=8,
            fg_color="#89b4fa",
            hover_color="#7aa2f7",
            text_color="#1a1a2e",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_add_clicked
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_frame,
            text="⚙",
            width=36,
            height=34,
            corner_radius=8,
            fg_color="#313244",
            hover_color="#45475a",
            command=self._on_settings_clicked
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            btn_frame,
            text="🗑",
            width=36,
            height=34,
            corner_radius=8,
            fg_color="#313244",
            hover_color="#45475a",
            command=self._on_clear_clicked
        ).pack(side="left")

        # ── Stats bar ─────────────────────────────────────────
        stats_bar = ctk.CTkFrame(self, height=36, corner_radius=0,
                                  fg_color=("#16213e", "#16213e"))
        stats_bar.grid(row=1, column=0, sticky="ew")
        stats_bar.grid_propagate(False)
        stats_bar.grid_columnconfigure(0, weight=1)

        self.stats_label = ctk.CTkLabel(
            stats_bar,
            text="No downloads yet",
            font=ctk.CTkFont(size=12),
            text_color="#6c7086"
        )
        self.stats_label.grid(row=0, column=0, padx=16, sticky="w")

        # ── Download list ─────────────────────────────────────
        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            corner_radius=0,
            fg_color=("#0f0f1a", "#0f0f1a"),
            scrollbar_button_color="#313244",
            scrollbar_button_hover_color="#45475a"
        )
        self.scroll_frame.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        # Empty state
        self.empty_frame = ctk.CTkFrame(
            self.scroll_frame,
            fg_color="transparent"
        )
        self.empty_frame.grid(row=0, column=0, pady=100)

        ctk.CTkLabel(
            self.empty_frame,
            text="⬇",
            font=ctk.CTkFont(size=48),
            text_color="#313244"
        ).pack()

        ctk.CTkLabel(
            self.empty_frame,
            text="No downloads yet",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#45475a"
        ).pack(pady=(8, 4))

        ctk.CTkLabel(
            self.empty_frame,
            text="Click '+ Add Download' or use the browser extension",
            font=ctk.CTkFont(size=12),
            text_color="#313244"
        ).pack()

        # ── Status bar ────────────────────────────────────────
        status_bar = ctk.CTkFrame(self, height=28, corner_radius=0,
                                   fg_color=("#1a1a2e", "#1a1a2e"))
        status_bar.grid(row=3, column=0, sticky="ew")
        status_bar.grid_propagate(False)

        self.status_label = ctk.CTkLabel(
            status_bar,
            text="Ready",
            font=ctk.CTkFont(size=11),
            text_color="#6c7086"
        )
        self.status_label.grid(row=0, column=0, padx=16, sticky="w")

    def _load_existing_downloads(self):
        downloads = get_all_downloads()
        for dl in downloads:
            self._add_row(dl)
        self._update_stats()

    def _add_row(self, download_data):
        if download_data["id"] in self.download_rows:
            return
        if self.empty_frame.winfo_ismapped():
            self.empty_frame.grid_forget()

        row_num = len(self.download_rows)
        row = DownloadRow(
            master=self.scroll_frame,
            download_data=download_data,
            on_pause=self._on_pause,
            on_resume=self._on_resume,
            on_cancel=self._on_cancel,
            on_delete=self._on_delete,
        )
        row.grid(row=row_num, column=0, sticky="ew",
                 padx=12, pady=(8, 0))
        self.download_rows[download_data["id"]] = row

    def _on_progress(self, download_id, downloaded, total, percent):
        self.after(0, self._update_row_progress,
                   download_id, downloaded, total, percent)

    def _update_row_progress(self, download_id, downloaded, total, percent):
        if download_id in self.download_rows:
            row = self.download_rows[download_id]
            row.update_progress(downloaded, total, percent)

            from engine.database import get_download
            dl = get_download(download_id)
            if dl:
                current = row.filename_var.get()
                if current in ("Fetching title...", "watch", "") \
                        and dl["filename"] not in ("Fetching title...", "watch", ""):
                    row.filename_var.set(dl["filename"])
                    row.save_path = dl["save_path"]
                if dl["status"] != row.status:
                    row.set_status(dl["status"])
        self._update_stats()

    def _update_stats(self):
        total = len(self.download_rows)
        active = len(self.queue.get_active_ids())
        queued = self.queue.queue_size()
        self.stats_label.configure(
            text=f"{total} download(s) — {active} active"
        )
        self.status_label.configure(
            text=f"Queue: {queued} waiting | {active} downloading"
        )

    def _on_add_clicked(self):
        dialog = AddDownloadDialog(self, self._on_download_confirmed)
        dialog.grab_set()

    def _on_download_confirmed(self, url, filename, is_video, audio_only, format_id):
        if is_video:
            def run():
                from engine.extractor import VideoExtractor
                ext = VideoExtractor(progress_callback=self._on_progress)
                try:
                    from engine.database import add_download, update_download
                    from engine.downloader import DOWNLOAD_DIR
                    import os
                    fname = "Fetching title..."
                    save_path = os.path.join(DOWNLOAD_DIR, fname)
                    dl_id = add_download(url, fname, save_path, 0, 1)
                    ext.download_id = dl_id
                    update_download(dl_id, status="downloading")
                    self.after(0, self._on_api_download, dl_id)
                    ext.download(url, format_id=format_id, audio_only=audio_only)
                except Exception as e:
                    print(f"[Extractor] Error: {e}")
            threading.Thread(target=run, daemon=True).start()
        else:
            self.queue.add(url=url, filename=filename)
            def notify():
                import time
                time.sleep(0.5)
                from engine.database import get_all_downloads
                downloads = get_all_downloads()
                if downloads:
                    self.after(0, self._on_api_download, downloads[0]["id"])
            threading.Thread(target=notify, daemon=True).start()

    def _on_api_download(self, download_id):
        from engine.database import get_download
        dl = get_download(download_id)
        if dl and download_id not in self.download_rows:
            self._add_row(dl)
            self._update_stats()

    def _on_pause(self, download_id):
        self.queue.pause(download_id)
        if download_id in self.download_rows:
            self.download_rows[download_id].set_status("paused")

    def _on_resume(self, download_id):
        self.queue.resume(download_id)
        if download_id in self.download_rows:
            self.download_rows[download_id].set_status("downloading")

    def _on_cancel(self, download_id):
        self.queue.cancel(download_id)
        if download_id in self.download_rows:
            self.download_rows[download_id].set_status("cancelled")

    def _on_delete(self, download_id):
        delete_download(download_id)
        if download_id in self.download_rows:
            row = self.download_rows.pop(download_id)
            row.destroy()
        if not self.download_rows:
            self.empty_frame.grid(row=0, column=0, pady=100)
        self._update_stats()

    def _on_clear_clicked(self):
        to_delete = [
            dl_id for dl_id, row in self.download_rows.items()
            if row.status in ("completed", "cancelled", "failed")
        ]
        for dl_id in to_delete:
            self._on_delete(dl_id)

    def _on_settings_clicked(self):
        dialog = SettingsDialog(self, on_save=self._on_settings_saved)
        dialog.grab_set()

    def _on_settings_saved(self, settings):
        import engine.downloader as dl_module
        dl_module.DOWNLOAD_DIR = settings["download_dir"]
        self.queue.set_max_concurrent(settings["max_concurrent"])

    def _poll_updates(self):
        self._update_stats()
        self.after(2000, self._poll_updates)
