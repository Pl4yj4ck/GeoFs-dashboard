#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

read -r -p "Versione da includere nell'AppImage (es. 1.2.3): " APP_VERSION
if [[ ! "$APP_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?$ ]]; then
    echo "Versione non valida. Usa il formato 1.2.3 o 1.2.3-beta."
    exit 1
fi

if [[ "$(uname -m)" != "x86_64" ]]; then
    echo "La build AppImage supporta al momento Linux x86_64."
    exit 1
fi

if ! command -v appimagetool >/dev/null 2>&1; then
    echo "appimagetool non è installato o non è disponibile nel PATH."
    echo "Installalo da https://github.com/AppImage/AppImageKit/releases e rilancia lo script."
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 non è installato o non è disponibile nel PATH."
    exit 1
fi

if [[ ! -x ".venv-linux/bin/python" ]]; then
    python3 -m venv .venv-linux
fi

PYTHON=".venv-linux/bin/python"

if ! "$PYTHON" -c "import tkinter" >/dev/null 2>&1; then
    echo "Tkinter non è disponibile. Installa il pacchetto Tk del sistema (ad esempio python3-tk) e rilancia."
    exit 1
fi

printf '%s\n' "$APP_VERSION" > "app_version.txt"
trap 'rm -f app_version.txt' EXIT
echo "Installazione/verifica di PyInstaller..."
"$PYTHON" -m pip install --upgrade pyinstaller

echo "Creazione dell'applicazione Linux..."
"$PYTHON" -m PyInstaller \
    --noconfirm \
    --clean \
    --onefile \
    --windowed \
    --name GeoFS_Server \
    --add-data "dashboard.html:." \
    --add-data "app_version.txt:." \
    --add-data "icon/GeoFS_Server.ico:icon" \
    --add-data "icon/planefavicon.svg:icon" \
    --distpath "dist/linux" \
    server_gui.py

APP_DIR="build/appimage/GeoFS_Server.AppDir"
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR/usr/bin" "$APP_DIR/usr/share/icons/hicolor/scalable/apps"
cp "dist/linux/GeoFS_Server" "$APP_DIR/usr/bin/GeoFS_Server"
cp "icon/planecircolare.svg" "$APP_DIR/usr/share/icons/hicolor/scalable/apps/GeoFS_Server.svg"
cp "icon/planecircolare.svg" "$APP_DIR/.DirIcon"

cat > "$APP_DIR/AppRun" <<'EOF'
#!/usr/bin/env sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/GeoFS_Server" "$@"
EOF
chmod +x "$APP_DIR/AppRun"

cat > "$APP_DIR/GeoFS_Server.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=GeoFS Flight Server
Comment=Local dashboard and telemetry server for GeoFS
Exec=GeoFS_Server
Icon=GeoFS_Server
Categories=Utility;
Terminal=false
EOF

echo "Creazione dell'AppImage..."
ARCH=x86_64 appimagetool "$APP_DIR" "dist/GeoFS_Server-x86_64.AppImage"
chmod +x "dist/GeoFS_Server-x86_64.AppImage"

echo "Fatto: dist/GeoFS_Server-x86_64.AppImage"
