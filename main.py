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
        # Init database
        init_db()

        # Create main window
        self.win = MainWindow(app)

        # Start local API server for browser extension
        start_server(self.win.queue)

        self.win.present()

def main():
    app = PixelDownloaderApp()
    app.run()

if __name__ == "__main__":
    main()
