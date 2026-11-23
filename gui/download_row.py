import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib
import os

def format_size(bytes_val):
    if bytes_val <= 0:
        return "Unknown"
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} TB"

def format_speed(bps):
    return format_size(bps) + "/s"

class DownloadRow(Gtk.ListBoxRow):
    def __init__(self, download_data, on_pause, on_resume, on_cancel, on_delete):
        super().__init__()
        self.download_id = download_data["id"]
        self.status = download_data.get("status", "queued")
        self.on_pause = on_pause
        self.on_resume = on_resume
        self.on_cancel = on_cancel
        self.on_delete = on_delete
        self._last_downloaded = 0
        self._last_time = GLib.get_monotonic_time()
        self._speed = 0

        self.add_css_class("activatable")
        self.save_path = download_data.get("save_path", "")
        self._build_ui(download_data)
        self._setup_right_click()

    def _build_ui(self, data):
        # Outer box with padding
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        outer.set_margin_start(12)
        outer.set_margin_end(12)
        outer.set_margin_top(10)
        outer.set_margin_bottom(10)
        self.set_child(outer)

        # Top row — filename + status badge + action buttons
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        # File icon
        icon_name = self._get_icon(data["filename"])
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(32)
        top_row.append(icon)

        # Filename + URL
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_box.set_hexpand(True)

        self.filename_label = Gtk.Label(label=data["filename"])
        self.filename_label.set_xalign(0)
        self.filename_label.add_css_class("heading")
        self.filename_label.set_ellipsize(3)  # PANGO_ELLIPSIZE_END

        self.url_label = Gtk.Label(label=data["url"])
        self.url_label.set_xalign(0)
        self.url_label.add_css_class("dim-label")
        self.url_label.add_css_class("caption")
        self.url_label.set_ellipsize(3)

        info_box.append(self.filename_label)
        info_box.append(self.url_label)
        top_row.append(info_box)

        # Status badge
        self.badge = Gtk.Label(label=self.status.upper())
        self.badge.set_size_request(90, -1)
        self._apply_badge_style(self.status)
        top_row.append(self.badge)

        # Action buttons box
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        # Pause button
        self.pause_btn = Gtk.Button()
        self.pause_btn.set_icon_name("media-playback-pause-symbolic")
        self.pause_btn.set_tooltip_text("Pause")
        self.pause_btn.add_css_class("flat")
        self.pause_btn.connect("clicked", lambda _: self.on_pause(self.download_id))

        # Resume button
        self.resume_btn = Gtk.Button()
        self.resume_btn.set_icon_name("media-playback-start-symbolic")
        self.resume_btn.set_tooltip_text("Resume")
        self.resume_btn.add_css_class("flat")
        self.resume_btn.connect("clicked", lambda _: self.on_resume(self.download_id))

        # Cancel button
        self.cancel_btn = Gtk.Button()
        self.cancel_btn.set_icon_name("process-stop-symbolic")
        self.cancel_btn.set_tooltip_text("Cancel")
        self.cancel_btn.add_css_class("flat")
        self.cancel_btn.connect("clicked", lambda _: self.on_cancel(self.download_id))

        # Delete button
        self.delete_btn = Gtk.Button()
        self.delete_btn.set_icon_name("edit-delete-symbolic")
        self.delete_btn.set_tooltip_text("Delete")
        self.delete_btn.add_css_class("flat")
        self.delete_btn.add_css_class("destructive-action")
        self.delete_btn.connect("clicked", lambda _: self.on_delete(self.download_id))

        btn_box.append(self.pause_btn)
        btn_box.append(self.resume_btn)
        btn_box.append(self.cancel_btn)
        btn_box.append(self.delete_btn)
        top_row.append(btn_box)

        outer.append(top_row)

        # Progress bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_fraction(0)
        self.progress_bar.set_show_text(False)
        outer.append(self.progress_bar)

        # Bottom row — size info + speed + percent
        bottom_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        self.size_label = Gtk.Label(label="Waiting...")
        self.size_label.set_xalign(0)
        self.size_label.add_css_class("dim-label")
        self.size_label.add_css_class("caption")
        self.size_label.set_hexpand(True)

        self.speed_label = Gtk.Label(label="")
        self.speed_label.add_css_class("dim-label")
        self.speed_label.add_css_class("caption")

        self.percent_label = Gtk.Label(label="0%")
        self.percent_label.add_css_class("caption")

        bottom_row.append(self.size_label)
        bottom_row.append(self.speed_label)
        bottom_row.append(self.percent_label)
        outer.append(bottom_row)

        # Set initial button visibility
        self._update_buttons()
        # Restore correct progress state from DB data
        self._restore_state(data)

    def _restore_state(self, data):
        status = data.get("status", "queued")
        downloaded = data.get("downloaded", 0)
        total = data.get("total_size", 0)
        save_path = data.get("save_path", "")

        if status == "completed":
            self.progress_bar.set_fraction(1.0)
            self.percent_label.set_label("100%")
            self.speed_label.set_label("")
            # Get real file size from disk if available
            real_size = downloaded
            if save_path and os.path.exists(save_path):
                real_size = os.path.getsize(save_path)
            self.size_label.set_label(
                f"Done — {format_size(real_size)}" if real_size > 0 else "Completed"
            )
        elif status == "failed":
            self.progress_bar.set_fraction(0.0)
            self.percent_label.set_label("0%")
            self.speed_label.set_label("")
            self.size_label.set_label("Failed — delete and retry")
        elif status == "queued":
            self.size_label.set_label("Waiting to start...")
        elif status == "paused":
            if total > 0:
                self.size_label.set_label(f"Paused — {format_size(total)} total")
            else:
                self.size_label.set_label("Paused")

    def _get_icon(self, filename):
        ext = os.path.splitext(filename)[-1].lower()
        icons = {
            ".mp4": "video-x-generic-symbolic",
            ".mkv": "video-x-generic-symbolic",
            ".webm": "video-x-generic-symbolic",
            ".mp3": "audio-x-generic-symbolic",
            ".m4a": "audio-x-generic-symbolic",
            ".zip": "package-x-generic-symbolic",
            ".tar": "package-x-generic-symbolic",
            ".gz":  "package-x-generic-symbolic",
            ".pdf": "x-office-document-symbolic",
            ".iso": "media-optical-symbolic",
        }
        return icons.get(ext, "text-x-generic-symbolic")

    def _apply_badge_style(self, status):
        for cls in ["success", "warning", "error", "accent"]:
            self.badge.remove_css_class(cls)
        style_map = {
            "completed": "success",
            "downloading": "accent",
            "paused": "warning",
            "failed": "error",
            "cancelled": "error",
            "queued": "warning",
        }
        css = style_map.get(status, "")
        if css:
            self.badge.add_css_class(css)
        self.badge.set_label(status.upper())

    def _update_buttons(self):
        is_active = self.status == "downloading"
        is_paused = self.status == "paused"
        is_done = self.status in ("completed", "cancelled", "failed")

        self.pause_btn.set_visible(is_active)
        self.resume_btn.set_visible(is_paused)
        self.cancel_btn.set_visible(is_active or is_paused)
        self.delete_btn.set_visible(is_done or self.status == "queued")

        # Show delete with tooltip hint for failed
        if self.status == "failed":
            self.delete_btn.set_tooltip_text("Delete and retry manually")

    def update_progress(self, downloaded, total, percent):
        now = GLib.get_monotonic_time()
        elapsed = (now - self._last_time) / 1_000_000
        if elapsed > 0.5:
            self._speed = (downloaded - self._last_downloaded) / elapsed
            self._last_downloaded = downloaded
            self._last_time = now

        self.progress_bar.set_fraction(min(percent / 100, 1.0))
        self.percent_label.set_label(f"{percent:.1f}%")
        self.speed_label.set_label(format_speed(self._speed) if self._speed > 0 else "")

        if total > 0:
            self.size_label.set_label(
                f"{format_size(downloaded)} of {format_size(total)}"
            )
        else:
            self.size_label.set_label(f"{format_size(downloaded)}")

        if percent >= 100:
            self.set_status("completed")

    def set_status(self, status):
        self.status = status
        self._apply_badge_style(status)
        self._update_buttons()
        if status == "completed":
            self.progress_bar.set_fraction(1.0)
            self.percent_label.set_label("100%")
            self.speed_label.set_label("")
            self.size_label.set_label("Completed")

    def update_filename(self, filename):
        self.filename_label.set_label(filename)

    def _setup_right_click(self):
        gesture = Gtk.GestureClick()
        gesture.set_button(3)  # Right click
        gesture.connect("pressed", self._on_right_click)
        self.add_controller(gesture)

    def _on_right_click(self, gesture, n_press, x, y):
        menu = Gtk.Popover()
        menu.set_parent(self)
        menu.set_has_arrow(False)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_margin_start(8)
        box.set_margin_end(8)
        box.set_margin_top(6)
        box.set_margin_bottom(6)

        open_btn = Gtk.Button(label="  Open File")
        open_btn.set_icon_name("document-open-symbolic")
        open_btn.add_css_class("flat")
        open_btn.connect("clicked", lambda _: self._open_file(menu))

        folder_btn = Gtk.Button(label="  Open Folder")
        folder_btn.set_icon_name("folder-open-symbolic")
        folder_btn.add_css_class("flat")
        folder_btn.connect("clicked", lambda _: self._open_folder(menu))

        copy_btn = Gtk.Button(label="  Copy URL")
        copy_btn.set_icon_name("edit-copy-symbolic")
        copy_btn.add_css_class("flat")
        copy_btn.connect("clicked", lambda _: self._copy_url(menu))

        box.append(open_btn)
        box.append(folder_btn)
        box.append(copy_btn)

        menu.set_child(box)

        rect = self.get_allocation()
        from gi.repository import Gdk
        r = Gdk.Rectangle()
        r.x, r.y, r.width, r.height = int(x), int(y), 1, 1
        menu.set_pointing_to(r)
        menu.popup()

    def _open_file(self, menu):
        menu.popdown()
        import subprocess, os
        if self.save_path and os.path.exists(self.save_path):
            subprocess.Popen(["xdg-open", self.save_path])

    def _open_folder(self, menu):
        menu.popdown()
        import subprocess, os
        folder = os.path.dirname(self.save_path)
        if folder and os.path.exists(folder):
            subprocess.Popen(["xdg-open", folder])

    def _copy_url(self, menu):
        menu.popdown()
        from gi.repository import Gdk, GLib
        clipboard = self.get_clipboard()
        clipboard.set(self.url_label.get_text())
