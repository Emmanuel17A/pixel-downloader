#!/bin/bash
set -e

echo "=================================="
echo "  Pixel Downloader Installer"
echo "  by Pixel & Galaxy Lab"
echo "=================================="
echo ""

# Check OS
if ! command -v apt &> /dev/null; then
  echo "ERROR: This installer requires a Debian/Ubuntu/Kali-based system."
  exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
  echo "ERROR: Python3 is required."
  exit 1
fi

INSTALL_DIR="$HOME/.pixel-downloader/app"
echo "Installing to: $INSTALL_DIR"
echo ""

# Install system dependencies
echo "[1/5] Installing system dependencies..."
sudo apt install -y \
  python3-gi \
  python3-gi-cairo \
  gir1.2-gtk-4.0 \
  gir1.2-adw-1 \
  ffmpeg \
  libnotify-bin \
  2>/dev/null

# Install Python dependencies
echo "[2/5] Installing Python dependencies..."
pip3 install \
  aiohttp \
  aiofiles \
  yt-dlp \
  requests \
  flask \
  flask-cors \
  Pillow \
  --break-system-packages \
  --quiet

# Clone or update repo
echo "[3/5] Downloading Pixel Downloader..."
if [ -d "$INSTALL_DIR" ]; then
  cd "$INSTALL_DIR" && git pull --quiet
else
  mkdir -p "$HOME/.pixel-downloader"
  git clone https://github.com/Emmanuel17A/pixel-downloader.git "$INSTALL_DIR" --quiet
fi

# Create launcher
echo "[4/5] Creating launcher..."
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/pixel-downloader" << 'LAUNCHER'
#!/bin/bash
cd "$HOME/.pixel-downloader/app"
exec python3 "$HOME/.pixel-downloader/app/main.py" "$@"
LAUNCHER
chmod +x "$HOME/.local/bin/pixel-downloader"

# Add to PATH if needed
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
  export PATH="$HOME/.local/bin:$PATH"
fi

# Desktop entry
echo "[5/5] Adding to app menu..."
mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/pixel-downloader.desktop" << DESKTOP
[Desktop Entry]
Name=Pixel Downloader
GenericName=Download Manager
Comment=Fast download manager by Pixel & Galaxy Lab
Exec=$HOME/.local/bin/pixel-downloader
Icon=folder-download
Terminal=false
Type=Application
Categories=Network;FileTransfer;
Keywords=download;video;youtube;idm;
StartupNotify=true
DESKTOP

update-desktop-database "$HOME/.local/share/applications/" 2>/dev/null || true

echo ""
echo "=================================="
echo "  Installation Complete!"
echo "=================================="
echo ""
echo "  Run it:       pixel-downloader"
echo "  App menu:     Search 'Pixel Downloader'"
echo ""
echo "  Browser Extension:"
echo "  1. Open Chrome → chrome://extensions"
echo "  2. Enable Developer Mode"
echo "  3. Load unpacked → $INSTALL_DIR/extension"
echo ""
echo "  Enjoy! — Pixel & Galaxy Lab"
echo "=================================="
