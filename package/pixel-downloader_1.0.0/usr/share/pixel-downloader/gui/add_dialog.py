import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib
import threading
import os
from engine.extractor import VideoExtractor

class AddDownloadDialog(Adw.Window):
    def __init__(self, parent, on_confirm):
        super().__init__()
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_title("Add Download")
        self.set_default_size(520, 420)
        self.on_confirm = on_confirm
        self.video_info = None
        self.formats = []
        self._build_ui()

    def _build_ui(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(root)

        # Header
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title="Add Download"))
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda _: self.close())
        header.pack_start(cancel_btn)
        root.append(header)

        # Scrollable content
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_start(20)
        content.set_margin_end(20)
        content.set_margin_top(16)
        content.set_margin_bottom(16)

        # URL entry group
        url_group = Adw.PreferencesGroup(title="Download URL")
        url_row = Adw.EntryRow(title="Paste URL here")
        self.url_entry = url_row
        url_group.add(url_row)
        content.append(url_group)

        # Detect button
        self.detect_btn = Gtk.Button(label="Detect / Fetch Info")
        self.detect_btn.add_css_class("suggested-action")
        self.detect_btn.set_margin_top(4)
        self.detect_btn.connect("clicked", self._on_detect_clicked)
        content.append(self.detect_btn)

        # Spinner
        self.spinner = Gtk.Spinner()
        self.spinner.set_visible(False)
        content.append(self.spinner)

        # Video info card (hidden until detected)
        self.info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.info_box.set_visible(False)

        # Thumbnail + title row
        media_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        self.thumb_image = Gtk.Image()
        self.thumb_image.set_pixel_size(80)
        self.thumb_image.set_icon_name("video-x-generic-symbolic")
        media_row.append(self.thumb_image)

        meta_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        meta_box.set_hexpand(True)

        self.title_label = Gtk.Label(label="")
        self.title_label.set_xalign(0)
        self.title_label.add_css_class("heading")
        self.title_label.set_wrap(True)

        self.uploader_label = Gtk.Label(label="")
        self.uploader_label.set_xalign(0)
        self.uploader_label.add_css_class("dim-label")

        self.duration_label = Gtk.Label(label="")
        self.duration_label.set_xalign(0)
        self.duration_label.add_css_class("dim-label")
        self.duration_label.add_css_class("caption")

        meta_box.append(self.title_label)
        meta_box.append(self.uploader_label)
        meta_box.append(self.duration_label)
        media_row.append(meta_box)
        self.info_box.append(media_row)

        # Format selection group
        format_group = Adw.PreferencesGroup(title="Quality / Format")

        self.format_row = Adw.ComboRow(title="Select quality")
        self.format_model = Gtk.StringList()
        self.format_row.set_model(self.format_model)
        format_group.add(self.format_row)

        # Audio only toggle
        self.audio_row = Adw.SwitchRow(title="Audio Only (MP3)")
        format_group.add(self.audio_row)

        self.info_box.append(format_group)
        content.append(self.info_box)

        # Save path group
        path_group = Adw.PreferencesGroup(title="Save Location")
        path_row = Adw.EntryRow(title="Save path")
        self.path_entry = path_row
        self.path_entry.set_text(
            os.path.expanduser("~/Downloads/PixelDownloader")
        )
        path_group.add(path_row)
        content.append(path_group)

        # Status label
        self.status_label = Gtk.Label(label="")
        self.status_label.add_css_class("dim-label")
        self.status_label.add_css_class("caption")
        content.append(self.status_label)

        scroll.set_child(content)
        root.append(scroll)

        # Bottom download button
        bottom_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        bottom_bar.set_margin_start(20)
        bottom_bar.set_margin_end(20)
        bottom_bar.set_margin_top(8)
        bottom_bar.set_margin_bottom(16)

        self.download_btn = Gtk.Button(label="Start Download")
        self.download_btn.add_css_class("suggested-action")
        self.download_btn.set_hexpand(True)
        self.download_btn.set_sensitive(False)
        self.download_btn.connect("clicked", self._on_download_clicked)
        bottom_bar.append(self.download_btn)

        root.append(bottom_bar)

    def _on_detect_clicked(self, btn):
        url = self.url_entry.get_text().strip()
        if not url:
            self.status_label.set_label("Please enter a URL first.")
            return

        self.detect_btn.set_sensitive(False)
        self.spinner.set_visible(True)
        self.spinner.start()
        self.status_label.set_label("Fetching info...")
        self.info_box.set_visible(False)
        self.download_btn.set_sensitive(False)

        def fetch():
            try:
                ext = VideoExtractor()
                info = ext.get_info(url)
                GLib.idle_add(self._on_info_fetched, info)
            except Exception as e:
                GLib.idle_add(self._on_fetch_failed, str(e))

        threading.Thread(target=fetch, daemon=True).start()

    def _on_info_fetched(self, info):
        self.spinner.stop()
        self.spinner.set_visible(False)
        self.detect_btn.set_sensitive(True)
        self.video_info = info
        self.formats = info.get("formats", [])

        # Populate UI
        self.title_label.set_label(info.get("title", "Unknown"))
        self.uploader_label.set_label(f"By {info.get('uploader', 'Unknown')}")

        duration = info.get("duration", 0)
        mins, secs = divmod(int(duration), 60)
        self.duration_label.set_label(f"Duration: {mins}:{secs:02d}")

        # Populate formats dropdown
        while self.format_model.get_n_items() > 0:
            self.format_model.remove(0)

        self.format_model.append("Best Quality (Auto)")
        for fmt in self.formats:
            label = f"{fmt['label']} — {fmt['ext'].upper()}"
            if fmt.get("filesize"):
                size_mb = fmt["filesize"] / 1024 / 1024
                label += f" ({size_mb:.1f} MB)"
            self.format_model.append(label)

        self.format_row.set_selected(0)
        self.info_box.set_visible(True)
        self.download_btn.set_sensitive(True)
        self.status_label.set_label("✓ Info fetched. Choose quality and download.")

    def _on_fetch_failed(self, error):
        self.spinner.stop()
        self.spinner.set_visible(False)
        self.detect_btn.set_sensitive(True)

        # Not a video URL — treat as regular file download
        self.status_label.set_label("Direct file download (not a video stream).")
        self.download_btn.set_sensitive(True)
        self.video_info = None

    def _on_download_clicked(self, btn):
        url = self.url_entry.get_text().strip()
        if not url:
            return

        save_path = self.path_entry.get_text().strip()
        is_video = self.video_info is not None
        audio_only = self.audio_row.get_active() if is_video else False
        format_id = None

        if is_video and self.formats:
            idx = self.format_row.get_selected()
            if idx > 0 and idx - 1 < len(self.formats):
                format_id = self.formats[idx - 1]["format_id"]

        filename = None
        if not is_video:
            filename = url.split("/")[-1].split("?")[0] or "download"

        self.on_confirm(url, filename, is_video, audio_only, format_id)
        self.close()
