import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib
import os
import json

SETTINGS_PATH = os.path.expanduser("~/.pixel-downloader/settings.json")

DEFAULT_SETTINGS = {
    "download_dir": os.path.expanduser("~/Downloads/PixelDownloader"),
    "max_concurrent": 3,
    "segments": 8,
    "auto_start": False,
    "notify_on_complete": True,
    "theme": "system",
}

def load_settings():
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH) as f:
                saved = json.load(f)
                return {**DEFAULT_SETTINGS, **saved}
        except:
            pass
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings, f, indent=2)

class SettingsDialog(Adw.Window):
    def __init__(self, parent, on_save=None):
        super().__init__()
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_title("Settings")
        self.set_default_size(480, 560)
        self.on_save = on_save
        self.settings = load_settings()
        self._build_ui()

    def _build_ui(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(root)

        # Header
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title="Settings"))

        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda _: self.close())
        header.pack_start(cancel_btn)

        save_btn = Gtk.Button(label="Save")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._on_save_clicked)
        header.pack_end(save_btn)

        root.append(header)

        # Scrollable content
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content.set_margin_start(20)
        content.set_margin_end(20)
        content.set_margin_top(16)
        content.set_margin_bottom(16)

        # ── Downloads ──────────────────────────────────────────
        dl_group = Adw.PreferencesGroup(title="Downloads")

        # Download folder
        folder_row = Adw.ActionRow(title="Download Folder")
        folder_row.set_subtitle(self.settings["download_dir"])
        self._folder_row = folder_row

        folder_btn = Gtk.Button(label="Change")
        folder_btn.set_valign(Gtk.Align.CENTER)
        folder_btn.add_css_class("flat")
        folder_btn.connect("clicked", self._on_choose_folder)
        folder_row.add_suffix(folder_btn)
        dl_group.add(folder_row)

        # Max concurrent downloads
        concurrent_row = Adw.ActionRow(title="Max Concurrent Downloads")
        concurrent_row.set_subtitle("How many files download at once")
        self._concurrent_spin = Gtk.SpinButton()
        self._concurrent_spin.set_range(1, 10)
        self._concurrent_spin.set_increments(1, 1)
        self._concurrent_spin.set_value(self.settings["max_concurrent"])
        self._concurrent_spin.set_valign(Gtk.Align.CENTER)
        concurrent_row.add_suffix(self._concurrent_spin)
        dl_group.add(concurrent_row)

        # Segments per download
        segments_row = Adw.ActionRow(title="Segments Per Download")
        segments_row.set_subtitle("More segments = faster downloads")
        self._segments_spin = Gtk.SpinButton()
        self._segments_spin.set_range(1, 32)
        self._segments_spin.set_increments(1, 4)
        self._segments_spin.set_value(self.settings["segments"])
        self._segments_spin.set_valign(Gtk.Align.CENTER)
        segments_row.add_suffix(self._segments_spin)
        dl_group.add(segments_row)

        content.append(dl_group)

        # ── Notifications ──────────────────────────────────────
        notif_group = Adw.PreferencesGroup(title="Notifications")

        notify_row = Adw.SwitchRow(title="Notify on Completion")
        notify_row.set_subtitle("Show desktop notification when download finishes")
        notify_row.set_active(self.settings["notify_on_complete"])
        self._notify_row = notify_row
        notif_group.add(notify_row)

        content.append(notif_group)

        # ── Appearance ─────────────────────────────────────────
        appear_group = Adw.PreferencesGroup(title="Appearance")

        theme_row = Adw.ActionRow(title="Theme")
        theme_row.set_subtitle("Choose app color scheme")

        self._theme_combo = Gtk.DropDown()
        theme_options = Gtk.StringList()
        theme_options.append("System Default")
        theme_options.append("Light")
        theme_options.append("Dark")
        self._theme_combo.set_model(theme_options)
        theme_map = {"system": 0, "light": 1, "dark": 2}
        self._theme_combo.set_selected(theme_map.get(self.settings["theme"], 0))
        self._theme_combo.set_valign(Gtk.Align.CENTER)
        theme_row.add_suffix(self._theme_combo)
        appear_group.add(theme_row)

        content.append(appear_group)

        # ── Startup ────────────────────────────────────────────
        startup_group = Adw.PreferencesGroup(title="Startup")

        autostart_row = Adw.SwitchRow(title="Start on Login")
        autostart_row.set_subtitle("Launch Pixel Downloader automatically on login")
        autostart_row.set_active(self.settings["auto_start"])
        self._autostart_row = autostart_row
        startup_group.add(autostart_row)

        content.append(startup_group)

        # ── About ──────────────────────────────────────────────
        about_group = Adw.PreferencesGroup(title="About")

        version_row = Adw.ActionRow(title="Pixel Downloader")
        version_row.set_subtitle("Version 1.0.0 • by Pixel & Galaxy Lab")
        version_row.add_prefix(Gtk.Image.new_from_icon_name("folder-download-symbolic"))

        github_btn = Gtk.Button(label="GitHub")
        github_btn.set_valign(Gtk.Align.CENTER)
        github_btn.add_css_class("flat")
        github_btn.connect("clicked", lambda _: self._open_url("https://github.com/Emmanuel17A/pixel-downloader"))
        version_row.add_suffix(github_btn)
        about_group.add(version_row)

        content.append(about_group)

        scroll.set_child(content)
        root.append(scroll)

    def _on_choose_folder(self, btn):
        dialog = Gtk.FileDialog()
        dialog.set_title("Choose Download Folder")
        dialog.select_folder(self, None, self._on_folder_chosen)

    def _on_folder_chosen(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                path = folder.get_path()
                self.settings["download_dir"] = path
                self._folder_row.set_subtitle(path)
        except Exception as e:
            print(f"[Settings] Folder pick cancelled: {e}")

    def _on_save_clicked(self, btn):
        self.settings["max_concurrent"] = int(self._concurrent_spin.get_value())
        self.settings["segments"] = int(self._segments_spin.get_value())
        self.settings["notify_on_complete"] = self._notify_row.get_active()
        self.settings["auto_start"] = self._autostart_row.get_active()

        theme_idx = self._theme_combo.get_selected()
        self.settings["theme"] = ["system", "light", "dark"][theme_idx]

        save_settings(self.settings)
        self._apply_theme(self.settings["theme"])
        self._apply_autostart(self.settings["auto_start"])

        if self.on_save:
            self.on_save(self.settings)

        self.close()

    def _apply_theme(self, theme):
        manager = Adw.StyleManager.get_default()
        theme_map = {
            "system": Adw.ColorScheme.DEFAULT,
            "light": Adw.ColorScheme.FORCE_LIGHT,
            "dark": Adw.ColorScheme.FORCE_DARK,
        }
        manager.set_color_scheme(theme_map.get(theme, Adw.ColorScheme.DEFAULT))

    def _apply_autostart(self, enabled):
        autostart_dir = os.path.expanduser("~/.config/autostart")
        autostart_file = os.path.join(autostart_dir, "pixel-downloader.desktop")
        if enabled:
            os.makedirs(autostart_dir, exist_ok=True)
            project_path = os.path.expanduser("~/Documents/Projects/pixel-downloader")
            with open(autostart_file, "w") as f:
                f.write(f"""[Desktop Entry]
Name=Pixel Downloader
Exec=python3 {project_path}/main.py
Type=Application
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
""")
        else:
            if os.path.exists(autostart_file):
                os.remove(autostart_file)

    def _open_url(self, url):
        import subprocess
        subprocess.Popen(["xdg-open", url])
