import sys
import os

# Windows: set download dir to user Downloads folder
if sys.platform == "win32":
    import engine.downloader as dl_module
    dl_module.DOWNLOAD_DIR = os.path.join(
        os.path.expanduser("~"), "Downloads", "PixelDownloader"
    )

from engine.database import init_db
from server.api import start_server
from windows_gui.main_window import MainWindow

def main():
    init_db()
    app = MainWindow()

    # Start API server for browser extension
    start_server(
        app.queue,
        progress_callback=app._on_progress,
        new_download_callback=app._on_api_download
    )

    app.mainloop()

if __name__ == "__main__":
    main()
