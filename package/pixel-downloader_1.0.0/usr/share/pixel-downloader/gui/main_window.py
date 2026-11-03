import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gio
import asyncio
import threading
from engine.queue import DownloadQueue
from engine.database import get_all_downloads, delete_download
from gui.download_row import DownloadRow
from gui.add_dialog import AddDownloadDialog
from gui.settings_dialog import SettingsDialog, load_settings

class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("Pixel Downloader")
        self.set_default_size(900, 600)

        # Download queue
        self.queue = DownloadQueue(
            max_concurrent=3,
            progress_callback=self._on_progress
        )
        self.download_rows = {}

        # Start async loop in background thread
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

        self._build_ui()
        self._load_existing_downloads()

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.queue.start())

    def _build_ui(self):
        # Root layout
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(root)

        # Header bar
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(
            title="Pixel Downloader",
            subtitle="by Pixel & Galaxy Lab"
        ))

        # Add download button
        add_btn = Gtk.Button(label="  Add Download")
        add_btn.set_icon_name("list-add-symbolic")
        add_btn.add_css_class("suggested-action")
        add_btn.connect("clicked", self._on_add_clicked)
        header.pack_start(add_btn)

        # Clear completed button
        clear_btn = Gtk.Button()
        clear_btn.set_icon_name("edit-clear-symbolic")
        clear_btn.set_tooltip_text("Clear completed downloads")
        clear_btn.connect("clicked", self._on_clear_clicked)
        header.pack_end(clear_btn)

        # Settings button
        menu_btn = Gtk.Button()
        menu_btn.set_icon_name("open-menu-symbolic")
        menu_btn.set_tooltip_text("Settings")
        menu_btn.connect("clicked", self._on_settings_clicked)
        header.pack_end(menu_btn)

        root.append(header)

        # Toolbar / stats bar
        stats_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        stats_bar.set_margin_start(16)
        stats_bar.set_margin_end(16)
        stats_bar.set_margin_top(8)
        stats_bar.set_margin_bottom(8)

        self.stats_label = Gtk.Label(label="No downloads yet")
        self.stats_label.add_css_class("dim-label")
        stats_bar.append(self.stats_label)

        root.append(stats_bar)

        # Separator
        root.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # Scrollable download list
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list_box.add_css_class("boxed-list")
        self.list_box.set_margin_start(16)
        self.list_box.set_margin_end(16)
        self.list_box.set_margin_top(12)
        self.list_box.set_margin_bottom(12)

        # Empty state
        self.empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.empty_box.set_valign(Gtk.Align.CENTER)
        self.empty_box.set_halign(Gtk.Align.CENTER)
        self.empty_box.set_vexpand(True)

        empty_icon = Gtk.Image.new_from_icon_name("folder-download-symbolic")
        empty_icon.set_pixel_size(64)
        empty_icon.add_css_class("dim-label")

        empty_label = Gtk.Label(label="No downloads yet")
        empty_label.add_css_class("title-2")
        empty_label.add_css_class("dim-label")

        empty_sub = Gtk.Label(label="Click 'Add Download' to get started")
        empty_sub.add_css_class("dim-label")

        self.empty_box.append(empty_icon)
        self.empty_box.append(empty_label)
        self.empty_box.append(empty_sub)

        self.stack = Gtk.Stack()
        self.stack.add_named(self.empty_box, "empty")
        self.stack.add_named(scroll, "downloads")
        self.stack.set_visible_child_name("empty")

        scroll.set_child(self.list_box)
        root.append(self.stack)

        # Bottom status bar
        status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        status_bar.set_margin_start(16)
        status_bar.set_margin_end(16)
        status_bar.set_margin_top(6)
        status_bar.set_margin_bottom(6)

        self.status_label = Gtk.Label(label="Ready")
        self.status_label.add_css_class("dim-label")
        self.status_label.set_xalign(0)
        self.status_label.set_hexpand(True)

        status_bar.append(self.status_label)
        root.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        root.append(status_bar)

    def _load_existing_downloads(self):
        self.download_rows.clear()
        downloads = get_all_downloads()
        for dl in downloads:
            self._add_row(dl)
        self._update_stats()

    def _on_api_download(self, download_id):
        from engine.database import get_download
        if download_id not in self.download_rows:
            dl = get_download(download_id)
            if dl:
                self._add_row(dl)
                self._update_stats()

    def _add_row(self, download_data):
        row = DownloadRow(
            download_data=download_data,
            on_pause=self._on_pause,
            on_resume=self._on_resume,
            on_cancel=self._on_cancel,
            on_delete=self._on_delete,
        )
        self.download_rows[download_data["id"]] = row
        self.list_box.prepend(row)
        self.stack.set_visible_child_name("downloads")

    def _on_progress(self, download_id, downloaded, total, percent):
        GLib.idle_add(self._update_row_progress, download_id, downloaded, total, percent)

    def _update_row_progress(self, download_id, downloaded, total, percent):
        if download_id in self.download_rows:
            row = self.download_rows[download_id]
            row.update_progress(downloaded, total, percent)

            # Refresh filename from DB in case yt-dlp resolved it
            from engine.database import get_download
            dl = get_download(download_id)
            if dl:
                current = row.filename_label.get_label()
                if current in ("Fetching title...", "watch", "") and dl["filename"] not in ("Fetching title...", "watch", ""):
                    row.update_filename(dl["filename"])
                    row.save_path = dl["save_path"]
                if dl["status"] != row.status:
                    row.set_status(dl["status"])
        self._update_stats()

    def _update_stats(self):
        total = len(self.download_rows)
        active = self.queue.queue_size() + len(self.queue.get_active_ids())
        self.stats_label.set_text(f"{total} download(s) — {active} active")
        self.status_label.set_text(f"Queue: {self.queue.queue_size()} waiting | {len(self.queue.get_active_ids())} downloading")

    def _on_settings_clicked(self, btn):
        dialog = SettingsDialog(self, on_save=self._on_settings_saved)
        dialog.present()

    def _on_settings_saved(self, settings):
        from engine.downloader import ChunkDownloader
        import engine.downloader as dl_module
        # Apply new download dir
        dl_module.DOWNLOAD_DIR = settings["download_dir"]
        # Apply new concurrency
        self.queue.set_max_concurrent(settings["max_concurrent"])
        self.status_label.set_text(f"Settings saved — max {settings['max_concurrent']} concurrent, {settings['segments']} segments")

    def _on_add_clicked(self, btn):
        dialog = AddDownloadDialog(self, self._on_download_confirmed)
        dialog.present()

    def _on_download_confirmed(self, url, filename, is_video, audio_only, format_id):
        if is_video:
            def run():
                from engine.extractor import VideoExtractor
                ext = VideoExtractor(progress_callback=self._on_progress)
                try:
                    # Register in DB first so GUI can show it immediately
                    from engine.database import add_download, get_download
                    import os
                    from engine.downloader import DOWNLOAD_DIR
                    fname = (filename or url.split("/")[-1] or "video") + (".mp3" if audio_only else ".mp4")
                    save_path = os.path.join(DOWNLOAD_DIR, fname)
                    dl_id = add_download(url, fname, save_path, 0, 1)
                    ext.download_id = dl_id
                    GLib.idle_add(self._on_video_download_started, dl_id)
                    path = ext.download(url, format_id=format_id, audio_only=audio_only)
                except Exception as e:
                    print(f"[Extractor] Error: {e}")
            threading.Thread(target=run, daemon=True).start()
        else:
            downloader = self.queue.add(url=url, filename=filename)
            from engine.database import get_download
            GLib.idle_add(self._on_regular_download_started, downloader)

    def _on_video_download_started(self, download_id):
        from engine.database import get_download
        dl = get_download(download_id)
        if dl and download_id not in self.download_rows:
            self._add_row(dl)
            self._update_stats()

    def _on_regular_download_started(self, downloader):
        from engine.database import get_all_downloads
        downloads = get_all_downloads()
        if downloads:
            self._add_row(downloads[0])
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
            self.list_box.remove(row)
        if not self.download_rows:
            self.stack.set_visible_child_name("empty")
        self._update_stats()

    def _on_clear_clicked(self, btn):
        to_delete = []
        for dl_id, row in self.download_rows.items():
            if row.status in ("completed", "cancelled", "failed"):
                to_delete.append(dl_id)
        for dl_id in to_delete:
            self._on_delete(dl_id)
