import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw
from gui.main_window import MainWindow
from engine.database import init_db
from server.api import start_server

class PixelDownloaderApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.pixelgalaxy.downloader")
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        init_db()
        self.win = MainWindow(app)
        start_server(
            self.win.queue,
            progress_callback=self.win._on_progress,
            new_download_callback=self.win._on_api_download
        )
        self.win.present()

def main():
    app = PixelDownloaderApp()
    app.run()

if __name__ == "__main__":
    main()
